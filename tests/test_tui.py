"""Smoke tests for the Textual front end.

Skipped automatically when Textual is not installed, because the TUI is an
optional extra.
"""

from __future__ import annotations

import asyncio

import pytest

textual = pytest.importorskip("textual")

from textual.widgets import Input, Select, Static  # noqa: E402

from lrcompanion.tui.app import LRFolderCraftApp  # noqa: E402
from lrcompanion.version import REVISION  # noqa: E402


def test_header_shows_the_revision():
    app = LRFolderCraftApp()
    assert REVISION in app.SUB_TITLE


async def _drive(app, steps):
    async with app.run_test(size=(160, 60)) as pilot:
        await pilot.pause()
        return await steps(app, pilot)


def test_loads_a_catalog_and_plans(simple_catalog):
    import asyncio

    async def steps(app, pilot):
        for _ in range(80):
            await pilot.pause(0.05)
            if "Files" in str(app.query_one("#catalog-info", Static).content):
                break
        assert "Files" in str(app.query_one("#catalog-info", Static).content)

        app.action_plan()
        for _ in range(200):
            await pilot.pause(0.05)
            if app.plan is not None:
                break
        assert app.plan is not None
        assert app.plan.stats.total == 6
        return True

    app = LRFolderCraftApp(catalog=str(simple_catalog.catalog_path))
    assert asyncio.run(_drive(app, steps))


def test_live_preview_follows_preset_and_custom_template():
    import asyncio

    async def steps(app, pilot):
        assert "2019-01-03" in str(app.query_one("#preview", Static).content)
        app.query_one("#custom", Input).value = "{camera_slug}/{iso_year}-W{iso_week}"
        await pilot.pause()
        assert "canon-eos-70d/2019-W01" in str(app.query_one("#preview", Static).content)
        app.query_one("#custom", Input).value = "{bogus}"
        await pilot.pause()
        assert "unknown token" in str(app.query_one("#preview", Static).content)
        app.query_one("#custom", Input).value = ""
        app.query_one("#preset", Select).value = "year/month/day"
        await pilot.pause()
        assert "2019/01/03" in str(app.query_one("#preview", Static).content)
        return True

    assert asyncio.run(_drive(LRFolderCraftApp(), steps))


def test_apply_requires_confirmation(simple_catalog):
    import asyncio

    async def steps(app, pilot):
        app.action_plan()
        for _ in range(200):
            await pilot.pause(0.05)
            if app.plan is not None:
                break
        app.action_apply()
        await pilot.pause(0.2)
        # The preconditions come first, and declining them stops the run.
        assert type(app.screen).__name__ == "PreconditionScreen"
        app.screen.dismiss(False)
        await pilot.pause(0.2)
        assert type(app.screen).__name__ != "ConfirmScreen"
        assert (simple_catalog.images_dir / "A0001.CR2").exists()
        return True

    app = LRFolderCraftApp(catalog=str(simple_catalog.catalog_path))
    assert asyncio.run(_drive(app, steps))


def test_language_toggle():
    import asyncio

    async def steps(app, pilot):
        assert app.language == "en"
        await pilot.press("f1")
        await pilot.pause()
        assert app.language == "de"
        return True

    assert asyncio.run(_drive(LRFolderCraftApp(), steps))


