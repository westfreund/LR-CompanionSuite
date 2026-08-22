"""Apply a :class:`~lrfoldercraft.planner.Plan`.

Order of operations, chosen so that the cheapest thing to undo happens last:

1. pre-flight checks (:mod:`lrfoldercraft.safety`)
2. copy the catalog to a timestamped backup and verify the copy
3. open the catalog read-write and, inside one *uncommitted* transaction,
   create the folder rows and re-parent (and if needed rename) the files
4. move the files on disk, journalling every single one
5. only if every move succeeded: commit the catalog transaction
6. optional verification pass and pruning of folders that fell empty

If step 4 fails, the catalog transaction is rolled back -- costing nothing --
and the files that had already been moved are put back using the journal. The
catalog on disk is then byte-identical to how the run found it.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .catalog.db import open_catalog
from .catalog.reader import CatalogReader
from .catalog.writer import CatalogWriter
from .config import Settings
from .journal import Journal, build_journal_path, journal_header
from .logging_setup import get_logger, step
from .planner import Plan, PlannedMove
from .safety import PreflightResult, preflight
from .version import __version__

log = get_logger("executor")

#: Called as ``progress(done, total, message)`` while files are moved.
ProgressCallback = Callable[[int, int, str], None]


class ExecutionError(RuntimeError):
    """Raised when a run had to be aborted; the rollback has already run."""


@dataclass
class RunResult:
    """What actually happened."""

    started_at: str
    finished_at: str = ""
    dry_run: bool = True
    success: bool = False
    catalog: str = ""
    backup_path: Optional[str] = None
    journal_path: Optional[str] = None
    folders_created: int = 0
    files_moved: int = 0
    files_renamed: int = 0
    sidecars_moved: int = 0
    folders_pruned: int = 0
    bytes_moved: int = 0
    errors: List[str] = field(default_factory=list)
    verification: List[str] = field(default_factory=list)
    rolled_back: bool = False
    tool_version: str = __version__


def backup_catalog(catalog: Path, backup_dir: Path) -> Path:
    """Copy *catalog* into *backup_dir* and verify the copy byte for byte."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / "{n}-{s}.lrcat".format(n=catalog.stem, s=stamp)
    step("Backing up catalog to %s", target)
    shutil.copy2(str(catalog), str(target))
    source_digest = _digest(catalog)
    target_digest = _digest(target)
    if source_digest != target_digest:
        target.unlink(missing_ok=True)
        raise ExecutionError("catalog backup verification failed -- refusing to continue")
    log.info("Backup verified (sha256 %s...)", source_digest[:16])
    return target


