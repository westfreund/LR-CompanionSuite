"""CLI wiring: exit codes, output formats, safe defaults."""

from __future__ import annotations

import json

from lrfoldercraft.cli import EXIT_OK, main


def test_info(simple_catalog, capsys):
    assert main(["info", str(simple_catalog.catalog_path)]) == EXIT_OK
    out = capsys.readouterr().out
    assert "Files" in out and "6" in out
    assert "LR-FolderCraft" in out


def test_folders_with_counts(simple_catalog, capsys):
    assert main(["folders", str(simple_catalog.catalog_path), "--counts"]) == EXIT_OK
    assert "files" in capsys.readouterr().out


def test_plan_is_read_only(simple_catalog, capsys):
    before = simple_catalog.catalog_paths()
    assert main(["plan", str(simple_catalog.catalog_path), "-s", "day"]) == EXIT_OK
    assert simple_catalog.catalog_paths() == before
    out = capsys.readouterr().out
    assert "PLAN" in out and "PRE-FLIGHT" in out


def test_plan_json_is_machine_readable(simple_catalog, capsys):
    main(["plan", str(simple_catalog.catalog_path), "-s", "day", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["stats"]["total"] == 6
    assert len(payload["moves"]) == 6
    assert payload["moves"][0]["target"].endswith(".CR2")


def test_plan_csv(simple_catalog, capsys):
    main(["plan", str(simple_catalog.catalog_path), "-s", "day", "--csv"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0].startswith("file_id,status,reason")
    assert len(lines) == 7


def test_plan_writes_files(simple_catalog, tmp_path, capsys):
    main(
        [
            "plan",
            str(simple_catalog.catalog_path),
            "-s",
            "day",
            "--out",
            str(tmp_path / "reports"),
        ]
    )
    written = list((tmp_path / "reports").glob("plan-*"))
    assert {p.suffix for p in written} == {".json", ".csv"}


def test_german_output(simple_catalog, capsys):
    main(["plan", str(simple_catalog.catalog_path), "-s", "day", "--lang", "de"])
    assert "Zusammenfassung" in capsys.readouterr().out


def test_bad_structure_is_reported(simple_catalog, capsys):
    assert main(["plan", str(simple_catalog.catalog_path), "-s", "{nope}"]) != EXIT_OK
    assert "unknown token" in capsys.readouterr().err


def test_missing_catalog_is_reported(tmp_path, capsys):
    assert main(["info", str(tmp_path / "nope.lrcat")]) != EXIT_OK
    assert "not found" in capsys.readouterr().err


def test_apply_moves_and_verifies(simple_catalog, tmp_path, capsys):
    code = main(
        [
            "apply",
            str(simple_catalog.catalog_path),
            "-s",
            "day",
            "--yes",
            "--out",
            str(tmp_path / "reports"),
        ]
    )
    assert code == EXIT_OK
    assert "Files moved" in capsys.readouterr().out
    assert (simple_catalog.images_dir / "2019-01-03" / "A0001.CR2").exists()


def test_tokens_and_presets(capsys):
    main(["tokens"])
    assert "{iso_week}" in capsys.readouterr().out
    main(["presets", "--lang", "de"])
    assert "Kalenderwoche" in capsys.readouterr().out


def test_no_command_prints_help(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().out.lower()


def test_save_and_list_profile(simple_catalog, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LRFC_CONFIG_DIR", str(tmp_path / "cfg"))
    main(
        [
            "plan",
            str(simple_catalog.catalog_path),
            "-s",
            "camera/day",
            "--save-profile",
            "cameras",
        ]
    )
    capsys.readouterr()
    main(["profiles"])
    assert "cameras" in capsys.readouterr().out
