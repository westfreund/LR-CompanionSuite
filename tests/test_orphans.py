"""Files that sit in the library's folders but are not in the catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from lrcompanion.catalog import CatalogReader, open_catalog
from lrcompanion.config import ConfigError, Settings
from lrcompanion.executor import execute, undo
from lrcompanion.planner import build_plan


def plan_for(builder, **kwargs):
    settings = Settings(catalog=str(builder.catalog_path), **kwargs)
    with open_catalog(builder.catalog_path) as conn:
        return build_plan(CatalogReader(conn), settings), settings


@pytest.fixture
def library_with_strays(builder):
    """A catalogued library with the kinds of leftovers a real one collects."""
    builder.add_photo("A0001.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    builder.add_photo("A0002.CR2", "2019-02-14T10:00:00", folder="raw2019/Urlaub/")
    root = builder.images_dir / "raw2019"

    # A sidecar of a catalogued photo -- travels with it, never an orphan.
    (root / "A0001.xmp").write_text("sidecar", encoding="utf-8")
    # Genuine leftovers.
    (root / "Export.tif").write_bytes(b"tif")
    (root / "Urlaub" / "Panorama.dng").write_bytes(b"dng")
    (root / "verwaist.xmp").write_text("no partner", encoding="utf-8")
    # Things that must never be swept.
    (root / ".DS_Store").write_bytes(b"junk")
    (root / "._A0001.CR2").write_bytes(b"appledouble")
    previews = builder.images_dir / "raw2019" / "Katalog Previews.lrdata"
    previews.mkdir()
    (previews / "0001.lrprev").write_bytes(b"preview")
    return builder


def orphan_names(plan):
    return sorted(Path(o.source_path).name for o in plan.orphans)


def test_nothing_is_swept_unless_asked(library_with_strays):
    plan, _s = plan_for(library_with_strays, structure=("{yyyy}-{mm}-{dd}",))
    assert plan.orphans == []
    assert plan.stats.orphans == 0


def test_only_the_real_leftovers_are_collected(library_with_strays):
    plan, _s = plan_for(library_with_strays, structure=("{yyyy}-{mm}-{dd}",), collect_orphans=True)
    assert orphan_names(plan) == ["Export.tif", "Panorama.dng", "verwaist.xmp"]


def test_a_sidecar_of_a_catalogued_photo_is_not_an_orphan(library_with_strays):
    """It belongs to its photo and travels with it."""
    plan, _s = plan_for(library_with_strays, structure=("{yyyy}-{mm}-{dd}",), collect_orphans=True)
    assert "A0001.xmp" not in orphan_names(plan)
    carried = [s for move in plan.moves for s, _t in move.sidecars]
    assert any(name.endswith("A0001.xmp") for name in carried)


def test_lightroom_and_system_files_are_left_alone(library_with_strays):
    plan, _s = plan_for(library_with_strays, structure=("{yyyy}-{mm}-{dd}",), collect_orphans=True)
    names = orphan_names(plan)
    for never in (".DS_Store", "._A0001.CR2", "0001.lrprev"):
        assert never not in names


def test_the_origin_is_visible_inside_the_collection(library_with_strays):
    plan, _s = plan_for(library_with_strays, structure=("{yyyy}-{mm}-{dd}",), collect_orphans=True)
    by_name = {Path(o.source_path).name: o for o in plan.orphans}
    assert by_name["Panorama.dng"].relative_path == str(Path("raw2019") / "Urlaub" / "Panorama.dng")
    assert by_name["Panorama.dng"].target_path.endswith(
        str(Path("_not-in-catalog") / "raw2019" / "Urlaub" / "Panorama.dng")
    )


def test_the_collection_folder_can_be_named(library_with_strays):
    plan, _s = plan_for(
        library_with_strays,
        structure=("{yyyy}-{mm}-{dd}",),
        collect_orphans=True,
        orphan_folder="_ohne_Katalog",
    )
    assert all("_ohne_Katalog" in o.target_path for o in plan.orphans)


def test_a_collection_folder_that_is_a_path_is_refused():
    with pytest.raises(ConfigError):
        Settings(catalog="x.lrcat", collect_orphans=True, orphan_folder="a/b").validate()


def test_a_second_run_does_not_sweep_the_collection_again(library_with_strays, tmp_path):
    """The folder the sweep creates must not become its own next input."""
    plan, settings = plan_for(
        library_with_strays,
        structure=("{yyyy}-{mm}-{dd}",),
        collect_orphans=True,
        dry_run=False,
        backup_dir=str(tmp_path / "backups"),
    )
    result = execute(plan, settings)
    assert result.orphans_moved == 3

    again, _s = plan_for(library_with_strays, structure=("{yyyy}-{mm}-{dd}",), collect_orphans=True)
    assert again.orphans == []


def test_collected_files_come_back_when_the_run_is_undone(library_with_strays, tmp_path):
    before = sorted(
        str(p.relative_to(library_with_strays.images_dir))
        for p in library_with_strays.images_dir.rglob("*")
        if p.is_file()
    )
    plan, settings = plan_for(
        library_with_strays,
        structure=("{yyyy}-{mm}-{dd}",),
        collect_orphans=True,
        dry_run=False,
        backup_dir=str(tmp_path / "backups"),
    )
    result = execute(plan, settings)
    assert result.orphans_moved == 3

    undo(result.journal_path)

    after = sorted(
        str(p.relative_to(library_with_strays.images_dir))
        for p in library_with_strays.images_dir.rglob("*")
        if p.is_file()
    )
    assert after == before


def test_a_dry_run_moves_nothing(library_with_strays, tmp_path):
    plan, settings = plan_for(
        library_with_strays,
        structure=("{yyyy}-{mm}-{dd}",),
        collect_orphans=True,
        dry_run=True,
        backup_dir=str(tmp_path / "backups"),
    )
    result = execute(plan, settings)
    assert result.orphans_moved == 0
    assert (library_with_strays.images_dir / "raw2019" / "Export.tif").exists()


def test_the_sweep_is_reported_so_it_is_never_a_surprise(library_with_strays):
    from lrcompanion.exceptions_report import collect_findings

    plan, _s = plan_for(library_with_strays, structure=("{yyyy}-{mm}-{dd}",), collect_orphans=True)
    finding = {f.category: f for f in collect_findings(plan)}["orphans"]
    assert finding.count == 3
    assert finding.setting == "--collect-orphans"
    assert finding.samples


# -- the collection belongs with the rest of the result ----------------------


def test_the_collection_lands_in_the_target_tree(library_with_strays, tmp_path):
    """Leaving it behind split the result across two folders.

    Afterwards it was not clear which one held the outcome of the run, which is
    exactly the confusion the sweep exists to remove.
    """
    target = tmp_path / "Neu"
    plan, _s = plan_for(
        library_with_strays,
        structure=("{yyyy}-{mm}-{dd}",),
        placement="new-tree",
        target_root=str(target),
        collect_orphans=True,
    )
    assert plan.orphans
    for orphan in plan.orphans:
        assert orphan.target_path.startswith(str(target / "_not-in-catalog"))
    # and the path each file came from is still visible inside it
    by_name = {Path(o.source_path).name: o for o in plan.orphans}
    assert by_name["Panorama.dng"].target_path.endswith(
        str(Path("_not-in-catalog") / "raw2019" / "Urlaub" / "Panorama.dng")
    )


def test_sorting_in_place_puts_it_where_it_always_was(library_with_strays):
    """The two roots are the same directory, so nothing changes."""
    plan, _s = plan_for(library_with_strays, structure=("{yyyy}-{mm}-{dd}",), collect_orphans=True)
    root = library_with_strays.images_dir
    for orphan in plan.orphans:
        assert orphan.target_path.startswith(str(root / "_not-in-catalog"))


def test_a_second_run_into_the_same_target_does_not_sweep_the_collection(
    library_with_strays, tmp_path
):
    """The collection now sits inside the tree the sweep must not walk into."""
    target = tmp_path / "Neu"
    plan, settings = plan_for(
        library_with_strays,
        structure=("{yyyy}-{mm}-{dd}",),
        placement="new-tree",
        target_root=str(target),
        collect_orphans=True,
        dry_run=False,
        backup_dir=str(tmp_path / "backups"),
    )
    result = execute(plan, settings)
    assert result.orphans_moved == 3

    again, _s = plan_for(
        library_with_strays,
        structure=("{yyyy}-{mm}-{dd}",),
        placement="new-tree",
        target_root=str(target),
        collect_orphans=True,
    )
    assert again.orphans == []


def test_the_move_is_marked_as_crossing_a_volume_when_it_does(
    library_with_strays, tmp_path, monkeypatch
):
    """A target on another drive makes it a copy, not a rename.

    Handing os.replace a cross-device path raises EXDEV, so the flag has to
    reach the mover rather than being assumed False.
    """
    import lrcompanion.planner as planner

    # Pretend the target sits on another device, which is what makes the move
    # a copy rather than a rename.
    real = planner._device_of
    target_root = str(tmp_path / "Anderes")
    monkeypatch.setattr(
        planner,
        "_device_of",
        lambda path: -1 if str(path).startswith(target_root) else real(path),
    )
    plan, _s = plan_for(
        library_with_strays,
        structure=("{yyyy}-{mm}-{dd}",),
        placement="new-tree",
        target_root=str(tmp_path / "Anderes"),
        collect_orphans=True,
    )
    assert plan.orphans
    assert all(o.cross_volume for o in plan.orphans)


def test_undo_brings_them_back_from_the_target_tree(library_with_strays, tmp_path):
    before = sorted(
        str(p.relative_to(library_with_strays.images_dir))
        for p in library_with_strays.images_dir.rglob("*")
        if p.is_file()
    )
    plan, settings = plan_for(
        library_with_strays,
        structure=("{yyyy}-{mm}-{dd}",),
        placement="new-tree",
        target_root=str(tmp_path / "Neu"),
        collect_orphans=True,
        dry_run=False,
        backup_dir=str(tmp_path / "backups"),
    )
    result = execute(plan, settings)
    assert result.orphans_moved == 3
    undo(result.journal_path)

    after = sorted(
        str(p.relative_to(library_with_strays.images_dir))
        for p in library_with_strays.images_dir.rglob("*")
        if p.is_file()
    )
    assert after == before
