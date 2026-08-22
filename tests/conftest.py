"""Shared fixtures.

The tests never need a real Lightroom installation: :func:`make_catalog`
builds a miniature catalog that carries exactly the tables LR-FolderCraft
reads and writes, with the same column names, conventions and the
``Adobe_entityIDCounter`` mechanism the real thing uses.
"""

from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lrfoldercraft.logging_setup import setup_logging  # noqa: E402

SCHEMA = """
CREATE TABLE Adobe_variablesTable (
    id_local INTEGER PRIMARY KEY, id_global UNIQUE NOT NULL, name, value);
CREATE TABLE AgLibraryRootFolder (
    id_local INTEGER PRIMARY KEY, id_global UNIQUE NOT NULL,
    absolutePath UNIQUE NOT NULL DEFAULT '', name NOT NULL DEFAULT '',
    relativePathFromCatalog);
CREATE TABLE AgLibraryFolder (
    id_local INTEGER PRIMARY KEY, id_global UNIQUE NOT NULL, parentId INTEGER,
    pathFromRoot NOT NULL DEFAULT '', rootFolder INTEGER NOT NULL DEFAULT 0,
    visibility INTEGER);
CREATE UNIQUE INDEX index_AgLibraryFolder_rootFolderAndPath
    ON AgLibraryFolder(rootFolder, pathFromRoot);
CREATE TABLE AgLibraryFile (
    id_local INTEGER PRIMARY KEY, id_global UNIQUE NOT NULL,
    baseName NOT NULL DEFAULT '', errorMessage, errorTime,
    extension NOT NULL DEFAULT '', externalModTime, folder INTEGER NOT NULL DEFAULT 0,
    idx_filename NOT NULL DEFAULT '', importHash, lc_idx_filename NOT NULL DEFAULT '',
    lc_idx_filenameExtension NOT NULL DEFAULT '', md5, modTime,
    originalFilename NOT NULL DEFAULT '', sidecarExtensions);
CREATE UNIQUE INDEX index_AgLibraryFile_nameAndFolder
    ON AgLibraryFile(lc_idx_filename, folder);
CREATE TABLE Adobe_images (
    id_local INTEGER PRIMARY KEY, id_global UNIQUE NOT NULL, captureTime,
    copyName, copyReason, fileFormat NOT NULL DEFAULT 'unset', masterImage INTEGER,
    rating, rootFile INTEGER NOT NULL DEFAULT 0);
CREATE TABLE AgHarvestedExifMetadata (
    id_local INTEGER PRIMARY KEY, image INTEGER, cameraModelRef INTEGER,
    cameraSNRef INTEGER, dateDay, dateMonth, dateYear, lensRef INTEGER);
CREATE TABLE AgInternedExifCameraModel (
    id_local INTEGER PRIMARY KEY, searchIndex, value);
CREATE TABLE AgInternedExifCameraSN (
    id_local INTEGER PRIMARY KEY, searchIndex, value);
CREATE TABLE AgInternedExifLens (
    id_local INTEGER PRIMARY KEY, searchIndex, value);
"""


