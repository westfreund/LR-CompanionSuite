"""Smoke tests for the Qt front end.

Skipped when PySide6 is absent, because the GUI is an optional extra. Qt runs
on the offscreen platform so these work in CI without a display.
"""

from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Importing the top-level package is not enough: PySide6 is a namespace whose
# submodules pull in the Qt shared libraries, and those are what a bare Linux
# image lacks. Skipping on the submodule turns a missing libglib into a skip
# instead of a collection error.
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from lrfoldercraft.config import Settings  # noqa: E402
from lrfoldercraft.gui.app import MainWindow, _split_extensions  # noqa: E402
from lrfoldercraft.version import REVISION  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    application = QApplication.instance() or QApplication([])
    yield application


def pump(condition, seconds: float = 15.0) -> bool:
    """Run the Qt event loop until *condition* holds or the time runs out."""
    end = time.time() + seconds
    while time.time() < end:
        QCoreApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return condition()


@pytest.fixture
def mixed_gui_catalog(builder):
    builder.add_photo("FLACH.CR2", "2019-01-03T10:00:00", folder="raw2019/")
    builder.add_photo("U1.CR2", "2019-01-03T11:00:00", folder="raw2019/Urlaub/")
    builder.add_photo("U2.CR2", "2019-05-20T11:00:00", folder="raw2019/Urlaub/")
    builder.add_photo("D1.CR2", "2019-03-10T11:00:00", folder="raw2019/2019-03-10 Fasching/")
    return builder


def test_window_shows_the_revision(qt_app):
    window = MainWindow()
    assert REVISION in window.windowTitle()


def test_option_defaults_match_the_settings_defaults(qt_app):
    """The GUI must not quietly disagree with the CLI and the documentation."""
    window = MainWindow()
    defaults = Settings()
    assert window.conflict_combo.currentText() == defaults.conflict
    assert window.missing_combo.currentText() == defaults.on_missing_date
    assert window.subfolder_combo.currentText() == defaults.subfolder_action
    assert window.dated_combo.currentText() == defaults.dated_folder_action
    assert window.mismatch_combo.currentText() == defaults.mismatch_action
    assert window.sidecars_check.isChecked() == defaults.move_sidecars
    assert window.backup_check.isChecked() == defaults.backup_catalog
    assert window.ascii_check.isChecked() == defaults.ascii_only


def test_live_preview_follows_preset_and_custom_template(qt_app):
    window = MainWindow()
    window.preset_combo.setCurrentText("year/month/day")
    assert window.preview_label.text() == "2019/01/03"
    window.custom_edit.setText("{camera_slug}/{iso_year}-W{iso_week}")
    assert window.preview_label.text() == "canon-eos-70d/2019-W01"
    window.custom_edit.setText("{bogus}")
    assert "unknown token" in window.preview_label.text()


