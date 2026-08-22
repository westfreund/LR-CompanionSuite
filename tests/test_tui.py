"""Smoke tests for the Textual front end.

Skipped automatically when Textual is not installed, because the TUI is an
optional extra.
"""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual")

from textual.widgets import Input, Select, Static  # noqa: E402

from lrfoldercraft.tui.app import LRFolderCraftApp  # noqa: E402
from lrfoldercraft.version import REVISION  # noqa: E402


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
        assert type(app.screen).__name__ == "ConfirmScreen"
        app.screen.dismiss(False)
        await pilot.pause(0.2)
        # nothing was written
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
