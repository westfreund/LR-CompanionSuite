"""The LR-MetaSearch window.

Built on what the folder tool's window had to learn the hard way: one tab per
step rather than one long scrolling column, the log outside the tabs because an
error behind a tab is an error nobody sees, and the buttons in the order the
work is done.

Nothing here writes to a catalog. The one command that writes anything at all
is the export, and it writes into copies it made itself.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...logging_setup import get_logger, setup_logging
from ...resources import logo_for
from ...version import METASEARCH_NAME, REVISION, SUITE_NAME, __build_date__
from .. import default_index_path
from ..query import Filter
from ..store import Index, IndexError_
from .i18n import tr
from .workers import DuplicateWorker, ExportWorker, ScanWorker, SearchWorker

log = get_logger("metasearch.gui")

#: How many hits the table shows. The count above it is the real total; drawing
#: fifty thousand rows helps nobody and takes seconds.
RESULT_LIMIT = 500


def _split(text: str) -> tuple:
    return tuple(part.strip() for part in text.split(",") if part.strip())


class MetaSearchWindow(QMainWindow):
    """Searching across libraries, in four steps."""

    RESULT_COLUMNS = 8

    def __init__(self, language: str = "en", index_path: str = ""):
        super().__init__()
        self.language = language
        self.index_path = index_path
        self.threads: list = []
        self.hits: list = []
        self.total = 0
        self._build()
        self._retranslate()
        self.resize(1080, 780)
        self.setWindowIcon(self._icon())
        self._refresh_libraries()

    # -- construction ---------------------------------------------------

    def _icon(self) -> QIcon:
        icon = QIcon()
        for size in (16, 24, 32, 64, 128, 256):
            icon.addPixmap(self._tinted(size))
        return icon

    def _tinted(self, size: int) -> QPixmap:
        """The mark in the current text colour, so it reads in either theme."""
        from PySide6.QtCore import QByteArray, QRectF
        from PySide6.QtSvg import QSvgRenderer

        colour = self.palette().windowText().color()
        text = logo_for(size, "metasearch").read_text(encoding="utf-8")
        text = text.replace("currentColor", colour.name(QColor.HexRgb))
        renderer = QSvgRenderer(QByteArray(text.encode("utf-8")))
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        return QPixmap.fromImage(image)

    def _masthead(self) -> QWidget:
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 6)
        self.mark = QLabel()
        self.mark.setPixmap(self._tinted(44))
        row.addWidget(self.mark)
        column = QVBoxLayout()
        title = QLabel("<b>{n}</b>".format(n=METASEARCH_NAME))
        title.setTextFormat(Qt.RichText)
        self.purpose_label = QLabel()
        self.purpose_label.setWordWrap(True)
        column.addWidget(title)
        column.addWidget(self.purpose_label)
        row.addLayout(column, 1)
        return holder

    def _build(self) -> None:
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.addWidget(self._masthead())

        self.tabs = QTabWidget()
        self.tab_pages = [
            ("tab_search", "tab_search_hint", self._search_page()),
            ("tab_libraries", "tab_libraries_hint", self._libraries_page()),
            ("tab_duplicates", "tab_duplicates_hint", self._duplicates_page()),
            ("tab_export", "tab_export_hint", self._export_page()),
        ]
        for _key, _hint, page in self.tab_pages:
            self.tabs.addTab(page, "")

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Menlo", 11))
        self.log_view.setMinimumHeight(60)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.tabs)
        self.splitter.addWidget(self.log_view)
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([600, 120])
        outer.addWidget(self.splitter, 1)
        outer.addWidget(self._actions())

        self.setCentralWidget(central)
        self.statusBar().showMessage(
            "{s} · {n} {r} - build {d}".format(
                s=SUITE_NAME, n=METASEARCH_NAME, r=REVISION, d=__build_date__
            )
        )
        self._build_menu()

    def _build_menu(self) -> None:
        self.actions_menu = self.menuBar().addMenu("")
        self.language_action = QAction(self)
        self.language_action.triggered.connect(self.toggle_language)
        self.about_action = QAction(self)
        self.about_action.triggered.connect(self.show_about)
        self.actions_menu.addAction(self.language_action)
        self.actions_menu.addAction(self.about_action)

    # -- the four tabs --------------------------------------------------

    def _search_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)

        self.criteria_group = QGroupBox()
        form = QFormLayout(self.criteria_group)
        self.keywords_edit = QLineEdit()
        self.any_keywords_edit = QLineEdit()
        self.text_edit = QLineEdit()
        self.camera_edit = QLineEdit()
        self.lens_edit = QLineEdit()
        self.catalog_edit = QLineEdit()
        self.extension_edit = QLineEdit()
        self.since_edit = QLineEdit()
        self.until_edit = QLineEdit()
        self.rating_combo = QComboBox()
        self.gps_check = QCheckBox()
        self.copies_check = QCheckBox()

        self.keyword_labels = {}
        for key, widget in (
            ("keywords", self.keywords_edit),
            ("any_keywords", self.any_keywords_edit),
            ("text", self.text_edit),
            ("camera", self.camera_edit),
            ("lens", self.lens_edit),
            ("catalog", self.catalog_edit),
            ("extension", self.extension_edit),
            ("since", self.since_edit),
            ("until", self.until_edit),
            ("min_rating", self.rating_combo),
        ):
            label = QLabel()
            self.keyword_labels[key] = label
            form.addRow(label, widget)
            if isinstance(widget, QLineEdit):
                widget.returnPressed.connect(self.do_search)
        form.addRow("", self.gps_check)
        form.addRow("", self.copies_check)

        area = QScrollArea()
        area.setWidget(self.criteria_group)
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setMaximumHeight(320)
        column.addWidget(area)

        self.hits_label = QLabel()
        self.hits_label.setWordWrap(True)
        column.addWidget(self.hits_label)

        self.result_table = QTableWidget(0, self.RESULT_COLUMNS)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.result_table.horizontalHeader()
        for index in range(self.RESULT_COLUMNS):
            header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        column.addWidget(self.result_table, 1)
        return page

    def _libraries_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)

        row = QHBoxLayout()
        self.scan_button = QPushButton()
        self.scan_button.clicked.connect(self.do_scan)
        self.copies_toggle = QCheckBox()
        self.copies_toggle.stateChanged.connect(self._refresh_libraries)
        row.addWidget(self.scan_button)
        row.addWidget(self.copies_toggle)
        row.addStretch(1)
        self.index_label = QLabel()
        self.index_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row.addWidget(self.index_label)
        column.addLayout(row)

        self.drives_group = QGroupBox()
        drives = QVBoxLayout(self.drives_group)
        self.drive_table = QTableWidget(0, 4)
        self.drive_table.verticalHeader().setVisible(False)
        self.drive_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.drive_table.setMaximumHeight(160)
        drives.addWidget(self.drive_table)
        column.addWidget(self.drives_group)

        self.libraries_group = QGroupBox()
        libraries = QVBoxLayout(self.libraries_group)
        self.library_table = QTableWidget(0, 5)
        self.library_table.verticalHeader().setVisible(False)
        self.library_table.setEditTriggers(QTableWidget.NoEditTriggers)
        libraries.addWidget(self.library_table)
        column.addWidget(self.libraries_group, 1)
        return page

    def _duplicates_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.duplicates_button = QPushButton()
        self.duplicates_button.clicked.connect(self.do_duplicates)
        self.across_check = QCheckBox()
        self.near_check = QCheckBox()
        row.addWidget(self.duplicates_button)
        row.addWidget(self.across_check)
        row.addWidget(self.near_check)
        row.addStretch(1)
        column.addLayout(row)

        self.duplicate_summary = QLabel()
        self.duplicate_summary.setWordWrap(True)
        column.addWidget(self.duplicate_summary)

        self.duplicate_view = QPlainTextEdit()
        self.duplicate_view.setReadOnly(True)
        self.duplicate_view.setFont(QFont("Menlo", 11))
        column.addWidget(self.duplicate_view, 1)

        self.similarity_note = QLabel()
        self.similarity_note.setWordWrap(True)
        column.addWidget(self.similarity_note)
        return page

    def _export_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        self.export_intro = QLabel()
        self.export_intro.setWordWrap(True)
        column.addWidget(self.export_intro)

        row = QHBoxLayout()
        self.export_label = QLabel()
        self.export_edit = QLineEdit()
        self.export_browse = QPushButton()
        self.export_browse.clicked.connect(self.pick_export_folder)
        row.addWidget(self.export_label)
        row.addWidget(self.export_edit, 1)
        row.addWidget(self.export_browse)
        column.addLayout(row)

        self.with_data_check = QCheckBox()
        self.with_data_check.setChecked(True)
        column.addWidget(self.with_data_check)
        self.with_data_hint = QLabel()
        self.with_data_hint.setWordWrap(True)
        self.with_data_hint.setEnabled(False)
        column.addWidget(self.with_data_hint)

        self.export_button = QPushButton()
        self.export_button.clicked.connect(self.do_export)
        column.addWidget(self.export_button, 0, Qt.AlignLeft)

        self.export_view = QPlainTextEdit()
        self.export_view.setReadOnly(True)
        self.export_view.setFont(QFont("Menlo", 11))
        column.addWidget(self.export_view, 1)
        return page

    def _actions(self) -> QWidget:
        holder = QWidget()
        row = QHBoxLayout(holder)
        self.search_button = QPushButton()
        self.search_button.clicked.connect(self.do_search)
        self.clear_button = QPushButton()
        self.clear_button.clicked.connect(self.clear_criteria)
        divider = QFrame()
        divider.setFrameShape(QFrame.NoFrame)
        divider.setFixedWidth(1)
        divider.setMinimumHeight(22)
        divider.setStyleSheet("background: palette(mid);")
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status_label = QLabel()
        row.addWidget(self.search_button)
        row.addWidget(self.clear_button)
        row.addSpacing(10)
        row.addWidget(divider)
        row.addSpacing(10)
        row.addWidget(self.progress, 1)
        row.addWidget(self.status_label)
        return holder

    # -- language -------------------------------------------------------

    def _retranslate(self) -> None:
        language = self.language
        self.setWindowTitle("{s} · {t}".format(s=SUITE_NAME, t=tr("window_title", language)))
        self.purpose_label.setText(tr("purpose", language))
        for index, (key, hint, _page) in enumerate(self.tab_pages):
            self.tabs.setTabText(index, tr(key, language).replace("&", "&&"))
            self.tabs.setTabToolTip(index, tr(hint, language))
        self.criteria_group.setTitle(tr("criteria", language))
        for key, label in self.keyword_labels.items():
            label.setText(tr(key, language))
        self.keywords_edit.setPlaceholderText(tr("keywords_hint", language))
        self.any_keywords_edit.setPlaceholderText(tr("keywords_hint", language))
        self.since_edit.setPlaceholderText("JJJJ-MM-TT" if language == "de" else "YYYY-MM-DD")
        self.until_edit.setPlaceholderText("JJJJ-MM-TT" if language == "de" else "YYYY-MM-DD")
        self.gps_check.setText(tr("with_gps", language))
        self.copies_check.setText(tr("include_copies", language))

        current = self.rating_combo.currentIndex()
        self.rating_combo.blockSignals(True)
        self.rating_combo.clear()
        self.rating_combo.addItem(tr("no_stars", language))
        for stars in range(1, 6):
            self.rating_combo.addItem(tr("stars", language).format(n=stars))
        self.rating_combo.setCurrentIndex(max(current, 0))
        self.rating_combo.blockSignals(False)

        self.scan_button.setText(tr("scan", language))
        self.copies_toggle.setText(tr("show_copies", language))
        self.drives_group.setTitle(tr("drives", language))
        self.libraries_group.setTitle(tr("libraries", language))
        self.drive_table.setHorizontalHeaderLabels(
            [
                tr("col_drive", language),
                tr("col_certain", language),
                tr("col_drive_id", language),
                tr("col_state", language),
            ]
        )
        self.library_table.setHorizontalHeaderLabels(
            [
                tr("col_catalog", language),
                tr("col_photos", language),
                tr("col_drive", language),
                tr("col_read", language),
                tr("col_state", language),
            ]
        )
        self.result_table.setHorizontalHeaderLabels(
            [
                "",
                tr("col_file", language),
                tr("col_catalog", language),
                tr("col_captured", language),
                tr("col_camera", language),
                tr("col_rating", language),
                tr("col_keywords", language),
                tr("col_drive", language),
            ]
        )
        self.duplicates_button.setText(tr("find_duplicates", language))
        self.across_check.setText(tr("across_only", language))
        self.near_check.setText(tr("near_instead", language))
        self.similarity_note.setText(tr("no_similarity", language))
        self.export_intro.setText(tr("export_intro", language))
        self.export_label.setText(tr("export_target", language))
        self.export_browse.setText(tr("browse", language))
        self.export_button.setText(tr("export", language))
        self.with_data_check.setText(tr("with_data", language))
        self.with_data_hint.setText(tr("with_data_hint", language))
        self.search_button.setText(tr("search", language))
        self.clear_button.setText(tr("clear", language))
        self.status_label.setText(tr("ready", language))
        self.actions_menu.setTitle(tr("menu_actions", language))
        self.language_action.setText(tr("language", language))
        self.about_action.setText(tr("about", language))
        self.index_label.setText(
            "{l}: {p}".format(
                l=tr("index_file", language), p=self.index_path or default_index_path()
            )
        )

    def toggle_language(self) -> None:
        self.language = "de" if self.language == "en" else "en"
        self._retranslate()
        self._refresh_libraries()

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            METASEARCH_NAME,
            "{s}\n{n} {r}\nbuild {d}\n\n{p}".format(
                s=SUITE_NAME,
                n=METASEARCH_NAME,
                r=REVISION,
                d=__build_date__,
                p=tr("purpose", self.language),
            ),
        )

    # -- doing things ---------------------------------------------------

    def say(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _busy(self, busy: bool, message: str = "") -> None:
        for button in (
            self.search_button,
            self.scan_button,
            self.duplicates_button,
            self.export_button,
        ):
            button.setEnabled(not busy)
        self.progress.setRange(0, 0 if busy else 100)
        if not busy:
            self.progress.setValue(0)
        self.status_label.setText(message or tr("ready" if not busy else "working", self.language))

    def current_filter(self) -> Filter:
        return Filter(
            keywords=_split(self.keywords_edit.text()),
            any_keywords=_split(self.any_keywords_edit.text()),
            text=self.text_edit.text().strip(),
            camera=self.camera_edit.text().strip(),
            lens=self.lens_edit.text().strip(),
            catalog=self.catalog_edit.text().strip(),
            extension=self.extension_edit.text().strip(),
            since=self.since_edit.text().strip(),
            until=self.until_edit.text().strip(),
            min_rating=self.rating_combo.currentIndex(),
            with_gps=self.gps_check.isChecked(),
            include_copies=self.copies_check.isChecked(),
        )

    def clear_criteria(self) -> None:
        for widget in (
            self.keywords_edit,
            self.any_keywords_edit,
            self.text_edit,
            self.camera_edit,
            self.lens_edit,
            self.catalog_edit,
            self.extension_edit,
            self.since_edit,
            self.until_edit,
        ):
            widget.clear()
        self.rating_combo.setCurrentIndex(0)
        self.gps_check.setChecked(False)
        self.copies_check.setChecked(False)
        self.result_table.setRowCount(0)
        self.hits_label.clear()
        self.hits = []
        self.total = 0

    def do_search(self) -> None:
        criteria = self.current_filter()
        if criteria.is_empty:
            QMessageBox.information(self, METASEARCH_NAME, tr("give_a_criterion", self.language))
            return
        self._busy(True, tr("working", self.language))
        worker = SearchWorker(criteria, self.index_path, RESULT_LIMIT)
        worker.finished.connect(self._search_done)
        worker.failed.connect(self._failed)
        self._start(worker)

    def _search_done(self, hits, total: int) -> None:
        self.hits = list(hits)
        self.total = int(total)
        self._busy(False)
        self._fill_results()

    def _fill_results(self) -> None:
        language = self.language
        table = self.result_table
        table.setRowCount(len(self.hits))
        for row, hit in enumerate(self.hits):
            table.setItem(row, 0, QTableWidgetItem("" if hit.reachable else "!"))
            table.setItem(row, 1, QTableWidgetItem(hit.file_name))
            table.setItem(row, 2, QTableWidgetItem(hit.catalog))
            table.setItem(row, 3, QTableWidgetItem(hit.capture_time[:16].replace("T", " ")))
            table.setItem(row, 4, QTableWidgetItem(hit.camera))
            table.setItem(row, 5, QTableWidgetItem("★" * int(hit.rating or 0)))
            table.setItem(row, 6, QTableWidgetItem(hit.keywords))
            table.setItem(row, 7, QTableWidgetItem(hit.volume))
            item = table.item(row, 0)
            if item is not None and not hit.reachable:
                item.setToolTip(tr("not_attached", language))
        if not self.hits:
            self.hits_label.setText(tr("no_hits", language))
            return
        text = tr("hits", language).format(n=self._n(self.total), s=len(self.hits))
        if any(not hit.reachable for hit in self.hits):
            text += "   " + tr("not_attached", language)
        self.hits_label.setText(text)

    def _n(self, number: int) -> str:
        grouped = "{n:,}".format(n=int(number))
        return grouped.replace(",", ".") if self.language == "de" else grouped

    def do_scan(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, tr("scan_where", self.language), str(Path.home())
        )
        if not directory:
            return
        self._busy(True, tr("working", self.language))
        worker = ScanWorker([directory], self.index_path)
        worker.progress.connect(self._scan_progress)
        worker.finished.connect(self._scan_done)
        worker.failed.connect(self._failed)
        self._start(worker)

    def _scan_progress(self, number: int, total: int, name: str) -> None:
        self.status_label.setText(tr("scan_running", self.language).format(n=name))
        self.progress.setRange(0, total)
        self.progress.setValue(number)

    def _scan_done(self, outcomes, counts) -> None:
        self._busy(False)
        states: dict = {}
        for outcome in outcomes:
            states[outcome.state] = states.get(outcome.state, 0) + 1
            if outcome.state in ("failed", "locked"):
                self.say(
                    "{s}: {n} — {d}".format(s=outcome.state, n=outcome.path.name, d=outcome.detail)
                )
        self.say(
            tr("scan_done", self.language).format(
                r=states.get("read", 0),
                c=states.get("copy", 0),
                p=self._n(counts["photos"]),
            )
        )
        self._refresh_libraries()

    def _refresh_libraries(self) -> None:
        try:
            with Index.open(self.index_path or None, create=False) as index:
                volumes = index.db.execute(
                    "select label, kind, identity, mount from volumes order by label"
                ).fetchall()
                catalogs = index.catalogs(include_superseded=self.copies_toggle.isChecked())
        except (IndexError_, Exception) as exc:  # noqa: BLE001 - shown in the window
            log.info("No index to show yet: %s", exc)
            self.drive_table.setRowCount(0)
            self.library_table.setRowCount(0)
            self.say(tr("index_empty", self.language))
            return

        language = self.language
        self.drive_table.setRowCount(len(volumes))
        for row, volume in enumerate(volumes):
            mount = volume[3] or ""
            attached = bool(mount) and os.path.ismount(mount)
            for column, value in enumerate(
                [
                    volume[0] or "",
                    tr("certain" if volume[1] == "uuid" else "guessed", language),
                    volume[2] or "",
                    tr("attached" if attached else "detached", language),
                ]
            ):
                self.drive_table.setItem(row, column, QTableWidgetItem(value))
        self.drive_table.resizeColumnsToContents()

        self.library_table.setRowCount(len(catalogs))
        for row, catalog in enumerate(catalogs):
            for column, value in enumerate(
                [
                    catalog.name,
                    self._n(catalog.images),
                    catalog.volume_label,
                    catalog.last_read[:16].replace("T", "  "),
                    tr(
                        "state_copy" if catalog.superseded_by is not None else "state_current",
                        language,
                    ),
                ]
            ):
                self.library_table.setItem(row, column, QTableWidgetItem(str(value)))
        self.library_table.resizeColumnsToContents()

    def do_duplicates(self) -> None:
        self._busy(True, tr("working", self.language))
        worker = DuplicateWorker(
            self.index_path, self.across_check.isChecked(), self.near_check.isChecked(), 60
        )
        worker.finished.connect(self._duplicates_done)
        worker.failed.connect(self._failed)
        self._start(worker)

    def _duplicates_done(self, groups, totals) -> None:
        self._busy(False)
        self.duplicate_summary.setText(
            tr("dup_summary", self.language).format(
                g=self._n(totals["groups"]),
                s=self._n(totals["surplus"]),
                a=self._n(totals["across_catalogs"]),
            )
            + "   "
            + tr("dup_note", self.language)
        )
        lines = []
        for group in groups:
            lines.append("{f}  ({n}x)".format(f=group.members[0].file_name, n=len(group.members)))
            for member in group.members:
                lines.append("      {c:<24} {f}".format(c=member.catalog[:24], f=member.folder))
        self.duplicate_view.setPlainText("\n".join(lines))

    def pick_export_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, tr("export_target", self.language), str(Path.home())
        )
        if directory:
            self.export_edit.setText(directory)

    def do_export(self) -> None:
        if not self.hits:
            QMessageBox.information(self, METASEARCH_NAME, tr("export_nothing", self.language))
            return
        target = self.export_edit.text().strip()
        if not target:
            self.pick_export_folder()
            target = self.export_edit.text().strip()
            if not target:
                return
        path = Path(target).expanduser()
        if path.exists() and any(path.iterdir()):
            QMessageBox.warning(
                self,
                METASEARCH_NAME,
                tr("export_not_empty", self.language).format(p=path),
            )
            return
        libraries = {hit.catalog for hit in self.hits}
        answer = QMessageBox.question(
            self,
            METASEARCH_NAME,
            tr("export_confirm", self.language).format(
                n=self._n(self.total), c=len(libraries), p=path
            ),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if answer != QMessageBox.Yes:
            return
        # The table shows at most RESULT_LIMIT rows; the export takes the whole
        # result, which is what the confirmation counted.
        self._busy(True, tr("working", self.language))
        worker = ExportWorker(
            self._all_matching_ids(),
            str(path),
            self.index_path,
            with_data=self.with_data_check.isChecked(),
        )
        worker.progress.connect(self.export_view.appendPlainText)
        worker.finished.connect(self._export_done)
        worker.failed.connect(self._failed)
        self._start(worker)

    def _all_matching_ids(self) -> List[int]:
        from ..query import search

        with Index.open(self.index_path or None, create=False) as index:
            return [hit.photo_id for hit in search(index, self.current_filter())]

    def _export_done(self, results) -> None:
        self._busy(False)
        for result in results:
            if not str(result.target):
                continue
            for was, now in result.relinked:
                self.export_view.appendPlainText("{w}  ->  {n}".format(w=was, n=now))
            self.export_view.appendPlainText(
                "{n}: {k} / {t}".format(
                    n=result.target.name, k=result.kept, t=result.kept + result.removed
                )
            )
        self.export_view.appendPlainText(tr("export_done", self.language))
        self.say(tr("export_done", self.language))

    def _failed(self, message: str) -> None:
        self._busy(False)
        self.say(message)
        QMessageBox.warning(self, METASEARCH_NAME, message)

    def _start(self, worker) -> None:
        from ...gui.workers import run_in_thread

        run_in_thread(worker, self.threads)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        from ...gui.workers import wait_for_threads

        wait_for_threads(self.threads)
        super().closeEvent(event)


def run(argv: Optional[list] = None) -> int:
    """Open the window on its own."""
    setup_logging(tag="lrms-gui")
    application = QApplication.instance() or QApplication(list(argv or sys.argv))
    language = "de" if "--lang=de" in (argv or sys.argv) else "en"
    window = MetaSearchWindow(language=language)
    window.show()
    if QGuiApplication.instance() is application:
        return application.exec()
    return 0  # pragma: no cover - already inside another event loop
