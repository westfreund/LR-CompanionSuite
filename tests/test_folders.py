"""Recognising and deciding about the folders a library already has."""

from __future__ import annotations

from datetime import date

import pytest

from lrfoldercraft.folders import (
    CONSOLIDATE,
    DATED,
    KEEP,
    PLAIN,
    classify,
    describes_only_a_date,
    parse_folder_date,
    summarise,
)
from lrfoldercraft.rules import parse_structure, structure_date_granularity


@pytest.mark.parametrize(
    "name,granularity,matched",
    [
        ("2019-04-15 Ostern in Tirol", "day", "2019-04-15"),
        ("2019_06_01 Hochzeit", "day", "2019_06_01"),
        ("2019.03.10", "day", "2019.03.10"),
        ("20190415_Hochzeit", "day", "20190415"),
        ("2019-03-10", "day", "2019-03-10"),
        ("2019-04", "month", "2019-04"),
        ("2019", "year", "2019"),
        ("2019 Jahresrueckblick", "year", "2019"),
    ],
)
def test_recognised_dates(name, granularity, matched):
    found = parse_folder_date(name)
    assert found is not None, name
    assert found.granularity == granularity
    assert found.matched_text == matched


@pytest.mark.parametrize(
    "name",
    ["Urlaub", "Sommer 2019", "20194", "raw2019", "", "   ", "Best of 2019-04-15"],
)
def test_not_dates(name):
    """A date must start the name; guessing at the middle would invent intent."""
    assert parse_folder_date(name) is None


def test_date_matching_respects_granularity():
    day = parse_folder_date("2019-04-15 Ostern")
    assert day.matches(date(2019, 4, 15))
    assert not day.matches(date(2019, 4, 16))

    month = parse_folder_date("2019-04")
    assert month.matches(date(2019, 4, 1)) and month.matches(date(2019, 4, 30))
    assert not month.matches(date(2019, 5, 1))

    year = parse_folder_date("2019")
    assert year.matches(date(2019, 12, 31))
    assert not year.matches(date(2020, 1, 1))


def test_descriptive_text_is_detected():
    assert describes_only_a_date("2019-04-15", parse_folder_date("2019-04-15"))
    assert not describes_only_a_date("2019-04-15 Ostern", parse_folder_date("2019-04-15 Ostern"))


@pytest.mark.parametrize(
    "spec,granularity",
    [
        ("{yyyy}-{mm}-{dd}", "day"),
        ("{yyyy}/{mm}/{dd}", "day"),
        ("{yyyy}/{mm}", "month"),
        ("{yyyy}", "year"),
        ("{iso_year}-W{iso_week}", "week"),
        ("{camera_slug}", None),
    ],
)
def test_structure_granularity(spec, granularity):
    assert structure_date_granularity(parse_structure(spec)) == granularity


def test_a_folder_too_coarse_for_the_structure_is_not_dated():
    """A folder called 2019 is no answer to a request for day folders."""
    case = classify("2019", 1, "2019/", ("2019",), wanted_granularity="day")
    assert case.kind == PLAIN

    case = classify("2019", 1, "2019/", ("2019",), wanted_granularity="year")
    assert case.kind == DATED


def test_a_finer_folder_still_counts():
    """A day folder satisfies a request for year folders."""
    case = classify("2019-04-15", 1, "2019-04-15/", ("2019-04-15",), wanted_granularity="year")
    assert case.kind == DATED


def test_without_date_tokens_folder_dates_are_irrelevant():
    case = classify("2019-04-15", 1, "x/", ("x",), wanted_granularity=None)
    assert case.kind == PLAIN


def test_summarise_counts_both_kinds():
    dated = classify("2019-04-15", 1, "a/", ("a",), wanted_granularity="day")
    dated.photo_count = 3
    dated.mismatched_photos = 1
    plain = classify("Urlaub", 2, "b/", ("b",), wanted_granularity="day")
    plain.photo_count = 2
    lines = summarise([dated, plain])
    assert "1 dated folder(s)" in lines[0]
    assert "1 topic subfolder(s)" in lines[1]
    assert "does not match" in lines[2]
    assert "datierte" in summarise([dated, plain], "de")[0]


def test_default_actions():
    dated = classify("2019-04-15", 1, "a/", ("a",), wanted_granularity="day")
    plain = classify("Urlaub", 2, "b/", ("b",), wanted_granularity="day")
    assert dated.is_dated and not plain.is_dated
    assert plain.action == CONSOLIDATE  # dataclass default
    dated.action = KEEP
    assert dated.action == KEEP
