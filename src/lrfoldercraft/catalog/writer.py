"""Write operations against a Lightroom catalog.

Only two kinds of change are ever made:

1. ``INSERT`` new rows into ``AgLibraryFolder`` for folders that do not exist
   yet (ids drawn from ``Adobe_entityIDCounter``, exactly like Lightroom).
2. ``UPDATE AgLibraryFile SET folder = ?`` to re-parent a file.

Nothing else is touched. Image rows, develop settings, virtual copies,
collections, keywords and history all reference ``AgLibraryFile.id_local``,
which never changes -- that is why the re-organisation is non destructive.
"""

from __future__ import annotations

import sqlite3
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..logging_setup import get_logger
from .db import CatalogConnection, CatalogError
from .model import Folder, lr_path_from_root

log = get_logger("catalog.writer")


def _split_filename(filename: str) -> Tuple[str, str]:
    """Split ``name.ext`` into ``("name", "ext")``; no extension yields ``""``."""
    base_name, _, extension = filename.rpartition(".")
    if not base_name:
        return filename, ""
    return base_name, extension


class CatalogWriter:
    """Applies folder creations and file re-parenting inside one transaction."""

    def __init__(self, connection: CatalogConnection):
        if not connection.writable:
            raise CatalogError("CatalogWriter requires a read-write connection")
        self.conn = connection
        self._folder_cache: Dict[Tuple[int, str], Folder] = {}
        self._created: List[Folder] = []
        self._load_folders()

    def _load_folders(self) -> None:
        rows = self.conn.query(
            "SELECT id_local, id_global, parentId, pathFromRoot, rootFolder, visibility "
            "FROM AgLibraryFolder"
        )
        for row in rows:
            folder = Folder(
                id_local=row["id_local"],
                id_global=row["id_global"],
                parent_id=row["parentId"],
                path_from_root=row["pathFromRoot"] or "",
                root_folder=row["rootFolder"],
                visibility=row["visibility"],
            )
            self._folder_cache[(folder.root_folder, folder.path_from_root)] = folder
        log.debug("Loaded %d existing folder rows into cache", len(self._folder_cache))

    # -- folders ---------------------------------------------------------

    @property
    def created_folders(self) -> Sequence[Folder]:
        """Folder rows inserted during this session."""
        return tuple(self._created)

    def find_folder(self, root_folder_id: int, path_from_root: str) -> Optional[Folder]:
        return self._folder_cache.get((root_folder_id, path_from_root))

    def ensure_folder(self, root_folder_id: int, segments: Sequence[str]) -> Folder:
        """Return the folder for *segments*, inserting rows as required.

        Intermediate levels are created too, so ``("2019", "01", "03")`` yields
        three rows if none of them exist yet, each pointing at its parent.
        """
        parent = self._require_root_folder_row(root_folder_id)
        current: List[str] = []
        for segment in segments:
            current.append(segment)
            path = lr_path_from_root(tuple(current))
            existing = self._folder_cache.get((root_folder_id, path))
            if existing is not None:
                parent = existing
                continue
            parent = self._insert_folder(root_folder_id, path, parent.id_local)
        return parent

    def _require_root_folder_row(self, root_folder_id: int) -> Folder:
        """Return the ``AgLibraryFolder`` row representing the root itself."""
        root_row = self._folder_cache.get((root_folder_id, ""))
        if root_row is not None:
            return root_row
        # A catalog may legitimately have no row for the bare root; create one
        # so every child has a valid parentId.
        log.info("Root folder %d has no AgLibraryFolder row -- creating it", root_folder_id)
        return self._insert_folder(root_folder_id, "", None)

    def _insert_folder(
        self, root_folder_id: int, path_from_root: str, parent_id: Optional[int]
    ) -> Folder:
        new_id = self.conn.allocate_ids(1)[0]
        id_global = self.conn.new_id_global()
        self.conn.connection.execute(
            "INSERT INTO AgLibraryFolder "
            "(id_local, id_global, parentId, pathFromRoot, rootFolder, visibility) "
            "VALUES (?, ?, ?, ?, ?, NULL)",
            (new_id, id_global, parent_id, path_from_root, root_folder_id),
        )
        folder = Folder(
            id_local=new_id,
            id_global=id_global,
            parent_id=parent_id,
            path_from_root=path_from_root,
            root_folder=root_folder_id,
            visibility=None,
        )
        self._folder_cache[(root_folder_id, path_from_root)] = folder
        self._created.append(folder)
        log.info(
            "Created folder row id=%d parent=%s pathFromRoot=%r",
            new_id,
            parent_id,
            path_from_root,
        )
        return folder

    # -- root folders ------------------------------------------------------

    def ensure_root_folder(self, absolute_path: str, name: str) -> int:
        """Return the ``AgLibraryRootFolder`` id for *absolute_path*.

        Lightroom stores root paths with a trailing slash. A new root folder is
        inserted when the path is not registered yet -- this is what the
        ``new-tree`` placement mode needs.
        """
        normalised = absolute_path.rstrip("/") + "/"
        row = self.conn.query_one(
            "SELECT id_local FROM AgLibraryRootFolder WHERE absolutePath = ?",
            (normalised,),
        )
        if row is not None:
            return int(row[0])
        new_id = self.conn.allocate_ids(1)[0]
        id_global = self.conn.new_id_global()
        self.conn.connection.execute(
            "INSERT INTO AgLibraryRootFolder "
            "(id_local, id_global, absolutePath, name, relativePathFromCatalog) "
            "VALUES (?, ?, ?, ?, NULL)",
            (new_id, id_global, normalised, name),
        )
        log.info("Created root folder row id=%d path=%s", new_id, normalised)
        return new_id

    # -- files -------------------------------------------------------------

    def reparent_file(self, file_id: int, new_folder_id: int) -> None:
        """Point ``AgLibraryFile.folder`` at *new_folder_id*."""
        self.conn.connection.execute(
            "UPDATE AgLibraryFile SET folder = ? WHERE id_local = ?",
            (new_folder_id, file_id),
        )
        log.debug("Re-parented file id=%d -> folder id=%d", file_id, new_folder_id)

    def reparent_files(self, pairs: Iterable[Tuple[int, int]]) -> int:
        """Bulk variant of :meth:`reparent_file`; returns the number of rows."""
        rows = [(folder_id, file_id) for file_id, folder_id in pairs]
        if not rows:
            return 0
        self.conn.connection.executemany(
            "UPDATE AgLibraryFile SET folder = ? WHERE id_local = ?", rows
        )
        log.info("Re-parented %d file rows", len(rows))
        return len(rows)

    def move_row(
        self, file_id: int, new_folder_id: int, new_filename: Optional[str] = None
    ) -> None:
        """Re-parent and (optionally) rename a file in a single statement.

        Doing both at once matters: ``AgLibraryFile`` carries a UNIQUE index on
        ``(lc_idx_filename, folder)``. Moving first and renaming afterwards
        would briefly place two identically named rows in the same folder and
        trip that constraint, even though the final state is perfectly valid.
        """
        if new_filename is None:
            self.reparent_file(file_id, new_folder_id)
            return
        base_name, extension = _split_filename(new_filename)
        self.conn.connection.execute(
            "UPDATE AgLibraryFile SET folder = ?, baseName = ?, extension = ?, "
            "idx_filename = ?, lc_idx_filename = ?, lc_idx_filenameExtension = ? "
            "WHERE id_local = ?",
            (
                new_folder_id,
                base_name,
                extension,
                new_filename,
                new_filename.lower(),
                extension.lower(),
                file_id,
            ),
        )
        log.debug("Moved file id=%d -> folder %d as %s", file_id, new_folder_id, new_filename)

    def rename_file(self, file_id: int, new_filename: str) -> None:
        """Update the file-name columns of ``AgLibraryFile``.

        Needed when a collision forced the executor to store a file under a
        different name. ``originalFilename`` is deliberately left alone: it
        records the name at import time and Lightroom shows it as such.
        """
        base_name, extension = _split_filename(new_filename)
        self.conn.connection.execute(
            "UPDATE AgLibraryFile SET baseName = ?, extension = ?, "
            "idx_filename = ?, lc_idx_filename = ?, lc_idx_filenameExtension = ? "
            "WHERE id_local = ?",
            (
                base_name,
                extension,
                new_filename,
                new_filename.lower(),
                extension.lower(),
                file_id,
            ),
        )
        log.info("Renamed file id=%d -> %s", file_id, new_filename)

    def prune_empty_folders(self, folder_ids: Sequence[int]) -> List[int]:
        """Delete folder rows from *folder_ids* that hold no files and no children.

        Never removes a root-level row (``pathFromRoot = ''``) because
        Lightroom expects it to exist for every registered root folder.
        """
        removed: List[int] = []
        for folder_id in folder_ids:
            row = self.conn.query_one(
                "SELECT pathFromRoot FROM AgLibraryFolder WHERE id_local = ?",
                (folder_id,),
            )
            if row is None or not (row[0] or ""):
                continue
            files = self.conn.scalar(
                "SELECT COUNT(*) FROM AgLibraryFile WHERE folder = ?", (folder_id,)
            )
            children = self.conn.scalar(
                "SELECT COUNT(*) FROM AgLibraryFolder WHERE parentId = ?", (folder_id,)
            )
            if files or children:
                continue
            self.conn.connection.execute(
                "DELETE FROM AgLibraryFolder WHERE id_local = ?", (folder_id,)
            )
            removed.append(folder_id)
            log.info("Removed now-empty folder row id=%d", folder_id)
        return removed

    # -- transaction -------------------------------------------------------

    def commit(self) -> None:
        """Commit, then fold the write-ahead log back into the catalog file.

        Lightroom catalogs run in WAL mode, so a plain commit leaves the new
        data in ``<catalog>.lrcat-wal`` until something checkpoints it. A
        checkpoint here makes the ``.lrcat`` file self-contained before any
        other program opens it, and leaves an empty WAL behind rather than one
        whose content the catalog still depends on.
        """
        self.conn.connection.commit()
        log.info("Catalog transaction committed")
        try:
            mode, pages, moved = self.conn.connection.execute(
                "PRAGMA wal_checkpoint(TRUNCATE)"
            ).fetchone()
            if mode == 0:
                log.info("WAL checkpointed: %s page(s) written, %s reclaimed", pages, moved)
            else:
                log.warning(
                    "WAL checkpoint returned busy (mode=%s); the catalog still "
                    "depends on its -wal file. Do not delete it.",
                    mode,
                )
        except sqlite3.Error as exc:
            # A catalog in rollback-journal mode has no WAL; that is fine.
            log.debug("No WAL checkpoint performed: %s", exc)

    def rollback(self) -> None:
        self.conn.connection.rollback()
        log.warning("Catalog transaction rolled back")