def _digest(path: Path, chunk: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def execute(
    plan: Plan,
    settings: Optional[Settings] = None,
    progress: Optional[ProgressCallback] = None,
    skip_preflight: bool = False,
) -> RunResult:
    """Execute *plan*. Honours ``settings.dry_run``."""
    settings = settings or plan.settings
    catalog = Path(plan.catalog_path)
    result = RunResult(
        started_at=datetime.now().isoformat(timespec="seconds"),
        dry_run=settings.dry_run,
        catalog=str(catalog),
    )

    if not skip_preflight:
        checks: PreflightResult = preflight(plan)
        if not checks.ok:
            messages = [c.message_en for c in checks.errors]
            result.errors.extend(messages)
            result.finished_at = datetime.now().isoformat(timespec="seconds")
            raise ExecutionError("pre-flight failed: " + "; ".join(messages))

    if settings.dry_run:
        step("DRY RUN -- no file and no catalog will be modified")
        result.folders_created = plan.stats.new_folders
        result.files_moved = plan.stats.to_move
        result.files_renamed = plan.stats.to_rename
        result.sidecars_moved = plan.stats.sidecars
        result.bytes_moved = plan.stats.bytes_to_move
        result.success = True
        result.finished_at = datetime.now().isoformat(timespec="seconds")
        return result

    if not plan.has_work:
        step("Nothing to do -- every file is already in place")
        result.success = True
        result.finished_at = datetime.now().isoformat(timespec="seconds")
        return result

    journal_path = build_journal_path(settings.resolved_backup_dir(), catalog)
    result.journal_path = str(journal_path)

    with Journal(journal_path) as journal:
        journal.write(
            "run-start",
            **journal_header(
                catalog,
                {
                    "structure": list(settings.structure),
                    "placement": settings.placement,
                    "target_root": plan.target_root_path,
                    "files": plan.stats.touched,
                    "folders": plan.stats.new_folders,
                },
            ),
        )
        try:
            if settings.backup_catalog:
                backup = backup_catalog(catalog, settings.resolved_backup_dir())
                result.backup_path = str(backup)
                journal.write("backup", source=str(catalog), target=str(backup))
            else:
                log.warning("Catalog backup skipped by configuration")

            _run(plan, settings, result, journal, progress)
            result.success = True
            journal.write("run-end", status="success", moved=result.files_moved)
        except Exception as exc:  # noqa: BLE001 - re-raised after journalling
            result.errors.append(str(exc))
            journal.write("run-end", status="failed", error=str(exc))
            log.exception("Run failed: %s", exc)
            raise
        finally:
            result.finished_at = datetime.now().isoformat(timespec="seconds")

    return result


def _run(
    plan: Plan,
    settings: Settings,
    result: RunResult,
    journal: Journal,
    progress: Optional[ProgressCallback],
) -> None:
    """The transactional core; assumes a backup already exists."""
    catalog = Path(plan.catalog_path)
    active = plan.active_moves
    total = len(active)
    moved: List[PlannedMove] = []
    moved_sidecars: List[Tuple[str, str]] = []
    created_dirs: List[Path] = []

    with open_catalog(
        catalog,
        writable=True,
        allow_unsupported=settings.allow_unsupported_catalog,
        ignore_lock=settings.ignore_lock,
    ) as conn:
        writer = CatalogWriter(conn)
        try:
            # --- 1. catalog side, still uncommitted -----------------------
            if settings.placement == "new-tree":
                target = Path(plan.target_root_path)
                root_id = writer.ensure_root_folder(str(target), target.name)
                step("Registered target root folder id=%d (%s)", root_id, target)
            else:
                root_id = plan.root_folder.id_local

            folder_ids: Dict[Tuple[str, ...], int] = {}
            for segments in plan.new_folder_segments:
                folder = writer.ensure_folder(root_id, segments)
                folder_ids[segments] = folder.id_local
            result.folders_created = len(writer.created_folders)
            step(
                "Prepared %d folder row(s) (%d newly created)",
                len(folder_ids),
                result.folders_created,
            )

            _stage_catalog_moves(writer, active, folder_ids)
            step("Staged %d catalog row update(s)", len(active))

            # --- 2. filesystem side, journalled ---------------------------
            root = Path(plan.target_root_path)
            for segments in plan.new_folder_segments:
                # Journal every level that is actually created, not just the
                # leaf: `mkdir(parents=True)` may create several, and an undo
                # can only remove what it knows about.
                for depth in range(1, len(segments) + 1):
                    directory = root.joinpath(*segments[:depth])
                    if directory.exists():
                        continue
                    journal.write("mkdir", path=str(directory))
                    directory.mkdir()
                    created_dirs.append(directory)
                    log.debug("Created directory %s", directory)

            for index, move in enumerate(active, start=1):
                journal.write(
                    "move-begin",
                    file_id=move.file_id,
                    source=move.source_path,
                    target=move.target_path,
                    renamed=move.renamed,
                )
                _move_file(move.source_path, move.target_path, move.cross_volume)
                moved.append(move)
                result.files_moved += 1
                result.bytes_moved += move.size_bytes
                if move.renamed:
                    result.files_renamed += 1

                for source, target in move.sidecars:
                    journal.write("move-begin", file_id=move.file_id, source=source, target=target)
                    _move_file(source, target, move.cross_volume)
                    moved_sidecars.append((source, target))
                    result.sidecars_moved += 1

                journal.write("move-done", file_id=move.file_id)
                if progress is not None and (index % 25 == 0 or index == total):
                    progress(index, total, move.target_path)

            step("Moved %d file(s) and %d sidecar(s)", result.files_moved, result.sidecars_moved)

            # --- 3. commit ------------------------------------------------
            if settings.prune_empty_folders:
                pruned = writer.prune_empty_folders(plan.source_folder_ids)
                result.folders_pruned = len(pruned)
                if pruned:
                    step("Pruned %d empty folder row(s)", len(pruned))

            writer.commit()
            journal.write(
                "catalog-commit", folders=result.folders_created, files=result.files_moved
            )
            step("Catalog committed")

        except Exception as exc:  # noqa: BLE001
            log.error("Failure during execution: %s -- rolling back", exc)
            writer.rollback()
            journal.write("rollback-begin", reason=str(exc))
            restored = _rollback_files(moved, moved_sidecars, journal)
            removed = _remove_created_directories(created_dirs)
            journal.write("rollback-end", restored=restored, directories=removed)
            result.rolled_back = True
            result.errors.append(
                "rolled back: {n} file(s) restored to their original location".format(n=restored)
            )
            raise

    # --- 4. after the catalog is closed again ---------------------------
    if settings.prune_empty_folders:
        _remove_empty_directories(plan, result)
    if settings.verify_after:
        _verify(plan, settings, result)


def _stage_catalog_moves(
    writer: CatalogWriter,
    moves: Sequence[PlannedMove],
    folder_ids: Dict[Tuple[str, ...], int],
) -> None:
    """Apply every catalog row change, order-independently.

    ``AgLibraryFile`` has a UNIQUE index on ``(lc_idx_filename, folder)``. The
    *final* layout always satisfies it -- the planner guarantees unique target
    names -- but an intermediate step may not: moving ``a/X.jpg`` into ``b/``
    fails while ``b/X.jpg`` is itself still waiting to be moved elsewhere.

    So rows that cannot move yet are deferred and retried. SQLite rolls back
    the offending statement only, leaving the surrounding transaction intact.
    If a whole round makes no progress the remaining rows form a rename cycle,
    which is broken by parking them under temporary names first.
    """
    pending: List[PlannedMove] = list(moves)
    while pending:
        deferred: List[PlannedMove] = []
        for move in pending:
            try:
                writer.move_row(
                    move.file_id,
                    folder_ids[move.target_segments],
                    move.target_filename if move.renamed else None,
                )
            except sqlite3.IntegrityError as exc:
                log.debug("Deferring file %d: %s", move.file_id, exc)
                deferred.append(move)
        if len(deferred) == len(pending):
            log.info("Breaking a rename cycle of %d row(s) via temporary names", len(deferred))
            for move in deferred:
                writer.rename_file(move.file_id, _temp_name(move))
            for move in deferred:
                writer.reparent_file(move.file_id, folder_ids[move.target_segments])
            for move in deferred:
                writer.rename_file(move.file_id, move.target_filename or move.filename)
            return
        pending = deferred


def _temp_name(move: PlannedMove) -> str:
    """Collision-proof placeholder name, unique through the row id."""
    _, _, extension = move.filename.rpartition(".")
    suffix = ".{e}".format(e=extension) if extension else ""
    return "__lrfc_tmp_{i}{s}".format(i=move.file_id, s=suffix)


def _remove_created_directories(directories: Sequence[Path]) -> int:
    """Delete directories the run created, deepest first, if they are empty."""
    removed = 0
    for directory in sorted(directories, key=lambda d: len(d.parts), reverse=True):
        try:
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
                removed += 1
        except OSError as exc:
            log.debug("Kept directory %s: %s", directory, exc)
    return removed


def _move_file(source: str, target: str, cross_volume: bool) -> None:
    """Move one file, using a verified copy when volumes differ."""
    source_path = Path(source)
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        raise ExecutionError("target already exists, refusing to overwrite: {t}".format(t=target))
    if not cross_volume:
        os.replace(str(source_path), str(target_path))
        return
    shutil.copy2(str(source_path), str(target_path))
    if _digest(source_path) != _digest(target_path):
        target_path.unlink(missing_ok=True)
        raise ExecutionError(
            "checksum mismatch after copying {s} -- original kept".format(s=source)
        )
    source_path.unlink()


def _rollback_files(
    moves: Sequence[PlannedMove],
    sidecars: Sequence[Tuple[str, str]],
    journal: Journal,
) -> int:
    """Put every already-moved file back. Best effort, fully journalled."""
    restored = 0
    for source, target in reversed(list(sidecars)):
        if _restore(target, source, journal):
            restored += 1
    for move in reversed(list(moves)):
        if _restore(move.target_path, move.source_path, journal):
            restored += 1
    log.warning("Rollback restored %d file(s)", restored)
    return restored


def _restore(current: str, original: str, journal: Journal) -> bool:
    try:
        if not Path(current).exists():
            journal.write("restore-missing", path=current)
            return False
        Path(original).parent.mkdir(parents=True, exist_ok=True)
        os.replace(current, original)
        journal.write("restore", source=current, target=original)
        return True
    except OSError as exc:
        journal.write("restore-failed", path=current, error=str(exc))
        log.error("Could not restore %s -> %s: %s", current, original, exc)
        return False


def _remove_empty_directories(plan: Plan, result: RunResult) -> None:
    """Delete source directories that fell empty, never the anchor itself."""
    anchor = Path(plan.target_root_path).joinpath(*plan.anchor_segments)
    candidates = {Path(m.source_path).parent for m in plan.active_moves}
    for directory in sorted(candidates, key=lambda p: len(p.parts), reverse=True):
        if directory == anchor or anchor not in directory.parents:
            continue
        try:
            if not any(directory.iterdir()):
                directory.rmdir()
                log.info("Removed empty source directory %s", directory)
        except OSError as exc:
            log.debug("Kept directory %s: %s", directory, exc)


def _verify(plan: Plan, settings: Settings, result: RunResult) -> None:
    """Re-read the catalog and confirm every moved file is where it should be."""
    step("Verifying catalog against the filesystem")
    expected = {m.file_id: m.target_path for m in plan.active_moves}
    problems: List[str] = []
    with open_catalog(
        plan.catalog_path,
        allow_unsupported=settings.allow_unsupported_catalog,
        ignore_lock=True,
    ) as conn:
        reader = CatalogReader(conn)
        seen = 0
        for photo in reader.photos():
            want = expected.get(photo.file_id)
            if want is None:
                continue
            seen += 1
            actual = photo.absolute_path
            if os.path.normpath(actual) != os.path.normpath(want):
                problems.append(
                    "file {i}: catalog says {a}, plan said {w}".format(
                        i=photo.file_id, a=actual, w=want
                    )
                )
            elif not os.path.exists(actual):
                problems.append(
                    "file {i}: missing on disk at {a}".format(i=photo.file_id, a=actual)
                )
        if seen != len(expected):
            problems.append(
                "verification saw {s} of {e} moved files".format(s=seen, e=len(expected))
            )
    result.verification = problems[:50]
    if problems:
        log.error("Verification found %d problem(s)", len(problems))
    else:
        step("Verification passed: %d file(s) confirmed", len(expected))


def undo(journal_path: str | Path, catalog_backup: Optional[str] = None) -> RunResult:
    """Reverse a completed run using its journal.

    Files are put back first; the catalog is then restored from the backup the
    run made, which is the only way to guarantee the database matches the
    filesystem again.
    """
    from .journal import completed_moves, read_journal

    records = read_journal(journal_path)
    result = RunResult(
        started_at=datetime.now().isoformat(timespec="seconds"),
        dry_run=False,
        journal_path=str(journal_path),
    )
    step("Undoing run recorded in %s", journal_path)

    backup = catalog_backup
    catalog = None
    for record in records:
        if record.get("event") == "backup":
            backup = backup or record.get("target")
            catalog = record.get("source")
    result.catalog = catalog or ""

    restored = 0
    for record in reversed(list(completed_moves(records))):
        source = record.get("target")
        target = record.get("source")
        if not source or not target:
            continue
        try:
            if Path(source).exists() and not Path(target).exists():
                Path(target).parent.mkdir(parents=True, exist_ok=True)
                os.replace(source, target)
                restored += 1
        except OSError as exc:
            result.errors.append("{s}: {e}".format(s=source, e=exc))
    result.files_moved = restored
    step("Restored %d file(s) to their original location", restored)

    # Directories the run created and that are empty again are removed, so an
    # undone run leaves no trace of the structure it built.
    created = [r.get("path") for r in records if r.get("event") == "mkdir" and r.get("path")]
    for directory in sorted(created, key=lambda d: len(Path(d).parts), reverse=True):
        try:
            path = Path(directory)
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                result.folders_pruned += 1
        except OSError as exc:
            log.debug("Kept directory %s during undo: %s", directory, exc)
    if result.folders_pruned:
        step("Removed %d empty directory/directories", result.folders_pruned)

    if backup and catalog and Path(backup).exists():
        shutil.copy2(backup, catalog)
        result.backup_path = backup
        step("Restored catalog from %s", backup)
    else:
        result.errors.append(
            "no catalog backup available -- the catalog still describes the "
            "reorganised layout. Restore it manually before opening Lightroom."
        )

    result.success = not result.errors
    result.finished_at = datetime.now().isoformat(timespec="seconds")
    return result
