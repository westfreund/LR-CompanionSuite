"""Picking up after a run that was cut short.

A run is a sequence: stage the catalog, move the files, commit. If the process
dies partway -- a crash, a pulled cable, a terminal window closed -- the
built-in rollback never gets to run, and the library is left between two
states. The journal records every step, so what actually happened is knowable;
this module reads it, says so plainly, and finishes the job.

Which direction "finishing" means depends on where it stopped, and the order of
the run decides it:

* **Before the catalog was committed.** SQLite discarded the staged transaction
  when the process died, so the catalog still describes the old layout while
  some files already sit at their new paths. The only consistent destination is
  backwards: put the files back. This is what the automatic rollback would have
  done.
* **After the catalog was committed.** Catalog and files agree; the run was
  effectively complete and only its bookkeeping is missing. Nothing moves.
* **A reversal that was itself cut short.** Undo restores the catalog last, so
  it is still describing the new layout while files are going back. Finishing
  means continuing the reversal, which is safe to repeat: a file is only moved
  when it is still at the place it is being moved from.

Nothing here guesses. Every decision is taken from the journal and from what is
on disk right now.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from .journal import read_journal
from .logging_setup import get_logger, step

log = get_logger("resume")

#: The run finished, one way or another. Nothing to do.
COMPLETE = "complete"
#: Interrupted before the catalog was committed: the files must go back.
NEEDS_REVERT = "needs-revert"
#: Interrupted after the commit: catalog and files agree, records incomplete.
NEEDS_RECORD = "needs-record"
#: A reversal was interrupted: continue it.
NEEDS_UNDO = "needs-undo"


@dataclass
class Interruption:
    """What a journal says about a run that did not finish."""

    state: str
    journal_path: str
    catalog: str = ""
    backup_path: Optional[str] = None
    #: Moves whose file currently sits at its target. On its own this says
    #: nothing about what should happen: after a committed run it is the normal
    #: state. Use :attr:`to_revert`, which is empty unless reverting is right.
    at_target: List[Tuple[str, str]] = field(default_factory=list)
    #: Moves already back where they started.
    already_back: int = 0
    #: Directories the run created, deepest first.
    created: List[str] = field(default_factory=list)

    @property
    def needs_work(self) -> bool:
        return self.state != COMPLETE

    @property
    def to_revert(self) -> List[Tuple[str, str]]:
        """Files that genuinely belong back where they came from.

        Only when the run stopped before the catalog was committed. After the
        commit the catalog describes the new layout, and moving the files back
        would break the very agreement the run established.
        """
        return self.at_target if self.state == NEEDS_REVERT else []

    def describe(self, language: str = "en") -> str:
        if language == "de":
            texts = {
                COMPLETE: "Der Lauf ist abgeschlossen; nichts zu tun.",
                NEEDS_REVERT: (
                    "Abgebrochen, bevor der Katalog festgeschrieben wurde. Der Katalog "
                    "beschreibt noch den alten Stand, {n} Datei(en) liegen aber schon am "
                    "neuen Ort. Sie gehören zurück."
                ),
                NEEDS_RECORD: (
                    "Abgebrochen, nachdem der Katalog festgeschrieben war. Katalog und "
                    "Dateien stimmen überein; nur die Aufzeichnung ist unvollständig."
                ),
                NEEDS_UNDO: (
                    "Eine Rücknahme wurde abgebrochen. {n} Datei(en) stehen noch aus, "
                    "und der Katalog ist noch nicht zurückgespielt."
                ),
            }
        else:
            texts = {
                COMPLETE: "The run finished; there is nothing to do.",
                NEEDS_REVERT: (
                    "Interrupted before the catalog was committed. The catalog still "
                    "describes the old layout, but {n} file(s) already sit at their new "
                    "paths. They belong back."
                ),
                NEEDS_RECORD: (
                    "Interrupted after the catalog was committed. Catalog and files "
                    "agree; only the record is incomplete."
                ),
                NEEDS_UNDO: (
                    "A reversal was interrupted. {n} file(s) are still to go back, and "
                    "the catalog has not been restored yet."
                ),
            }
        return texts[self.state].format(n=len(self.to_revert))


def inspect(journal_path: str | Path) -> Interruption:
    """Read *journal_path* and work out what state its run is in."""
    records = read_journal(journal_path)
    events = [r.get("event") for r in records]
    found = Interruption(state=COMPLETE, journal_path=str(journal_path))

    for record in records:
        if record.get("event") == "run-start":
            found.catalog = record.get("catalog", "") or found.catalog
        elif record.get("event") == "backup":
            found.backup_path = record.get("target")
            found.catalog = found.catalog or record.get("source", "")
        elif record.get("event") == "mkdir" and record.get("path"):
            found.created.append(record["path"])

    committed = "catalog-commit" in events
    ended = "run-end" in events

    # What is where, right now.
    for record in records:
        if record.get("event") != "move-begin":
            continue
        source, target = record.get("source"), record.get("target")
        if not source or not target:
            continue
        if os.path.exists(target) and not os.path.exists(source):
            found.at_target.append((source, target))
        elif os.path.exists(source):
            found.already_back += 1

    if not committed:
        # The catalog was never written, so the files are the only thing out of
        # place. That holds whether or not the built-in rollback got to run.
        found.state = NEEDS_REVERT if found.at_target else COMPLETE
    elif not ended:
        found.state = NEEDS_RECORD
    else:
        # A completed run. If files have started going back, a reversal was cut
        # short -- undo restores the catalog last, so it never got that far.
        found.state = NEEDS_UNDO if found.already_back and found.at_target else COMPLETE

    log.info(
        "Journal %s: state=%s, %d to move back, %d already back",
        journal_path,
        found.state,
        len(found.at_target),
        found.already_back,
    )
    return found


def find_interruptions(catalog: Path) -> List[Interruption]:
    """Every recorded run of *catalog* that did not finish cleanly."""
    from .runs import history, journal_of

    out = []
    for record in history(catalog):
        journal = journal_of(record)
        if not journal.exists():
            continue
        found = inspect(journal)
        if found.needs_work:
            out.append(found)
    return out


def revert_files(found: Interruption) -> Tuple[int, List[str]]:
    """Put back every file the interrupted run had already moved.

    Newest first, and never onto something that is already there: a file is
    moved only while its origin is still free, so running this twice is safe.
    Does nothing unless reverting is the right direction -- see
    :attr:`Interruption.to_revert`.
    """
    restored, errors = 0, []
    for source, target in reversed(found.to_revert):
        try:
            if not os.path.exists(target) or os.path.exists(source):
                continue
            Path(source).parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, source)
            restored += 1
        except OSError as error:
            errors.append("{t}: {e}".format(t=target, e=error))
    step("Put %d file(s) back", restored)
    return restored, errors


def remove_created_directories(found: Interruption) -> int:
    """Remove the directories the run made, deepest first, if empty."""
    removed = 0
    for directory in sorted(found.created, key=lambda d: len(Path(d).parts), reverse=True):
        try:
            path = Path(directory)
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                removed += 1
        except OSError as error:  # pragma: no cover - best effort
            log.debug("Kept %s: %s", directory, error)
    return removed
