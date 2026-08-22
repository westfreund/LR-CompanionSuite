"""Read-only queries against a Lightroom catalog."""

from __future__ import annotations

from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from ..logging_setup import get_logger
from .db import CatalogConnection
from .model import CatalogInfo, Folder, Photo, RootFolder

log = get_logger("catalog.reader")

_PHOTO_SELECT = """
SELECT
    f.id_local              AS file_id,
    f.id_global             AS file_id_global,
    f.baseName              AS base_name,
    f.extension             AS extension,
    f.idx_filename          AS filename,
    f.folder                AS folder_id,
    f.sidecarExtensions     AS sidecar_extensions,
    fo.pathFromRoot         AS path_from_root,
    fo.rootFolder           AS root_folder_id,
    rf.absolutePath         AS root_absolute_path,
    i.id_local              AS image_id,
    i.captureTime           AS capture_time,
    i.fileFormat            AS file_format,
    {camera}                AS camera_model,
    {camera_sn}             AS camera_serial,
    {lens}                  AS lens,
    e.dateYear              AS exif_year,
    e.dateMonth             AS exif_month,
    e.dateDay               AS exif_day,
    (SELECT COUNT(*) FROM Adobe_images vc WHERE vc.masterImage = i.id_local)
                            AS virtual_copy_count
FROM AgLibraryFile f
JOIN AgLibraryFolder fo     ON fo.id_local = f.folder
JOIN AgLibraryRootFolder rf ON rf.id_local = fo.rootFolder
LEFT JOIN Adobe_images i    ON i.rootFile = f.id_local AND i.masterImage IS NULL
LEFT JOIN AgHarvestedExifMetadata e ON e.image = i.id_local
{camera_join}
{camera_sn_join}
{lens_join}
"""


