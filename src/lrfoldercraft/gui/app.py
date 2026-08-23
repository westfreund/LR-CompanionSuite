"""The Qt main window.

Layout, top to bottom: catalog, source, target, structure, options, the folders
that were found with their decisions, then the action buttons, a progress bar
and a log. Every long operation runs on a worker thread (:mod:`.workers`), so
the window stays usable while nine thousand files are moved.

Nothing here reaches past the three core calls the TUI already uses --
``build_plan``, ``preflight``, ``execute`` -- so the graphical front end adds no
knowledge of its own about catalogs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
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
    QRadioButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..catalog.model import CatalogInfo, RootFolder
from ..config import CONFLICT_MODES, MISSING_DATE_MODES, Settings
from ..folders import (
    ALL_ACTIONS,
    CONSOLIDATE,
    DATED_FOLDER_ACTIONS,
    MISMATCH_ACTIONS,
    SUBFOLDER_ACTIONS,
    FolderCase,
)
from ..folders import label as action_label
from ..logging_setup import get_logger, setup_logging
from ..planner import Plan
from ..report import human_bytes, render_result
from ..rules import PRESETS, RuleError, describe_structure, parse_structure, token_help
from ..version import APP_NAME, REVISION, __build_date__
from .i18n import tr
from .workers import (
    ApplyWorker,
    CatalogWorker,
    PlanWorker,
    run_in_thread,
    wait_for_threads,
)

log = get_logger("gui")


class MainWindow(QMainWindow):
    """Everything a run needs, in one window."""

    def __init__(self, catalog: str = "", language: str = "en"):
        super().__init__()
        self.language = language if language in ("en", "de") else "en"
        self.plan: Optional[Plan] = None
        self.folder_decisions: Dict[int, str] = {}
        #: The ordered rule list, as (pattern, action) pairs. Order is meaning.
        self.rules: List[Tuple[str, str]] = []
        self.cases: List[FolderCase] = []
        self.roots: List[RootFolder] = []
        self._threads: list = []

        self.setWindowTitle("{n} - {r}".format(n=APP_NAME, r=REVISION))
        self._build()
        self._size_to_screen()
        self._retranslate()
        if catalog:
            self.catalog_edit.setText(catalog)
            self.load_catalog()

    # -- construction ---------------------------------------------------

    def _build(self) -> None:
        central = QWidget()
        outer = QVBoxLayout(central)

        # The settings are the tall part, so they live in a scroll area: on a
        # small screen the window must still fit, and the buttons and progress
        # bar must never be what scrolls out of sight.
        settings = QWidget()
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.addWidget(self._catalog_box())
        settings_layout.addWidget(self._source_box())
        settings_layout.addWidget(self._target_box())
        settings_layout.addWidget(self._structure_box())
        settings_layout.addWidget(self._options_box())
        settings_layout.addStretch(0)

        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidget(settings)
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setFrameShape(QScrollArea.NoFrame)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.settings_scroll.setMinimumHeight(140)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Menlo", 11))
        self.log_view.setMinimumHeight(60)

        # One splitter for everything above the action row, so the operator can
        # give the space to whichever part they are working with.
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.settings_scroll)
        self.splitter.addWidget(self._folders_box())
        self.splitter.addWidget(self.log_view)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setStretchFactor(2, 1)
        outer.addWidget(self.splitter, 1)

        outer.addWidget(self._actions_box())
        self.setCentralWidget(central)
        self.statusBar().showMessage(
            "{n} {r} - build {d}".format(n=APP_NAME, r=REVISION, d=__build_date__)
        )
        self._build_menu()

    def _size_to_screen(self) -> None:
        """Open at a comfortable size, but never larger than the screen.

        A fixed 1024x860 is taller than the usable area of a 13-inch laptop once
        the menu bar and the dock are taken off, which put the buttons below the
        bottom edge with no way to reach them.
        """
        self.setMinimumSize(720, 420)
        screen = QGuiApplication.primaryScreen()
        if screen is None:  # pragma: no cover - always present in practice
            self.resize(1024, 800)
            return
        available = screen.availableGeometry()
        width = min(1024, max(720, available.width() - 80))
        height = min(940, max(420, available.height() - 80))
        self.resize(width, height)
        self._balance_splitter(height)

    def _balance_splitter(self, height: int) -> None:
        """Give the settings most of the room, but keep the other two usable."""
        settings = max(200, int(height * 0.55))
        folders = max(140, int(height * 0.30))
        log = max(60, height - settings - folders)
        self.splitter.setSizes([settings, folders, log])

    def _build_menu(self) -> None:
        language_action = QAction(tr("language", self.language), self)
        language_action.triggered.connect(self.toggle_language)
        self.language_action = language_action
        self.menuBar().addAction(language_action)

    def _catalog_box(self) -> QGroupBox:
        box = QGroupBox()
        layout = QVBoxLayout(box)
        row = QHBoxLayout()
        self.catalog_edit = QLineEdit()
        self.catalog_browse = QPushButton()
        self.catalog_browse.clicked.connect(self.pick_catalog)
        self.catalog_load = QPushButton()
        self.catalog_load.clicked.connect(self.load_catalog)
        row.addWidget(self.catalog_edit, 1)
        row.addWidget(self.catalog_browse)
        row.addWidget(self.catalog_load)
        layout.addLayout(row)
        self.catalog_info = QLabel()
        self.catalog_info.setWordWrap(True)
        layout.addWidget(self.catalog_info)
        self.catalog_group = box
        return box

    def _source_box(self) -> QGroupBox:
        box = QGroupBox()
        form = QFormLayout(box)
        self.root_combo = QComboBox()
        self.include_edit = QLineEdit()
        self.exclude_edit = QLineEdit()
        self.root_label = QLabel()
        self.include_label = QLabel()
        self.exclude_label = QLabel()
        form.addRow(self.root_label, self.root_combo)
        form.addRow(self.include_label, self.include_edit)
        form.addRow(self.exclude_label, self.exclude_edit)
        self.source_group = box
        return box

    def _target_box(self) -> QGroupBox:
        box = QGroupBox()
        layout = QVBoxLayout(box)
        self.target_in_place = QRadioButton()
        self.target_in_place.setChecked(True)
        self.target_new_tree = QRadioButton()
        layout.addWidget(self.target_in_place)
        row = QHBoxLayout()
        row.addWidget(self.target_new_tree)
        self.target_edit = QLineEdit()
        self.target_edit.setEnabled(False)
        self.target_browse = QPushButton()
        self.target_browse.setEnabled(False)
        self.target_browse.clicked.connect(self.pick_target)
        row.addWidget(self.target_edit, 1)
        row.addWidget(self.target_browse)
        layout.addLayout(row)
        self.target_hint = QLabel()
        self.target_hint.setWordWrap(True)
        self.target_hint.setEnabled(False)
        layout.addWidget(self.target_hint)
        self.target_new_tree.toggled.connect(self._target_mode_changed)
        self.target_group = box
        return box

    def _structure_box(self) -> QGroupBox:
        box = QGroupBox()
        form = QFormLayout(box)
        self.preset_combo = QComboBox()
        for name in PRESETS:
            self.preset_combo.addItem(name)
        self.preset_combo.currentTextChanged.connect(self.update_preview)
        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText("{camera_slug}/{yyyy}-{mm}-{dd}")
        self.custom_edit.textChanged.connect(self.update_preview)
        self.preview_label = QLabel()
        preview_font = QFont("Menlo", 12)
        preview_font.setBold(True)
        self.preview_label.setFont(preview_font)
        self.tokens_button = QPushButton()
        self.tokens_button.clicked.connect(self.show_tokens)
        self.preset_label = QLabel()
        self.custom_label = QLabel()
        self.preview_title = QLabel()
        form.addRow(self.preset_label, self.preset_combo)
        custom_row = QHBoxLayout()
        custom_row.addWidget(self.custom_edit, 1)
        custom_row.addWidget(self.tokens_button)
        form.addRow(self.custom_label, custom_row)
        form.addRow(self.preview_title, self.preview_label)
        self.structure_group = box
        return box

    def _options_box(self) -> QGroupBox:
        box = QGroupBox()
        grid = QHBoxLayout(box)

        defaults = Settings()

        left = QFormLayout()
        self.conflict_combo = self._combo(CONFLICT_MODES, defaults.conflict)
        self.missing_combo = self._combo(MISSING_DATE_MODES, defaults.on_missing_date)
        self.conflict_label = QLabel()
        self.missing_label = QLabel()
        left.addRow(self.conflict_label, self.conflict_combo)
        left.addRow(self.missing_label, self.missing_combo)

        middle = QFormLayout()
        self.subfolder_combo = self._combo(SUBFOLDER_ACTIONS, defaults.subfolder_action)
        self.dated_combo = self._combo(DATED_FOLDER_ACTIONS, defaults.dated_folder_action)
        self.mismatch_combo = self._combo(MISMATCH_ACTIONS, defaults.mismatch_action)
        self.subfolder_label = QLabel()
        self.dated_label = QLabel()
        self.mismatch_label = QLabel()
        middle.addRow(self.subfolder_label, self.subfolder_combo)
        middle.addRow(self.dated_label, self.dated_combo)
        middle.addRow(self.mismatch_label, self.mismatch_combo)

        right = QVBoxLayout()
        self.sidecars_check = QCheckBox()
        self.sidecars_check.setChecked(defaults.move_sidecars)
        self.backup_check = QCheckBox()
        self.backup_check.setChecked(defaults.backup_catalog)
        self.ascii_check = QCheckBox()
        self.ascii_check.setChecked(defaults.ascii_only)
        right.addWidget(self.sidecars_check)
        right.addWidget(self.backup_check)
        right.addWidget(self.ascii_check)
        right.addStretch(1)

        grid.addLayout(left, 1)
        grid.addLayout(middle, 1)
        grid.addLayout(right, 1)
        self.options_group = box
        return box

    @staticmethod
    def _combo(values, default: str) -> QComboBox:
        """A combo whose initial choice is the documented default.

        Taking the first list entry instead would let the graphical front end
        drift away from the defaults the CLI and the documentation state --
        silently, and differently per option.
        """
        combo = QComboBox()
        for value in values:
            combo.addItem(value)
        if default in values:
            combo.setCurrentIndex(list(values).index(default))
        return combo

    def _folders_box(self) -> QGroupBox:
        box = QGroupBox()
        layout = QVBoxLayout(box)
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        layout.addWidget(self._rules_widget())
        self.folder_table = QTableWidget(0, 5)
        self.folder_table.verticalHeader().setVisible(False)
        self.folder_table.setSelectionBehavior(QTableWidget.SelectRows)
        header = self.folder_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3, 4):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.folder_table.setMinimumHeight(110)
        layout.addWidget(self.folder_table, 1)
        self.folders_group = box
        return box

    def _rules_widget(self) -> QWidget:
        """The ordered rule list: a handful of lines instead of one answer per folder."""
        holder = QWidget()
        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 0, 0)

        self.rules_hint = QLabel()
        self.rules_hint.setWordWrap(True)
        column.addWidget(self.rules_hint)

        self.rule_table = QTableWidget(0, 2)
        self.rule_table.verticalHeader().setVisible(False)
        self.rule_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rule_table.setSelectionMode(QTableWidget.SingleSelection)
        rule_header = self.rule_table.horizontalHeader()
        rule_header.setSectionResizeMode(0, QHeaderView.Stretch)
        rule_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.rule_table.setMaximumHeight(140)
        self.rule_table.itemChanged.connect(self._rule_edited)
        column.addWidget(self.rule_table)

        buttons = QHBoxLayout()
        self.rule_add_button = QPushButton()
        self.rule_add_button.clicked.connect(self._add_rule)
        self.rule_remove_button = QPushButton()
        self.rule_remove_button.clicked.connect(self._remove_rule)
        self.rule_up_button = QPushButton("\u2191")
        self.rule_up_button.clicked.connect(lambda: self._move_rule(-1))
        self.rule_down_button = QPushButton("\u2193")
        self.rule_down_button.clicked.connect(lambda: self._move_rule(1))
        for button in (
            self.rule_add_button,
            self.rule_remove_button,
            self.rule_up_button,
            self.rule_down_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch(1)
        column.addLayout(buttons)
        return holder

    # -- the rule list ------------------------------------------------------

    def _redraw_rules(self) -> None:
        """Rewrite the rule table from :attr:`rules` without re-firing edits."""
        table = self.rule_table
        table.blockSignals(True)
        table.setRowCount(len(self.rules))
        for row, (pattern, action) in enumerate(self.rules):
            table.setItem(row, 0, QTableWidgetItem(pattern))
            combo = QComboBox()
            for choice in ALL_ACTIONS:
                combo.addItem(action_label(choice, self.language), choice)
            if action in ALL_ACTIONS:
                combo.setCurrentIndex(list(ALL_ACTIONS).index(action))
            combo.currentIndexChanged.connect(
                lambda _index, r=row, c=combo: self._rule_action_changed(r, c)
            )
            table.setCellWidget(row, 1, combo)
        table.blockSignals(False)

    def _rule_edited(self, item: QTableWidgetItem) -> None:
        if item.column() != 0 or item.row() >= len(self.rules):
            return
        _pattern, action = self.rules[item.row()]
        self.rules[item.row()] = (item.text().strip(), action)
        self._rules_changed()

    def _rule_action_changed(self, row: int, combo: QComboBox) -> None:
        if row >= len(self.rules):
            return
        pattern, _action = self.rules[row]
        self.rules[row] = (pattern, combo.currentData())
        self._rules_changed()

    def _add_rule(self) -> None:
        self.rules.append(("*", CONSOLIDATE))
        self._redraw_rules()
        self._rules_changed()

    def _remove_rule(self) -> None:
        row = self.rule_table.currentRow()
        if 0 <= row < len(self.rules):
            del self.rules[row]
            self._redraw_rules()
            self._rules_changed()

    def _move_rule(self, delta: int) -> None:
        """Order is meaning here: the first matching rule decides."""
        row = self.rule_table.currentRow()
        target = row + delta
        if 0 <= row < len(self.rules) and 0 <= target < len(self.rules):
            self.rules[row], self.rules[target] = self.rules[target], self.rules[row]
            self._redraw_rules()
            self.rule_table.selectRow(target)
            self._rules_changed()

    def _rules_changed(self) -> None:
        """A changed rule invalidates every decision it might have made."""
        self.folder_decisions.clear()
        if self.catalog_edit.text().strip():
            self.do_plan()

    def _rule_strings(self) -> Tuple[str, ...]:
        return tuple(
            "{p}={a}".format(p=pattern, a=action)
            for pattern, action in self.rules
            if pattern.strip()
        )

    def _actions_box(self) -> QWidget:
        holder = QWidget()
        row = QHBoxLayout(holder)
        self.plan_button = QPushButton()
        self.plan_button.clicked.connect(self.do_plan)
        self.apply_button = QPushButton()
        self.apply_button.clicked.connect(self.do_apply)
        self.apply_button.setEnabled(False)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status_label = QLabel()
        row.addWidget(self.plan_button)
        row.addWidget(self.apply_button)
        row.addWidget(self.progress, 1)
        row.addWidget(self.status_label)
        return holder

    # -- language --------------------------------------------------------

    def _retranslate(self) -> None:
        language = self.language
        self.catalog_group.setTitle(tr("catalog", language))
        self.catalog_browse.setText(tr("browse", language))
        self.catalog_load.setText(tr("load", language))
        self.source_group.setTitle(tr("source", language))
        self.root_label.setText(tr("root_folder", language))
        self.include_label.setText(tr("include_ext", language))
        self.exclude_label.setText(tr("exclude_ext", language))
        self.include_edit.setPlaceholderText(tr("ext_hint", language))
        self.exclude_edit.setPlaceholderText(tr("ext_hint", language))
        self.target_group.setTitle(tr("target", language))
        self.target_in_place.setText(tr("in_place", language))
        self.target_new_tree.setText(tr("new_tree", language))
        self.target_browse.setText(tr("browse", language))
        self.target_hint.setText(tr("target_hint", language))
        self.structure_group.setTitle(tr("structure", language))
        self.preset_label.setText(tr("preset", language))
        self.custom_label.setText(tr("custom", language))
        self.preview_title.setText(tr("preview", language))
        self.tokens_button.setText(tr("tokens", language))
        self.options_group.setTitle(tr("options", language))
        self.conflict_label.setText(tr("conflict", language))
        self.missing_label.setText(tr("missing_date", language))
        self.subfolder_label.setText(tr("subfolder_action", language))
        self.dated_label.setText(tr("dated_action", language))
        self.mismatch_label.setText(tr("mismatch_action", language))
        self.sidecars_check.setText(tr("sidecars", language))
        self.backup_check.setText(tr("backup", language))
        self.ascii_check.setText(tr("ascii", language))
        self.folders_group.setTitle(tr("existing", language))
        self.folder_table.setHorizontalHeaderLabels(
            [
                tr("col_folder", language),
                tr("col_kind", language),
                tr("col_photos", language),
                tr("col_decided_by", language),
                tr("col_decision", language),
            ]
        )
        self.rule_table.setHorizontalHeaderLabels(
            [tr("col_pattern", language), tr("col_decision", language)]
        )
        self.rules_hint.setText(tr("rules_hint", language))
        self.rule_add_button.setText(tr("rule_add", language))
        self.rule_remove_button.setText(tr("rule_remove", language))
        self.rule_up_button.setToolTip(tr("rule_up", language))
        self.rule_down_button.setToolTip(tr("rule_down", language))
        self._redraw_rules()
        self.plan_button.setText(tr("plan", language))
        self.apply_button.setText(tr("apply", language))
        self.status_label.setText(tr("ready", language))
        self.language_action.setText(tr("language", language))
        if self.root_combo.count():
            self.root_combo.setItemText(0, tr("all_roots", language))
        if not self.catalog_info.text() or self.catalog_info.text().startswith(
            ("No catalog", "Kein Katalog")
        ):
            self.catalog_info.setText(tr("no_catalog", language))
        self.update_preview()

    def toggle_language(self) -> None:
        self.language = "de" if self.language == "en" else "en"
        self._retranslate()
        if self.plan is not None:
            self._show_plan(self.plan, None)

    # -- helpers -----------------------------------------------------------

    def say(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _target_mode_changed(self, checked: bool) -> None:
        self.target_edit.setEnabled(checked)
        self.target_browse.setEnabled(checked)
        self.target_hint.setEnabled(checked)

    def _busy(self, busy: bool, message: str = "") -> None:
        self.plan_button.setEnabled(not busy)
        self.apply_button.setEnabled(not busy and self.plan is not None)
        self.progress.setRange(0, 0 if busy else 100)
        if not busy:
            self.progress.setValue(0)
        self.status_label.setText(message or tr("ready", self.language))

    def current_structure(self):
        custom = self.custom_edit.text().strip()
        if custom:
            return parse_structure(custom)
        return PRESETS[self.preset_combo.currentText()]

    def update_preview(self) -> None:
        try:
            structure = self.current_structure()
        except RuleError as exc:
            self.preview_label.setText(str(exc))
            self.preview_label.setStyleSheet("color: #b00;")
            return
        self.preview_label.setStyleSheet("")
        self.preview_label.setText(describe_structure(structure, self.language))

    def collect_settings(self) -> Settings:
        settings = Settings()
        settings.catalog = self.catalog_edit.text().strip()
        settings.structure = self.current_structure()
        if self.target_new_tree.isChecked():
            settings.placement = "new-tree"
            settings.target_root = self.target_edit.text().strip() or None
        else:
            settings.placement = "in-place"
        index = self.root_combo.currentIndex()
        data = self.root_combo.itemData(index) if index >= 0 else None
        settings.root_folder_id = int(data) if data else None
        settings.include_extensions = _split_extensions(self.include_edit.text())
        settings.exclude_extensions = _split_extensions(self.exclude_edit.text())
        settings.conflict = self.conflict_combo.currentText()
        settings.on_missing_date = self.missing_combo.currentText()
        settings.subfolder_action = self.subfolder_combo.currentText()
        settings.dated_folder_action = self.dated_combo.currentText()
        settings.mismatch_action = self.mismatch_combo.currentText()
        settings.move_sidecars = self.sidecars_check.isChecked()
        settings.backup_catalog = self.backup_check.isChecked()
        settings.ascii_only = self.ascii_check.isChecked()
        settings.language = self.language
        settings.folder_rules = self._rule_strings()
        settings.folder_actions = dict(self.folder_decisions)
        settings.__post_init__()
        settings.validate()
        return settings

    # -- catalog -----------------------------------------------------------

    def pick_catalog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("pick_catalog", self.language),
            str(Path.home()),
            tr("catalog_filter", self.language),
        )
        if path:
            self.catalog_edit.setText(path)
            self.load_catalog()

    def pick_target(self) -> None:
        """Native folder chooser -- it has a New Folder button of its own."""
        start = self.target_edit.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(
            self,
            tr("pick_target", self.language),
            start,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if path:
            self.target_edit.setText(path)

    def load_catalog(self) -> None:
        path = self.catalog_edit.text().strip()
        if not path:
            return
        self.folder_decisions.clear()
        self._busy(True, tr("loading", self.language))
        worker = CatalogWorker(path)
        worker.finished.connect(self._catalog_loaded)
        worker.failed.connect(self._worker_failed)
        run_in_thread(worker, self._threads)

    def _catalog_loaded(self, info: CatalogInfo, roots, folders) -> None:
        self.roots = list(roots)
        self.root_combo.clear()
        self.root_combo.addItem(tr("all_roots", self.language), None)
        for root in self.roots:
            self.root_combo.addItem(
                "{n}  ({p})".format(n=root.name, p=root.absolute_path),
                root.id_local,
            )
        self.catalog_info.setText(
            "{f:,} {files} · {i:,} {images} · {v:,} {vc} · {a} .. {b}".format(
                f=info.files,
                files="Dateien" if self.language == "de" else "files",
                i=info.images,
                images="Bilder" if self.language == "de" else "images",
                v=info.virtual_copies,
                vc="virtuelle Kopien" if self.language == "de" else "virtual copies",
                a=(info.earliest_capture or "?")[:10],
                b=(info.latest_capture or "?")[:10],
            )
        )
        self.say(self.catalog_info.text())
        self._busy(False)

    # -- planning ----------------------------------------------------------

    def do_plan(self) -> None:
        try:
            settings = self.collect_settings()
        except Exception as exc:  # noqa: BLE001 - shown to the user
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self.plan = None
        self.apply_button.setEnabled(False)
        self._busy(True, tr("planning", self.language))
        worker = PlanWorker(settings, self.folder_decisions)
        worker.finished.connect(self._plan_ready)
        worker.failed.connect(self._worker_failed)
        run_in_thread(worker, self._threads)

    def _plan_ready(self, plan: Plan, checks) -> None:
        self.plan = plan
        self._show_plan(plan, checks)
        self._busy(False, tr("done", self.language))
        self.apply_button.setEnabled(plan.has_work)

    def _show_plan(self, plan: Plan, checks) -> None:
        stats = plan.stats
        parts = [
            "{l}: {n:,}".format(l=tr("to_move", self.language), n=stats.touched),
            "{l}: {n:,}".format(l=tr("in_place_count", self.language), n=stats.already_in_place),
            "{l}: {n:,}".format(
                l=tr("skipped", self.language),
                n=stats.skipped_no_date
                + stats.skipped_conflict
                + stats.skipped_filtered
                + stats.missing_source,
            ),
            "{l}: {n:,}".format(l=tr("new_folders", self.language), n=stats.new_folders),
            "{l}: {n:,}".format(
                l=tr("virtual_copies", self.language), n=stats.virtual_copies_carried
            ),
            "{l}: {b}".format(l=tr("volume", self.language), b=human_bytes(stats.bytes_to_move)),
        ]
        text = "   ".join(parts)
        if plan.warnings:
            text += "\n" + "\n".join("! " + w for w in plan.warnings)
        if checks is not None:
            for check in checks.checks:
                if check.level != "ok":
                    text += "\n{lvl}: {m}".format(
                        lvl=check.level.upper(), m=check.message(self.language)
                    )
                    self.say(
                        "{lvl} {n}: {m}".format(
                            lvl=check.level.upper(),
                            n=check.name,
                            m=check.message(self.language),
                        )
                    )
        self.summary_label.setText(text)
        self._fill_folder_table(plan)

    def _fill_folder_table(self, plan: Plan) -> None:
        self.cases = [c for c in plan.folder_cases if c.photo_count]
        table = self.folder_table
        table.setRowCount(len(self.cases))
        for row, case in enumerate(self.cases):
            table.setItem(row, 0, QTableWidgetItem(case.path_from_root or "."))
            kind = (
                tr("kind_anchor", self.language)
                if case.is_anchor
                else tr("kind_dated" if case.is_dated else "kind_plain", self.language)
            )
            table.setItem(row, 1, QTableWidgetItem(kind))
            photos = "{n:,}".format(n=case.photo_count)
            if case.is_dated and case.mismatched_photos:
                photos += "  " + tr("mismatched", self.language).format(n=case.mismatched_photos)
            table.setItem(row, 2, QTableWidgetItem(photos))
            if case.action_source == "override":
                decided_by = tr("decided_by_you", self.language)
            elif case.matched_rule:
                decided_by = case.matched_rule
            else:
                decided_by = tr("decided_by_default", self.language)
            table.setItem(row, 3, QTableWidgetItem(decided_by))
            if case.is_anchor:
                item = QTableWidgetItem("-")
                item.setFlags(Qt.ItemIsEnabled)
                table.setItem(row, 4, item)
                continue
            combo = QComboBox()
            choices = DATED_FOLDER_ACTIONS if case.is_dated else SUBFOLDER_ACTIONS
            for action in choices:
                combo.addItem(action_label(action, self.language), action)
            current = self.folder_decisions.get(case.folder_id, case.action)
            if current in choices:
                combo.setCurrentIndex(choices.index(current))
            combo.currentIndexChanged.connect(
                lambda _index, c=combo, f=case.folder_id: self._decide(f, c)
            )
            table.setCellWidget(row, 4, combo)

    def _decide(self, folder_id: int, combo: QComboBox) -> None:
        self.folder_decisions[folder_id] = combo.currentData()
        self.say("{f}: {a}".format(f=folder_id, a=action_label(combo.currentData(), self.language)))
        self.do_plan()

    # -- applying -----------------------------------------------------------

    def do_apply(self) -> None:
        if self.plan is None:
            QMessageBox.information(self, APP_NAME, tr("plan_first", self.language))
            return
        if not self.plan.has_work:
            QMessageBox.information(self, APP_NAME, tr("nothing_to_do", self.language))
            return
        answer = QMessageBox.warning(
            self,
            tr("confirm_title", self.language),
            tr("confirm_text", self.language).format(n=self.plan.stats.touched),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if answer != QMessageBox.Yes:
            return
        settings = self.plan.settings
        self._busy(True, tr("applying", self.language))
        self.progress.setRange(0, self.plan.stats.touched)
        worker = ApplyWorker(self.plan, settings)
        worker.progress.connect(self._progress)
        worker.finished.connect(self._applied)
        worker.failed.connect(self._worker_failed)
        run_in_thread(worker, self._threads)

    def _progress(self, done: int, total: int, message: str) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.status_label.setText("{d:,} / {t:,}".format(d=done, t=total))

    def _applied(self, result) -> None:
        self.plan = None
        self._busy(False, tr("done", self.language))
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        text = render_result(result, self.language)
        self.say(text)
        QMessageBox.information(self, tr("result", self.language), text)

    def _worker_failed(self, message: str) -> None:
        self._busy(False)
        first = message.splitlines()[0] if message else "?"
        self.say(message)
        QMessageBox.critical(self, APP_NAME, first)

    # -- lifecycle ------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        """Never tear the window down while a worker is still running."""
        wait_for_threads(self._threads)
        super().closeEvent(event)

    def wait_for_workers(self, milliseconds: int = 30000) -> None:
        """Block until no worker thread is running. Used by the tests."""
        wait_for_threads(self._threads, milliseconds)

    # -- help ---------------------------------------------------------------

    def show_tokens(self) -> None:
        lines = [
            "{t:<18} {e:<28} {d}".format(t=token, e=example[:28], d=description)
            for token, example, description in token_help(self.language)
        ]
        box = QMessageBox(self)
        box.setWindowTitle(tr("tokens", self.language))
        box.setFont(QFont("Menlo", 11))
        box.setText("\n".join(lines))
        box.exec()


def _split_extensions(text: str):
    return tuple(
        part.strip().lstrip(".").lower()
        for part in text.replace(";", ",").split(",")
        if part.strip()
    )


def run_gui(catalog: str = "", language: str = "en", debug: bool = False) -> int:
    """Entry point used by ``lrfc gui``."""
    setup_logging(debug=debug, quiet=True, tag="gui")
    application = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(catalog=catalog, language=language)
    window.show()
    return application.exec()
