"""Background work for the LR-MetaSearch window.

Reading forty libraries takes half a minute, and a window that freezes for half
a minute looks broken. Each long job runs on a worker thread and reports back
through Qt signals; the folder tool's helpers move them there and, crucially,
wait for them when the window closes.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, Signal

from ...logging_setup import get_logger
from ..duplicates import identical, near, summary
from ..query import search
from ..scan import scan
from ..store import Index
from ..subset import build

log = get_logger("metasearch.gui.workers")


class ScanWorker(QObject):
    """Reads catalogs into the index."""

    progress = Signal(int, int, str)
    finished = Signal(object, object)  # outcomes, counts
    failed = Signal(str)

    def __init__(self, roots, index_path: str):
        super().__init__()
        self.roots = list(roots)
        self.index_path = index_path

    def run(self) -> None:
        try:
            with Index.open(self.index_path or None) as index:
                outcomes = scan(self.roots, index, progress=self.progress.emit)
                counts = index.counts()
            self.finished.emit(outcomes, counts)
        except Exception as exc:  # noqa: BLE001 - reported in the window
            log.error("Scan failed: %s", traceback.format_exc())
            self.failed.emit(str(exc))


class SearchWorker(QObject):
    """Answers one search."""

    finished = Signal(object, int)  # hits, total
    failed = Signal(str)

    def __init__(self, criteria, index_path: str, limit: int):
        super().__init__()
        self.criteria = criteria
        self.index_path = index_path
        self.limit = limit

    def run(self) -> None:
        try:
            from ..query import count

            with Index.open(self.index_path or None, create=False) as index:
                total = count(index, self.criteria._replace(limit=0))
                hits = search(index, self.criteria._replace(limit=self.limit))
            self.finished.emit(hits, total)
        except Exception as exc:  # noqa: BLE001 - reported in the window
            log.error("Search failed: %s", traceback.format_exc())
            self.failed.emit(str(exc))


class DuplicateWorker(QObject):
    """Builds the duplicate report."""

    finished = Signal(object, object)  # groups, totals
    failed = Signal(str)

    def __init__(self, index_path: str, across_only: bool, use_near: bool, limit: int):
        super().__init__()
        self.index_path = index_path
        self.across_only = across_only
        self.use_near = use_near
        self.limit = limit

    def run(self) -> None:
        try:
            with Index.open(self.index_path or None, create=False) as index:
                totals = summary(index)
                if self.use_near:
                    groups = near(index, limit=self.limit)
                else:
                    groups = identical(
                        index, across_catalogs_only=self.across_only, limit=self.limit
                    )
            self.finished.emit(groups, totals)
        except Exception as exc:  # noqa: BLE001 - reported in the window
            log.error("Duplicate report failed: %s", traceback.format_exc())
            self.failed.emit(str(exc))


class ExportWorker(QObject):
    """Copies each library and reduces the copy to the selection."""

    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, photo_ids, target: str, index_path: str):
        super().__init__()
        self.photo_ids = list(photo_ids)
        self.target = target
        self.index_path = index_path

    def run(self) -> None:
        try:
            with Index.open(self.index_path or None, create=False) as index:
                results = build(index, self.photo_ids, self.target, progress=self.progress.emit)
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001 - reported in the window
            log.error("Export failed: %s", traceback.format_exc())
            self.failed.emit(str(exc))
