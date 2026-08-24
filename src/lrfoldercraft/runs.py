"""One folder per run, kept beside the catalog it belongs to.

Everything a run leaves behind used to be scattered: the journal and the
catalog backup in the user's configuration directory, the move log beside the
library, the settings nowhere at all. With one catalog that is merely untidy.
With several catalogs on several external drives it is a hazard -- the journals
of two libraries sit in the same directory under similar names, and undoing the
wrong one puts a library back to a state it was never in.

So a run writes its record where it belongs:

    <catalog folder>/LR-FolderCraft/2026-08-23_165247/
        run.json        what was done, how much of it, and whether it was undone
        settings.json   every option the run used, loadable as a profile
        journal.jsonl   the machine readable record undo works from
        moves.log       the same thing in prose, for a person

The catalog backup deliberately stays out of it. A 700 MB copy beside the
original, on the same drive, protects against a mistake but not against the
drive -- so it keeps going to the configuration directory, and ``run.json``
records where. Set ``backup_dir`` to the catalog folder if portability matters
more to you than surviving a dead disk.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logging_setup import get_logger

log = get_logger("runs")

#: The directory a catalog's run records live in, beside the catalog itself.
RUNS_DIRECTORY = "LR-FolderCraft"

RUN_FILE = "run.json"
SETTINGS_FILE = "settings.json"
JOURNAL_FILE = "journal.jsonl"
MOVE_LOG_FILE = "moves.log"

#: Bumped when a stored record changes shape.
RECORD_VERSION = 1


@dataclass
class RunRecord:
    """What one run did, and whether it still stands."""

    stamp: str
    catalog: str
    started_at: str = ""
    finished_at: str = ""
    tool_version: str = ""
    structure: str = ""
    placement: str = ""
    target_roots: List[str] = field(default_factory=list)
    files_moved: int = 0
    folders_created: int = 0
    orphans_moved: int = 0
    bytes_moved: int = 0
    backup_path: Optional[str] = None
    success: bool = False
    #: Set when an interrupted run has been put back by `resume`. Without it
    #: the run is judged from the paths alone, and a later run into the same
    #: target recreates them -- so a run settled hours ago is reported again.
    repaired_at: Optional[str] = None
    #: Set when a reversal begins. A reversal cut short leaves this set and
    #: :attr:`undone_at` empty, which is the only reliable way to tell -- two
    #: runs into the same target tree make the paths on disk say nothing.
    undo_started_at: Optional[str] = None
    #: Set once the run has been reversed, so it is never reversed twice.
    undone_at: Optional[str] = None
    undo_restored: int = 0
    undo_errors: List[str] = field(default_factory=list)
    version: int = RECORD_VERSION

    @property
    def can_be_undone(self) -> bool:
        return self.success and self.undone_at is None

    def structure_example(self, language: str = "en") -> str:
        """The structure as a path it would produce, not as its placeholders.

        A list of runs is read at a glance, and "{yyyy}/{yyyy}-{mm}" tells the
        reader nothing about what came out of it. Rendered from the stored
        template on the way out, so records written before this still show it.
        """
        if not self.structure:
            return "-"
        try:
            from .rules import describe_structure

            example = describe_structure(self.structure.split("/"), language)
        except Exception:  # noqa: BLE001 - a record must never fail to display
            return self.structure
        # A template of tokens this revision no longer knows renders to
        # nothing, and a blank cell is worse than the raw text.
        return example or self.structure

    @property
    def reversal_was_cut_short(self) -> bool:
        return bool(self.undo_started_at) and not self.undone_at

    @property
    def is_settled(self) -> bool:
        """True once nothing is outstanding, whatever the paths now look like."""
        return bool(self.undone_at) or bool(self.repaired_at)

    def describe(self, language: str = "en") -> str:
        when = self.started_at.replace("T", " ")[:16] or self.stamp
        if language == "de":
            state = (
                "zurückgenommen {u}".format(u=self.undone_at.replace("T", " ")[:16])
                if self.undone_at
                else ("erfolgreich" if self.success else "fehlgeschlagen")
            )
            return "{w}  {n:,} Datei(en)  wie {s}  [{st}]".format(
                w=when, n=self.files_moved, s=self.structure_example("de"), st=state
            )
        state = (
            "undone {u}".format(u=self.undone_at.replace("T", " ")[:16])
            if self.undone_at
            else ("success" if self.success else "failed")
        )
        return "{w}  {n:,} file(s)  like {s}  [{st}]".format(
            w=when, n=self.files_moved, s=self.structure_example(language), st=state
        )


def runs_directory(catalog: Path) -> Path:
    """Where this catalog's run records live."""
    return Path(catalog).resolve().parent / RUNS_DIRECTORY


