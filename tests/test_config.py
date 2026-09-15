"""Settings, validation and profiles."""

from __future__ import annotations

import json

import pytest

from lrcompanion.config import ConfigError, Settings, list_profiles


def test_defaults_are_safe():
    settings = Settings(catalog="x.lrcat")
    assert settings.dry_run is True
    assert settings.backup_catalog is True
    assert settings.verify_after is True
    assert settings.placement == "in-place"
    assert settings.move_sidecars is True
    # the file date must not silently stand in for a capture date
    assert "file-mtime" not in settings.date_source


def test_validate_accepts_a_sane_configuration():
    Settings(catalog="x.lrcat", structure=("{yyyy}", "{mm}")).validate()


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"catalog": ""}, "no catalog"),
        ({"structure": ("{nope}",)}, "unknown token"),
        ({"structure": ()}, "at least one level"),
        ({"placement": "sideways"}, "placement must be"),
        ({"placement": "new-tree"}, "requires --target-root"),
        ({"on_missing_date": "panic"}, "on-missing-date must be"),
        ({"conflict": "explode"}, "conflict must be"),
        ({"date_source": ("stars",)}, "unknown date source"),
        ({"date_source": ()}, "must not be empty"),
        ({"language": "fr"}, "language must be"),
        ({"unsorted_folder": "  "}, "must not be empty"),
        (
            {"include_extensions": ("cr2",), "exclude_extensions": ("cr2",)},
            "both included and excluded",
        ),
    ],
)
def test_validation_errors(kwargs, message):
    base = {"catalog": "x.lrcat"}
    base.update(kwargs)
    with pytest.raises(ConfigError, match=message):
        Settings(**base).validate()


def test_extension_filters_normalise_dots_and_case():
    settings = Settings(catalog="x", include_extensions=(".CR2", "Dng"))
    assert settings.include_extensions == ("cr2", "dng")
    assert settings.accepts_extension("cr2")
    assert settings.accepts_extension(".DNG")
    assert not settings.accepts_extension("jpg")


def test_profile_roundtrip(tmp_path):
    settings = Settings(
        catalog="/x/y.lrcat",
        structure=("{camera_slug}", "{yyyy}-{mm}-{dd}"),
        conflict="skip",
        language="de",
    )
    settings.save_profile("My Profile", tmp_path)
    assert list_profiles(tmp_path) == ["My-Profile"]

    loaded = Settings.load_profile("My-Profile", tmp_path)
    assert loaded.structure == ("{camera_slug}", "{yyyy}-{mm}-{dd}")
    assert loaded.conflict == "skip"
    assert loaded.language == "de"
    # a profile describes how to sort, never that a run was live
    assert loaded.dry_run is True


def test_unknown_keys_in_a_profile_are_ignored(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(
        json.dumps({"catalog": "c.lrcat", "structure": ["{yyyy}"], "legacy_flag": 1}),
        encoding="utf-8",
    )
    settings = Settings.load_file(path)
    assert settings.structure == ("{yyyy}",)


def test_missing_profile_raises(tmp_path):
    with pytest.raises(ConfigError, match="profile not found"):
        Settings.load_profile("nope", tmp_path)


def test_with_structure_uses_presets():
    settings = Settings(catalog="x").with_structure("year/month/day")
    assert settings.structure == ("{yyyy}", "{mm}", "{dd}")
