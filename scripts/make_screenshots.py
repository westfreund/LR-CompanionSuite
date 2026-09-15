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

# The window remembers what it was last set to, and this script sets it to a
# throwaway catalog in a temporary directory. Left alone it would write that
# path into the real configuration and the operator's next start would point at
# a catalog that no longer exists -- so the whole run gets its own config home.
_CONFIG_HOME = tempfile.mkdtemp(prefix="lrfc-screenshots-")
os.environ["LRFC_CONFIG_DIR"] = _CONFIG_HOME

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
    # Keywords, so the search window has something to find. Lightroom users
    # keep them; a demonstration catalog without any shows an empty table.
    holiday = builder.add_keyword("Urlaub")
    carnival = builder.add_keyword("Fasching")
    for file_id in builder.query("SELECT id_local FROM AgLibraryFile ORDER BY id_local"):
        builder.tag(file_id[0], holiday if file_id[0] % 2 else carnival)
    return builder


def shoot_tui(catalog: Path) -> None:
    from lrcompanion.tui.app import LRFolderCraftApp

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
    """Two pictures per language: what you meet, and what you work in.

    One shot cannot do both since the window went to tabs -- the first tab is
    where a reader starts, and the folder table is where the tool earns its
    keep.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from lrcompanion.gui.app import MainWindow

    app = QApplication.instance() or QApplication([])
    for language in LANGUAGES:
        window = MainWindow(catalog=str(catalog), language=language)
        window.resize(1180, 820)
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
        for tab, suffix in ((0, ""), (3, "-folders")):
            window.tabs.setCurrentIndex(tab)
            for _ in range(20):
                app.processEvents()
            target = IMAGES / "gui-{lang}{s}.png".format(lang=language, s=suffix)
            window.grab().save(str(target))
            print("  wrote {p}".format(p=target.relative_to(ROOT)))
        window.close()
        app.processEvents()


def shoot_metasearch(catalog: Path) -> None:
    """The LR-MetaSearch window, with a small index behind it."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import tempfile

    from PySide6.QtWidgets import QApplication

    from lrcompanion.metasearch.gui.app import MetaSearchWindow
    from lrcompanion.metasearch.scan import scan
    from lrcompanion.metasearch.store import Index

    index_path = Path(tempfile.mkdtemp(prefix="lrcs-shot-")) / "index.db"
    with Index.open(index_path) as index:
        scan([catalog], index)

    app = QApplication.instance() or QApplication([])
    for language in LANGUAGES:
        window = MetaSearchWindow(language=language, index_path=str(index_path))
        window.resize(1100, 780)
        window.show()
        for _ in range(60):
            app.processEvents()
        window.keywords_edit.setText("Urlaub")
        window.do_search()
        for _ in range(400):
            app.processEvents()
            if window.hits:
                break
        for _ in range(20):
            app.processEvents()
        target = IMAGES / "metasearch-{lang}.png".format(lang=language)
        window.grab().save(str(target))
        print("  wrote {p}".format(p=target.relative_to(ROOT)))
        window.close()
        app.processEvents()


def shoot_launcher() -> None:
    """The suite's launcher, which is the first thing anybody sees."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from lrcompanion.suite.launcher import Launcher

    app = QApplication.instance() or QApplication([])
    for language in LANGUAGES:
        window = Launcher(language=language)
        window.resize(760, 540)
        window.show()
        for _ in range(40):
            app.processEvents()
        target = IMAGES / "launcher-{lang}.png".format(lang=language)
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
        # Inside the temporary directory: the catalog it reads is in there.
        print("LR-MetaSearch:")
        shoot_metasearch(catalog)
    print("Launcher:")
    shoot_launcher()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
