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
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",), on_missing_date="skip")
    assert by_name(plan)["A0006.CR2"].status == SKIP_NO_DATE
    assert plan.stats.skipped_no_date == 1


def test_on_missing_date_abort(simple_catalog):
    with pytest.raises(PlanError, match="no usable capture date"):
        plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",), on_missing_date="abort")


def test_file_mtime_fallback(builder):
    builder.add_photo("NODATE.CR2", capture_time=None, camera=None)
    os.utime(builder.images_dir / "NODATE.CR2", (1_500_000_000, 1_500_000_000))
    plan = plan_for(builder, structure=("{yyyy}",), date_source=("capture", "file-mtime"))
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
    plan = plan_for(builder, structure=("{yyyy}",), on_missing_date="skip")
    assert by_name(plan)["NODATE.CR2"].status == SKIP_NO_DATE


def test_rerun_when_the_anchor_covers_only_part_of_the_structure(builder):
    """One camera, one year -> the common parent is only the first 2 of 4 levels."""
    builder.add_photo(
        "A.CR2", "2019-01-20T10:00:00", camera="Canon EOS 70D", folder="canon-eos-70d/2019/01/20/"
    )
    builder.add_photo(
        "B.CR2", "2019-03-12T10:00:00", camera="Canon EOS 70D", folder="canon-eos-70d/2019/03/12/"
    )
    plan = plan_for(builder, structure=("{camera_slug}", "{yyyy}", "{mm}", "{dd}"))
    assert plan.anchor_segments == ()
    assert all(m.status == STAY for m in plan.moves)
    assert not plan.has_work


def test_rerun_with_a_single_overlapping_level(builder):
    """Photos already in year folders, asked for year/month/day."""
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="archive/2019/")
    builder.add_photo("B.CR2", "2019-02-14T10:00:00", folder="archive/2019/")
    plan = plan_for(builder, structure=("{yyyy}", "{mm}", "{dd}"))
    # 'archive/2019' ends with the structure's first level, so it is not repeated
    assert plan.anchor_segments == ("archive",)
    assert by_name(plan)["A.CR2"].target_segments == ("archive", "2019", "01", "03")


def test_a_date_ish_source_folder_is_not_mistaken_for_a_level(builder):
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    builder.add_photo("B.CR2", "2019-02-14T10:00:00", folder="raw2019/")
    plan = plan_for(builder, structure=("{yyyy}", "{mm}", "{dd}"))
    assert plan.anchor_segments == ("raw2019",)
    assert by_name(plan)["A.CR2"].target_segments == ("raw2019", "2019", "01", "03")


def test_deeper_partial_overlap(builder):
    """Common parent covers three of four levels."""
    builder.add_photo(
        "A.CR2", "2019-01-20T09:00:00", camera="Canon EOS 70D", folder="canon-eos-70d/2019/01/20/"
    )
    builder.add_photo(
        "B.CR2", "2019-01-21T09:00:00", camera="Canon EOS 70D", folder="canon-eos-70d/2019/01/21/"
    )
    plan = plan_for(builder, structure=("{camera_slug}", "{yyyy}", "{mm}", "{dd}"))
    assert plan.anchor_segments == ()
    assert all(m.status == STAY for m in plan.moves)


# -- AppleDouble companions -------------------------------------------------
#
# On macOS the kernel moves ._X together with X, so the tool must NOT move it
# again. Elsewhere ._X is an ordinary file that a rename leaves behind, so it
# must be carried along. Both branches are exercised by faking sys.platform.


def test_macos_leaves_appledouble_to_the_kernel(builder, monkeypatch):
    """Measured behaviour: macOS moves ._X itself; moving it again collides."""
    monkeypatch.setattr("lrfoldercraft.planner.sys.platform", "darwin")
    builder.add_photo("A.CR2", "2019-01-03T10:00:00")
    (builder.images_dir / "._A.CR2").write_bytes(b"resource fork")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    assert by_name(plan)["A.CR2"].sidecars == ()