def test_loading_a_catalog_fills_the_summary_and_roots(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    assert "4" in window.catalog_info.text()
    assert window.root_combo.count() == 2  # "all" plus the one root


def test_planning_fills_the_folder_table(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.do_plan()
    assert pump(lambda: window.plan is not None)

    paths = [c.path_from_root for c in window.cases]
    assert "raw2019/Urlaub/" in paths
    assert "raw2019/2019-03-10 Fasching/" in paths
    assert window.folder_table.rowCount() == len(window.cases)

    anchor_row = paths.index("raw2019/")
    assert window.folder_table.cellWidget(anchor_row, 4) is None  # never decided
    urlaub_row = paths.index("raw2019/Urlaub/")
    assert window.folder_table.cellWidget(urlaub_row, 4).currentData() == "consolidate"


def test_changing_a_decision_replans(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.do_plan()
    assert pump(lambda: window.plan is not None)

    paths = [c.path_from_root for c in window.cases]
    combo = window.folder_table.cellWidget(paths.index("raw2019/Urlaub/"), 4)
    combo.setCurrentIndex([combo.itemData(i) for i in range(combo.count())].index("sort-inside"))
    assert pump(lambda: window.plan is not None)

    targets = {m.filename: m.target_segments for m in window.plan.moves}
    assert targets["U1.CR2"] == ("raw2019", "Urlaub", "2019-01-03")
    assert targets["FLACH.CR2"] == ("raw2019", "2019-01-03")


def test_applying_moves_the_files(qt_app, mixed_gui_catalog, tmp_path, monkeypatch):
    monkeypatch.setenv("LRFC_BACKUP_DIR", str(tmp_path / "backups"))
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.do_plan()
    assert pump(lambda: window.plan is not None)

    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
    # The preconditions dialog is modal; acknowledge it without opening it.
    monkeypatch.setattr(window, "_preconditions_accepted", lambda: True)
    window.do_apply()
    assert pump(lambda: window.plan is None and window.progress.value() == 100)

    images = mixed_gui_catalog.images_dir
    assert (images / "raw2019" / "2019-01-03" / "FLACH.CR2").exists()
    assert (images / "raw2019" / "2019-03-10 Fasching" / "D1.CR2").exists()
    for path in mixed_gui_catalog.catalog_paths():
        assert os.path.exists(path), path


def test_new_tree_target_is_collected(qt_app, mixed_gui_catalog, tmp_path):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.target_new_tree.setChecked(True)
    window.target_edit.setText(str(tmp_path / "Sortiert"))
    settings = window.collect_settings()
    assert settings.placement == "new-tree"
    assert settings.target_root == str(tmp_path / "Sortiert")
    window.wait_for_workers()


def test_closing_while_a_worker_runs_does_not_abort(qt_app, mixed_gui_catalog):
    """Tearing the window down mid-run used to kill the process."""
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    window.close()  # immediately, while the catalog worker is starting
    assert not any(thread.isRunning() for thread, _ in window._threads)


def test_finished_threads_are_forgotten(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    assert pump(lambda: not window._threads), "thread list keeps growing"


def test_language_can_be_switched(qt_app):
    window = MainWindow(language="en")
    assert window.plan_button.text().startswith("Plan")
    window.toggle_language()
    assert window.language == "de"
    assert window.plan_button.text().startswith("Planen")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("cr2, dng", ("cr2", "dng")),
        (".CR2;.DNG", ("cr2", "dng")),
        ("", ()),
        ("  ", ()),
    ],
)
def test_extension_parsing(text, expected):
    assert _split_extensions(text) == expected


# -- fitting on a small screen ----------------------------------------------


def _bottom_of(window, widget) -> int:
    """Y coordinate of a widget's lower edge, in window coordinates."""
    return widget.mapTo(window, widget.rect().bottomLeft()).y()


def test_the_window_never_opens_larger_than_the_screen(qt_app):
    from PySide6.QtGui import QGuiApplication

    window = MainWindow()
    available = QGuiApplication.primaryScreen().availableGeometry()
    assert window.width() <= available.width()
    assert window.height() <= available.height()


def test_the_minimum_size_fits_a_small_laptop(qt_app):
    """A fixed 1024x860 put the buttons below the bottom edge of a 13-inch."""
    window = MainWindow()
    assert window.minimumWidth() <= 800
    assert window.minimumHeight() <= 500


@pytest.mark.parametrize("height", [900, 700, 560, 480, 420])
def test_the_action_row_stays_visible_at_every_height(qt_app, height):
    window = MainWindow()
    window.show()
    window.resize(900, height)
    for _ in range(20):
        QCoreApplication.processEvents()
    for widget in (window.plan_button, window.apply_button, window.progress):
        assert _bottom_of(window, widget) <= window.height(), (
            "{w} is below the bottom edge at height {h}".format(
                w=widget.objectName() or type(widget).__name__, h=height
            )
        )
    window.close()


def test_the_settings_area_scrolls_when_it_does_not_fit(qt_app):
    window = MainWindow()
    window.show()
    window.resize(900, 420)
    for _ in range(20):
        QCoreApplication.processEvents()
    scrollbar = window.settings_scroll.verticalScrollBar()
    assert scrollbar.maximum() > 0, "the settings cannot be reached by scrolling"
    window.close()


def test_shrinking_below_the_minimum_is_refused(qt_app):
    window = MainWindow()
    window.show()
    window.resize(1, 1)
    for _ in range(20):
        QCoreApplication.processEvents()
    assert window.width() >= window.minimumWidth()
    assert window.height() >= window.minimumHeight()
    assert _bottom_of(window, window.plan_button) <= window.height()
    window.close()


# -- the ordered rule list ---------------------------------------------------


def test_rules_are_carried_into_the_settings(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.rules = [("_extern", "leave"), ("dated+label", "resort")]
    window._redraw_rules()
    settings = window.collect_settings()
    assert settings.folder_rules == ("_extern=leave", "dated+label=resort")


def test_a_rule_decides_the_folder_and_says_so(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.rules = [("Urlaub", "leave"), ("*", "consolidate")]
    window._redraw_rules()
    window.do_plan()
    assert pump(lambda: window.plan is not None)

    paths = [c.path_from_root for c in window.cases]
    row = paths.index("raw2019/Urlaub/")
    assert window.folder_table.cellWidget(row, 4).currentData() == "leave"
    assert window.folder_table.item(row, 3).text() == "1. Urlaub"


def test_reordering_rules_changes_which_one_wins(qt_app, mixed_gui_catalog):
    """Order is the whole point: the first match decides."""
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.rules = [("*", "consolidate"), ("Urlaub", "leave")]
    window._redraw_rules()
    window.do_plan()
    assert pump(lambda: window.plan is not None)
    paths = [c.path_from_root for c in window.cases]
    assert window.folder_table.item(paths.index("raw2019/Urlaub/"), 3).text() == "1. *"

    window.rule_table.selectRow(1)
    window._move_rule(-1)
    assert pump(lambda: window.plan is not None)
    paths = [c.path_from_root for c in window.cases]
    assert window.folder_table.item(paths.index("raw2019/Urlaub/"), 3).text() == "1. Urlaub"


def test_an_empty_pattern_is_dropped_rather_than_breaking_the_run(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.rules = [("", "leave"), ("*", "consolidate")]
    assert window.collect_settings().folder_rules == ("*=consolidate",)


def test_adding_and_removing_a_rule_keeps_the_table_in_step(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window._add_rule()
    assert pump(lambda: window.plan is not None)
    assert window.rule_table.rowCount() == len(window.rules) == 1
    window.rule_table.selectRow(0)
    window._remove_rule()
    assert pump(lambda: window.plan is not None)
    assert window.rule_table.rowCount() == len(window.rules) == 0


# -- what the plan could not decide alone ------------------------------------


@pytest.fixture
def catalog_with_a_stray_date(builder):
    """A dated folder holding one photo shot on a different day."""
    builder.add_photo("D1.CR2", "2019-03-10T11:00:00", folder="raw2019/2019-03-10 Fasching/")
    builder.add_photo("X1.CR2", "2019-07-07T11:00:00", folder="raw2019/2019-03-10 Fasching/")
    return builder


def test_the_findings_table_names_the_setting_to_change(qt_app, catalog_with_a_stray_date):
    """The point of the panel: an exception and its remedy in the same row."""
    window = MainWindow(catalog=str(catalog_with_a_stray_date.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.do_plan()
    assert pump(lambda: window.plan is not None)

    rows = {
        window.findings_table.item(r, 2).text(): r for r in range(window.findings_table.rowCount())
    }
    assert rows, "a grown library always has something worth reporting"
    mismatch = [r for text, r in rows.items() if "folder name" in text]
    assert mismatch, rows
    assert window.findings_table.item(mismatch[0], 3).text() == "--mismatch-action"
    assert window.findings_table.item(mismatch[0], 4).text() == "move-out"


def test_selecting_a_finding_shows_which_files_it_concerns(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.do_plan()
    assert pump(lambda: window.plan is not None)

    for row in range(window.findings_table.rowCount()):
        if window.findings[row].samples:
            window.findings_table.selectRow(row)
            assert window.findings[row].samples[0] in window.findings_detail.text()
            return
    pytest.fail("no finding carried examples")


def test_the_summary_line_no_longer_carries_the_detail(qt_app, mixed_gui_catalog):
    """Warnings used to be crammed into the counts line; they have their own place now."""
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.do_plan()
    assert pump(lambda: window.plan is not None)
    assert "\n" not in window.summary_label.text()


# -- naming a target folder --------------------------------------------------


def test_the_target_field_is_usable_without_selecting_the_radio_first(qt_app, mixed_gui_catalog):
    """A greyed-out field beside a greyed-out button reads as "impossible"."""
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    assert window.target_edit.isEnabled()
    assert window.target_browse.isEnabled()


def test_naming_a_target_folder_selects_the_new_tree_mode(qt_app, mixed_gui_catalog, tmp_path):
    """Typing a path while 'in place' is selected cannot mean anything else."""
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    assert window.target_in_place.isChecked()

    target = tmp_path / "Neu"
    target.mkdir()
    window.target_edit.setText(str(target))
    window._target_named(str(target))

    assert window.target_new_tree.isChecked()
    settings = window.collect_settings()
    assert settings.placement == "new-tree"
    assert settings.target_root == str(target)


def test_choosing_in_place_again_ignores_the_leftover_path(qt_app, mixed_gui_catalog, tmp_path):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.target_edit.setText(str(tmp_path))
    window._target_named(str(tmp_path))
    window.target_in_place.setChecked(True)

    settings = window.collect_settings()
    assert settings.placement == "in-place"
    assert settings.target_root is None


# -- remembering the settings ------------------------------------------------


def test_the_language_survives_a_restart(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    assert window.language == "en"
    window.toggle_language()
    assert window.language == "de"
    window.close()

    again = MainWindow()
    assert again.language == "de"


def test_an_explicit_language_beats_the_remembered_one(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.toggle_language()  # remembers German
    window.close()

    assert MainWindow(language="en").language == "en"


def test_the_settings_come_back(qt_app, mixed_gui_catalog, tmp_path):
    target = tmp_path / "Ziel"
    target.mkdir()
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.target_edit.setText(str(target))
    window._target_named(str(target))
    window.mismatch_combo.setCurrentText("leave")
    window.subfolder_combo.setCurrentText("sort-inside")
    window.exclude_edit.setText("tif")
    window.sidecars_check.setChecked(False)
    window.rules = [("_extern", "leave"), ("dated+label", "resort")]
    window.close()

    again = MainWindow()
    assert again.catalog_edit.text() == str(mixed_gui_catalog.catalog_path)
    assert again.target_new_tree.isChecked()
    assert again.target_edit.text() == str(target)
    assert again.preset_combo.currentText() == "day"
    assert again.mismatch_combo.currentText() == "leave"
    assert again.subfolder_combo.currentText() == "sort-inside"
    assert again.exclude_edit.text() == "tif"
    assert again.sidecars_check.isChecked() is False
    assert again.rules == [("_extern", "leave"), ("dated+label", "resort")]
    again.close()


def test_the_backup_switch_is_never_restored(qt_app, mixed_gui_catalog):
    """Turning the safety net off must be decided for the run at hand."""
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.backup_check.setChecked(False)
    window.close()

    again = MainWindow()
    assert again.backup_check.isChecked() is True
    again.close()


def test_per_folder_decisions_are_never_restored(qt_app, mixed_gui_catalog):
    """They are catalog folder ids; another catalog would reuse the numbers."""
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.folder_decisions = {4711: "leave"}
    window.close()

    assert "folder_decisions" not in window.collect_state()
    again = MainWindow()
    assert again.folder_decisions == {}
    again.close()


def test_a_remembered_value_a_later_revision_dropped_is_ignored(qt_app):
    """An unknown action must leave the default standing, not empty the combo."""
    from lrfoldercraft.gui.state import save_state

    save_state({"language": "de", "subfolder_action": "teleport", "preset": "nonsense"})
    window = MainWindow()
    assert window.language == "de"
    assert window.subfolder_combo.currentText() == Settings().subfolder_action
    assert window.preset_combo.currentText() != "nonsense"
    window.close()


def test_an_unreadable_state_file_is_shrugged_off(qt_app):
    from lrfoldercraft.gui.state import state_path

    state_path().parent.mkdir(parents=True, exist_ok=True)
    state_path().write_text("{not json", encoding="utf-8")
    window = MainWindow()  # must not raise
    assert window.language == "en"
    window.close()


# -- the dividers between the sections ---------------------------------------


def test_every_splitter_section_gets_a_size(qt_app):
    """Qt calls a short size list undefined, and the log section was the loser."""
    window = MainWindow()
    assert len(window.SPLITTER_SHARES) == window.splitter.count()
    window._balance_splitter(900)
    assert len(window.splitter.sizes()) == window.splitter.count()
    assert all(size > 0 for size in window.splitter.sizes())
    window.close()


def test_the_dividers_say_what_they_are(qt_app):
    window = MainWindow()
    handles = [window.splitter.handle(i) for i in range(1, window.splitter.count())]
    assert handles and all(h is not None for h in handles)
    assert all(h.toolTip() for h in handles)
    window.close()


def test_the_divider_tooltip_follows_the_language(qt_app):
    window = MainWindow(language="de")
    assert "Ziehen" in window.splitter.handle(1).toolTip()
    window.toggle_language()
    assert "Drag" in window.splitter.handle(1).toolTip()
    window.close()


# -- reversing a run from the window -----------------------------------------


def test_the_window_offers_to_undo_a_run(qt_app):
    window = MainWindow()
    assert window.undo_action is not None
    assert window.undo_action.text()
    window.close()


def test_the_undo_entry_follows_the_language(qt_app):
    window = MainWindow(language="de")
    assert "rückgängig" in window.undo_action.text()
    window.toggle_language()
    assert "Undo" in window.undo_action.text()
    window.close()


def _library_files(builder):
    return sorted(
        str(p.relative_to(builder.images_dir))
        for p in builder.images_dir.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    )


def test_undoing_puts_the_library_back(qt_app, mixed_gui_catalog, monkeypatch):
    """End to end through the window: apply, then undo, and nothing has moved."""
    from PySide6.QtWidgets import QMessageBox

    before = _library_files(mixed_gui_catalog)
    before_catalog = mixed_gui_catalog.catalog_paths()

    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.do_plan()
    assert pump(lambda: window.plan is not None)

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
    # The preconditions dialog is modal; acknowledge it without opening it.
    monkeypatch.setattr(window, "_preconditions_accepted", lambda: True)
    window.do_apply()
    assert pump(lambda: window.plan is None and window.progress.value() == 100)
    assert window.last_journal, "the run must record where it can be undone from"
    assert _library_files(mixed_gui_catalog) != before  # something really moved

    monkeypatch.setattr(window, "_choose_journal", lambda: window.last_journal)
    window.do_undo()
    # Wait on the outcome itself: "busy" leaves the progress bar indeterminate,
    # so its value says nothing about whether the work has finished.
    assert pump(lambda: _library_files(mixed_gui_catalog) == before)
    window.wait_for_workers()

    assert mixed_gui_catalog.catalog_paths() == before_catalog
    window.close()


def test_menu_entries_live_inside_a_menu_not_on_the_bar(qt_app):
    """Qt does not support bare actions on the menu bar on macOS.

    Both entries were invisible there, which is how an undo nobody could reach
    shipped in r8.0.0.
    """
    window = MainWindow()
    # Every top-level entry on the bar must open a menu; a bare action there
    # is what macOS silently drops.
    top_level = window.menuBar().actions()
    assert top_level
    assert all(action.menu() is not None for action in top_level)

    entries = [entry.text() for entry in window.actions_menu.actions()]
    assert window.undo_action.text() in entries
    assert window.language_action.text() in entries
    window.close()


def test_undo_is_also_a_button_beside_apply(qt_app):
    """A rollback reachable only through a menu is one nobody finds in time."""
    window = MainWindow()
    assert window.undo_button.text()
    assert window.undo_button.isEnabled()
    window.close()


def test_undo_cannot_be_started_while_something_is_running(qt_app):
    window = MainWindow()
    window._busy(True, "…")
    assert not window.undo_button.isEnabled()
    assert not window.undo_action.isEnabled()
    window._busy(False)
    assert window.undo_button.isEnabled()
    window.close()


# -- sweeping files the catalog does not know --------------------------------


def test_the_sweep_is_off_until_it_is_asked_for(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    assert window.orphans_check.isChecked() is False
    assert window.orphan_edit.isEnabled() is False
    assert window.collect_settings().collect_orphans is False
    window.close()


def test_switching_the_sweep_on_enables_its_folder_name(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.orphans_check.setChecked(True)
    assert window.orphan_edit.isEnabled()
    settings = window.collect_settings()
    assert settings.collect_orphans
    assert settings.orphan_folder == Settings().orphan_folder
    window.close()


def test_an_empty_folder_name_falls_back_to_the_default(qt_app, mixed_gui_catalog):
    """An empty name would be refused by validation; the window must not send one."""
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.orphans_check.setChecked(True)
    window.orphan_edit.setText("   ")
    assert window.collect_settings().orphan_folder == Settings().orphan_folder
    window.close()


def test_the_sweep_setting_is_remembered(qt_app):
    window = MainWindow()
    window.orphans_check.setChecked(True)
    window.orphan_edit.setText("_ohne_Katalog")
    window.close()

    again = MainWindow()
    assert again.orphans_check.isChecked()
    assert again.orphan_edit.text() == "_ohne_Katalog"
    assert again.orphan_edit.isEnabled()
    again.close()


# -- the preconditions, acknowledged before the first run --------------------


def _preconditions_for(catalog):
    from pathlib import Path as _Path

    from lrfoldercraft.safety import preconditions

    return preconditions(_Path(catalog), Settings(catalog=str(catalog)))


def test_the_dialog_cannot_be_confirmed_without_ticking(qt_app, mixed_gui_catalog):
    """A confirmation given by reflex is not a confirmation."""
    from lrfoldercraft.gui.app import PreconditionDialog

    result = _preconditions_for(mixed_gui_catalog.catalog_path)
    dialog = PreconditionDialog(result, "en")
    assert dialog.ok_button.isEnabled() is False
    dialog.acknowledge.setChecked(True)
    assert dialog.ok_button.isEnabled() is True


def test_a_blocking_finding_cannot_be_acknowledged_away(qt_app, mixed_gui_catalog):
    from lrfoldercraft.gui.app import PreconditionDialog
    from lrfoldercraft.safety import ERROR, Check, PreflightResult

    blocked = PreflightResult(
        checks=[Check("folders-connected", ERROR, "root folder missing", "Wurzel fehlt")]
    )
    dialog = PreconditionDialog(blocked, "de")
    assert dialog.acknowledge.isEnabled() is False
    dialog.acknowledge.setChecked(True)  # cannot take effect
    assert dialog.ok_button.isEnabled() is False


def test_the_dialog_reports_what_was_actually_found(qt_app, mixed_gui_catalog):
    """The point of it: real numbers, not three recited rules."""
    result = _preconditions_for(mixed_gui_catalog.catalog_path)
    names = {check.name for check in result.checks}
    assert names == {
        "lightroom-closed",
        "catalog-version",
        "folders-connected",
        "backup-present",
    }
    connected = next(c for c in result.checks if c.name == "folders-connected")
    assert connected.level == "ok"
    assert "4" in connected.message("en")  # the fixture's four photos


def test_apply_stops_when_the_preconditions_are_declined(qt_app, mixed_gui_catalog, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.do_plan()
    assert pump(lambda: window.plan is not None)

    before = sorted(p.name for p in mixed_gui_catalog.images_dir.rglob("*") if p.is_file())
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Yes)
    monkeypatch.setattr(window, "_preconditions_accepted", lambda: False)
    window.do_apply()
    window.wait_for_workers()

    after = sorted(p.name for p in mixed_gui_catalog.images_dir.rglob("*") if p.is_file())
    assert after == before, "declining the preconditions must not start the run"
    window.close()


def test_the_preconditions_are_asked_once_per_catalog(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window._acknowledged = str(mixed_gui_catalog.catalog_path)
    assert window._preconditions_accepted() is True  # no dialog, already given
    window.close()


# -- saying what the tool is -------------------------------------------------


def test_the_window_states_its_purpose_without_opening_anything(qt_app):
    window = MainWindow()
    text = window.purpose_label.text()
    assert "Lightroom" in text and "catalog" in text.lower()
    window.close()


def test_the_purpose_line_follows_the_language(qt_app):
    window = MainWindow(language="de")
    assert "Bibliothek" in window.purpose_label.text()
    window.toggle_language()
    assert "library" in window.purpose_label.text()
    window.close()


def test_about_says_the_revision_and_the_promise(qt_app):
    window = MainWindow()
    text = window.about_html()
    assert REVISION in text
    assert "MIT" in text
    assert "gitlab.com" in text
    assert "folder column" in text  # the promise that matters
    assert window.about_action.isEnabled()
    window.close()


def test_the_window_carries_the_mark(qt_app):
    window = MainWindow()
    icon = window.windowIcon()
    assert not icon.isNull()
    # Both cuts are in it, so a 16 px request gets the one drawn for 16 px.
    assert {size.width() for size in icon.availableSizes()} >= {16, 32, 256}
    window.close()


# -- the mark, where it can actually be seen ---------------------------------


def test_the_mark_is_inside_the_window_not_only_in_the_icon(qt_app):
    """macOS shows no icon in a title bar, so the window icon alone is invisible."""
    window = MainWindow()
    pixmap = window.logo_label.pixmap()
    assert pixmap is not None and not pixmap.isNull()
    assert pixmap.width() >= 44
    window.close()


def test_the_masthead_names_the_tool_and_says_what_it_does(qt_app):
    window = MainWindow(language="de")
    assert window.wordmark_label.text() == "LR-FolderCraft"
    assert "Bibliothek" in window.purpose_label.text()
    window.toggle_language()
    assert "library" in window.purpose_label.text()
    window.close()


def test_the_mark_takes_the_text_colour(qt_app):
    """Single-colour by design: it must follow the theme, not fight it."""
    window = MainWindow()
    first = window.logo_label.pixmap().toImage()
    window._tint_logo()
    assert window.logo_label.pixmap().toImage() == first
    window.close()


def test_the_application_carries_the_icon_for_the_dock(qt_app):
    """setWindowIcon on the window is not what the Dock or task bar reads."""
    from lrfoldercraft.gui.app import window_icon

    icon = window_icon()
    assert not icon.isNull()
    assert {size.width() for size in icon.availableSizes()} >= {16, 256}


# -- date levels that name the whole date ------------------------------------


def test_the_preview_shows_the_cumulative_form(qt_app):
    """The preview has to show what will be built, not what was typed."""
    window = MainWindow()
    window.preset_combo.setCurrentText("year/month/day")
    plain = window.preview_label.text()
    window.cumulative_check.setChecked(True)
    cumulative = window.preview_label.text()
    assert plain != cumulative
    assert "2019-01-03" in cumulative
    window.close()


def test_the_option_reaches_the_settings_and_is_remembered(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.cumulative_check.setChecked(True)
    assert window.collect_settings().cumulative_dates is True
    window.close()

    again = MainWindow()
    assert again.cumulative_check.isChecked()
    again.close()
