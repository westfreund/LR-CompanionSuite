"""Regenerate the screenshots in docs/images from the current code.

The images in the READMEs went stale within one revision because there was no
way to remake them. This script builds a small demonstration catalog, drives
both interfaces against it and writes the four files, so the pictures can be
refreshed as part of a release rather than redrawn by hand.

    python scripts/make_screenshots.py

Needs the tui and gui extras. Run it from the repository root.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

IMAGES = ROOT / "docs" / "images"
LANGUAGES = ("en", "de")


def build_demo_catalog(directory: Path):
    """A library with the shapes the screenshots should show off."""
    from conftest import CatalogBuilder

    builder = CatalogBuilder(directory, catalog_name="Beispiel.lrcat")
    for day, name in (("01-03", "A0001"), ("01-03", "A0002"), ("02-14", "A0003")):
        builder.add_photo(
            "{n}.CR2".format(n=name), "2019-{d}T11:00:00".format(d=day), folder="raw2019/"
        )
    builder.add_photo("U1.CR2", "2019-05-20T11:00:00", folder="raw2019/Urlaub/")
    builder.add_photo("U2.CR2", "2019-05-21T11:00:00", folder="raw2019/Urlaub/")
    builder.add_photo("D1.CR2", "2019-03-10T11:00:00", folder="raw2019/2019-03-10 Fasching/")
    # A photo whose own date disagrees with the folder naming the session --
    # this is what puts a row in the findings table.
    builder.add_photo("D2.CR2", "2019-07-07T11:00:00", folder="raw2019/2019-03-10 Fasching/")
    return builder


def shoot_tui(catalog: Path) -> None:
    from lrfoldercraft.tui.app import LRFolderCraftApp

    async def run(language: str) -> None:
        app = LRFolderCraftApp(catalog=str(catalog), language=language)
        async with app.run_test(size=(150, 42)) as pilot:
            await pilot.pause()
            await asyncio.sleep(0.5)
            target = IMAGES / "tui-{lang}.svg".format(lang=language)
            app.save_screenshot(str(target))
            print("  wrote {p}".format(p=target.relative_to(ROOT)))

    for language in LANGUAGES:
        asyncio.run(run(language))


def shoot_gui(catalog: Path) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from lrfoldercraft.gui.app import MainWindow

    app = QApplication.instance() or QApplication([])
    for language in LANGUAGES:
        window = MainWindow(catalog=str(catalog), language=language)
        window.resize(1180, 900)
        window.show()
        for _ in range(80):  # let the catalog worker finish and the plan land
            app.processEvents()
        window.do_plan()
        for _ in range(200):
            app.processEvents()
            if window.plan is not None:
                break
        for _ in range(20):
            app.processEvents()
        target = IMAGES / "gui-{lang}.png".format(lang=language)
        window.grab().save(str(target))
        print("  wrote {p}".format(p=target.relative_to(ROOT)))
        window.close()
        app.processEvents()


def main() -> int:
    IMAGES.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        builder = build_demo_catalog(Path(tmp))
        catalog = builder.catalog_path
        print("Demonstration catalog: {c}".format(c=catalog))
        print("TUI:")
        shoot_tui(catalog)
        print("GUI:")
        shoot_gui(catalog)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
