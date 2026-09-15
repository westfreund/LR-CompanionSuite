"""The launcher and the LR-MetaSearch window.

Skipped when PySide6 is absent, like the folder tool's window tests: the
graphical front ends are an optional extra.
"""

from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from lrcompanion.metasearch.gui.app import MetaSearchWindow  # noqa: E402
from lrcompanion.metasearch.gui.i18n import TEXT as SEARCH_TEXT  # noqa: E402
from lrcompanion.metasearch.scan import scan  # noqa: E402
from lrcompanion.metasearch.store import Index  # noqa: E402
from lrcompanion.suite import TOOLS  # noqa: E402
from lrcompanion.suite.i18n import TEXT as SUITE_TEXT  # noqa: E402
from lrcompanion.suite.launcher import Launcher  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    application = QApplication.instance() or QApplication([])
    yield application


def pump(condition, seconds: float = 20.0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        QCoreApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return condition()


@pytest.fixture
def index_with_a_library(builder, tmp_path):
    holiday = builder.add_keyword("Urlaub")
    first = builder.add_photo("A0001.CR2", "2019-01-03T11:00:00", camera="Canon EOS 70D")
    builder.tag(first, holiday)
    builder.set_size(first, 6000, 4000)
    builder.add_photo("B0001.CR2", "2020-06-08T09:00:00", camera="Nikon Z6")
    path = tmp_path / "index.db"
    with Index.open(path) as index:
        scan([builder.catalog_path], index)
    return str(path)


# -- the launcher ------------------------------------------------------------


def test_the_launcher_offers_every_tool(qt_app):
    window = Launcher()
    assert [tile.tool.name for tile in window.tiles] == [tool.name for tool in TOOLS]
    window.close()


def test_a_tile_opens_its_own_tool(qt_app):
    """Each tile must open the tool it names.

    A lambda over the loop variable would give every tile the last tool, which
    nobody notices while there are two and everybody notices at three.
    """
    window = Launcher()
    opened = []
    window.open_tool = opened.append
    for tile in window.tiles:
        tile.open_button.click()
    assert opened == [tool.key for tool in TOOLS]
    window.close()


def test_the_launcher_speaks_both_languages(qt_app):
    window = Launcher(language="de")
    german = window.purpose.text()
    window.toggle_language()
    assert window.purpose.text() != german
    window.close()


def test_every_tool_has_a_description_in_both_languages():
    """A tile with no text is a tile nobody presses."""
    for tool in TOOLS:
        key = "{k}_what".format(k=tool.key)
        assert key in SUITE_TEXT, key
        english, german = SUITE_TEXT[key]
        assert english and german and english != german


# -- the search window -------------------------------------------------------


def test_the_search_window_lists_what_the_index_holds(qt_app, index_with_a_library):
    window = MetaSearchWindow(index_path=index_with_a_library)
    assert pump(lambda: window.library_table.rowCount() == 1)
    assert window.drive_table.rowCount() == 1
    window.close()


def test_searching_fills_the_table(qt_app, index_with_a_library):
    window = MetaSearchWindow(index_path=index_with_a_library)
    window.keywords_edit.setText("Urlaub")
    window.do_search()
    assert pump(lambda: bool(window.hits))
    assert window.result_table.rowCount() == 1
    assert window.result_table.item(0, 1).text() == "A0001.CR2"
    window.close()


def test_a_search_without_criteria_is_refused(qt_app, index_with_a_library):
    """Rather than returning every photograph in every library."""
    from lrcompanion.metasearch.gui import app as gui_app

    window = MetaSearchWindow(index_path=index_with_a_library)
    seen = []
    original = gui_app.QMessageBox.information
    gui_app.QMessageBox.information = staticmethod(lambda *a, **k: seen.append(a[-1]))
    try:
        window.do_search()
    finally:
        gui_app.QMessageBox.information = original
    assert len(seen) == 1
    assert window.hits == []
    window.close()


def test_clearing_puts_every_criterion_back(qt_app, index_with_a_library):
    window = MetaSearchWindow(index_path=index_with_a_library)
    window.keywords_edit.setText("Urlaub")
    window.camera_edit.setText("Nikon")
    window.rating_combo.setCurrentIndex(3)
    window.do_search()
    pump(lambda: window.hits is not None)
    window.clear_criteria()
    assert window.current_filter().is_empty
    assert window.result_table.rowCount() == 0
    window.close()


def test_the_window_speaks_both_languages(qt_app, index_with_a_library):
    window = MetaSearchWindow(language="de", index_path=index_with_a_library)
    german = window.tabs.tabText(0)
    window.toggle_language()
    assert window.tabs.tabText(0) != german
    window.close()


def test_every_string_exists_in_both_languages():
    for key, (english, german) in SEARCH_TEXT.items():
        assert english, key
        assert german, key


def test_the_buttons_do_not_lie_about_the_commands():
    """The launcher tells people what to type; it had better work."""
    from lrcompanion.metasearch.main import build_parser

    choices = build_parser()._subparsers._group_actions[0].choices
    for tool in TOOLS:
        command, _, subcommand = tool.command.partition(" ")
        if command == "lrms":
            assert subcommand in choices, tool.command
