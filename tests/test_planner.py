"""Planning: grouping, anchors, conflicts, sidecars and edge cases."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lrfoldercraft.catalog import CatalogReader, open_catalog
from lrfoldercraft.config import Settings
from lrfoldercraft.planner import (
    MOVE,
    RENAMED,
    SKIP_CONFLICT,
    SKIP_FILTERED,
    SKIP_MISSING_SOURCE,
    SKIP_NO_DATE,
    STAY,
    PlanError,
    build_plan,
    common_prefix,
)


def plan_for(builder, **kwargs):
    settings = Settings(catalog=str(builder.catalog_path), **kwargs)
    with open_catalog(builder.catalog_path) as conn:
        return build_plan(CatalogReader(conn), settings)


def by_name(plan):
    return {Path(m.source_path).name: m for m in plan.moves}


# -- grouping ---------------------------------------------------------------


def test_day_structure_groups_by_capture_day(simple_catalog):
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",))
    moves = by_name(plan)
    assert moves["A0001.CR2"].target_segments == ("2019-01-03",)
    assert moves["A0002.CR2"].target_segments == ("2019-01-03",)
    assert moves["A0003.CR2"].target_segments == ("2019-02-14",)
    assert moves["A0005.CR2"].target_segments == ("2019-12-29",)
    assert plan.stats.new_folders == 4  # three days plus _unsorted


def test_multi_level_structure_creates_nested_segments(simple_catalog):
    plan = plan_for(simple_catalog, structure=("{yyyy}", "{mm}", "{dd}"))
    assert by_name(plan)["A0001.CR2"].target_segments == ("2019", "01", "03")


def test_camera_level(simple_catalog):
    plan = plan_for(simple_catalog, structure=("{camera_slug}", "{yyyy}-{mm}-{dd}"))
    moves = by_name(plan)
    assert moves["A0001.CR2"].target_segments == ("canon-eos-70d", "2019-01-03")
    assert moves["A0003.CR2"].target_segments == ("canon-eos-5d-mark-iv", "2019-02-14")


def test_virtual_copies_are_counted_not_moved(simple_catalog):
    plan = plan_for(simple_catalog, structure=("{yyyy}",))
    assert by_name(plan)["A0001.CR2"].virtual_copy_count == 2
    assert plan.stats.virtual_copies_carried == 2
    # one row per file, never one per image
    assert plan.stats.total == 6


# -- missing dates ----------------------------------------------------------


def test_undated_photo_goes_to_the_unsorted_folder(simple_catalog):
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",))
    move = by_name(plan)["A0006.CR2"]
    assert move.target_segments == ("_unsorted",)
    assert move.status == MOVE


def test_on_missing_date_skip(simple_catalog):
    plan = plan_for(
        simple_catalog, structure=("{yyyy}-{mm}-{dd}",), on_missing_date="skip"
    )
    assert by_name(plan)["A0006.CR2"].status == SKIP_NO_DATE
    assert plan.stats.skipped_no_date == 1


def test_on_missing_date_abort(simple_catalog):
    with pytest.raises(PlanError, match="no usable capture date"):
        plan_for(
            simple_catalog, structure=("{yyyy}-{mm}-{dd}",), on_missing_date="abort"
        )


def test_file_mtime_fallback(builder):
    builder.add_photo("NODATE.CR2", capture_time=None, camera=None)
    os.utime(builder.images_dir / "NODATE.CR2", (1_500_000_000, 1_500_000_000))
    plan = plan_for(
        builder, structure=("{yyyy}",), date_source=("capture", "file-mtime")
    )
    assert by_name(plan)["NODATE.CR2"].target_segments == ("2017",)


def test_exif_field_fallback_when_capture_time_is_junk(builder):
    builder.add_photo("ODD.CR2", capture_time="2019-05-06T00:00:00")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",), date_source=("exif-fields",))
    assert by_name(plan)["ODD.CR2"].target_segments == ("2019-05-06",)


def test_structure_without_date_tokens_needs_no_date(builder):
    builder.add_photo("X.CR2", capture_time=None, camera="Canon EOS 70D")
    plan = plan_for(builder, structure=("{camera_slug}",))
    assert by_name(plan)["X.CR2"].target_segments == ("canon-eos-70d",)


# -- already in place -------------------------------------------------------


def test_file_already_in_its_target_folder_stays(builder):
    builder.add_photo("IN.CR2", "2019-01-03T10:00:00", folder="2019-01-03/")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    move = by_name(plan)["IN.CR2"]
    assert move.status == STAY
    assert plan.stats.already_in_place == 1
    assert not plan.has_work


# -- conflicts --------------------------------------------------------------


def test_collision_between_two_source_folders_is_renamed(builder):
    builder.add_photo("SAME.CR2", "2019-01-03T10:00:00", folder="a/")
    builder.add_photo("SAME.CR2", "2019-01-03T11:00:00", folder="b/")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    statuses = sorted(m.status for m in plan.moves)
    assert statuses == [MOVE, RENAMED]
    renamed = next(m for m in plan.moves if m.status == RENAMED)
    assert renamed.target_filename == "SAME_1.CR2"
    assert plan.stats.to_rename == 1


def test_conflict_skip_mode(builder):
    builder.add_photo("SAME.CR2", "2019-01-03T10:00:00", folder="a/")
    builder.add_photo("SAME.CR2", "2019-01-03T11:00:00", folder="b/")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",), conflict="skip")
    assert sorted(m.status for m in plan.moves) == [MOVE, SKIP_CONFLICT]
    assert plan.stats.skipped_conflict == 1


def test_conflict_abort_mode(builder):
    builder.add_photo("SAME.CR2", "2019-01-03T10:00:00", folder="a/")
    builder.add_photo("SAME.CR2", "2019-01-03T11:00:00", folder="b/")
    with pytest.raises(PlanError, match="name collision"):
        plan_for(builder, structure=("{yyyy}-{mm}-{dd}",), conflict="abort")


def test_stray_file_at_the_target_is_never_overwritten(builder):
    builder.add_photo("P.CR2", "2019-01-03T10:00:00")
    target_dir = builder.images_dir / "2019-01-03"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "P.CR2").write_bytes(b"a stranger")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    move = by_name(plan)["P.CR2"]
    assert move.status == RENAMED
    assert move.target_filename == "P_1.CR2"


# -- sidecars ---------------------------------------------------------------


def test_sidecar_travels_with_its_master(simple_catalog):
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",))
    move = by_name(plan)["A0001.CR2"]
    assert len(move.sidecars) == 1
    source, target = move.sidecars[0]
    assert Path(source).name == "A0001.xmp"
    assert target.endswith("2019-01-03/A0001.xmp")


def test_sidecar_is_found_only_once_on_case_insensitive_filesystems(builder):
    """Probing name.xmp and name.XMP must not report the same file twice."""
    builder.add_photo("C.CR2", "2019-01-03T10:00:00", sidecars=["C.xmp"])
    plan = plan_for(builder, structure=("{yyyy}",))
    assert len(by_name(plan)["C.CR2"].sidecars) == 1


def test_dotted_sidecar_convention(builder):
    builder.add_photo("D.CR2", "2019-01-03T10:00:00", sidecars=["D.CR2.xmp"])
    plan = plan_for(builder, structure=("{yyyy}",))
    sidecars = by_name(plan)["D.CR2"].sidecars
    assert len(sidecars) == 1
    assert Path(sidecars[0][0]).name == "D.CR2.xmp"


def test_sidecars_can_be_disabled(simple_catalog):
    plan = plan_for(simple_catalog, structure=("{yyyy}",), move_sidecars=False)
    assert by_name(plan)["A0001.CR2"].sidecars == ()


def test_renamed_file_keeps_its_sidecar_glued(builder):
    builder.add_photo("E.CR2", "2019-01-03T10:00:00", folder="a/", sidecars=["E.xmp"])
    builder.add_photo("E.CR2", "2019-01-03T11:00:00", folder="b/", sidecars=["E.xmp"])
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    renamed = next(m for m in plan.moves if m.status == RENAMED)
    assert Path(renamed.sidecars[0][1]).name == "E_1.xmp"


# -- filters and missing files ----------------------------------------------


def test_extension_filters(simple_catalog):
    plan = plan_for(simple_catalog, structure=("{yyyy}",), include_extensions=("cr2",))
    assert by_name(plan)["A0004.JPG"].status == SKIP_FILTERED
    assert by_name(plan)["A0001.CR2"].status == MOVE

    plan = plan_for(simple_catalog, structure=("{yyyy}",), exclude_extensions=("jpg",))
    assert by_name(plan)["A0004.JPG"].status == SKIP_FILTERED


def test_missing_file_is_reported_and_skipped(builder):
    builder.add_photo("GHOST.CR2", "2019-01-03T10:00:00", on_disk=False)
    plan = plan_for(builder, structure=("{yyyy}",))
    assert by_name(plan)["GHOST.CR2"].status == SKIP_MISSING_SOURCE
    assert plan.stats.missing_source == 1
    assert any("missing on disk" in w for w in plan.warnings)


# -- anchors ----------------------------------------------------------------


def test_anchor_is_the_common_parent_of_the_selection(builder):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="archive/2019/")
    builder.add_photo("B.CR2", "2019-02-03T10:00:00", folder="archive/2019/")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    assert plan.anchor_segments == ("archive", "2019")
    assert by_name(plan)["A.CR2"].target_segments == ("archive", "2019", "2019-01-03")


def test_anchor_drops_to_the_shared_prefix(builder):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="archive/2019/")
    builder.add_photo("B.CR2", "2019-02-03T10:00:00", folder="archive/2020/")
    plan = plan_for(builder, structure=("{yyyy}",))
    assert plan.anchor_segments == ("archive",)


def test_explicit_anchor_folder(builder):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="archive/2019/")
    folder_id = builder.folders["archive/"]
    plan = plan_for(builder, structure=("{yyyy}",), anchor_folder_id=folder_id)
    assert plan.anchor_segments == ("archive",)


def test_new_tree_placement_starts_at_the_target_root(builder, tmp_path):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="old/")
    target = tmp_path / "sorted"
    plan = plan_for(
        builder, structure=("{yyyy}", "{mm}"), placement="new-tree", target_root=str(target)
    )
    assert plan.anchor_segments == ()
    assert plan.target_root_path == str(target)
    assert by_name(plan)["A.CR2"].target_path == str(target / "2019" / "01" / "A.CR2")


def test_common_prefix():
    assert common_prefix([("a", "b", "c"), ("a", "b", "d")]) == ("a", "b")
    assert common_prefix([("a",), ("b",)]) == ()
    assert common_prefix([]) == ()


def test_folder_selection_limits_the_plan(builder):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="one/")
    builder.add_photo("B.CR2", "2019-01-03T10:00:00", folder="two/")
    plan = plan_for(builder, structure=("{yyyy}",), folder_ids=(builder.folders["one/"],))
    assert plan.stats.total == 1


def test_empty_selection_raises(builder):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00")
    with pytest.raises(PlanError, match="no photos matched"):
        plan_for(builder, structure=("{yyyy}",), folder_ids=(999999,))


# -- idempotency ------------------------------------------------------------


def test_rerun_on_an_already_sorted_library_is_a_no_op(builder):
    """The second run must not nest 2019-01-03 inside 2019-01-03."""
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="2019-01-03/")
    builder.add_photo("B.CR2", "2019-02-14T10:00:00", folder="2019-02-14/")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    assert plan.anchor_segments == ()
    assert all(m.status == STAY for m in plan.moves)
    assert not plan.has_work


def test_single_already_sorted_folder_is_also_a_no_op(builder):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="2019-01-03/")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    assert plan.anchor_segments == ()
    assert by_name(plan)["A.CR2"].status == STAY


def test_multi_level_rerun_is_a_no_op(builder):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="2019/01/03/")
    plan = plan_for(builder, structure=("{yyyy}", "{mm}", "{dd}"))
    assert plan.anchor_segments == ()
    assert by_name(plan)["A.CR2"].status == STAY


def test_anchor_is_kept_when_it_is_not_a_rendered_level(builder):
    """A flat source folder must stay the anchor, even if it looks date-ish."""
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    builder.add_photo("B.CR2", "2019-02-14T10:00:00", folder="raw2019/")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    assert plan.anchor_segments == ("raw2019",)
    assert by_name(plan)["A.CR2"].target_segments == ("raw2019", "2019-01-03")


def test_mtime_is_not_a_default_date_source(builder):
    """Silently filing a photo under its file date would be wrong."""
    builder.add_photo("NODATE.CR2", capture_time=None, camera=None)
    plan = plan_for(
        builder, structure=("{yyyy}",), on_missing_date="skip"
    )
    assert by_name(plan)["NODATE.CR2"].status == SKIP_NO_DATE