class CatalogBuilder:
    """Creates a catalog file plus the matching image files on disk."""

    def __init__(self, root: Path, catalog_name: str = "test.lrcat"):
        self.root = root
        self.images_dir = root / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_path = root / catalog_name
        self._next_id = 1000
        self._conn = sqlite3.connect(str(self.catalog_path))
        self._conn.executescript(SCHEMA)
        self._var("Adobe_DBVersion", "18.0.0")
        self._var("Adobe_entityIDCounter", "5000.0")
        self.root_folder_id = self._new_id()
        self._conn.execute(
            "INSERT INTO AgLibraryRootFolder VALUES (?,?,?,?,?)",
            (self.root_folder_id, self._uuid(), str(self.images_dir) + "/", "images", None),
        )
        self.folders = {}
        self.folders[""] = self._new_id()
        self._conn.execute(
            "INSERT INTO AgLibraryFolder VALUES (?,?,?,?,?,?)",
            (self.folders[""], self._uuid(), None, "", self.root_folder_id, None),
        )
        self._conn.commit()

    # -- helpers --------------------------------------------------------

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    @staticmethod
    def _uuid() -> str:
        return str(uuid.uuid4()).upper()

    def _var(self, name: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO Adobe_variablesTable VALUES (?,?,?,?)",
            (self._new_id(), self._uuid(), name, value),
        )

    def add_folder(self, path_from_root: str) -> int:
        """Register a subfolder (``'2019/'`` style) and create it on disk."""
        if path_from_root in self.folders:
            return self.folders[path_from_root]
        segments = path_from_root.strip("/").split("/")
        parent = self.folders[""]
        current = ""
        for segment in segments:
            current = current + segment + "/"
            if current not in self.folders:
                folder_id = self._new_id()
                self._conn.execute(
                    "INSERT INTO AgLibraryFolder VALUES (?,?,?,?,?,?)",
                    (folder_id, self._uuid(), parent, current, self.root_folder_id, None),
                )
                self.folders[current] = folder_id
                (self.images_dir / current).mkdir(parents=True, exist_ok=True)
            parent = self.folders[current]
        self._conn.commit()
        return parent

    def add_photo(
        self,
        filename: str,
        capture_time: Optional[str] = "2019-01-03T17:42:29.18",
        camera: Optional[str] = "Canon EOS 70D",
        serial: Optional[str] = "0530",
        lens: Optional[str] = "EF 50mm",
        folder: str = "",
        file_format: str = "RAW",
        content: bytes = b"binary-image-data",
        sidecars: Sequence[str] = (),
        on_disk: bool = True,
        virtual_copies: int = 0,
    ) -> int:
        """Insert one file plus its master image and return the file id."""
        folder_id = self.add_folder(folder) if folder else self.folders[""]
        base, _, extension = filename.rpartition(".")
        file_id = self._new_id()
        self._conn.execute(
            "INSERT INTO AgLibraryFile "
            "(id_local,id_global,baseName,extension,folder,idx_filename,"
            "lc_idx_filename,lc_idx_filenameExtension,originalFilename,sidecarExtensions) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                file_id,
                self._uuid(),
                base,
                extension,
                folder_id,
                filename,
                filename.lower(),
                extension.lower(),
                filename,
                None,
            ),
        )
        image_id = self._new_id()
        self._conn.execute(
            "INSERT INTO Adobe_images "
            "(id_local,id_global,captureTime,fileFormat,masterImage,rootFile) "
            "VALUES (?,?,?,?,NULL,?)",
            (image_id, self._uuid(), capture_time, file_format, file_id),
        )
        for index in range(virtual_copies):
            self._conn.execute(
                "INSERT INTO Adobe_images "
                "(id_local,id_global,captureTime,fileFormat,copyName,masterImage,rootFile) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    self._new_id(),
                    self._uuid(),
                    capture_time,
                    file_format,
                    "Copy {n}".format(n=index + 1),
                    image_id,
                    file_id,
                ),
            )

        exif_id = self._new_id()
        camera_ref = self._intern("AgInternedExifCameraModel", camera)
        serial_ref = self._intern("AgInternedExifCameraSN", serial)
        lens_ref = self._intern("AgInternedExifLens", lens)
        when = _parse(capture_time)
        self._conn.execute(
            "INSERT INTO AgHarvestedExifMetadata "
            "(id_local,image,cameraModelRef,cameraSNRef,dateDay,dateMonth,dateYear,lensRef) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                exif_id,
                image_id,
                camera_ref,
                serial_ref,
                when.day if when else None,
                when.month if when else None,
                when.year if when else None,
                lens_ref,
            ),
        )
        self._conn.commit()

        if on_disk:
            target = self.images_dir / folder / filename if folder else self.images_dir / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            for sidecar in sidecars:
                (target.parent / sidecar).write_text("<x:xmpmeta/>", encoding="utf-8")
        return file_id

    def _intern(self, table: str, value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        row = self._conn.execute(
            "SELECT id_local FROM {t} WHERE value = ?".format(t=table), (value,)
        ).fetchone()
        if row:
            return row[0]
        new_id = self._new_id()
        self._conn.execute(
            "INSERT INTO {t} VALUES (?,?,?)".format(t=table),
            (new_id, value.lower(), value),
        )
        return new_id

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()

    # -- inspection used by assertions -----------------------------------

    def query(self, sql: str, params: Tuple = ()) -> List[Tuple]:
        conn = sqlite3.connect(str(self.catalog_path))
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def catalog_paths(self) -> List[str]:
        """Absolute path of every file as the catalog currently describes it."""
        return [
            row[0]
            for row in self.query(
                "SELECT rf.absolutePath || fo.pathFromRoot || f.idx_filename "
                "FROM AgLibraryFile f "
                "JOIN AgLibraryFolder fo ON fo.id_local = f.folder "
                "JOIN AgLibraryRootFolder rf ON rf.id_local = fo.rootFolder "
                "ORDER BY f.id_local"
            )
        ]


def _parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@pytest.fixture(autouse=True)
def _logging(tmp_path_factory):
    """Every test writes its log into the pytest temp tree, not the user's."""
    setup_logging(log_dir=tmp_path_factory.mktemp("logs"), quiet=True)


@pytest.fixture
def builder(tmp_path: Path) -> Iterable[CatalogBuilder]:
    catalog = CatalogBuilder(tmp_path / "lib")
    yield catalog
    catalog.close()


@pytest.fixture
def simple_catalog(builder: CatalogBuilder) -> CatalogBuilder:
    """Six photos on three days from two cameras, one with a sidecar."""
    builder.add_photo(
        "A0001.CR2",
        "2019-01-03T10:00:00",
        camera="Canon EOS 70D",
        sidecars=["A0001.xmp"],
        virtual_copies=2,
    )
    builder.add_photo("A0002.CR2", "2019-01-03T18:30:00", camera="Canon EOS 70D")
    builder.add_photo("A0003.CR2", "2019-02-14T09:15:00", camera="Canon EOS 5D Mark IV")
    builder.add_photo(
        "A0004.JPG", "2019-02-14T09:16:00", camera="Canon EOS 5D Mark IV", file_format="JPG"
    )
    builder.add_photo("A0005.CR2", "2019-12-29T23:59:00", camera="Canon EOS 70D")
    builder.add_photo("A0006.CR2", None, camera=None)
    return builder