def test_other_platforms_carry_the_appledouble_along(builder, monkeypatch):
    monkeypatch.setattr("lrfoldercraft.planner.sys.platform", "linux")
    builder.add_photo("A.CR2", "2019-01-03T10:00:00")
    (builder.images_dir / "._A.CR2").write_bytes(b"resource fork")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    targets = {Path(t).name for _, t in by_name(plan)["A.CR2"].sidecars}
    assert targets == {"._A.CR2"}


def test_appledouble_moves_even_with_sidecars_disabled(builder, monkeypatch):
    """It is part of the file, not a document beside it."""
    monkeypatch.setattr("lrfoldercraft.planner.sys.platform", "linux")
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", sidecars=["A.xmp"])
    (builder.images_dir / "._A.CR2").write_bytes(b"resource fork")
    plan = plan_for(builder, structure=("{yyyy}",), move_sidecars=False)
    names = {Path(s).name for s, _ in by_name(plan)["A.CR2"].sidecars}
    assert names == {"._A.CR2"}  # the xmp stays, the companion travels


def test_appledouble_follows_a_renamed_photo(builder, monkeypatch):
    monkeypatch.setattr("lrfoldercraft.planner.sys.platform", "linux")
    builder.add_photo("SAME.CR2", "2019-01-03T10:00:00", folder="a/")
    builder.add_photo("SAME.CR2", "2019-01-03T11:00:00", folder="b/")
    (builder.images_dir / "b" / "._SAME.CR2").write_bytes(b"resource fork")
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    renamed = next(m for m in plan.moves if m.status == RENAMED)
    if "/b/" in renamed.source_path:
        targets = {Path(t).name for _, t in renamed.sidecars}
        assert "._SAME_1.CR2" in targets


def test_no_companion_means_no_extra_move(builder, monkeypatch):
    monkeypatch.setattr("lrfoldercraft.planner.sys.platform", "linux")
    builder.add_photo("A.CR2", "2019-01-03T10:00:00")
    plan = plan_for(builder, structure=("{yyyy}",))
    assert by_name(plan)["A.CR2"].sidecars == ()


def test_companion_is_never_treated_as_a_sidecar_document(builder, monkeypatch):
    """._A.CR2 must be reported once, not twice."""
    monkeypatch.setattr("lrfoldercraft.planner.sys.platform", "linux")
    builder.add_photo("A.CR2", "2019-01-03T10:00:00")
    (builder.images_dir / "._A.CR2").write_bytes(b"resource fork")
    plan = plan_for(builder, structure=("{yyyy}",))
    sources = [s for s, _ in by_name(plan)["A.CR2"].sidecars]
    assert len(sources) == len(set(sources)) == 1


# -- existing folder structure ----------------------------------------------


