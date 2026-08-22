"""Append-only run journal.

The journal is what makes a half finished run recoverable. Every filesystem
action is recorded *before* it is attempted and confirmed afterwards, each
line flushed and fsynced, so even a power cut leaves a usable record:

    {"event": "run-start",   ...}
    {"event": "backup",      "source": ..., "target": ...}
    {"event": "mkdir",       "path": ...}
    {"event": "move-begin",  "file_id": 1, "source": ..., "target": ...}
    {"event": "move-done",   "file_id": 1}
    {"event": "catalog-commit"}
    {"event": "run-end",     "status": "success"}

``lrfc undo`` replays such a file backwards.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, TextIO

from .logging_setup import get_logger
from .version import __version__

log = get_logger("journal")

JOURNAL_SUFFIX = ".lrfc-journal.jsonl"


class Journal:
    """Write side of the run journal."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle: Optional[TextIO] = None

    def open(self) -> "Journal":
        self._handle = self.path.open("a", encoding="utf-8")
        return self

    def write(self, event: str, **payload: Any) -> None:
        """Append one event and force it to disk."""
        if self._handle is None:
            raise RuntimeError("journal is not open")
        record: Dict[str, Any] = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "event": event,
        }
        record.update(payload)
        self._handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._handle.flush()
        try:
            os.fsync(self._handle.fileno())
        except OSError:  # pragma: no cover - not all filesystems support fsync
            pass

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> "Journal":
        return self.open()

    def __exit__(self, *exc: object) -> None:
        self.close()


def build_journal_path(directory: Path, catalog: Path) -> Path:
    """Return a timestamped journal path for *catalog* inside *directory*."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    Path(directory).mkdir(parents=True, exist_ok=True)
    return Path(directory) / "{n}-{s}{x}".format(
        n=catalog.stem, s=stamp, x=JOURNAL_SUFFIX
    )


def read_journal(path: "str | Path") -> List[Dict[str, Any]]:
    """Load every well formed record from a journal file."""
    records: List[Dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # A torn last line is expected after a crash; keep the rest.
                log.warning("Ignoring malformed journal line %d in %s", line_number, path)
    return records


def completed_moves(records: List[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    """Yield the ``move-begin`` records that have a matching ``move-done``."""
    done = {
        r.get("file_id")
        for r in records
        if r.get("event") == "move-done" and r.get("file_id") is not None
    }
    for record in records:
        if record.get("event") == "move-begin" and record.get("file_id") in done:
            yield record


def journal_header(catalog: Path, plan_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Standard payload for the ``run-start`` record."""
    return {
        "tool_version": __version__,
        "catalog": str(catalog),
        "plan": plan_summary,
    }
