"""End to end execution: apply, rollback, undo, verification."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lrfoldercraft.catalog import CatalogReader, open_catalog
from lrfoldercraft.config import Settings
from lrfoldercraft.executor import ExecutionError, backup_catalog, execute, undo
from lrfoldercraft.journal import read_journal
from lrfoldercraft.planner import build_plan
from lrfoldercraft.safety import preflight


def make_plan(builder, tmp_path, **kwargs):
    kwargs.setdefault("structure", ("{yyyy}-{mm}-{dd}",))
    settings = Settings(
        catalog=str(builder.catalog_path),
        dry_run=False,
        backup_dir=str(tmp_path / "backups"),
        **kwargs,
    )
    with open_catalog(builder.catalog_path) as conn:
        return build_plan(CatalogReader(conn), settings), settings


# -- dry run ----------------------------------------------------------------


def test_dry_run_changes_nothing(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    settings.dry_run = True
    before_paths = simple_catalog.catalog_paths()
    before_disk = sorted(p.name for p in simple_catalog.images_dir.iterdir())

    result = execute(plan, settings)

    assert result.success and result.dry_run
    assert result.files_moved == plan.stats.to_move
    assert simple_catalog.catalog_paths() == before_paths
    assert sorted(p.name for p in simple_catalog.images_dir.iterdir()) == before_disk


# -- the happy path ----------------------------------------------------------


def test_apply_moves_files_and_rewrites_the_catalog(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)

    assert result.success
    assert result.files_moved == 6
    assert result.sidecars_moved == 1
    assert not result.verification

    for path in simple_catalog.catalog_paths():
        assert os.path.exists(path), path
    assert (simple_catalog.images_dir / "2019-01-03" / "A0001.CR2").exists()
    assert (simple_catalog.images_dir / "2019-01-03" / "A0001.xmp").exists()
    assert (simple_catalog.images_dir / "2019-02-14" / "A0003.CR2").exists()
    assert (simple_catalog.images_dir / "_unsorted" / "A0006.CR2").exists()
    assert not (simple_catalog.images_dir / "A0001.CR2").exists()


def test_apply_is_idempotent(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    execute(plan, settings)
    plan2, settings2 = make_plan(simple_catalog, tmp_path)
    assert not plan2.has_work
    result = execute(plan2, settings2)
    assert result.success and result.files_moved == 0


def test_image_rows_are_untouched(simple_catalog, tmp_path):
    """Only AgLibraryFolder and AgLibraryFile.folder may change."""
    before = simple_catalog.query("SELECT * FROM Adobe_images ORDER BY id_local")
    plan, settings = make_plan(simple_catalog, tmp_path)
    execute(plan, settings)
    assert simple_catalog.query("SELECT * FROM Adobe_images ORDER BY id_local") == before


def test_virtual_copies_follow_their_master(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    execute(plan, settings)
    rows = simple_catalog.query(
        "SELECT i.copyName, fo.pathFromRoot FROM Adobe_images i "
        "JOIN AgLibraryFile f ON f.id_local = i.rootFile "
        "JOIN AgLibraryFolder fo ON fo.id_local = f.folder "
        "WHERE i.masterImage IS NOT NULL"
    )
    assert sorted(rows) == [("Copy 1", "2019-01-03/"), ("Copy 2", "2019-01-03/")]


def test_folder_rows_form_a_valid_tree(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path, structure=("{yyyy}", "{mm}", "{dd}"))
    execute(plan, settings)
    orphans = simple_catalog.query(
        "SELECT COUNT(*) FROM AgLibraryFolder f WHERE f.pathFromRoot <> '' AND "
        "(f.parentId IS NULL OR NOT EXISTS "
        "(SELECT 1 FROM AgLibraryFolder p WHERE p.id_local = f.parentId))"
    )[0][0]
    assert orphans == 0
    bad_prefix = simple_catalog.query(
        "SELECT COUNT(*) FROM AgLibraryFolder f JOIN AgLibraryFolder p "
        "ON p.id_local = f.parentId "
        "WHERE substr(f.pathFromRoot, 1, length(p.pathFromRoot)) <> p.pathFromRoot"
    )[0][0]
    assert bad_prefix == 0
    # every path is stored with Lightroom's trailing slash
    for (path,) in simple_catalog.query(
        "SELECT pathFromRoot FROM AgLibraryFolder WHERE pathFromRoot <> ''"
    ):
        assert path.endswith("/")


def test_new_folder_ids_come_from_the_counter(simple_catalog, tmp_path):
    before = float(
        simple_catalog.query(
            "SELECT value FROM Adobe_variablesTable WHERE name = 'Adobe_entityIDCounter'"
        )[0][0]
    )
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)
    after = float(
        simple_catalog.query(
            "SELECT value FROM Adobe_variablesTable WHERE name = 'Adobe_entityIDCounter'"
        )[0][0]
    )
    assert after == before + result.folders_created
    new_ids = [
        row[0]
        for row in simple_catalog.query(
            "SELECT id_local FROM AgLibraryFolder WHERE pathFromRoot <> ''"
        )
    ]
    assert all(i >= before for i in new_ids)


def test_backup_is_written_and_verified(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)
    backup = Path(result.backup_path)
    assert backup.exists()
    assert backup.parent == tmp_path / "backups"


def test_renamed_collision_updates_the_catalog(builder, tmp_path):
    builder.add_photo("SAME.CR2", "2019-01-03T10:00:00", folder="a/")
    builder.add_photo("SAME.CR2", "2019-01-03T11:00:00", folder="b/")
    plan, settings = make_plan(builder, tmp_path)
    result = execute(plan, settings)
    assert result.files_renamed == 1
    names = sorted(row[0] for row in builder.query("SELECT idx_filename FROM AgLibraryFile"))
    assert names == ["SAME.CR2", "SAME_1.CR2"]
    for path in builder.catalog_paths():
        assert os.path.exists(path)


def test_empty_source_folders_are_pruned(builder, tmp_path):
    # two source folders -> the anchor is the root, so both fall empty
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="old/")
    builder.add_photo("B.CR2", "2019-02-14T10:00:00", folder="older/")
    plan, settings = make_plan(builder, tmp_path)
    result = execute(plan, settings)
    assert result.folders_pruned == 2
    assert not builder.query(
        "SELECT 1 FROM AgLibraryFolder WHERE pathFromRoot IN ('old/', 'older/')"
    )
    assert not (builder.images_dir / "old").exists()


def test_keeping_empty_folders(builder, tmp_path):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="old/")
    builder.add_photo("B.CR2", "2019-02-14T10:00:00", folder="older/")
    plan, settings = make_plan(builder, tmp_path, prune_empty_folders=False)
    execute(plan, settings)
    assert builder.query("SELECT 1 FROM AgLibraryFolder WHERE pathFromRoot = 'old/'")


# -- new-tree placement -------------------------------------------------------


def test_new_tree_registers_a_second_root_folder(builder, tmp_path):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00")
    target = tmp_path / "sorted"
    target.mkdir()
    plan, settings = make_plan(
        builder,
        tmp_path,
        placement="new-tree",
        target_root=str(target),
        structure=("{yyyy}", "{mm}"),
    )
    execute(plan, settings)
    roots = [row[0] for row in builder.query("SELECT absolutePath FROM AgLibraryRootFolder")]
    assert str(target) + "/" in roots
    assert (target / "2019" / "01" / "A.CR2").exists()
    for path in builder.catalog_paths():
        assert os.path.exists(path)


# -- failure and rollback -----------------------------------------------------


def test_rollback_restores_everything_when_a_move_fails(simple_catalog, tmp_path, monkeypatch):
    plan, settings = make_plan(simple_catalog, tmp_path)
    before_paths = simple_catalog.catalog_paths()
    before_disk = sorted(p.name for p in simple_catalog.images_dir.iterdir())

    import lrfoldercraft.executor as executor_module

    real_move = executor_module._move_file
    calls = {"n": 0}

    def flaky(source, target, cross_volume):
        calls["n"] += 1
        if calls["n"] == 4:
            raise OSError("simulated disk failure")
        return real_move(source, target, cross_volume)

    monkeypatch.setattr(executor_module, "_move_file", flaky)

    with pytest.raises(OSError, match="simulated disk failure"):
        execute(plan, settings)

    # the catalog transaction was never committed ...
    assert simple_catalog.catalog_paths() == before_paths
    # ... and every already moved file is back where it started
    assert sorted(p.name for p in simple_catalog.images_dir.iterdir()) == before_disk
    for path in before_paths:
        assert os.path.exists(path)


def test_existing_target_is_never_overwritten(builder, tmp_path):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", content=b"original")
    plan, settings = make_plan(builder, tmp_path)
    # plant a stranger *after* planning, so the planner could not see it
    target_dir = builder.images_dir / "2019-01-03"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "A.CR2").write_bytes(b"stranger")

    with pytest.raises(ExecutionError, match="refusing to overwrite"):
        execute(plan, settings)
    assert (target_dir / "A.CR2").read_bytes() == b"stranger"
    assert (builder.images_dir / "A.CR2").read_bytes() == b"original"


def test_preflight_blocks_a_locked_catalog(simple_catalog, tmp_path):
    from lrfoldercraft.catalog.db import lock_file_for

    plan, settings = make_plan(simple_catalog, tmp_path)
    lock = lock_file_for(Path(simple_catalog.catalog_path))
    lock.write_text("locked", encoding="utf-8")
    try:
        checks = preflight(plan)
        assert not checks.ok
        assert any(c.name == "lightroom-closed" for c in checks.errors)
        with pytest.raises(ExecutionError, match="pre-flight failed"):
            execute(plan, settings)
    finally:
        lock.unlink()


# -- journal and undo ----------------------------------------------------------


def test_journal_records_every_step(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)
    records = read_journal(result.journal_path)
    events = [r["event"] for r in records]
    assert events[0] == "run-start"
    assert "backup" in events
    assert events.count("move-done") == 6
    assert "catalog-commit" in events
    assert records[-1]["event"] == "run-end"
    assert records[-1]["status"] == "success"


def test_undo_restores_files_and_catalog(simple_catalog, tmp_path):
    before_paths = simple_catalog.catalog_paths()
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)
    assert (simple_catalog.images_dir / "2019-01-03" / "A0001.CR2").exists()

    undo_result = undo(result.journal_path)

    assert undo_result.success, undo_result.errors
    assert simple_catalog.catalog_paths() == before_paths
    for path in before_paths:
        assert os.path.exists(path), path
    assert not (simple_catalog.images_dir / "2019-01-03").exists()


def test_backup_helper_verifies_the_copy(simple_catalog, tmp_path):
    target = backup_catalog(Path(simple_catalog.catalog_path), tmp_path / "b")
    assert target.exists()
    assert target.read_bytes() == Path(simple_catalog.catalog_path).read_bytes()


def test_swap_cycle_between_two_folders(builder, tmp_path):
    """a/X -> b/ and b/X -> a/ must not trip the unique index."""
    builder.add_photo("X.CR2", "2019-01-03T10:00:00", folder="b/", content=b"one")
    builder.add_photo("X.CR2", "2019-02-14T10:00:00", folder="a/", content=b"two")
    plan, settings = make_plan(
        builder, tmp_path, structure=("{yyyy}-{mm}-{dd}",), conflict="rename"
    )
    result = execute(plan, settings)
    assert result.success
    for path in builder.catalog_paths():
        assert os.path.exists(path), path
    assert not builder.query(
        "SELECT lc_idx_filename, folder FROM AgLibraryFile "
        "GROUP BY lc_idx_filename, folder HAVING COUNT(*) > 1"
    )


def test_undo_removes_every_directory_the_run_created(builder, tmp_path):
    """Intermediate levels must be journalled too, not only the leaf."""
    builder.add_photo("A.CR2", "2019-01-20T10:00:00", camera="Canon EOS 70D")
    builder.add_photo("B.CR2", "2019-03-12T10:00:00", camera="Canon EOS 70D")
    plan, settings = make_plan(
        builder, tmp_path, structure=("{camera_slug}", "{yyyy}", "{mm}", "{dd}")
    )
    result = execute(plan, settings)
    assert result.success
    assert (builder.images_dir / "canon-eos-70d" / "2019" / "01" / "20").is_dir()

    undo(result.journal_path)

    leftovers = [p for p in builder.images_dir.rglob("*") if p.is_dir()]
    assert leftovers == [], leftovers
    assert (builder.images_dir / "A.CR2").exists()


def test_appledouble_companion_is_actually_moved(builder, tmp_path, monkeypatch):
    """Non-macOS branch: the tool moves ._X itself."""
    monkeypatch.setattr("lrfoldercraft.planner.sys.platform", "linux")
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", content=b"image")
    (builder.images_dir / "._A.CR2").write_bytes(b"resource fork")
    builder.add_photo("B.CR2", "2019-02-14T10:00:00", content=b"image")
    plan, settings = make_plan(builder, tmp_path)
    result = execute(plan, settings)
    assert result.success
    assert (builder.images_dir / "2019-01-03" / "._A.CR2").read_bytes() == b"resource fork"
    assert not (builder.images_dir / "._A.CR2").exists()