@pytest.fixture
def mixed_library(builder):
    """A grown library: flat files, topic folders and already dated folders."""
    builder.add_photo("FLACH.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    builder.add_photo("U1.CR2", "2019-01-03T11:00:00", folder="raw2019/Urlaub/")
    builder.add_photo("U2.CR2", "2019-05-20T11:00:00", folder="raw2019/Urlaub/")
    builder.add_photo("F1.CR2", "2019-02-14T11:00:00", folder="raw2019/Familie/")
    builder.add_photo("D1.CR2", "2019-03-10T11:00:00", folder="raw2019/2019-03-10/")
    builder.add_photo("D2.CR2", "2019-04-15T11:00:00", folder="raw2019/2019-04-15 Ostern in Tirol/")
    builder.add_photo("D3.CR2", "2019-06-01T11:00:00", folder="raw2019/2019_06_01 Hochzeit/")
    builder.add_photo("X1.CR2", "2019-07-07T11:00:00", folder="raw2019/2019-04-15 Ostern in Tirol/")
    return builder


def test_dated_folders_with_descriptive_text_are_kept(mixed_library):
    plan = plan_for(mixed_library, structure=("{yyyy}-{mm}-{dd}",))
    moves = by_name(plan)
    assert moves["D1.CR2"].status == STAY  # 2019-03-10
    assert moves["D2.CR2"].status == STAY  # 2019-04-15 Ostern in Tirol
    assert moves["D3.CR2"].status == STAY  # 2019_06_01 Hochzeit


def test_a_misplaced_photo_leaves_a_kept_dated_folder(mixed_library):
    plan = plan_for(mixed_library, structure=("{yyyy}-{mm}-{dd}",))
    move = by_name(plan)["X1.CR2"]  # shot 07-07, sits in 04-15
    assert move.status == MOVE
    assert move.target_segments == ("raw2019", "2019-07-07")


def test_mismatch_action_leave_keeps_it(mixed_library):
    plan = plan_for(mixed_library, structure=("{yyyy}-{mm}-{dd}",), mismatch_action="leave")
    assert by_name(plan)["X1.CR2"].status == STAY


def test_topic_folders_are_consolidated_by_default(mixed_library):
    plan = plan_for(mixed_library, structure=("{yyyy}-{mm}-{dd}",))
    assert by_name(plan)["U1.CR2"].target_segments == ("raw2019", "2019-01-03")
    assert by_name(plan)["F1.CR2"].target_segments == ("raw2019", "2019-02-14")


def test_topic_folders_can_be_sorted_internally(mixed_library):
    plan = plan_for(mixed_library, structure=("{yyyy}-{mm}-{dd}",), subfolder_action="sort-inside")
    moves = by_name(plan)
    assert moves["U1.CR2"].target_segments == ("raw2019", "Urlaub", "2019-01-03")
    assert moves["U2.CR2"].target_segments == ("raw2019", "Urlaub", "2019-05-20")
    assert moves["F1.CR2"].target_segments == ("raw2019", "Familie", "2019-02-14")
    assert moves["FLACH.CR2"].target_segments == ("raw2019", "2019-01-03")


def test_topic_folders_can_be_left_alone(mixed_library):
    plan = plan_for(mixed_library, structure=("{yyyy}-{mm}-{dd}",), subfolder_action="leave")
    moves = by_name(plan)
    assert moves["U1.CR2"].status == STAY
    assert moves["F1.CR2"].status == STAY
    assert moves["FLACH.CR2"].status == MOVE  # the anchor itself still sorts


def test_dated_folders_can_be_dissolved(mixed_library):
    plan = plan_for(
        mixed_library,
        structure=("{yyyy}-{mm}-{dd}",),
        dated_folder_action="consolidate",
    )
    assert by_name(plan)["D2.CR2"].target_segments == ("raw2019", "2019-04-15")
    assert by_name(plan)["D3.CR2"].target_segments == ("raw2019", "2019-06-01")


def test_one_folder_can_be_decided_differently(mixed_library):
    urlaub = mixed_library.folders["raw2019/Urlaub/"]
    plan = plan_for(
        mixed_library,
        structure=("{yyyy}-{mm}-{dd}",),
        folder_actions={urlaub: "sort-inside"},
    )
    moves = by_name(plan)
    assert moves["U1.CR2"].target_segments == ("raw2019", "Urlaub", "2019-01-03")
    assert moves["F1.CR2"].target_segments == ("raw2019", "2019-02-14")  # Familie unchanged


def test_the_operator_is_asked_and_answered(mixed_library):
    asked = []

    def decide(case):
        asked.append(case.path_from_root)
        return "leave" if case.name == "Urlaub" else None

    settings = Settings(catalog=str(mixed_library.catalog_path), structure=("{yyyy}-{mm}-{dd}",))
    with open_catalog(mixed_library.catalog_path) as conn:
        plan = build_plan(CatalogReader(conn), settings, decide=decide)

    assert "raw2019/Urlaub/" in asked
    assert "raw2019/" not in asked  # never asked about the anchor
    moves = by_name(plan)
    assert moves["U1.CR2"].status == STAY
    assert moves["F1.CR2"].status == MOVE
    urlaub = next(c for c in plan.folder_cases if c.name == "Urlaub")
    assert urlaub.action_source == "operator"


def test_an_explicit_override_beats_the_operator(mixed_library):
    urlaub = mixed_library.folders["raw2019/Urlaub/"]
    settings = Settings(
        catalog=str(mixed_library.catalog_path),
        structure=("{yyyy}-{mm}-{dd}",),
        folder_actions={urlaub: "sort-inside"},
    )
    with open_catalog(mixed_library.catalog_path) as conn:
        plan = build_plan(CatalogReader(conn), settings, decide=lambda case: "leave")
    assert by_name(plan)["U1.CR2"].target_segments == ("raw2019", "Urlaub", "2019-01-03")


def test_folder_cases_are_reported(mixed_library):
    plan = plan_for(mixed_library, structure=("{yyyy}-{mm}-{dd}",))
    kinds = {c.path_from_root: c.kind for c in plan.folder_cases}
    assert kinds["raw2019/2019-04-15 Ostern in Tirol/"] == "dated"
    assert kinds["raw2019/Urlaub/"] == "plain"
    ostern = next(c for c in plan.folder_cases if c.name == "2019-04-15 Ostern in Tirol")
    assert ostern.matching_photos == 1 and ostern.mismatched_photos == 1


def test_sorting_inside_is_idempotent(mixed_library):
    """A second run must not build Urlaub/2019-01-03/2019-01-03."""
    import shutil

    from lrfoldercraft.executor import execute

    settings = Settings(
        catalog=str(mixed_library.catalog_path),
        structure=("{yyyy}-{mm}-{dd}",),
        subfolder_action="sort-inside",
        dry_run=False,
        backup_dir=str(mixed_library.root / "backups"),
    )
    with open_catalog(mixed_library.catalog_path) as conn:
        plan = build_plan(CatalogReader(conn), settings)
    execute(plan, settings)

    with open_catalog(mixed_library.catalog_path) as conn:
        plan2 = build_plan(CatalogReader(conn), settings)
    assert not plan2.has_work, [(m.source_path, m.target_path) for m in plan2.active_moves]
    del shutil


# -- several root folders in one run ----------------------------------------


@pytest.fixture
def two_roots(builder, tmp_path):
    """A catalog whose photos live under two root folders, as on two drives."""
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    builder.add_photo("B.CR2", "2019-02-14T10:00:00", folder="raw2019/")
    second = tmp_path / "drive2" / "Fotos2020"
    root_id = builder.add_root_folder(second, "Fotos2020")
    builder.add_photo_to_root(root_id, "C.CR2", "2020-05-05T10:00:00")
    builder.add_photo_to_root(root_id, "D.CR2", "2020-06-06T10:00:00")
    return builder, root_id, second


def test_a_run_spans_several_root_folders(two_roots):
    builder, _root_id, second = two_roots
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    assert len(plan.scopes) == 2
    assert plan.spans_several_roots
    assert plan.stats.to_move == 4
    assert any("spans 2 root folders" in w for w in plan.warnings)


def test_each_root_gets_its_own_anchor(two_roots):
    builder, _root_id, second = two_roots
    plan = plan_for(builder, structure=("{yyyy}-{mm}-{dd}",))
    anchors = {sc.root_folder.name: sc.anchor_segments for sc in plan.scopes}
    assert anchors["images"] == ("raw2019",)  # both photos sit in raw2019
    assert anchors["Fotos2020"] == ()  # they sit in the root itself
    moves = by_name(plan)
    assert moves["A.CR2"].target_segments == ("raw2019", "2019-01-03")
    assert moves["C.CR2"].target_segments == ("2020-05-05",)


def test_moves_carry_their_scope(two_roots):
    builder, _root_id, second = two_roots
    plan = plan_for(builder, structure=("{yyyy}",))
    scopes = {m.filename: plan.scope_for(m).root_folder.name for m in plan.moves}
    assert scopes["A.CR2"] == "images"
    assert scopes["C.CR2"] == "Fotos2020"


def test_one_root_can_still_be_selected(two_roots):
    builder, root_id, second = two_roots
    plan = plan_for(builder, structure=("{yyyy}",), root_folder_id=root_id)
    assert len(plan.scopes) == 1
    assert plan.stats.total == 2


def test_an_anchor_from_another_root_is_refused(two_roots):
    builder, root_id, second = two_roots
    other = builder.folders["raw2019/"]
    with pytest.raises(PlanError, match="different root folder"):
        plan_for(builder, structure=("{yyyy}",), root_folder_id=root_id, anchor_folder_id=other)


def test_new_tree_merges_every_root_into_one(two_roots, tmp_path):
    builder, _root_id, second = two_roots
    target = tmp_path / "Sortiert"
    plan = plan_for(builder, structure=("{yyyy}",), placement="new-tree", target_root=str(target))
    assert len(plan.scopes) == 1
    assert all(m.target_path.startswith(str(target)) for m in plan.active_moves)


def test_a_repeated_new_tree_run_is_a_no_op(builder, tmp_path):
    """Photos already in the new tree must be recognised, not moved onto themselves."""
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    builder.add_photo("B.CR2", "2019-02-14T10:00:00", folder="raw2019/")
    target = tmp_path / "Sortiert"

    from lrfoldercraft.executor import execute

    settings = Settings(
        catalog=str(builder.catalog_path),
        structure=("{camera_slug}", "{yyyy}", "{mm}", "{dd}"),
        placement="new-tree",
        target_root=str(target),
        dry_run=False,
        backup_dir=str(tmp_path / "b"),
    )
    with open_catalog(builder.catalog_path) as conn:
        plan = build_plan(CatalogReader(conn), settings)
    execute(plan, settings)

    with open_catalog(builder.catalog_path) as conn:
        again = build_plan(CatalogReader(conn), settings)
    assert not again.has_work, [(m.source_path, m.target_path) for m in again.active_moves]
    assert again.stats.already_in_place == 2


# -- rebuilding a folder where it stands ------------------------------------


def test_resort_splits_a_dated_folder_below_its_own_parent(mixed_library):
    """'2019-04-15 Ostern in Tirol' becomes '2019-04-15/Ostern in Tirol'."""
    plan = plan_for(
        mixed_library,
        structure=("{yyyy}-{mm}-{dd}", "{folder_label}"),
        dated_folder_action="resort",
        mismatch_action="move-out",
    )
    moves = by_name(plan)
    assert moves["D2.CR2"].target_segments == ("raw2019", "2019-04-15", "Ostern in Tirol")
    assert moves["D3.CR2"].target_segments == ("raw2019", "2019-06-01", "Hochzeit")
    # A folder with nothing but a date has no text level to build.
    assert moves["D1.CR2"].target_segments == ("raw2019", "2019-03-10")


def test_resort_does_not_drag_photos_out_of_their_parent(mixed_library):
    """The difference to consolidate: raw2019 is kept, not bypassed."""
    plan = plan_for(
        mixed_library,
        structure=("{yyyy}-{mm}-{dd}", "{folder_label}"),
        dated_folder_action="resort",
    )
    for move in plan.moves:
        if move.status == MOVE:
            assert move.target_segments[0] == "raw2019"


def test_resort_keeps_a_session_that_ran_past_midnight_together(mixed_library):
    """X1 was shot 07-07 but belongs to the 04-15 session it sits in.

    Filing it by its own date would tear the session in two, which is exactly
    what mismatch-action=leave forbids.
    """
    plan = plan_for(
        mixed_library,
        structure=("{yyyy}-{mm}-{dd}", "{folder_label}"),
        dated_folder_action="resort",
        mismatch_action="leave",
    )
    moves = by_name(plan)
    assert moves["X1.CR2"].target_segments == ("raw2019", "2019-04-15", "Ostern in Tirol")
    assert moves["D2.CR2"].target_segments == moves["X1.CR2"].target_segments


def test_resort_files_a_stray_photo_by_its_own_date_when_asked_to(mixed_library):
    plan = plan_for(
        mixed_library,
        structure=("{yyyy}-{mm}-{dd}", "{folder_label}"),
        dated_folder_action="resort",
        mismatch_action="move-out",
    )
    assert by_name(plan)["X1.CR2"].target_segments == (
        "raw2019",
        "2019-07-07",
        "Ostern in Tirol",
    )


def test_an_empty_level_collapses_instead_of_becoming_unnamed(mixed_library):
    plan = plan_for(
        mixed_library,
        structure=("{yyyy}", "{folder_label}", "{mm}-{dd}"),
        subfolder_action="consolidate",
    )
    # FLACH sits in the anchor itself, which carries no date and no text.
    assert by_name(plan)["FLACH.CR2"].target_segments == ("raw2019", "2019", "01-03")


# -- the ordered rule list, end to end --------------------------------------


def test_rules_decide_whole_classes_of_folders_at_once(mixed_library):
    """The four lines that express a grown library, instead of one per folder."""
    plan = plan_for(
        mixed_library,
        structure=("{yyyy}-{mm}-{dd}", "{folder_label}"),
        folder_rules=("Urlaub=leave", "dated+label=resort", "dated=keep", "*=sort-inside"),
        mismatch_action="leave",
    )
    moves = by_name(plan)
    assert moves["U1.CR2"].status == STAY  # rule 1
    assert moves["D2.CR2"].target_segments == ("raw2019", "2019-04-15", "Ostern in Tirol")
    assert moves["D1.CR2"].status == STAY  # rule 3, bare date kept
    assert moves["F1.CR2"].target_segments == ("raw2019", "Familie", "2019-02-14")


def test_a_rule_records_which_line_decided_the_folder(mixed_library):
    plan = plan_for(
        mixed_library,
        structure=("{yyyy}-{mm}-{dd}",),
        folder_rules=("Urlaub=leave", "*=consolidate"),
    )
    cases = {case.name: case for case in plan.folder_cases}
    assert cases["Urlaub"].action_source == "rule"
    assert cases["Urlaub"].matched_rule == "1. Urlaub"
    assert cases["Familie"].matched_rule == "2. *"


def test_a_manual_decision_still_beats_a_rule(mixed_library):
    urlaub = mixed_library.folders["raw2019/Urlaub/"]
    plan = plan_for(
        mixed_library,
        structure=("{yyyy}-{mm}-{dd}",),
        folder_rules=("*=leave",),
        folder_actions={urlaub: "sort-inside"},
    )
    cases = {case.name: case for case in plan.folder_cases}
    assert cases["Urlaub"].action_source == "override"
    assert by_name(plan)["U1.CR2"].target_segments == ("raw2019", "Urlaub", "2019-01-03")


def test_a_rule_silences_the_question_it_already_answers(mixed_library):
    """Rules exist so the operator is not asked 39 times over."""
    asked = []

    settings = Settings(
        catalog=str(mixed_library.catalog_path),
        structure=("{yyyy}-{mm}-{dd}",),
        folder_rules=("Urlaub=leave", "*=consolidate"),
    )
    with open_catalog(mixed_library.catalog_path) as conn:
        build_plan(CatalogReader(conn), settings, decide=lambda case: asked.append(case.name))
    assert asked == []
