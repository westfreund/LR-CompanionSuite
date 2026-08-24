"""Picking up after a run that was cut short.

The interruption is produced for real: the move loop is stopped partway by an
exception the executor does not catch as a rollback trigger, or the process is
simulated as having died between two steps. Asserting against a hand-written
journal would only test the parser.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lrfoldercraft.catalog import CatalogReader, open_catalog
from lrfoldercraft.config import Settings
from lrfoldercraft.executor import execute, undo
from lrfoldercraft.planner import build_plan
from lrfoldercraft.resume import (
    COMPLETE,
    NEEDS_RECORD,
    NEEDS_REVERT,
    NEEDS_UNDO,
    find_interruptions,
    inspect,
    remove_created_directories,
    revert_files,
)
from lrfoldercraft.safety import preflight


def make_plan(builder, tmp_path, **kwargs):
    settings = Settings(
        catalog=str(builder.catalog_path),
        dry_run=False,
        structure=kwargs.pop("structure", ("{yyyy}-{mm}-{dd}",)),
        backup_dir=str(tmp_path / "backups"),
        **kwargs,
    )
    with open_catalog(builder.catalog_path) as conn:
        return build_plan(CatalogReader(conn), settings), settings


def files_under(builder):
    return sorted(
        str(p.relative_to(builder.images_dir))
        for p in builder.images_dir.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    )


def kill_after(count, monkeypatch):
    """Make the move loop die after *count* files, as a crash would."""
    import lrfoldercraft.executor as executor

    real = executor._move_file
    state = {"n": 0}

    def dying(source, target, cross_volume=False):
        if state["n"] >= count:
            raise KeyboardInterrupt("process died")
        state["n"] += 1
        return real(source, target, cross_volume)

    monkeypatch.setattr(executor, "_move_file", dying)


def test_a_completed_run_needs_nothing(simple_catalog, tmp_path):
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)
    found = inspect(result.journal_path)
    assert found.state == COMPLETE
    assert not found.needs_work


def test_an_interrupted_run_is_recognised_and_can_be_put_back(
    simple_catalog, tmp_path, monkeypatch
):
    before = files_under(simple_catalog)
    plan, settings = make_plan(simple_catalog, tmp_path)
    kill_after(2, monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)

    journal = sorted(
        (Path(simple_catalog.catalog_path).parent / "LR-FolderCraft").rglob("journal.jsonl")
    )[-1]
    found = inspect(journal)
    assert found.state == NEEDS_REVERT
    assert found.to_revert, "some files were moved and are still at their new paths"

    restored, errors = revert_files(found)
    remove_created_directories(found)
    assert not errors
    assert restored == len(found.to_revert)
    assert files_under(simple_catalog) == before


def test_the_catalog_is_untouched_by_an_interrupted_run(simple_catalog, tmp_path, monkeypatch):
    """It commits last, so a run cut short leaves it describing the old layout."""
    before = simple_catalog.catalog_paths()
    plan, settings = make_plan(simple_catalog, tmp_path)
    kill_after(2, monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)
    assert simple_catalog.catalog_paths() == before


def test_a_new_run_is_refused_while_one_is_unfinished(simple_catalog, tmp_path, monkeypatch):
    """Planning on top of a half-moved library plans for a library that is not there."""
    plan, settings = make_plan(simple_catalog, tmp_path)
    kill_after(2, monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)

    monkeypatch.undo()
    fresh, _s = make_plan(simple_catalog, tmp_path)
    checks = preflight(fresh)
    failed = [c for c in checks.checks if c.name == "unfinished-run"]
    assert failed and failed[0].failed
    assert "resume" in failed[0].message_en
    assert not checks.ok


def test_the_refusal_lifts_once_the_run_is_finished(simple_catalog, tmp_path, monkeypatch):
    plan, settings = make_plan(simple_catalog, tmp_path)
    kill_after(2, monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)
    monkeypatch.undo()

    for found in find_interruptions(Path(simple_catalog.catalog_path)):
        revert_files(found)
        remove_created_directories(found)

    fresh, _s = make_plan(simple_catalog, tmp_path)
    checks = preflight(fresh)
    assert [c for c in checks.checks if c.name == "unfinished-run"][0].level == "ok"


def test_putting_files_back_twice_is_harmless(simple_catalog, tmp_path, monkeypatch):
    before = files_under(simple_catalog)
    plan, settings = make_plan(simple_catalog, tmp_path)
    kill_after(2, monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)
    monkeypatch.undo()

    found = find_interruptions(Path(simple_catalog.catalog_path))[0]
    revert_files(found)
    again, errors = revert_files(found)
    assert again == 0 and not errors
    assert files_under(simple_catalog) == before


def test_moved_back_files_alone_do_not_mean_an_interrupted_reversal(simple_catalog, tmp_path):
    """The filesystem cannot tell the difference, so it is not asked to.

    Files sitting at their old paths look the same whether a reversal was cut
    short or another run put them there. Only the run's record knows.
    """
    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)

    for move in [m for m in plan.moves if m.is_active][:2]:
        Path(move.source_path).parent.mkdir(parents=True, exist_ok=True)
        os.replace(move.target_path, move.source_path)

    from lrfoldercraft.runs import read_record

    record = read_record(Path(result.run_directory))
    assert not record.reversal_was_cut_short
    assert inspect(result.journal_path, record).state == COMPLETE


def test_a_run_that_committed_but_did_not_finish_needs_no_moving(
    simple_catalog, tmp_path, monkeypatch
):
    """Past the commit the two sides agree; only the bookkeeping is missing."""
    import lrfoldercraft.executor as executor

    plan, settings = make_plan(simple_catalog, tmp_path)
    real = executor._verify
    monkeypatch.setattr(
        executor, "_verify", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt("died"))
    )
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)
    monkeypatch.setattr(executor, "_verify", real)

    journal = sorted(
        (Path(simple_catalog.catalog_path).parent / "LR-FolderCraft").rglob("journal.jsonl")
    )[-1]
    found = inspect(journal)
    assert found.state == NEEDS_RECORD
    assert found.at_target, "the files are at their new paths, which is correct"
    assert not found.to_revert, "and must not be moved back"
    assert revert_files(found) == (0, [])


def test_a_committed_run_is_never_reverted_by_mistake(simple_catalog, tmp_path, monkeypatch):
    """The dangerous case: files at their targets after the catalog agreed.

    Reverting there would break the agreement the run established. The list of
    files to move back is empty unless reverting is the right direction, so a
    caller cannot get this wrong by reading the wrong field.
    """
    import lrfoldercraft.executor as executor

    plan, settings = make_plan(simple_catalog, tmp_path)
    monkeypatch.setattr(
        executor, "_verify", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt("died"))
    )
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)
    monkeypatch.undo()

    after = files_under(simple_catalog)
    for found in find_interruptions(Path(simple_catalog.catalog_path)):
        revert_files(found)
        remove_created_directories(found)
    assert files_under(simple_catalog) == after, "nothing may move"


def test_a_finished_reversal_is_not_reported_as_interrupted(simple_catalog, tmp_path):
    """Two runs into the same target tree made a finished reversal look half done.

    The later run recreates the very paths the earlier one left behind, so the
    filesystem says nothing. It produced a blocking pre-flight error against a
    library that was perfectly sound, which is worse than no check at all.
    """
    plan, settings = make_plan(simple_catalog, tmp_path)
    first = execute(plan, settings)
    undo(first.journal_path)

    # A second run puts files back at the same targets the first one used.
    plan2, settings2 = make_plan(simple_catalog, tmp_path)
    execute(plan2, settings2)

    reported = [f.journal_path for f in find_interruptions(Path(simple_catalog.catalog_path))]
    assert first.journal_path not in reported


def test_an_interrupted_reversal_is_recorded_not_guessed(simple_catalog, tmp_path, monkeypatch):
    import lrfoldercraft.executor as executor

    plan, settings = make_plan(simple_catalog, tmp_path)
    result = execute(plan, settings)

    real = executor.os.replace
    state = {"n": 0}

    def dying(source, target):
        if state["n"] >= 2:
            raise KeyboardInterrupt("died mid-reversal")
        state["n"] += 1
        return real(source, target)

    monkeypatch.setattr(executor.os, "replace", dying)
    with pytest.raises(KeyboardInterrupt):
        undo(result.journal_path)
    monkeypatch.undo()

    from lrfoldercraft.runs import read_record

    record = read_record(Path(result.run_directory))
    assert record.undo_started_at and not record.undone_at
    assert record.reversal_was_cut_short
    assert inspect(result.journal_path, record).state == NEEDS_UNDO

    # and finishing it is simply running undo again
    undo(result.journal_path)
    assert read_record(Path(result.run_directory)).undone_at


def test_a_repaired_run_is_never_reported_again(simple_catalog, tmp_path, monkeypatch):
    """Putting the files back has to leave a mark.

    Without one the run is judged from the paths alone next time, and a later
    run into the same target recreates them -- which reported runs repaired
    hours earlier and raised a blocking pre-flight error against a library that
    was perfectly sound. The user met exactly this on reopening the window.
    """
    plan, settings = make_plan(simple_catalog, tmp_path)
    kill_after(2, monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)
    monkeypatch.undo()

    found = find_interruptions(Path(simple_catalog.catalog_path))[0]
    restored, _errors = revert_files(found)
    remove_created_directories(found)
    assert restored

    from lrfoldercraft.runs import read_record

    record = read_record(Path(found.journal_path).parent)
    assert record.repaired_at and record.is_settled
    assert find_interruptions(Path(simple_catalog.catalog_path)) == []

    # and a later run recreating the same paths must not resurrect it
    later, later_settings = make_plan(simple_catalog, tmp_path)
    execute(later, later_settings)
    reported = [f.journal_path for f in find_interruptions(Path(simple_catalog.catalog_path))]
    assert found.journal_path not in reported


def test_the_command_line_marks_it_too(simple_catalog, tmp_path, monkeypatch):
    """inspect() looks the record up itself, so `lrfc resume` settles the run."""
    plan, settings = make_plan(simple_catalog, tmp_path)
    kill_after(2, monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)
    monkeypatch.undo()

    journal = sorted(
        (Path(simple_catalog.catalog_path).parent / "LR-FolderCraft").rglob("journal.jsonl")
    )[-1]
    found = inspect(journal)  # no record passed, as the command does it
    assert found.record is not None
    revert_files(found)

    from lrfoldercraft.runs import read_record

    assert read_record(journal.parent).is_settled


def test_an_overtaken_interruption_is_never_acted_on(simple_catalog, tmp_path, monkeypatch):
    """The dangerous one: the files at those paths belong to a later run.

    An interrupted run leaves files at target paths. If a later run then
    reorganises the library into the same tree, those paths are occupied by the
    newer run's files -- and "putting them back" would tear that run apart
    while its catalog still points at them.
    """
    plan, settings = make_plan(simple_catalog, tmp_path)
    kill_after(2, monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)
    monkeypatch.undo()

    # Repair it, then run again into the same structure.
    for found in find_interruptions(Path(simple_catalog.catalog_path)):
        revert_files(found)
        remove_created_directories(found)
    later, later_settings = make_plan(simple_catalog, tmp_path)
    result = execute(later, later_settings)
    assert result.success

    after = files_under(simple_catalog)
    assert find_interruptions(Path(simple_catalog.catalog_path)) == []

    # Even asked about it directly, the older run offers nothing to move.
    from lrfoldercraft.runs import history, journal_of

    oldest = history(Path(simple_catalog.catalog_path))[-1]
    found = inspect(journal_of(oldest), oldest)
    found.overtaken = True
    assert found.to_revert == []
    revert_files(found)
    assert files_under(simple_catalog) == after, "the later run must be untouched"


def test_an_interruption_is_actionable_while_it_is_the_newest(
    simple_catalog, tmp_path, monkeypatch
):
    """The case that must keep working: nothing has happened since."""
    plan, settings = make_plan(simple_catalog, tmp_path)
    kill_after(2, monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        execute(plan, settings)
    monkeypatch.undo()

    pending = find_interruptions(Path(simple_catalog.catalog_path))
    assert pending and pending[0].to_revert
    assert not pending[0].overtaken
