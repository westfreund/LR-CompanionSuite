"""What the plan could not decide on its own, and the setting that decides it."""

from __future__ import annotations

import pytest

from lrfoldercraft.catalog import CatalogReader, open_catalog
from lrfoldercraft.config import Settings
from lrfoldercraft.exceptions_report import (
    ERROR,
    EXCEPTION,
    NOTE,
    WARNING,
    collect_findings,
    render_findings,
)
from lrfoldercraft.planner import build_plan


def plan_for(builder, **kwargs):
    settings = Settings(catalog=str(builder.catalog_path), **kwargs)
    with open_catalog(builder.catalog_path) as conn:
        return build_plan(CatalogReader(conn), settings)


def by_category(findings):
    return {f.category: f for f in findings}


@pytest.fixture
def mixed_library(builder):
    """A grown library: flat files, topic folders and already dated folders."""
    builder.add_photo("FLACH.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    builder.add_photo("U1.CR2", "2019-01-03T11:00:00", folder="raw2019/Urlaub/")
    builder.add_photo("F1.CR2", "2019-02-14T11:00:00", folder="raw2019/Familie/")
    builder.add_photo("D2.CR2", "2019-04-15T11:00:00", folder="raw2019/2019-04-15 Ostern in Tirol/")
    builder.add_photo("X1.CR2", "2019-07-07T11:00:00", folder="raw2019/2019-04-15 Ostern in Tirol/")
    return builder


def test_a_clean_plan_needs_no_answers(simple_catalog):
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",), on_missing_date="unsorted")
    categories = by_category(collect_findings(plan))
    assert "no-date" not in categories
    assert "conflict" not in categories


def test_photos_without_a_date_name_the_setting_that_governs_them(simple_catalog):
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",), on_missing_date="skip")
    finding = by_category(collect_findings(plan))["no-date"]
    assert finding.level == EXCEPTION
    assert finding.count >= 1
    assert finding.setting == "--on-missing-date"
    assert finding.current("en") == "skip"
    assert finding.samples  # so the operator can see which files


def test_a_stray_date_in_a_dated_folder_is_reported_with_its_folder(mixed_library):
    plan = plan_for(mixed_library, structure=("{yyyy}-{mm}-{dd}",), mismatch_action="leave")
    finding = by_category(collect_findings(plan))["date-mismatch"]
    assert finding.count == 1  # X1.CR2, shot 07-07, sitting in 04-15
    assert finding.setting == "--mismatch-action"
    assert finding.current("en") == "leave"
    assert any("Ostern" in sample for sample in finding.samples)


def test_folders_no_rule_spoke_about_are_pointed_out(mixed_library):
    """So an operator can tell that a rule set does not cover everything yet."""
    plan = plan_for(mixed_library, structure=("{yyyy}-{mm}-{dd}",), folder_rules=("Urlaub=leave",))
    finding = by_category(collect_findings(plan))["folders-on-default"]
    assert finding.level == NOTE
    assert finding.setting == "--rule"
    assert "Urlaub" not in " ".join(finding.samples)  # that one a rule did decide


def test_a_complete_rule_set_leaves_nothing_on_the_default(mixed_library):
    plan = plan_for(mixed_library, structure=("{yyyy}-{mm}-{dd}",), folder_rules=("*=consolidate",))
    assert "folders-on-default" not in by_category(collect_findings(plan))


def test_missing_files_block_rather_than_merely_warn(simple_catalog, tmp_path):
    """A file the catalog names but the disk does not have is not an exception."""
    victim = next(simple_catalog.images_dir.glob("*.CR2"))
    victim.unlink()
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",))
    finding = by_category(collect_findings(plan))["missing-source"]
    assert finding.level == ERROR
    assert finding.count == 1


def test_findings_are_ordered_by_how_much_they_matter(simple_catalog):
    victim = next(simple_catalog.images_dir.glob("*.CR2"))
    victim.unlink()
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",), on_missing_date="skip")
    levels = [f.level for f in collect_findings(plan)]
    assert levels == sorted(
        levels, key=lambda lv: {ERROR: 0, WARNING: 1, EXCEPTION: 2, NOTE: 3}[lv]
    )


@pytest.mark.parametrize("language", ["en", "de"])
def test_rendering_names_the_setting_and_the_examples(simple_catalog, language):
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",), on_missing_date="skip")
    text = "\n".join(render_findings(collect_findings(plan), language))
    assert "--on-missing-date = skip" in text
    assert ".CR2" in text


def test_preflight_results_join_the_same_list(simple_catalog):
    from lrfoldercraft.safety import preflight

    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",))
    findings = collect_findings(plan, preflight(plan))
    assert any(f.category.startswith("preflight:") for f in findings) or all(
        f.level != WARNING for f in findings
    )
