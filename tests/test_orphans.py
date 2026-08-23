"""Files that sit in the library's folders but are not in the catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from lrfoldercraft.catalog import CatalogReader, open_catalog
from lrfoldercraft.config import ConfigError, Settings
from lrfoldercraft.executor import execute, undo
from lrfoldercraft.planner import build_plan


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
    from lrfoldercraft.exceptions_report import collect_findings

    plan, _s = plan_for(library_with_strays, structure=("{yyyy}-{mm}-{dd}",), collect_orphans=True)
    finding = {f.category: f for f in collect_findings(plan)}["orphans"]
    assert finding.count == 3
    assert finding.setting == "--collect-orphans"
    assert finding.samples
