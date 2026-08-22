"""Catalog reading, writing and id allocation."""

from __future__ import annotations

import sqlite3

import pytest

from lrfoldercraft.catalog import CatalogError, CatalogLockedError, CatalogReader, CatalogWriter
from lrfoldercraft.catalog.db import lock_file_for, open_catalog
from lrfoldercraft.catalog.model import parse_capture_time


def test_reader_reads_photos_and_metadata(simple_catalog):
    with open_catalog(simple_catalog.catalog_path) as conn:
        photos = {p.filename: p for p in CatalogReader(conn).photos()}
    assert set(photos) == {
        "A0001.CR2",
        "A0002.CR2",
        "A0003.CR2",
        "A0004.JPG",
        "A0005.CR2",
        "A0006.CR2",
    }
    first = photos["A0001.CR2"]
    assert first.camera_model == "Canon EOS 70D"
    assert first.camera_serial == "0530"
    assert first.lens == "EF 50mm"
    assert first.virtual_copy_count == 2
    assert first.capture_time.year == 2019
    assert photos["A0006.CR2"].capture_time is None


def test_info_counts(simple_catalog):
    with open_catalog(simple_catalog.catalog_path) as conn:
        info = CatalogReader(conn).info()
    assert info.files == 6
    assert info.images == 8  # six masters plus two virtual copies
    assert info.virtual_copies == 2
    assert info.missing_capture_time == 1
    assert info.schema_version == "18.0.0"
    assert dict(info.cameras)["Canon EOS 70D"] == 3


def test_rejects_a_non_catalog(tmp_path):
    plain = tmp_path / "notes.lrcat"
    sqlite3.connect(str(plain)).execute("CREATE TABLE x (a)")
    with pytest.raises(CatalogError, match="missing tables"):
        with open_catalog(plain):
            pass


def test_refuses_a_locked_catalog(simple_catalog):
    lock = lock_file_for(simple_catalog.catalog_path)
    lock.write_text("locked", encoding="utf-8")
    try:
        with pytest.raises(CatalogLockedError, match="Close Lightroom"):
            with open_catalog(simple_catalog.catalog_path):
                pass
        # the override exists for forensic inspection
        with open_catalog(simple_catalog.catalog_path, ignore_lock=True) as conn:
            assert CatalogReader(conn).info().files == 6
    finally:
        lock.unlink()


def test_read_only_connection_cannot_write(simple_catalog):
    with open_catalog(simple_catalog.catalog_path) as conn:
        assert not conn.writable
        with pytest.raises(sqlite3.OperationalError):
            conn.connection.execute("DELETE FROM AgLibraryFile")
        with pytest.raises(CatalogError):
            conn.allocate_ids(1)


def test_ids_come_from_the_entity_counter(simple_catalog):
    with open_catalog(simple_catalog.catalog_path, writable=True) as conn:
        start = conn.peek_entity_id_counter()
        ids = conn.allocate_ids(3)
        assert ids == [int(start), int(start) + 1, int(start) + 2]
        assert conn.peek_entity_id_counter() == start + 3
        conn.connection.commit()
    with open_catalog(simple_catalog.catalog_path) as conn:
        assert conn.peek_entity_id_counter() == start + 3


def test_writer_creates_the_full_folder_chain(simple_catalog):
    with open_catalog(simple_catalog.catalog_path, writable=True) as conn:
        writer = CatalogWriter(conn)
        folder = writer.ensure_folder(simple_catalog.root_folder_id, ("2019", "01", "03"))
        writer.commit()
    rows = dict(simple_catalog.query("SELECT pathFromRoot, id_local FROM AgLibraryFolder"))
    assert "2019/" in rows and "2019/01/" in rows and "2019/01/03/" in rows
    assert folder.id_local == rows["2019/01/03/"]
    parents = dict(simple_catalog.query("SELECT pathFromRoot, parentId FROM AgLibraryFolder"))
    assert parents["2019/01/03/"] == rows["2019/01/"]
    assert parents["2019/01/"] == rows["2019/"]


def test_ensure_folder_is_idempotent(simple_catalog):
    with open_catalog(simple_catalog.catalog_path, writable=True) as conn:
        writer = CatalogWriter(conn)
        first = writer.ensure_folder(simple_catalog.root_folder_id, ("2019", "01"))
        second = writer.ensure_folder(simple_catalog.root_folder_id, ("2019", "01"))
        writer.commit()
    assert first.id_local == second.id_local
    assert len(simple_catalog.query("SELECT 1 FROM AgLibraryFolder")) == 3


def test_rename_file_updates_every_name_column(simple_catalog):
    file_id = simple_catalog.query(
        "SELECT id_local FROM AgLibraryFile WHERE idx_filename = 'A0001.CR2'"
    )[0][0]
    with open_catalog(simple_catalog.catalog_path, writable=True) as conn:
        writer = CatalogWriter(conn)
        writer.rename_file(file_id, "A0001_1.CR2")
        writer.commit()
    row = simple_catalog.query(
        "SELECT baseName, extension, idx_filename, lc_idx_filename, "
        "lc_idx_filenameExtension, originalFilename FROM AgLibraryFile "
        "WHERE id_local = ?",
        (file_id,),
    )[0]
    assert row == ("A0001_1", "CR2", "A0001_1.CR2", "a0001_1.cr2", "cr2", "A0001.CR2")


def test_prune_never_removes_the_root_row(simple_catalog):
    root_row = simple_catalog.folders[""]
    with open_catalog(simple_catalog.catalog_path, writable=True) as conn:
        writer = CatalogWriter(conn)
        assert writer.prune_empty_folders([root_row]) == []
        writer.commit()
    assert (
        simple_catalog.query(
            "SELECT COUNT(*) FROM AgLibraryFolder WHERE id_local = ?", (root_row,)
        )[0][0]
        == 1
    )


def test_rollback_leaves_no_trace(simple_catalog):
    before = simple_catalog.query("SELECT COUNT(*) FROM AgLibraryFolder")[0][0]
    with open_catalog(simple_catalog.catalog_path, writable=True) as conn:
        writer = CatalogWriter(conn)
        writer.ensure_folder(simple_catalog.root_folder_id, ("2019", "01", "03"))
        writer.rollback()
    assert simple_catalog.query("SELECT COUNT(*) FROM AgLibraryFolder")[0][0] == before


@pytest.mark.parametrize(
    "raw,year",
    [
        ("2019-01-03T17:42:29.18", 2019),
        ("2019-01-03T17:42:29", 2019),
        ("2019-01-03T17:42:29+01:00", 2019),
        ("2019-01-03T17:42:29Z", 2019),
        ("2019-01-03", 2019),
        ("2019", 2019),
    ],
)
def test_capture_time_variants(raw, year):
    assert parse_capture_time(raw).year == year


@pytest.mark.parametrize("raw", [None, "", "   ", "not-a-date"])
def test_capture_time_rejects_junk(raw):
    assert parse_capture_time(raw) is None