def new_run_directory(catalog: Path, when: Optional[datetime] = None) -> Path:
    """Create and return the folder for a run starting now.

    Two runs within the same second would otherwise share a folder and the
    second would overwrite the first -- unlikely for a large library, trivially
    reachable for a small one, and silent when it happens.
    """
    base = runs_directory(catalog)
    stamp = (when or datetime.now()).strftime("%Y-%m-%d_%H%M%S")
    directory = base / stamp
    suffix = 2
    while (directory / RUN_FILE).exists():
        directory = base / "{s}-{n}".format(s=stamp, n=suffix)
        suffix += 1
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_record(directory: Path, record: RunRecord) -> Path:
    path = Path(directory) / RUN_FILE
    path.write_text(json.dumps(asdict(record), indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_record(directory: Path) -> Optional[RunRecord]:
    """The record in *directory*, or ``None`` if there is nothing readable."""
    path = Path(directory) / RUN_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("version") != RECORD_VERSION:
        return None
    known = set(RunRecord.__dataclass_fields__)
    return RunRecord(**{k: v for k, v in data.items() if k in known})


def write_settings(directory: Path, settings: Dict[str, Any]) -> Path:
    """Store the options the run used, in the shape a profile has.

    Answering "what did I actually do to this library in March" should not
    require reading a journal of fifty thousand lines.
    """
    path = Path(directory) / SETTINGS_FILE
    path.write_text(json.dumps(settings, indent=2, sort_keys=True), encoding="utf-8")
    return path


def history(catalog: Path) -> List[RunRecord]:
    """Every recorded run for *catalog*, newest first."""
    directory = runs_directory(catalog)
    if not directory.is_dir():
        return []
    records = []
    for child in sorted(directory.iterdir(), reverse=True):
        if not child.is_dir():
            continue
        record = read_record(child)
        if record is not None:
            records.append(record)
    return records


def directory_of(record: RunRecord) -> Path:
    return runs_directory(Path(record.catalog)) / record.stamp


def journal_of(record: RunRecord) -> Path:
    return directory_of(record) / JOURNAL_FILE


def find_record_for_journal(journal: Path) -> Optional[RunRecord]:
    """The record belonging to a journal path, if it lives in a run folder."""
    directory = Path(journal).resolve().parent
    if directory.name == RUNS_DIRECTORY or not (directory / RUN_FILE).exists():
        return None
    return read_record(directory)


def mark_repaired(record: RunRecord, restored: int) -> Optional[Path]:
    """Note that an interrupted run has been put back, so it is settled."""
    record.repaired_at = datetime.now().isoformat(timespec="seconds")
    record.undo_restored = restored
    directory = directory_of(record)
    if not directory.is_dir():
        return None
    return write_record(directory, record)


def mark_undo_started(record: RunRecord) -> Optional[Path]:
    """Note that a reversal has begun, before a single file is touched."""
    record.undo_started_at = datetime.now().isoformat(timespec="seconds")
    directory = directory_of(record)
    if not directory.is_dir():
        return None
    return write_record(directory, record)


def mark_undone(record: RunRecord, restored: int, errors: List[str]) -> Optional[Path]:
    """Record that this run has been reversed, so it is not reversed twice.

    The journal is kept rather than deleted. A partly failed undo leaves the
    journal as the only account of what actually moved, and throwing that away
    exactly when it is needed would be the wrong kind of tidiness. Marking the
    run is what stops it being offered again.
    """
    record.undone_at = datetime.now().isoformat(timespec="seconds")
    record.undo_restored = restored
    record.undo_errors = list(errors)
    directory = directory_of(record)
    if not directory.is_dir():
        return None
    return write_record(directory, record)