class CatalogReader:
    """All read access the planner and the reports need."""

    def __init__(self, connection: CatalogConnection):
        self.conn = connection
        self._tables = {
            row[0]
            for row in connection.query(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    # -- capability probing --------------------------------------------

    def _has(self, table: str) -> bool:
        return table in self._tables

    def _photo_sql(self) -> str:
        """Build the photo query, degrading gracefully on older schemas."""
        has_cam = self._has("AgInternedExifCameraModel")
        has_sn = self._has("AgInternedExifCameraSN")
        has_lens = self._has("AgInternedExifLens")
        return _PHOTO_SELECT.format(
            camera="cm.value" if has_cam else "NULL",
            camera_sn="sn.value" if has_sn else "NULL",
            lens="ln.value" if has_lens else "NULL",
            camera_join=(
                "LEFT JOIN AgInternedExifCameraModel cm ON cm.id_local = e.cameraModelRef"
                if has_cam
                else ""
            ),
            camera_sn_join=(
                "LEFT JOIN AgInternedExifCameraSN sn ON sn.id_local = e.cameraSNRef"
                if has_sn
                else ""
            ),
            lens_join=(
                "LEFT JOIN AgInternedExifLens ln ON ln.id_local = e.lensRef"
                if has_lens
                else ""
            ),
        )

    # -- folders --------------------------------------------------------

    def root_folders(self) -> List[RootFolder]:
        rows = self.conn.query(
            "SELECT id_local, id_global, absolutePath, name, relativePathFromCatalog "
            "FROM AgLibraryRootFolder ORDER BY absolutePath"
        )
        return [
            RootFolder(
                id_local=row["id_local"],
                id_global=row["id_global"],
                absolute_path=row["absolutePath"],
                name=row["name"],
                relative_path_from_catalog=row["relativePathFromCatalog"],
            )
            for row in rows
        ]

    def folders(self, root_folder_id: Optional[int] = None) -> List[Folder]:
        sql = (
            "SELECT id_local, id_global, parentId, pathFromRoot, rootFolder, visibility "
            "FROM AgLibraryFolder"
        )
        params: Tuple[object, ...] = ()
        if root_folder_id is not None:
            sql += " WHERE rootFolder = ?"
            params = (root_folder_id,)
        sql += " ORDER BY rootFolder, pathFromRoot"
        return [
            Folder(
                id_local=row["id_local"],
                id_global=row["id_global"],
                parent_id=row["parentId"],
                path_from_root=row["pathFromRoot"] or "",
                root_folder=row["rootFolder"],
                visibility=row["visibility"],
            )
            for row in self.conn.query(sql, params)
        ]

    def folder_by_path(self, root_folder_id: int, path_from_root: str) -> Optional[Folder]:
        row = self.conn.query_one(
            "SELECT id_local, id_global, parentId, pathFromRoot, rootFolder, visibility "
            "FROM AgLibraryFolder WHERE rootFolder = ? AND pathFromRoot = ?",
            (root_folder_id, path_from_root),
        )
        if row is None:
            return None
        return Folder(
            id_local=row["id_local"],
            id_global=row["id_global"],
            parent_id=row["parentId"],
            path_from_root=row["pathFromRoot"] or "",
            root_folder=row["rootFolder"],
            visibility=row["visibility"],
        )

    def folder_file_counts(self) -> "dict[int, int]":
        return {
            row["folder"]: row["n"]
            for row in self.conn.query(
                "SELECT folder, COUNT(*) AS n FROM AgLibraryFile GROUP BY folder"
            )
        }

    # -- photos ----------------------------------------------------------

    def photos(
        self,
        folder_ids: Optional[Sequence[int]] = None,
        root_folder_ids: Optional[Sequence[int]] = None,
    ) -> Iterator[Photo]:
        """Yield :class:`Photo` records, optionally restricted to folders."""
        sql = self._photo_sql()
        clauses: List[str] = []
        params: List[object] = []
        if folder_ids:
            clauses.append(
                "f.folder IN ({q})".format(q=",".join("?" * len(folder_ids)))
            )
            params.extend(folder_ids)
        if root_folder_ids:
            clauses.append(
                "fo.rootFolder IN ({q})".format(q=",".join("?" * len(root_folder_ids)))
            )
            params.extend(root_folder_ids)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY f.id_local"

        log.debug("Photo query with %d filter clause(s)", len(clauses))
        cursor = self.conn.connection.execute(sql, tuple(params))
        while True:
            batch = cursor.fetchmany(2000)
            if not batch:
                break
            for row in batch:
                yield Photo(
                    file_id=row["file_id"],
                    file_id_global=row["file_id_global"],
                    base_name=row["base_name"],
                    extension=row["extension"],
                    filename=row["filename"],
                    folder_id=row["folder_id"],
                    root_folder_id=row["root_folder_id"],
                    folder_path_from_root=row["path_from_root"] or "",
                    root_absolute_path=row["root_absolute_path"],
                    sidecar_extensions=row["sidecar_extensions"],
                    image_id=row["image_id"],
                    capture_time_raw=row["capture_time"],
                    file_format=row["file_format"],
                    camera_model=row["camera_model"],
                    camera_serial=row["camera_serial"],
                    lens=row["lens"],
                    exif_year=row["exif_year"],
                    exif_month=row["exif_month"],
                    exif_day=row["exif_day"],
                    virtual_copy_count=row["virtual_copy_count"] or 0,
                )

    # -- summary ---------------------------------------------------------

    def info(self) -> CatalogInfo:
        """Collect the headline numbers shown by ``lrfc info``."""
        conn = self.conn
        cameras: Tuple[Tuple[str, int], ...] = ()
        if self._has("AgInternedExifCameraModel"):
            cameras = tuple(
                (row[0] or "(unknown)", row[1])
                for row in conn.query(
                    "SELECT cm.value, COUNT(*) FROM Adobe_images i "
                    "LEFT JOIN AgHarvestedExifMetadata e ON e.image = i.id_local "
                    "LEFT JOIN AgInternedExifCameraModel cm ON cm.id_local = e.cameraModelRef "
                    "WHERE i.masterImage IS NULL "
                    "GROUP BY cm.value ORDER BY COUNT(*) DESC"
                )
            )
        formats = tuple(
            (row[0] or "(unknown)", row[1])
            for row in conn.query(
                "SELECT fileFormat, COUNT(*) FROM Adobe_images "
                "WHERE masterImage IS NULL GROUP BY fileFormat ORDER BY COUNT(*) DESC"
            )
        )
        span = conn.query_one(
            "SELECT MIN(captureTime), MAX(captureTime) FROM Adobe_images "
            "WHERE masterImage IS NULL AND captureTime IS NOT NULL AND captureTime <> ''"
        )
        counter: Optional[float]
        try:
            counter = conn.peek_entity_id_counter()
        except Exception:  # pragma: no cover - counter missing is reported elsewhere
            counter = None

        return CatalogInfo(
            path=str(conn.path),
            schema_version=conn.schema_version(),
            entity_id_counter=counter,
            root_folders=int(conn.scalar("SELECT COUNT(*) FROM AgLibraryRootFolder") or 0),
            folders=int(conn.scalar("SELECT COUNT(*) FROM AgLibraryFolder") or 0),
            files=int(conn.scalar("SELECT COUNT(*) FROM AgLibraryFile") or 0),
            images=int(conn.scalar("SELECT COUNT(*) FROM Adobe_images") or 0),
            virtual_copies=int(
                conn.scalar("SELECT COUNT(*) FROM Adobe_images WHERE masterImage IS NOT NULL")
                or 0
            ),
            missing_capture_time=int(
                conn.scalar(
                    "SELECT COUNT(*) FROM Adobe_images WHERE masterImage IS NULL "
                    "AND (captureTime IS NULL OR captureTime = '')"
                )
                or 0
            ),
            earliest_capture=span[0] if span else None,
            latest_capture=span[1] if span else None,
            cameras=cameras,
            file_formats=formats,
        )


def photo_count(photos: Iterable[Photo]) -> int:
    """Small helper used by reports."""
    return sum(1 for _ in photos)
