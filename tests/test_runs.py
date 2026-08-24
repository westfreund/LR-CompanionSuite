"""A run records itself beside the catalog it changed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lrfoldercraft.catalog import CatalogReader, open_catalog
from lrfoldercraft.config import Settings
from lrfoldercraft.executor import ExecutionError, execute, undo
from lrfoldercraft.planner import build_plan
from lrfoldercraft.runs import (
    JOURNAL_FILE,
    RUN_FILE,
    SETTINGS_FILE,
    history,
    read_record,
    runs_directory,
)


def make_plan(builder, tmp_path, **kwargs):
    settings = Settings(
        catalog=str(builder.catalog_path),
        dry_run=False,
        backup_dir=str(tmp_path / "backups"),
        structure=kwargs.pop("structure", ("{yyyy}-{mm}-{dd}",)),
        **kwargs,
    )
    with open_catalog(builder.catalog_path) as conn:
        return build_plan(CatalogReader(conn), settings), settings


def test_a_run_writes_its_record_beside_the_catalog(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)

    directory = Path(result.run_directory)
    assert directory.parent == runs_directory(simple_catalog.catalog_path)
    assert (directory / RUN_FILE).is_file()
    assert (directory / SETTINGS_FILE).is_file()
    assert (directory / JOURNAL_FILE).is_file()
    assert result.journal_path == str(directory / JOURNAL_FILE)


def test_the_record_says_what_the_run_did(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)

    record = read_record(Path(result.run_directory))
    assert record.success is True
    assert record.files_moved == result.files_moved
    assert record.structure == "{yyyy}-{mm}-{dd}"
    assert record.catalog == str(simple_catalog.catalog_path)
    assert record.backup_path == result.backup_path
    assert record.can_be_undone


def test_the_record_holds_everything_the_run_was_told_to_do(simple_catalog, tmp_path):
    """Answering "what did I do to this library" must not need the journal.

    This is not a profile and must not be pruned like one. The first version
    copied the profile's exclusions and so recorded neither the rules nor the
    per-folder decisions -- a folder had visibly been moved somewhere only a
    rule could explain, and no artefact said why.
    """
    plan, settings = make_plan(
        simple_catalog,
        tmp_path,
        cumulative_dates=True,
        folder_rules=("_extern=relocate", "*=consolidate"),
        ignore_lock=True,
    )
    result = execute(plan, settings)

    stored = json.loads((Path(result.run_directory) / SETTINGS_FILE).read_text(encoding="utf-8"))
    assert stored["cumulative_dates"] is True
    assert stored["catalog"] == str(simple_catalog.catalog_path)
    assert stored["folder_rules"] == ["_extern=relocate", "*=consolidate"]
    # even the escape hatches: knowing one was used is part of the record
    assert stored["ignore_lock"] is True
    assert "dry_run" not in stored


def test_a_per_folder_decision_reaches_the_move_log(simple_catalog, tmp_path):
    folders = {}
    with open_catalog(simple_catalog.catalog_path) as conn:
        for folder in CatalogReader(conn).folders():
            folders[folder.path_from_root] = folder.id_local
    any_id = sorted(folders.values())[0]

    plan, settings = make_plan(simple_catalog, tmp_path, folder_actions={any_id: "leave"})
    result = execute(plan, settings)
    text = Path(result.move_log_path).read_text(encoding="utf-8")
    assert "Per-folder decisions" in text
    assert str(any_id) in text


def test_undoing_marks_the_run_so_it_is_not_offered_again(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)

    undo(result.journal_path)

    record = read_record(Path(result.run_directory))
    assert record.undone_at
    assert not record.can_be_undone


def test_a_run_cannot_be_undone_twice(simple_catalog, tmp_path):
    """The files are back where they started; doing it again moves the wrong ones."""
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)
    undo(result.journal_path)

    with pytest.raises(ExecutionError, match="already undone"):
        undo(result.journal_path)


def test_the_journal_is_kept_after_an_undo(simple_catalog, tmp_path):
    """After a partly failed undo it is the only account of what moved."""
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)
    undo(result.journal_path)
    assert Path(result.journal_path).is_file()


def test_history_lists_the_runs_newest_first(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    first = execute(plan, settings)
    undo(first.journal_path)

    plan2, settings2 = make_plan(simple_catalog, tmp_path, structure=("{yyyy}", "{mm}"))
    second = execute(plan2, settings2)

    records = history(simple_catalog.catalog_path)
    assert len(records) == 2
    assert records[0].stamp >= records[1].stamp
    by_stamp = {r.stamp: r for r in records}
    assert by_stamp[Path(second.run_directory).name].can_be_undone
    assert not by_stamp[Path(first.run_directory).name].can_be_undone


def test_two_catalogs_keep_their_runs_apart(builder, tmp_path):
    """The whole point on an external drive full of libraries."""
    from conftest import CatalogBuilder

    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    other_root = tmp_path / "andere"
    other = CatalogBuilder(other_root, catalog_name="Zweiter.lrcat")
    other.add_photo("B.CR2", "2020-05-05T10:00:00", folder="raw2020/")

    plan_a, settings_a = make_plan(builder, tmp_path / "a")
    execute(plan_a, settings_a)
    plan_b, settings_b = make_plan(other, tmp_path / "b")
    execute(plan_b, settings_b)

    assert len(history(builder.catalog_path)) == 1
    assert len(history(other.catalog_path)) == 1
    assert history(builder.catalog_path)[0].catalog == str(builder.catalog_path)
    assert history(other.catalog_path)[0].catalog == str(other.catalog_path)


def test_a_catalog_with_no_runs_has_an_empty_history(simple_catalog):
    assert history(simple_catalog.catalog_path) == []


def test_an_unwritable_catalog_folder_does_not_stop_the_run(simple_catalog, tmp_path, monkeypatch):
    """A read-only volume costs the records, never the migration."""
    import lrfoldercraft.executor as executor

    def refuse(_catalog, when=None):
        raise OSError("read-only file system")

    monkeypatch.setattr(executor, "new_run_directory", refuse)
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)

    assert result.success
    assert result.run_directory is None
    assert any("run records" in note for note in result.notes)
    assert Path(result.journal_path).is_file()  # fell back to the backup directory


def test_two_runs_in_the_same_second_do_not_share_a_folder(simple_catalog, tmp_path):
    """The second would otherwise overwrite the first, silently."""
    plan, settings = make_plan(simple_catalog, tmp_path)
    first = execute(plan, settings)
    undo(first.journal_path)
    plan2, settings2 = make_plan(simple_catalog, tmp_path, structure=("{yyyy}",))
    second = execute(plan2, settings2)

    assert first.run_directory != second.run_directory
    assert len(history(simple_catalog.catalog_path)) == 2


# -- what the list of runs shows ---------------------------------------------


def test_the_run_list_shows_a_path_not_placeholders():
    """A list is read at a glance, and "{yyyy}/{yyyy}-{mm}" says nothing.

    The user saw a column of raw tokens and could not tell one run from
    another. Rendered on the way out, so records written before this show it
    too.
    """
    from lrfoldercraft.runs import RunRecord

    record = RunRecord(stamp="x", catalog="y", structure="{yyyy}/{yyyy}-{mm}/{yyyy}-{mm}-{dd}")
    assert record.structure_example("de") == "2019/2019-01/2019-01-03"
    assert "2019/2019-01/2019-01-03" in record.describe("de")
    # framed as a shape, so the sample date cannot read as a fact about the run
    assert "wie " in record.describe("de")
    assert "like " in record.describe("en")


def test_a_record_never_fails_to_display():
    """Whatever is in the field, the list still renders."""
    from lrfoldercraft.runs import RunRecord

    for spec in ("", "kaputt{", "{unbekannt}", "/"):
        record = RunRecord(stamp="x", catalog="y", structure=spec)
        assert record.structure_example("de")
        assert record.describe("de")


def test_the_template_itself_is_still_reachable():
    """The example is for reading; the template is what was actually set."""
    from lrfoldercraft.runs import RunRecord

    record = RunRecord(stamp="x", catalog="y", structure="{yyyy}/{mm}")
    assert record.structure == "{yyyy}/{mm}"
