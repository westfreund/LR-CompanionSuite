"""Catalog reading, writing and id allocation."""

from __future__ import annotations

import sqlite3
from pathlib import Path

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


def test_readonly_falls_back_when_the_filesystem_has_no_locking(simple_catalog, monkeypatch):
    """exFAT and FAT cannot provide SQLite's shared lock.

    sqlite3.connect() is lazy, so such a volume fails on the first *statement*.
    The fallback must therefore be driven by a probe query, not by connect().
    """
    import sqlite3 as sqlite3_module

    from lrfoldercraft.catalog import db as db_module

    real_connect = sqlite3_module.connect
    attempts = []

    class Unlockable:
        """Connects fine, then refuses the first statement -- like exFAT."""

        def __init__(self, inner):
            self._inner = inner

        def execute(self, *args, **kwargs):
            raise sqlite3_module.OperationalError("unable to open database file")

        def close(self):
            self._inner.close()

        def __getattr__(self, name):
            return getattr(self._inner, name)

    def fake_connect(target, *args, **kwargs):
        attempts.append(target)
        inner = real_connect(target, *args, **kwargs)
        if "immutable=1" not in target:
            return Unlockable(inner)
        return inner

    monkeypatch.setattr(db_module.sqlite3, "connect", fake_connect)

    with db_module.open_catalog(simple_catalog.catalog_path) as conn:
        assert CatalogReader(conn).info().files == 6

    assert any("immutable=1" in uri for uri in attempts), attempts
    assert any("mode=ro" in uri and "immutable" not in uri for uri in attempts), attempts


def test_readonly_probe_does_not_hide_a_real_failure(simple_catalog, monkeypatch):
    """If even immutable=1 cannot read the file, the error must surface."""
    import sqlite3 as sqlite3_module

    from lrfoldercraft.catalog import db as db_module

    def always_broken(target, *args, **kwargs):
        raise sqlite3_module.OperationalError("unable to open database file")

    monkeypatch.setattr(db_module.sqlite3, "connect", always_broken)
    with pytest.raises(sqlite3_module.OperationalError):
        with db_module.open_catalog(simple_catalog.catalog_path):
            pass


def test_commit_checkpoints_the_write_ahead_log(simple_catalog):
    """Lightroom catalogs run in WAL mode; the .lrcat must be self-contained."""
    import sqlite3 as sqlite3_module

    from lrfoldercraft.catalog.db import open_catalog as open_cat

    path = Path(simple_catalog.catalog_path)
    raw = sqlite3_module.connect(str(path))
    raw.execute("PRAGMA journal_mode=WAL").fetchone()
    raw.close()

    with open_cat(path, writable=True) as conn:
        writer = CatalogWriter(conn)
        writer.ensure_folder(simple_catalog.root_folder_id, ("2019", "01", "03"))
        writer.commit()

    wal = path.with_name(path.name + "-wal")
    assert not wal.exists() or wal.stat().st_size == 0, (
        "the catalog still depends on its write-ahead log after commit"
    )
    # the rows must be readable from the main file alone
    plain = sqlite3_module.connect("file:{p}?mode=ro&immutable=1".format(p=path), uri=True)
    assert (
        plain.execute(
            "SELECT COUNT(*) FROM AgLibraryFolder WHERE pathFromRoot = '2019/01/03/'"
        ).fetchone()[0]
        == 1
    )
    plain.close()


def test_side_file_check_never_calls_a_wal_stale(simple_catalog):
    """An earlier revision told users to clear -wal files. That destroys data."""
    from lrfoldercraft.safety import _check_side_files

    path = Path(simple_catalog.catalog_path)
    wal = path.with_name(path.name + "-wal")
    wal.write_bytes(b"x" * 4096)
    try:
        check = _check_side_files(path)
        assert check.level != "error"
        for text in (check.message_en.lower(), check.message_de.lower()):
            assert "stale" not in text
            assert "delete" not in text or "never delete" in text or "not delete" in text
            assert "loeschen" not in text or "niemals loeschen" in text or "nicht loeschen" in text
        assert "4,096" in check.message_en
    finally:
        wal.unlink()


def test_side_file_check_flags_an_interrupted_journal(simple_catalog):
    from lrfoldercraft.safety import _check_side_files

    path = Path(simple_catalog.catalog_path)
    journal = path.with_name(path.name + "-journal")
    journal.write_bytes(b"x" * 512)
    try:
        check = _check_side_files(path)
        assert check.level == "warning"
        assert "interrupted" in check.message_en
        assert "not delete" in check.message_en
    finally:
        journal.unlink()
