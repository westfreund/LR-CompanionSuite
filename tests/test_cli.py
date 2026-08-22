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


def _mixed(builder):
    builder.add_photo("FLACH.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    builder.add_photo("U1.CR2", "2019-01-03T11:00:00", folder="raw2019/Urlaub/")
    builder.add_photo("D1.CR2", "2019-03-10T11:00:00", folder="raw2019/2019-03-10 Fasching/")
    return builder


def test_plan_reports_the_folders_it_found(builder, capsys):
    _mixed(builder)
    main(["plan", str(builder.catalog_path), "-s", "day", "--lang", "de"])
    out = capsys.readouterr().out
    assert "VORGEFUNDENE ORDNER" in out
    assert "datierte Ordner" in out
    assert "thematische Unterordner" in out


def test_plan_json_carries_the_folder_decisions(builder, capsys):
    _mixed(builder)
    main(["plan", str(builder.catalog_path), "-s", "day", "--json"])
    payload = json.loads(capsys.readouterr().out)
    by_path = {f["path"]: f for f in payload["folders"]}
    assert by_path["raw2019/2019-03-10 Fasching/"]["kind"] == "dated"
    assert by_path["raw2019/2019-03-10 Fasching/"]["action"] == "keep"
    assert by_path["raw2019/Urlaub/"]["action"] == "consolidate"


def test_folder_actions_can_be_set_globally(builder, capsys):
    _mixed(builder)
    main(
        [
            "plan",
            str(builder.catalog_path),
            "-s",
            "day",
            "--json",
            "--subfolder-action",
            "sort-inside",
            "--dated-folder-action",
            "consolidate",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    by_path = {f["path"]: f for f in payload["folders"]}
    assert by_path["raw2019/Urlaub/"]["action"] == "sort-inside"
    assert by_path["raw2019/2019-03-10 Fasching/"]["action"] == "consolidate"


def test_a_single_folder_can_be_set(builder, capsys):
    _mixed(builder)
    urlaub = builder.folders["raw2019/Urlaub/"]
    main(
        [
            "plan",
            str(builder.catalog_path),
            "-s",
            "day",
            "--json",
            "--folder-action",
            "{i}=leave".format(i=urlaub),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    by_path = {f["path"]: f for f in payload["folders"]}
    assert by_path["raw2019/Urlaub/"]["action"] == "leave"
    assert by_path["raw2019/Urlaub/"]["action_source"] == "override"


def test_a_malformed_folder_action_is_rejected(builder, capsys):
    _mixed(builder)
    assert (
        main(["plan", str(builder.catalog_path), "-s", "day", "--folder-action", "nonsense"])
        != EXIT_OK
    )
    assert "ID=ACTION" in capsys.readouterr().err


def test_interactive_asks_and_honours_the_answer(builder, capsys, monkeypatch):
    _mixed(builder)
    answers = iter(["leave", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    main(["plan", str(builder.catalog_path), "-s", "day", "--json", "--interactive"])
    payload = json.loads(capsys.readouterr().out)
    by_path = {f["path"]: f for f in payload["folders"]}
    # the first folder asked about was answered "leave"
    assert "leave" in {f["action"] for f in payload["folders"]}
    assert "operator" in {f["action_source"] for f in payload["folders"]}
    assert by_path["raw2019/"]["is_anchor"] is True
