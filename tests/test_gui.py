"""Smoke tests for the Qt front end.

Skipped when PySide6 is absent, because the GUI is an optional extra. Qt runs
on the offscreen platform so these work in CI without a display.
"""

from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

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
    assert window.folder_table.cellWidget(anchor_row, 3) is None  # never decided
    urlaub_row = paths.index("raw2019/Urlaub/")
    assert window.folder_table.cellWidget(urlaub_row, 3).currentData() == "consolidate"


def test_changing_a_decision_replans(qt_app, mixed_gui_catalog):
    window = MainWindow(catalog=str(mixed_gui_catalog.catalog_path))
    assert pump(lambda: "files" in window.catalog_info.text())
    window.preset_combo.setCurrentText("day")
    window.do_plan()
    assert pump(lambda: window.plan is not None)

    paths = [c.path_from_root for c in window.cases]
    combo = window.folder_table.cellWidget(paths.index("raw2019/Urlaub/"), 3)
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
