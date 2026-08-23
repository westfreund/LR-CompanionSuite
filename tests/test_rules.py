"""Template rendering, sanitising and structure parsing."""

from __future__ import annotations

from datetime import datetime

import pytest

from lrfoldercraft.rules import (
    PRESETS,
    RuleError,
    TokenContext,
    describe_structure,
    fold_to_ascii,
    parse_structure,
    render_level,
    render_structure,
    sanitise_segment,
    slugify,
    structure_requires_date,
    template_tokens,
    validate_structure,
    validate_template,
)


def ctx(**kwargs) -> TokenContext:
    defaults = {
        "when": datetime(2019, 1, 3, 17, 42),
        "camera": "Canon EOS 70D",
        "camera_serial": "053022010127",
        "lens": "EF-S18-55mm f/3.5-5.6 IS STM",
        "file_format": "RAW",
        "extension": "CR2",
        "original_folder": "raw2019",
        "language": "en",
    }
    defaults.update(kwargs)
    return TokenContext(**defaults)


@pytest.mark.parametrize(
    "template,expected",
    [
        ("{yyyy}-{mm}-{dd}", "2019-01-03"),
        ("{yy}{mm}{dd}", "190103"),
        ("{d}.{m}.{yyyy}", "3.1.2019"),
        ("{month_name}", "January"),
        ("{month_short} {yyyy}", "Jan 2019"),
        ("{quarter}", "Q1"),
        ("{iso_year}-W{iso_week}", "2019-W01"),
        ("{weekday}", "Thursday"),
        ("{weekday_short}", "Thu"),
        ("{doy}", "003"),
        ("{hh}{mi}", "1742"),
        ("{camera}", "Canon EOS 70D"),
        ("{camera_slug}", "canon-eos-70d"),
        ("{camera_sn}", "053022010127"),
        ("{lens_slug}", "ef-s18-55mm-f-3-5-5-6-is-stm"),
        ("{format}", "RAW"),
        ("{ext}", "CR2"),
        ("{ext_lower}", "cr2"),
        ("{orig_folder}", "raw2019"),
    ],
)
def test_tokens_render(template, expected):
    assert render_level(template, ctx()) == expected


def test_iso_week_year_boundary():
    """2019-12-30 belongs to ISO week 1 of 2020 -- a classic off-by-one trap."""
    context = ctx(when=datetime(2019, 12, 30))
    assert render_level("{iso_year}-W{iso_week}", context) == "2020-W01"
    assert render_level("{yyyy}", context) == "2019"


def test_german_month_and_weekday_names():
    context = ctx(language="de")
    assert render_level("{month_name}", context) == "Januar"
    assert render_level("{weekday}", context) == "Donnerstag"
    assert render_level("{weekday_short}", context) == "Do"


def test_missing_metadata_falls_back():
    context = ctx(camera=None, lens=None, camera_serial=None)
    assert render_level("{camera}", context) == "Unknown Camera"
    assert render_level("{camera_slug}", context) == "unknown-camera"
    assert render_level("{camera_sn}", context) == "unknown-sn"


def test_date_tokens_empty_without_a_date():
    context = ctx(when=None)
    assert render_level("x{yyyy}y", context) == "xy"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("a/b", "a-b"),
        ("a\\b", "a-b"),
        ('q"uote', "q-uote"),
        ("colon:name", "colon-name"),
        ("  padded  ", "padded"),
        ("trailing...", "trailing"),
        ("", "unnamed"),
        ("CON", "_CON"),
        ("lpt1", "_lpt1"),
        ("multi   space", "multi space"),
    ],
)
def test_sanitise_segment(raw, expected):
    assert sanitise_segment(raw) == expected


def test_sanitise_length_limit():
    assert len(sanitise_segment("x" * 500)) == 100


def test_ascii_folding():
    # This used to assert "Grun Strae": the umlaut was dropped and the sharp s
    # vanished outright, which is not a romanisation of anything.
    assert sanitise_segment("Grün Straße", ascii_only=True) == "Gruen Strasse"
    assert sanitise_segment("Grün Straße") == "Grün Straße"


def test_slugify():
    assert slugify("Canon EOS 5D Mark IV") == "canon-eos-5d-mark-iv"
    assert slugify("!!!") == "unknown"


def test_validate_template_rejects_separators_and_unknown_tokens():
    with pytest.raises(RuleError, match="path separator"):
        validate_template("{yyyy}/{mm}")
    with pytest.raises(RuleError, match="unknown token"):
        validate_template("{nope}")
    with pytest.raises(RuleError):
        validate_template("   ")


def test_validate_structure_requires_a_level():
    with pytest.raises(RuleError):
        validate_structure([])


def test_parse_structure_accepts_presets_and_templates():
    assert parse_structure("year/month/day") == PRESETS["year/month/day"]
    assert parse_structure("{camera_slug}/{yyyy}") == ("{camera_slug}", "{yyyy}")
    with pytest.raises(RuleError):
        parse_structure("")


def test_every_preset_renders():
    for name, structure in PRESETS.items():
        rendered = describe_structure(structure)
        assert rendered and "{" not in rendered, name


def test_structure_requires_date():
    assert structure_requires_date(("{yyyy}",))
    assert not structure_requires_date(("{camera_slug}",))


def test_template_tokens():
    assert template_tokens("{yyyy}-{mm} x {camera}") == ["yyyy", "mm", "camera"]


def test_render_structure_returns_one_segment_per_level():
    assert render_structure(("{yyyy}", "{mm}", "{dd}"), ctx()) == ("2019", "01", "03")


# -- romanising names for the ASCII option -----------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        # German, where dropping the mark makes a different word
        ("Völki", "Voelki"),
        ("Tabaksmühle", "Tabaksmuehle"),
        ("Straße", "Strasse"),
        ("Größe", "Groesse"),
        ("Bärbel Müller-Weiß", "Baerbel Mueller-Weiss"),
        # case follows the neighbour, so an all-caps word stays all caps
        ("MÜNCHEN", "MUENCHEN"),
        ("München", "Muenchen"),
        ("Öl", "Oel"),
        ("ÖL", "OEL"),
        # Nordic and French
        ("Ærø", "Aeroe"),
        ("Œuvre", "Oeuvre"),
        # dropping the accent is right here, and still happens
        ("Café", "Cafe"),
        ("Señor", "Senor"),
        ("Ostern in Tirol", "Ostern in Tirol"),
    ],
)
def test_ascii_folding_spells_out_what_an_accent_cannot_carry(text, expected):
    assert fold_to_ascii(text) == expected


def test_the_ascii_option_uses_it(tmp_path):
    assert sanitise_segment("2026-06-18 Völki", ascii_only=True) == "2026-06-18 Voelki"
    # and leaves the name alone when the option is off
    assert sanitise_segment("2026-06-18 Völki") == "2026-06-18 Völki"


def test_slugs_are_romanised_the_same_way():
    assert slugify("Bärbel Müller-Weiß") == "baerbel-mueller-weiss"


def test_folding_is_stable_when_run_twice():
    """A second run must not turn Voelki into something else again."""
    once = fold_to_ascii("Völki Straße MÜNCHEN")
    assert fold_to_ascii(once) == once
