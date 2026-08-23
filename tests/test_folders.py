"""Recognising and deciding about the folders a library already has."""

from __future__ import annotations

from datetime import date

import pytest

from lrfoldercraft.folders import (
    CONSOLIDATE,
    DATED,
    KEEP,
    LEAVE,
    PLAIN,
    RESORT,
    SORT_INSIDE,
    FolderRuleError,
    classify,
    describes_only_a_date,
    first_matching_rule,
    folder_label,
    parse_folder_date,
    parse_rule,
    parse_rules,
    summarise,
    usable_action,
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


# -- descriptive text after a date ------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ("2026-06-28 Makro Blume im Garten", "Makro Blume im Garten"),
        ("2019_06_01 Hochzeit", "Hochzeit"),
        ("20190415_Hochzeit", "Hochzeit"),
        ("2019.03.10 - Ostern", "Ostern"),
        ("2026-06-28", ""),
        ("raw2020", ""),
        ("_extern", ""),
    ],
)
def test_folder_label_is_the_text_after_the_date(name, expected):
    assert folder_label(name) == expected


def test_a_demoted_folder_keeps_its_label():
    """Being too coarse for the structure must not lose the folder's text."""
    case = classify(
        name="2019 Jahresrueckblick",
        folder_id=1,
        path_from_root="2019 Jahresrueckblick/",
        segments=("2019 Jahresrueckblick",),
        wanted_granularity="day",
    )
    assert case.kind == PLAIN  # a year folder is no answer to a day structure
    assert case.label == "Jahresrueckblick"


# -- the ordered rule list ---------------------------------------------------


def _case(name, path_from_root, granularity="day"):
    return classify(
        name=name,
        folder_id=abs(hash(path_from_root)) % 100000,
        path_from_root=path_from_root,
        segments=tuple(path_from_root.strip("/").split("/")),
        wanted_granularity=granularity,
    )


def test_rules_are_read_from_pattern_equals_action():
    rule = parse_rule("dated+label=resort")
    assert rule.pattern == "dated+label"
    assert rule.action == RESORT


@pytest.mark.parametrize(
    "text",
    ["_extern", "=leave", "_extern=nonsense", "_extern="],
)
def test_a_broken_rule_is_refused(text):
    with pytest.raises(FolderRuleError):
        parse_rule(text)


def test_the_first_matching_rule_wins():
    rules = parse_rules(["dated+label=resort", "dated=keep", "*=sort-inside"])
    dated_with_text = _case("2026-06-28 Makro", "raw2026/2026-06-28 Makro/")
    position, rule = first_matching_rule(dated_with_text, rules)
    assert (position, rule.action) == (1, RESORT)

    bare_date = _case("2026-06-27", "raw2026/2026-06-27/")
    position, rule = first_matching_rule(bare_date, rules)
    assert (position, rule.action) == (2, KEEP)

    topic = _case("raw2020", "raw2020/")
    position, rule = first_matching_rule(topic, rules)
    assert (position, rule.action) == (3, SORT_INSIDE)


def test_a_path_pattern_also_covers_everything_below_it():
    """Naming a folder must not need a second rule for its children."""
    rules = parse_rules(["_extern=leave", "*=consolidate"])
    for path in ("_extern/", "_extern/2019/", "_extern/2019/Sub/"):
        position, _rule = first_matching_rule(_case("x", path), rules)
        assert position == 1, path
    assert first_matching_rule(_case("x", "_externals/"), rules)[0] == 2


def test_no_rule_matches_when_none_speaks_about_the_folder():
    rules = parse_rules(["_extern=leave"])
    assert first_matching_rule(_case("raw2020", "raw2020/"), rules) is None


def test_dated_only_and_plain_select_opposite_sets():
    rules = parse_rules(["dated-only=keep", "plain=consolidate"])
    assert first_matching_rule(_case("2026-06-27", "a/2026-06-27/"), rules)[0] == 1
    assert first_matching_rule(_case("2026-06-27 Fest", "a/2026-06-27 Fest/"), rules) is None
    assert first_matching_rule(_case("Urlaub", "a/Urlaub/"), rules)[0] == 2


def test_keep_softens_to_leave_where_there_is_no_date():
    """'Honour the date in the name' has to mean something for a plain folder."""
    plain = _case("Urlaub", "Urlaub/")
    assert usable_action(KEEP, plain) == LEAVE
    dated = _case("2026-06-27", "2026-06-27/")
    assert usable_action(KEEP, dated) == KEEP


def test_a_pattern_finds_its_folder_however_deep_it_sits():
    """'_extern=leave' must mean _extern, not "_extern if it is at the top"."""
    rules = parse_rules(["_extern=leave", "*=consolidate"])
    for path in (
        "_extern/",
        "raw2019/_extern/",
        "a/b/_extern/",
        "raw2019/_extern/2020/",
        "raw2019/_extern/2020/Fest/",
    ):
        assert first_matching_rule(_case("x", path), rules)[0] == 1, path
    for path in ("_externals/", "raw2019/extern/", "raw2019/"):
        assert first_matching_rule(_case("x", path), rules)[0] == 2, path


def test_a_rooted_pattern_still_says_where_it_starts():
    """A pattern with a slash is matched as a path, not as a bare name."""
    rules = parse_rules(["_in_Arbeit/2021=leave", "*=consolidate"])
    assert first_matching_rule(_case("2021", "_in_Arbeit/2021/"), rules)[0] == 1
    assert first_matching_rule(_case("2021", "raw2019/_in_Arbeit/2021/"), rules)[0] == 1
    assert first_matching_rule(_case("2021", "_in_Arbeit/2022/"), rules)[0] == 2
    assert first_matching_rule(_case("2021", "sonst/2021/"), rules)[0] == 2


def test_a_rule_matches_a_decomposed_folder_name():
    """Patterns are typed composed; macOS hands back folder names decomposed."""
    import unicodedata

    decomposed = unicodedata.normalize("NFD", "2026-06-18 Völki")
    case = classify(
        name=decomposed,
        folder_id=1,
        path_from_root=unicodedata.normalize("NFD", "raw2026/2026-06-18 Völki/"),
        segments=("raw2026", decomposed),
        wanted_granularity="day",
    )
    for pattern in ("*Völki", "*völki", "2026-06-18 Völki"):
        rules = parse_rules([pattern + "=leave", "*=consolidate"])
        assert first_matching_rule(case, rules)[1].pattern == pattern, pattern