def test_folder_decisions_are_shown_and_can_be_cycled(builder):
    """Enter on a folder row changes its decision and re-plans."""
    import asyncio

    from textual.widgets import DataTable

    builder.add_photo("FLACH.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    builder.add_photo("U1.CR2", "2019-01-03T11:00:00", folder="raw2019/Urlaub/")
    builder.add_photo("D1.CR2", "2019-03-10T11:00:00", folder="raw2019/2019-03-10/")

    async def steps(app, pilot):
        app.action_plan()
        for _ in range(200):
            await pilot.pause(0.05)
            if app.plan is not None:
                break
        assert app.plan is not None

        cases = app.query_one("#cases", DataTable)
        assert cases.row_count == 3  # anchor, Urlaub, dated
        paths = [c.path_from_root for c in app._case_rows]
        assert "raw2019/Urlaub/" in paths

        # the dated folder is kept by default
        dated = next(c for c in app._case_rows if c.name == "2019-03-10")
        assert dated.action == "keep"

        # cycle the topic folder's decision
        index = paths.index("raw2019/Urlaub/")
        urlaub_id = app._case_rows[index].folder_id
        app.folder_overrides[urlaub_id] = "sort-inside"
        app.plan = None
        app.action_plan()
        for _ in range(200):
            await pilot.pause(0.05)
            if app.plan is not None:
                break
        move = next(m for m in app.plan.moves if m.filename == "U1.CR2")
        assert move.target_segments == ("raw2019", "Urlaub", "2019-01-03")
        return True

    app = LRFolderCraftApp(catalog=str(builder.catalog_path))
    assert asyncio.run(_drive(app, steps))


# -- the shortcuts the footer advertises -------------------------------------


def test_every_advertised_shortcut_actually_fires():
    """Three of the four did nothing at all.

    Textual reserves ctrl+p for its command palette and binds it with priority,
    so an ordinary binding of the same key never fires; ctrl+r and f1 were
    swallowed the same way. The footer promised four shortcuts and delivered
    one, which is worse than promising none.
    """
    keys = [
        ("ctrl+l", "action_load_catalog"),
        ("ctrl+p", "action_plan"),
        ("ctrl+r", "action_apply"),
        ("f1", "action_toggle_language"),
    ]
    app = LRFolderCraftApp(catalog="", language="de")
    called = []

    async def drive():
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            for _key, name in keys:
                setattr(app, name, (lambda n=name: called.append(n)))
            for key, name in keys:
                called.clear()
                await pilot.press(key)
                await pilot.pause()
                assert name in called, key

    asyncio.run(drive())


def test_the_shortcuts_work_while_typing_in_a_field():
    """Which is where an operator's hands actually are."""
    app = LRFolderCraftApp(catalog="", language="de")
    called = []

    async def drive():
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.action_plan = lambda: called.append("plan")
            app.query_one("#catalog-path").focus()
            await pilot.pause()
            await pilot.press("ctrl+p")
            await pilot.pause()

    asyncio.run(drive())
    assert called == ["plan"]


def test_escape_declines_the_confirmation(simple_catalog):
    """A modal in front of fifty thousand moves must be escapable."""
    app = LRFolderCraftApp(catalog=str(simple_catalog.catalog_path), language="de")
    seen = {}

    async def drive():
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+l")
            for _ in range(80):
                await asyncio.sleep(0.05)
            await pilot.press("ctrl+p")
            for _ in range(200):
                await asyncio.sleep(0.05)
                if app.plan is not None:
                    break
            await pilot.press("ctrl+r")
            await asyncio.sleep(0.3)
            # Acknowledge the preconditions so the confirmation is reached.
            app.screen.query_one("#ack").value = True
            await asyncio.sleep(0.2)
            app.screen.dismiss(True)
            await asyncio.sleep(0.4)
            seen["modal"] = type(app.screen_stack[-1]).__name__
            await pilot.press("escape")
            await asyncio.sleep(0.3)
            seen["after"] = type(app.screen_stack[-1]).__name__

    asyncio.run(drive())
    assert seen["modal"] == "ConfirmScreen"
    assert seen["after"] != "ConfirmScreen", "escape must dismiss the dialog"


# -- the safety net, now present here too ------------------------------------


def test_the_preconditions_gate_the_apply(simple_catalog):
    """Without this the text interface could write with less protection
    than the window, which is how it shipped for twelve revisions."""
    seen = {}

    async def steps(app, pilot):
        app.action_plan()
        for _ in range(200):
            await pilot.pause(0.05)
            if app.plan is not None:
                break
        app.action_apply()
        await pilot.pause(0.3)
        seen["first"] = type(app.screen).__name__
        seen["blocked"] = app.screen.query_one("#pre-yes").disabled
        app.screen.query_one("#ack").value = True
        await pilot.pause(0.2)
        seen["after_tick"] = app.screen.query_one("#pre-yes").disabled
        app.screen.dismiss(False)
        await pilot.pause(0.2)
        return True

    assert asyncio.run(_drive(LRFolderCraftApp(catalog=str(simple_catalog.catalog_path)), steps))
    assert seen["first"] == "PreconditionScreen"
    assert seen["blocked"] is True, "the button must start unusable"
    assert seen["after_tick"] is False, "ticking must enable it"


def test_the_history_screen_lists_recorded_runs(simple_catalog, tmp_path):
    from lrcompanion.catalog import CatalogReader, open_catalog
    from lrcompanion.config import Settings
    from lrcompanion.executor import execute
    from lrcompanion.planner import build_plan

    settings = Settings(
        catalog=str(simple_catalog.catalog_path),
        dry_run=False,
        structure=("{yyyy}-{mm}-{dd}",),
        backup_dir=str(tmp_path / "backups"),
    )
    with open_catalog(simple_catalog.catalog_path) as conn:
        plan = build_plan(CatalogReader(conn), settings)
    execute(plan, settings)

    seen = {}

    async def steps(app, pilot):
        app.action_history()
        await pilot.pause(0.3)
        seen["screen"] = type(app.screen).__name__
        seen["rows"] = app.screen.query_one("#runs").row_count
        app.screen.dismiss(None)
        await pilot.pause(0.2)
        return True

    assert asyncio.run(_drive(LRFolderCraftApp(catalog=str(simple_catalog.catalog_path)), steps))
    assert seen["screen"] == "HistoryScreen"
    assert seen["rows"] == 1


def test_the_new_options_reach_the_settings(simple_catalog):
    from textual.widgets import Checkbox, Input

    seen = {}

    async def steps(app, pilot):
        app.query_one("#cumulative", Checkbox).value = True
        app.query_one("#orphans", Checkbox).value = True
        app.query_one("#orphan-folder", Input).value = "_ohne_Katalog"
        app.query_one("#exclude-ext", Input).value = "tif, jpg"
        app.query_one("#rules", Input).value = "_extern=leave, *=consolidate"
        await pilot.pause(0.1)
        seen["settings"] = app._collect_settings()
        return True

    assert asyncio.run(_drive(LRFolderCraftApp(catalog=str(simple_catalog.catalog_path)), steps))
    s = seen["settings"]
    assert s.cumulative_dates is True
    assert s.collect_orphans is True
    assert s.orphan_folder == "_ohne_Katalog"
    assert s.exclude_extensions == ("tif", "jpg")
    assert s.folder_rules == ("_extern=leave", "*=consolidate")
