"""Background work for the graphical interface.

Reading a catalog, planning and moving files all take long enough to freeze a
window, so each runs on a worker thread and reports back through Qt signals.
The workers are the only place in the GUI that touches the core, and they pass
nothing but finished data objects back to the interface.
"""

from __future__ import annotations

import traceback
from typing import Dict, Optional

from PySide6.QtCore import QObject, Signal

from ..catalog import CatalogReader, open_catalog
from ..config import Settings
from ..executor import execute, undo
from ..planner import FolderCase, Plan, build_plan
from ..safety import preflight


class CatalogWorker(QObject):
    """Reads a catalog and hands back its summary and folder tree."""

    finished = Signal(object, object, object)  # info, roots, folders
    failed = Signal(str)

    def __init__(self, catalog: str):
        super().__init__()
        self.catalog = catalog

    def run(self) -> None:
        try:
            with open_catalog(self.catalog) as conn:
                reader = CatalogReader(conn)
                info = reader.info()
                roots = reader.root_folders()
                counts = reader.folder_file_counts()
                folders = [(f, counts.get(f.id_local, 0)) for f in reader.folders()]
            self.finished.emit(info, roots, folders)
        except Exception as exc:  # noqa: BLE001 - surfaced in the interface
            self.failed.emit("{e}\n\n{t}".format(e=exc, t=traceback.format_exc()))


class PlanWorker(QObject):
    """Builds a plan and runs the pre-flight checks."""

    finished = Signal(object, object)  # Plan, PreflightResult
    failed = Signal(str)
    #: Emitted for every folder the operator could reasonably decide about. The
    #: interface answers by writing into ``decisions`` before planning again;
    #: the worker itself never blocks waiting for a human.
    found_folder = Signal(object)

    def __init__(self, settings: Settings, decisions: Optional[Dict[int, str]] = None):
        super().__init__()
        self.settings = settings
        self.decisions = decisions or {}

    def run(self) -> None:
        try:
            self.settings.dry_run = True
            self.settings.folder_actions = dict(self.decisions)

            def decide(case: FolderCase) -> Optional[str]:
                self.found_folder.emit(case)
                return None

            with open_catalog(
                self.settings.catalog,
                allow_unsupported=self.settings.allow_unsupported_catalog,
            ) as conn:
                plan = build_plan(CatalogReader(conn), self.settings, decide=decide)
            checks = preflight(plan)
            self.finished.emit(plan, checks)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit("{e}\n\n{t}".format(e=exc, t=traceback.format_exc()))


class ApplyWorker(QObject):
    """Executes a plan, reporting progress as it goes."""

    progress = Signal(int, int, str)
    finished = Signal(object)  # RunResult
    failed = Signal(str)

    def __init__(self, plan: Plan, settings: Settings):
        super().__init__()
        self.plan = plan
        self.settings = settings

    def run(self) -> None:
        try:
            self.settings.dry_run = False

            def report(done: int, total: int, message: str) -> None:
                self.progress.emit(done, total, message)

            result = execute(self.plan, self.settings, progress=report)
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit("{e}\n\n{t}".format(e=exc, t=traceback.format_exc()))


class UndoWorker(QObject):
    """Reverses a completed run from its journal."""

    finished = Signal(object)  # RunResult
    failed = Signal(str)

    def __init__(self, journal_path: str):
        super().__init__()
        self.journal_path = journal_path

    def run(self) -> None:
        try:
            self.finished.emit(undo(self.journal_path))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit("{e}\n\n{t}".format(e=exc, t=traceback.format_exc()))


def run_in_thread(worker: QObject, thread_holder: list) -> None:
    """Move *worker* onto a fresh thread, start it, and keep both alive.

    Qt destroys a QThread that goes out of scope, taking the worker with it and
    aborting the process if the thread is still running -- which is exactly what
    happens when a window is closed, or garbage collected, while work is in
    flight. The holder keeps a reference until the thread has finished, and the
    entry is dropped again afterwards so the list does not grow without bound.
    """
    from PySide6.QtCore import QThread

    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    for signal_name in ("finished", "failed"):
        signal = getattr(worker, signal_name, None)
        if signal is not None:
            signal.connect(thread.quit)

    entry = (thread, worker)
    thread_holder.append(entry)

    def forget() -> None:
        if entry in thread_holder:
            thread_holder.remove(entry)

    thread.finished.connect(forget)
    thread.finished.connect(thread.deleteLater)
    thread.start()


def wait_for_threads(thread_holder: list, milliseconds: int = 30000) -> None:
    """Ask every running thread to stop and wait for it.

    Called when the window closes: letting the interpreter tear down while a
    worker is still moving files would abort the process mid-run.
    """
    for thread, _worker in list(thread_holder):
        if thread.isRunning():
            thread.quit()
            thread.wait(milliseconds)
