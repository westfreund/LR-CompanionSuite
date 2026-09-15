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
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QImage,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..catalog.model import CatalogInfo, RootFolder
from ..config import (
    CONFLICT_MODES,
    MISSING_DATE_MODES,
    ConfigError,
    Settings,
    delete_profile,
    list_profiles,
    profile_exists,
)
from ..exceptions_report import (
    ERROR,
    EXCEPTION,
    NOTE,
    WARNING,
    Finding,
    collect_findings,
)
from ..folders import (
    ALL_ACTIONS,
    CONSOLIDATE,
    DATED_FOLDER_ACTIONS,
    KEEP,
    MISMATCH_ACTIONS,
    REFILE,
    SUBFOLDER_ACTIONS,
    FolderCase,
)
from ..folders import label as action_label
from ..journal import JOURNAL_SUFFIX
from ..logging_setup import get_logger, setup_logging
from ..planner import Plan
from ..report import human_bytes, render_result
from ..resources import logo_for
from ..resume import find_interruptions, remove_created_directories, revert_files
from ..rules import (
    PRESETS,
    RuleError,
    describe_structure,
    make_cumulative,
    parse_structure,
    token_help,
)
from ..runs import history, journal_of, runs_directory
from ..safety import preconditions
from ..version import APP_NAME, APP_URL, REVISION, __build_date__
from .i18n import tr
from .state import load_state, save_state
from .workers import (
    ApplyWorker,
    CatalogWorker,
    PlanWorker,
    UndoWorker,
    run_in_thread,
    wait_for_threads,
)

#: Shown beside each precondition, so the state is readable at a glance.
_CHECK_MARKS = {"ok": "\u2713", "warning": "!", "error": "\u2717"}

#: Severity at a glance. Chosen to stay legible on a light and a dark theme.
_LEVEL_COLOURS = {
    ERROR: QColor("#b00020"),
    WARNING: QColor("#b06000"),
    EXCEPTION: QColor("#0057b0"),
    NOTE: QColor("#606060"),
}


def _logo_pixmap(size: int, colour) -> QPixmap:
    """The mark, rendered at *size* in *colour*.

    The SVG is single-colour and takes ``currentColor``, so a front end tints
    it to whatever the surrounding theme uses rather than shipping a light and
    a dark copy. Below 24 px the small cut is used, because the full mark
    cannot read at that size.
    """
    from PySide6.QtCore import QByteArray, QRectF
    from PySide6.QtSvg import QSvgRenderer

    source = logo_for(size)
    text = source.read_text(encoding="utf-8").replace("currentColor", colour.name())
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    QSvgRenderer(QByteArray(text.encode("utf-8"))).render(painter, QRectF(0, 0, size, size))
    painter.end()
    return QPixmap.fromImage(image)


def window_icon() -> QIcon:
    """Every size the window manager may ask for, in one icon.

    Both cuts go in: the system picks whichever size it needs, and at 16 and
    24 px that is the one drawn to be legible there.
    """
    icon = QIcon()
    ink = QColor("#1d1f22")
    for size in (16, 24, 32, 64, 128, 256):
        icon.addPixmap(_logo_pixmap(size, ink))
    return icon


log = get_logger("gui")


class PreconditionDialog(QDialog):
    """States what was found about the library, and asks for a deliberate yes.

    Deliberately not a QMessageBox: the acknowledgement is a checkbox that must
    be ticked before the button becomes usable, so the confirmation cannot be
    given by reflex. A finding that blocks cannot be acknowledged at all.
    """

    def __init__(self, result, language: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("preconditions_title", language))
        self.setMinimumWidth(620)
        layout = QVBoxLayout(self)

        intro = QLabel(tr("preconditions_intro", language))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        for check in result.checks:
            row = QLabel(
                "{mark}  {message}".format(
                    mark=_CHECK_MARKS.get(check.level, "-"), message=check.message(language)
                )
            )
            row.setWordWrap(True)
            row.setTextInteractionFlags(Qt.TextSelectableByMouse)
            colour = _LEVEL_COLOURS.get({"error": ERROR, "warning": WARNING}.get(check.level, NOTE))
            if colour is not None and check.level != "ok":
                row.setStyleSheet("color: {c};".format(c=colour.name()))
            layout.addWidget(row)

        # A blocking finding is not a matter of persuasion, so the refusal is
        # in the rule rather than in whether the box happens to be clickable:
        # a disabled checkbox can still be ticked from code.
        self._blocked = not result.ok
        self.acknowledge = QCheckBox(tr("preconditions_ack", language))
        self.acknowledge.setEnabled(not self._blocked)
        layout.addWidget(self.acknowledge)

        if self._blocked:
            note = QLabel(tr("preconditions_blocked", language))
            note.setWordWrap(True)
            note.setStyleSheet("color: {c};".format(c=_LEVEL_COLOURS[ERROR].name()))
            layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        self.acknowledge.toggled.connect(self._acknowledgement_changed)
        layout.addWidget(buttons)

    def _acknowledgement_changed(self, checked: bool) -> None:
        self.ok_button.setEnabled(checked and not self._blocked)


class RunPickerDialog(QDialog):
    """The runs recorded beside this catalog, and which of them can be undone.

    A file chooser full of similarly named journals is exactly how the wrong
    library gets rolled back. This lists the runs of *this* catalog, says what
    each one did, and refuses to select one that has already been reversed.
    """

    def __init__(self, records, language: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("history_title", language))
        self.setMinimumWidth(680)
        self.records = list(records)
        layout = QVBoxLayout(self)

        intro = QLabel(tr("history_intro", language))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.table = QTableWidget(len(self.records), 4)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(
            [
                tr("history_when", language),
                tr("history_what", language),
                tr("history_files", language),
                tr("history_state", language),
            ]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        for row, record in enumerate(self.records):
            self.table.setItem(row, 0, QTableWidgetItem(record.started_at[:16].replace("T", "  ")))
            # The example, not the placeholders: a list is read at a glance.
            structure = QTableWidgetItem(record.structure_example(language))
            structure.setToolTip(record.structure or "")
            self.table.setItem(row, 1, structure)
            self.table.setItem(row, 2, QTableWidgetItem("{n:,}".format(n=record.files_moved)))
            if record.undone_at:
                state = tr("history_undone", language).format(
                    w=record.undone_at.replace("T", " ")[:16]
                )
            elif record.success:
                state = tr("history_can_undo", language)
            else:
                state = tr("history_failed", language)
            item = QTableWidgetItem(state)
            if not record.can_be_undone:
                item.setForeground(_LEVEL_COLOURS[NOTE])
            self.table.setItem(row, 3, item)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setText(tr("history_undo_this", language))
        self.ok_button.setEnabled(False)
        layout.addWidget(buttons)

        for row, record in enumerate(self.records):
            if record.can_be_undone:
                self.table.selectRow(row)
                break

    def _selection_changed(self) -> None:
        record = self.selected()
        self.ok_button.setEnabled(record is not None and record.can_be_undone)

    def selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.records):
            return self.records[row]
        return None


class MainWindow(QMainWindow):
    """Everything a run needs, in one window."""

    def __init__(self, catalog: str = "", language: Optional[str] = None):
        super().__init__()
        # An explicit --lang wins for this session; otherwise use what was set
        # last time, and only then fall back to English.
        self.state = load_state()
        chosen = language or self.state.get("language")
        self.language = chosen if chosen in ("en", "de") else "en"
        self.plan: Optional[Plan] = None
        self.folder_decisions: Dict[int, str] = {}
        #: The ordered rule list, as (pattern, action) pairs. Order is meaning.
        self.rules: List[Tuple[str, str]] = []
        self.findings: List[Finding] = []
        #: Counts planning requests, so a superseded result can be discarded.
        self._plan_ticket = 0
        #: Set when the operator asked for the plan, so only that one moves
        #: the window to the result tab.
        self._review_plan = False
        self._review_ticket = 0
        #: The journal of the run made in this session, offered first for undo.
        self.last_journal: str = ""
        #: Catalog whose preconditions were acknowledged in this session.
        self._acknowledged: str = ""
        #: Set once the window has been laid out, so geometry is worth saving.
        self._was_shown = False
        self.cases: List[FolderCase] = []
        self.roots: List[RootFolder] = []
        self._threads: list = []

        self.setWindowTitle("{n} - {r}".format(n=APP_NAME, r=REVISION))
        self.setWindowIcon(window_icon())
        self._build()
        self._size_to_screen()
        self._apply_state()
        self._retranslate()
        # A catalog named on the command line beats the remembered one.
        if catalog:
            self.catalog_edit.setText(catalog)
        if self.catalog_edit.text().strip():
            self.load_catalog()

    # -- construction ---------------------------------------------------

    def _build(self) -> None:
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.addWidget(self._masthead())
        outer.addWidget(self._profile_box())

        # One tab per step. Everything used to be stacked in a single scrolling
        # column, which meant most of it was somewhere out of sight: the window
        # showed the catalog and hid the structure, the options and the rules
        # behind a scrollbar nobody had reason to suspect.
        self.tabs = QTabWidget()
        self.tab_pages = [
            (
                "tab_library",
                "tab_library_hint",
                self._scrolling([self._catalog_box(), self._source_box(), self._target_box()]),
            ),
            ("tab_structure", "tab_structure_hint", self._scrolling([self._structure_box()])),
            ("tab_options", "tab_options_hint", self._scrolling([self._options_box()])),
            ("tab_folders", "tab_folders_hint", self._filling(self._folders_box())),
            ("tab_findings", "tab_findings_hint", self._filling(self._findings_box())),
        ]
        for _key, _hint, page in self.tab_pages:
            self.tabs.addTab(page, "")

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Menlo", 11))
        self.log_view.setMinimumHeight(60)

        # The log stays out of the tabs on purpose: it is where an error
        # appears, and an error behind a tab is an error nobody sees.
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.tabs)
        self.splitter.addWidget(self.log_view)
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 1)
        self._make_handles_visible()
        outer.addWidget(self.splitter, 1)

        outer.addWidget(self._actions_box())
        self.setCentralWidget(central)
        self.statusBar().showMessage(
            "{n} {r} - build {d}".format(n=APP_NAME, r=REVISION, d=__build_date__)
        )
        self._build_menu()

    @staticmethod
    def _scrolling(boxes) -> QWidget:
        """A tab of form-like boxes, scrollable for a short screen."""
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        for box in boxes:
            column.addWidget(box)
        column.addStretch(1)
        area = QScrollArea()
        area.setWidget(page)
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return area

    @staticmethod
    def _filling(box) -> QWidget:
        """A tab whose content is a table, and should take all the room there is."""
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(box, 1)
        return page

    def _make_handles_visible(self) -> None:
        """Make the dividers between the sections look like something to grab.

        Qt draws a splitter handle as a few faint dots, which is easy to miss
        entirely -- a section that will not show everything then looks broken
        rather than merely small. A wider handle with a rule through it, a
        resize cursor and a tooltip say what it is.
        """
        self.splitter.setHandleWidth(11)
        self.splitter.setStyleSheet(
            "QSplitter::handle:vertical {"
            "  margin: 3px 0px;"
            "  border-top: 1px solid palette(mid);"
            "  border-bottom: 1px solid palette(mid);"
            "}"
            "QSplitter::handle:vertical:hover { background: palette(highlight); }"
        )
        for index in range(1, self.splitter.count()):
            handle = self.splitter.handle(index)
            if handle is not None:
                handle.setCursor(Qt.SplitVCursor)

    def _retranslate_handles(self) -> None:
        for index in range(1, self.splitter.count()):
            handle = self.splitter.handle(index)
            if handle is not None:
                handle.setToolTip(tr("splitter_hint", self.language))

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

    #: Share of the window the tabs and the log get on a fresh start, and the
    #: height below which each stops being worth showing. The list must have one
    #: entry per widget in the splitter: Qt calls a short list undefined.
    SPLITTER_SHARES = ((0.82, 320), (0.18, 60))

    def _balance_splitter(self, height: int) -> None:
        """Give the settings most of the room, but keep the others usable."""
        sizes = [max(floor, int(height * share)) for share, floor in self.SPLITTER_SHARES]
        assert len(sizes) == self.splitter.count(), "one size per splitter section"
        self.splitter.setSizes(sizes)

    def _build_menu(self) -> None:
        """Entries have to live inside a menu, not on the menu bar itself.

        Qt documents that adding an action directly to a QMenuBar is not
        supported on macOS, where the bar is the system-wide one. Both entries
        were therefore invisible on exactly the platform this was developed on:
        the language switch nobody found, and an undo nobody could reach.
        """
        menu = self.menuBar().addMenu(tr("menu_actions", self.language))
        self.actions_menu = menu

        self.language_action = QAction(tr("language", self.language), self)
        self.language_action.triggered.connect(self.toggle_language)
        menu.addAction(self.language_action)

        self.about_action = QAction(tr("about", self.language), self)
        self.about_action.triggered.connect(self.show_about)
        menu.addAction(self.about_action)

        menu.addSeparator()

        self.history_action = QAction(tr("history_menu", self.language), self)
        self.history_action.triggered.connect(self.show_history)
        menu.addAction(self.history_action)

        self.undo_action = QAction(tr("undo_run", self.language), self)
        self.undo_action.triggered.connect(self.do_undo)
        menu.addAction(self.undo_action)

    def _masthead(self) -> QWidget:
        """The mark and what the tool is, at the top of the window.

        A window icon is not enough: macOS shows no icon in a title bar at all,
        so on the platform this is developed on the mark would never be seen.
        Inside the window it is visible everywhere, and it sits beside the one
        sentence that says what the tool does.
        """
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 2)
        row.setSpacing(12)

        self.logo_label = QLabel()
        self.logo_label.setFixedSize(44, 44)
        self.logo_label.setScaledContents(True)
        row.addWidget(self.logo_label, 0, Qt.AlignTop)

        column = QVBoxLayout()
        column.setSpacing(0)
        self.wordmark_label = QLabel(APP_NAME)
        wordmark_font = self.wordmark_label.font()
        wordmark_font.setBold(True)
        wordmark_font.setPointSize(wordmark_font.pointSize() + 3)
        self.wordmark_label.setFont(wordmark_font)
        column.addWidget(self.wordmark_label)

        self.purpose_label = QLabel()
        self.purpose_label.setWordWrap(True)
        column.addWidget(self.purpose_label)
        row.addLayout(column, 1)

        self._tint_logo()
        return holder

    def _tint_logo(self) -> None:
        """Draw the mark in the current text colour, so it follows the theme."""
        colour = self.palette().windowText().color()
        # Rendered at twice the label size so it stays crisp on a retina screen.
        self.logo_label.setPixmap(_logo_pixmap(88, colour))

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        """Re-tint when the system switches between light and dark."""
        from PySide6.QtCore import QEvent

        super().changeEvent(event)
        if event.type() == QEvent.PaletteChange and hasattr(self, "logo_label"):
            self._tint_logo()

    def _profile_box(self) -> QGroupBox:
        """Save a way of working once, apply it to the next library.

        A profile holds the options and nothing that belongs to one library:
        no catalog, no target folder, no rule list, no per-folder decisions.
        That is what lets the same profile serve several collections.

        The first cut offered a name field with Load and Save beside it, and
        left the reader to work out that typing a name nobody had used yet and
        pressing Save was how a profile came into being. Making one is now its
        own button, and the box lists what exists rather than inviting you to
        type into it.
        """
        box = QGroupBox()
        row = QHBoxLayout(box)
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(220)
        self.profile_combo.currentIndexChanged.connect(self._profile_selection_changed)
        self.profile_new = QPushButton()
        self.profile_new.clicked.connect(self.new_profile)
        self.profile_load = QPushButton()
        self.profile_load.clicked.connect(self.load_profile)
        self.profile_save = QPushButton()
        self.profile_save.clicked.connect(self.save_profile)
        self.profile_delete = QPushButton()
        self.profile_delete.clicked.connect(self.remove_profile)
        row.addWidget(self.profile_combo, 1)
        row.addWidget(self.profile_new)
        row.addWidget(self.profile_load)
        row.addWidget(self.profile_save)
        row.addWidget(self.profile_delete)
        self.profile_group = box
        self._refresh_profiles()
        return box

    def _profile_selection_changed(self) -> None:
        """Everything but New needs a profile to act on."""
        chosen = bool(self.current_profile())
        for button in (self.profile_load, self.profile_save, self.profile_delete):
            button.setEnabled(chosen)

    def current_profile(self) -> str:
        """The selected profile, or "" when the placeholder row is showing."""
        if self.profile_combo.currentIndex() <= 0:
            return ""
        return self.profile_combo.currentText().strip()

    def _refresh_profiles(self, select: str = "") -> None:
        """Re-read the profile folder, keeping the selection where possible."""
        current = select or self.current_profile()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem(tr("profile_none", self.language))
        self.profile_combo.addItems(list_profiles())
        index = self.profile_combo.findText(current) if current else -1
        self.profile_combo.setCurrentIndex(index if index > 0 else 0)
        self.profile_combo.blockSignals(False)
        self._profile_selection_changed()

    def new_profile(self) -> None:
        """Make a profile out of the options currently set."""
        name, accepted = QInputDialog.getText(
            self,
            tr("profile_new_title", self.language),
            tr("profile_new_prompt", self.language),
        )
        if not accepted or not name.strip():
            return
        name = name.strip()
        if profile_exists(name) and not self._confirm(
            tr("profile_overwrite", self.language).format(n=name)
        ):
            return
        self._write_profile(name)

    def save_profile(self) -> None:
        """Put the options currently set back into the chosen profile."""
        name = self.current_profile()
        if not name:
            QMessageBox.information(self, APP_NAME, tr("profile_pick_first", self.language))
            return
        self._write_profile(name)

    def _write_profile(self, name: str) -> None:
        try:
            settings = self.collect_settings()
        except Exception as exc:  # noqa: BLE001 - shown to the user
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        path = settings.save_profile(name)
        # The stored name is sanitised for the filesystem, so select what was
        # actually written rather than what was typed.
        self._refresh_profiles(path.stem)
        self.say(tr("profile_saved", self.language).format(n=name, p=path))

    def remove_profile(self) -> None:
        name = self.current_profile()
        if not name:
            return
        if not self._confirm(tr("profile_confirm_delete", self.language).format(n=name)):
            return
        try:
            delete_profile(name)
        except ConfigError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self._refresh_profiles()
        self.say(tr("profile_deleted", self.language).format(n=name))

    def _confirm(self, question: str) -> bool:
        answer = QMessageBox.question(
            self, APP_NAME, question, QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel
        )
        return answer == QMessageBox.Yes

    def load_profile(self) -> None:
        name = self.current_profile()
        if not name:
            return
        try:
            settings = Settings.load_profile(name)
        except ConfigError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self._apply_settings(settings)
        self.say(tr("profile_loaded", self.language).format(n=name))
        if self.catalog_edit.text().strip():
            self.do_plan()

    def _apply_settings(self, settings: Settings) -> None:
        """Put a profile's options into the widgets.

        The catalog, the target folder and the rules are untouched on purpose:
        a profile does not carry them, and overwriting what the operator has
        already set for *this* library would be the opposite of helpful.
        """
        self._restore_text(self.include_edit, ", ".join(settings.include_extensions))
        self._restore_text(self.exclude_edit, ", ".join(settings.exclude_extensions))
        self._restore_choice(self.conflict_combo, settings.conflict)
        self._restore_choice(self.missing_combo, settings.on_missing_date)
        self._restore_choice(self.subfolder_combo, settings.subfolder_action)
        self._restore_choice(self.dated_combo, settings.dated_folder_action)
        self._restore_choice(self.mismatch_combo, settings.mismatch_action)
        self.sidecars_check.setChecked(settings.move_sidecars)
        self.ascii_check.setChecked(settings.ascii_only)
        self.cumulative_check.setChecked(settings.cumulative_dates)
        self.orphans_check.setChecked(settings.collect_orphans)
        self._restore_text(self.orphan_edit, settings.orphan_folder)
        spec = "/".join(settings.structure)
        for name, preset in PRESETS.items():
            if tuple(preset) == tuple(settings.structure):
                self.preset_combo.setCurrentText(name)
                self.custom_edit.clear()
                break
        else:
            self.custom_edit.setText(spec)
        self.update_preview()

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
        # Both stay usable in either mode. Greying them out until the radio
        # button above is selected reads as "this cannot be done" rather than
        # "select that first", and leaves no hint which control to press --
        # naming a target folder is instead taken as saying which mode is meant.
        self.target_edit = QLineEdit()
        self.target_edit.textEdited.connect(self._target_named)
        self.target_browse = QPushButton()
        self.target_browse.clicked.connect(self.pick_target)
        row.addWidget(self.target_edit, 1)
        row.addWidget(self.target_browse)
        layout.addLayout(row)
        self.target_hint = QLabel()
        self.target_hint.setWordWrap(True)
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
        self.dated_combo.currentTextChanged.connect(self._dated_action_changed)
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
        self.cumulative_check = QCheckBox()
        self.cumulative_check.setChecked(defaults.cumulative_dates)
        self.cumulative_check.toggled.connect(self.update_preview)
        self.orphans_check = QCheckBox()
        self.orphans_check.setChecked(defaults.collect_orphans)
        self.orphans_check.toggled.connect(self._orphans_toggled)
        self.orphan_edit = QLineEdit(defaults.orphan_folder)
        self.orphan_edit.setEnabled(defaults.collect_orphans)
        right.addWidget(self.sidecars_check)
        right.addWidget(self.backup_check)
        right.addWidget(self.ascii_check)
        right.addWidget(self.cumulative_check)
        right.addWidget(self.orphans_check)
        right.addWidget(self.orphan_edit)
        right.addStretch(1)

        grid.addLayout(left, 1)
        grid.addLayout(middle, 1)
        grid.addLayout(right, 1)
        self.options_group = box
        return box

    def _orphans_toggled(self, checked: bool) -> None:
        """The folder name only means something once the sweep is on."""
        self.orphan_edit.setEnabled(checked)

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

    def _findings_box(self) -> QGroupBox:
        """What the plan could not decide alone, and the setting that decides it.

        Reporting these as a single "skipped: 43" is the same as not reporting
        them, so each cause gets its own row, its own count and the name of the
        option that governs it.
        """
        box = QGroupBox()
        layout = QVBoxLayout(box)
        self.findings_table = QTableWidget(0, 5)
        self.findings_table.verticalHeader().setVisible(False)
        self.findings_table.setSelectionBehavior(QTableWidget.SelectRows)
        header = self.findings_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.findings_table.setMinimumHeight(90)
        self.findings_table.itemSelectionChanged.connect(self._show_finding_samples)
        layout.addWidget(self.findings_table, 1)
        self.findings_detail = QLabel()
        self.findings_detail.setWordWrap(True)
        self.findings_detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.findings_detail)
        self.findings_group = box
        return box

    def _fill_findings(self, plan: Plan, checks) -> None:
        self.findings = collect_findings(plan, checks)
        table = self.findings_table
        table.setRowCount(len(self.findings))
        for row, finding in enumerate(self.findings):
            level = QTableWidgetItem(tr("level_" + finding.level, self.language))
            level.setForeground(_LEVEL_COLOURS.get(finding.level, QColor("gray")))
            font = level.font()
            font.setBold(finding.level in (ERROR, WARNING))
            level.setFont(font)
            table.setItem(row, 0, level)
            table.setItem(
                row, 1, QTableWidgetItem("{n:,}".format(n=finding.count) if finding.count else "")
            )
            table.setItem(row, 2, QTableWidgetItem(finding.text(self.language)))
            table.setItem(row, 3, QTableWidgetItem(finding.setting or ""))
            table.setItem(row, 4, QTableWidgetItem(finding.current(self.language)))
        self.findings_detail.setText(
            tr("findings_none", self.language)
            if not self.findings
            else tr("findings_hint", self.language)
        )

    def _show_finding_samples(self) -> None:
        row = self.findings_table.currentRow()
        if not (0 <= row < len(self.findings)):
            return
        finding = self.findings[row]
        if not finding.samples:
            self.findings_detail.setText(finding.text(self.language))
            return
        more = finding.count - len(finding.samples)
        text = "\n".join("    " + sample for sample in finding.samples)
        if more > 0:
            text += "\n    " + tr("findings_more", self.language).format(n=more)
        self.findings_detail.setText(finding.text(self.language) + "\n" + text)

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

        # The one folder decision most libraries need, one click up front,
        # instead of a rule the operator has to know how to write. It drives
        # the dated-folder box in the options rather than duplicating it, so
        # there is still only one setting underneath.
        self.dated_refile_check = QCheckBox()
        self.dated_refile_check.toggled.connect(self._dated_refile_toggled)
        column.addWidget(self.dated_refile_check)

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

    def _dated_refile_toggled(self, checked: bool) -> None:
        """Set the dated-folder default, and re-plan so the effect is visible."""
        wanted = REFILE if checked else KEEP
        if self.dated_combo.currentText() == wanted:
            return
        self.dated_combo.setCurrentText(wanted)

    def _dated_action_changed(self, value: str) -> None:
        """Keep the shortcut in step when the box below is used instead."""
        self.dated_refile_check.blockSignals(True)
        self.dated_refile_check.setChecked(value == REFILE)
        self.dated_refile_check.blockSignals(False)
        if self.catalog_edit.text().strip():
            self.do_plan()

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
        """The buttons, in the order the work is done.

        Forward on the left -- look, then act -- and after a rule, the two that
        deal with a run that has already happened. The rule matters: without it
        Undo sat next to Apply as though it were the next step, which for a
        button that moves fifty thousand files back is the wrong invitation.
        """
        holder = QWidget()
        row = QHBoxLayout(holder)
        self.plan_button = QPushButton()
        self.plan_button.clicked.connect(self.plan_and_review)
        self.apply_button = QPushButton()
        self.apply_button.clicked.connect(self.do_apply)
        self.apply_button.setEnabled(False)
        # The way back belongs beside the way forward. A rollback reachable
        # only through a menu is one nobody finds when they need it.
        self.undo_button = QPushButton()
        self.undo_button.clicked.connect(self.do_undo)
        self.history_button = QPushButton()
        self.history_button.clicked.connect(self.show_history)

        # Painted as a background rather than a sunken VLine: at one pixel
        # wide the framed version drew nothing at all in several styles, which
        # is worse than no rule, because the spacing then looks like a mistake.
        divider = QFrame()
        divider.setFrameShape(QFrame.NoFrame)
        divider.setFixedWidth(1)
        divider.setMinimumHeight(22)
        divider.setStyleSheet("background: palette(mid);")

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status_label = QLabel()
        row.addWidget(self.plan_button)
        row.addWidget(self.apply_button)
        row.addSpacing(10)
        row.addWidget(divider)
        row.addSpacing(10)
        row.addWidget(self.undo_button)
        row.addWidget(self.history_button)
        row.addSpacing(12)
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
        self.cumulative_check.setText(tr("cumulative_dates", language))
        self.cumulative_check.setToolTip(tr("cumulative_dates_hint", language))
        self.orphans_check.setText(tr("collect_orphans", language))
        self.orphans_check.setToolTip(tr("collect_orphans_hint", language))
        self.orphan_edit.setToolTip(tr("orphan_folder_hint", language))
        self.folders_group.setTitle(tr("existing", language))
        self.profile_group.setTitle(tr("profile", language))
        self.profile_new.setText(tr("profile_new", language))
        self.profile_load.setText(tr("profile_load", language))
        self.profile_save.setText(tr("profile_save", language))
        self.profile_delete.setText(tr("profile_delete", language))
        self.profile_combo.setToolTip(tr("profile_hint", language))
        for index, (key, hint, _page) in enumerate(self.tab_pages):
            # Qt reads a single & in a tab label as the accelerator marker and
            # swallows it, which turned "Folders & rules" into "Folders  rules".
            self.tabs.setTabText(index, tr(key, language).replace("&", "&&"))
            self.tabs.setTabToolTip(index, tr(hint, language))
        # The placeholder row is a translated word, so it is rebuilt with the
        # rest -- and the selection has to survive that.
        self._refresh_profiles(self.current_profile())
        self.findings_group.setTitle(tr("findings", language))
        self._retranslate_handles()
        self.findings_table.setHorizontalHeaderLabels(
            [
                "",
                tr("col_count", language),
                tr("col_what", language),
                tr("col_setting", language),
                tr("col_current", language),
            ]
        )
        if not self.findings:
            self.findings_detail.setText(tr("findings_none", language))
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
        self.dated_refile_check.setText(tr("refile_dated", language))
        self.dated_refile_check.setToolTip(tr("refile_dated_hint", language))
        self.rules_hint.setText(tr("rules_hint", language))
        self.rule_add_button.setText(tr("rule_add", language))
        self.rule_remove_button.setText(tr("rule_remove", language))
        self.rule_up_button.setToolTip(tr("rule_up", language))
        self.rule_down_button.setToolTip(tr("rule_down", language))
        self._redraw_rules()
        self.plan_button.setText(tr("plan", language))
        self.apply_button.setText(tr("apply", language))
        self.status_label.setText(tr("ready", language))
        self.actions_menu.setTitle(tr("menu_actions", language))
        self.purpose_label.setText(tr("purpose", language))
        self.about_action.setText(tr("about", language))
        self.language_action.setText(tr("language", language))
        self.history_action.setText(tr("history_menu", language))
        self.undo_action.setText(tr("undo_run", language))
        self.undo_button.setText(tr("undo_button", language))
        self.history_button.setText(tr("history_button", language))
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
        # Written straight away: a language chosen and then lost to a crash is
        # more annoying than the cost of one small file.
        self.remember_state()

    # -- helpers -----------------------------------------------------------

    def say(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _target_mode_changed(self, checked: bool) -> None:
        """Only the emphasis changes; both controls stay reachable."""
        font = self.target_edit.font()
        font.setBold(checked)
        self.target_edit.setFont(font)

    def _target_named(self, text: str) -> None:
        """Naming a folder is what "sort into a new tree" means.

        Typing a path while "below the folder the photos are in" is selected
        cannot mean anything else, so it selects the mode rather than being
        quietly ignored.
        """
        if text.strip() and not self.target_new_tree.isChecked():
            self.target_new_tree.setChecked(True)

    def _busy(self, busy: bool, message: str = "") -> None:
        self.plan_button.setEnabled(not busy)
        self.undo_button.setEnabled(not busy)
        self.undo_action.setEnabled(not busy)
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
            if self.cumulative_check.isChecked():
                structure = make_cumulative(structure)
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
        settings.cumulative_dates = self.cumulative_check.isChecked()
        settings.collect_orphans = self.orphans_check.isChecked()
        settings.orphan_folder = self.orphan_edit.text().strip() or Settings().orphan_folder
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
            self.target_new_tree.setChecked(True)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        """First time the window appears: settle anything left half done.

        Not from the constructor. A modal dialog raised before the window has
        been laid out leaves it reporting default geometry, which was then
        saved on close and restored as an unusable page.
        """
        super().showEvent(event)
        if self._was_shown:
            return
        self._was_shown = True
        if self._offer_to_finish_an_interrupted_run():
            self._load_catalog()

    def load_catalog(self) -> None:
        self._offer_to_finish_an_interrupted_run()
        self._load_catalog()

    def _load_catalog(self) -> None:
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

    def plan_and_review(self) -> None:
        """Plan because the operator asked, and show the result when it lands.

        Only this route moves the window. Changing a rule or a folder decision
        re-plans too, and a window that jumped to the result each time would
        pull the operator out of the table they are working in -- which is the
        crowding problem again, wearing a different coat.
        """
        self._review_plan = True
        self.do_plan()

    def do_plan(self) -> None:
        try:
            settings = self.collect_settings()
        except Exception as exc:  # noqa: BLE001 - shown to the user
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self.plan = None
        self.apply_button.setEnabled(False)
        self._busy(True, tr("planning", self.language))
        # Changing a setting re-plans, and on a large catalog a plan takes long
        # enough for two to overlap. Without a ticket the slower, older one
        # lands last and becomes the plan that Apply would run -- a plan that
        # does not match what is on screen. Only the newest request counts.
        self._plan_ticket += 1
        ticket = self._plan_ticket
        # Tie the request to its ticket, so a superseded plan cannot move the
        # window either.
        if self._review_plan:
            self._review_ticket = ticket
            self._review_plan = False
        # Connect the bound method, never a lambda: a lambda has no QObject
        # receiver, so Qt makes the connection direct rather than queued and
        # the slot runs on the worker thread -- where creating the widgets of
        # the folder table is illegal and silently produces dead ones.
        worker = PlanWorker(settings, self.folder_decisions, ticket)
        worker.finished.connect(self._plan_ready)
        worker.failed.connect(self._worker_failed)
        run_in_thread(worker, self._threads)

    def _plan_ready(self, plan: Plan, checks, ticket: int) -> None:
        # No default: a sentinel that means "accept anyway" is exactly how a
        # superseded result slips through.
        if ticket != self._plan_ticket:
            log.info("Discarding a superseded plan (ticket %d)", ticket)
            return
        self.plan = plan
        self._show_plan(plan, checks)
        self._busy(False, tr("done", self.language))
        self.apply_button.setEnabled(plan.has_work)
        if ticket == self._review_ticket:
            self._show_result_tab()

    #: The tab that holds the findings, by position in `tab_pages`.
    RESULT_TAB = 4

    def _show_result_tab(self) -> None:
        """Move to the result once there is one.

        The findings say what the plan could not decide alone, which is the
        next thing to read -- and somebody who pressed Plan while looking at
        the options has no reason to suspect there is anything to go and find.
        """
        self._review_ticket = 0
        if self.tabs.currentIndex() != self.RESULT_TAB:
            self.tabs.setCurrentIndex(self.RESULT_TAB)

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
        self.summary_label.setText("   ".join(parts))
        # The detail belongs in the findings table, not squeezed into one line.
        self._fill_findings(plan, checks)
        for finding in self.findings:
            if finding.level in (ERROR, WARNING):
                self.say(
                    "{lvl} {c}: {m}".format(
                        lvl=finding.level.upper(),
                        c=finding.category,
                        m=finding.text(self.language),
                    )
                )
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

    # -- the preconditions, acknowledged once per session --------------------

    def _preconditions_accepted(self) -> bool:
        """Show what was actually found, and require a deliberate yes.

        A dialog that recites three rules gets clicked away. This one reports
        the schema version it read, whether every root folder resolves, and
        when the last backup was made -- and has to be ticked before Apply is
        allowed. Once per catalog per session; a blocking finding cannot be
        ticked past at all.
        """
        catalog = self.catalog_edit.text().strip()
        if not catalog or self._acknowledged == catalog:
            return True

        try:
            result = preconditions(Path(catalog), self.collect_settings())
        except Exception as exc:  # noqa: BLE001 - shown to the user
            QMessageBox.warning(self, APP_NAME, str(exc))
            return False

        dialog = PreconditionDialog(result, self.language, self)
        if dialog.exec() != QDialog.Accepted:
            return False
        self._acknowledged = catalog
        for check in result.checks:
            self.say(
                "{lvl} {n}: {m}".format(
                    lvl=check.level.upper(), n=check.name, m=check.message(self.language)
                )
            )
        return True

    def do_apply(self) -> None:
        if self.plan is None:
            QMessageBox.information(self, APP_NAME, tr("plan_first", self.language))
            return
        if not self.plan.has_work:
            QMessageBox.information(self, APP_NAME, tr("nothing_to_do", self.language))
            return
        if not self._preconditions_accepted():
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
        # Remember where the run recorded itself, so undoing it is one click
        # rather than a hunt through the backup directory.
        if result.journal_path:
            self.last_journal = result.journal_path
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

    # -- reversing a run ----------------------------------------------------

    def do_undo(self) -> None:
        """Put a completed run back, files and catalog together.

        The journal is the record of what actually happened, so reversing means
        choosing one. The newest is offered first because it is nearly always
        the one meant, but any of them can be picked -- runs are undone in the
        order they were made, newest first.
        """
        journal = self._choose_journal()
        if not journal:
            return
        if not self._confirm_undo(journal):
            return
        self._busy(True, tr("undoing", self.language))
        worker = UndoWorker(journal)
        worker.finished.connect(self._undo_finished)
        worker.failed.connect(self._worker_failed)
        run_in_thread(worker, self._threads)

    def _recorded_runs(self):
        catalog = self.catalog_edit.text().strip()
        return history(Path(catalog)) if catalog else []

    def _offer_to_finish_an_interrupted_run(self) -> bool:
        """Ask about a half-done earlier run before anything else happens.

        Pre-flight refuses to plan on top of one, so the operator would
        otherwise meet a refusal with no way to act on it from here.
        """
        catalog = self.catalog_edit.text().strip()
        if not catalog:
            return False
        try:
            pending = find_interruptions(Path(catalog))
        except Exception as exc:  # noqa: BLE001 - shown to the user
            self.say(str(exc))
            return False
        if not pending:
            return False
        found = pending[0]
        answer = QMessageBox.warning(
            self,
            APP_NAME,
            tr("interrupted_found", self.language).format(
                d=found.describe(self.language), n=len(found.to_revert)
            ),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return False
        restored, errors = revert_files(found)
        removed = remove_created_directories(found)
        self.say(tr("interrupted_fixed", self.language).format(n=restored, d=removed))
        for error in errors:
            self.say(error)
        return True

    def show_history(self) -> None:
        """What has been done to this catalog, and what can still be taken back."""
        records = self._recorded_runs()
        if not records:
            QMessageBox.information(self, APP_NAME, self._nothing_recorded())
            return
        RunPickerDialog(records, self.language, self).exec()

    def _nothing_recorded(self) -> str:
        """Say which of the two empty-handed cases this is.

        Runs are recorded beside the catalog, so with no catalog named there is
        nothing to look in -- which is not the same as a catalog that has never
        been touched, and telling the user the latter sends them hunting for a
        file that is not missing at all.
        """
        if not self.catalog_edit.text().strip():
            return tr("no_catalog_for_runs", self.language)
        return tr("history_empty", self.language)

    def _choose_journal(self) -> str:
        """Pick a run of *this* catalog, or fall back to choosing a file.

        A file chooser full of similarly named journals from several libraries
        is how the wrong one gets rolled back, so the recorded runs of the
        catalog on screen come first.
        """
        records = self._recorded_runs()
        if records:
            dialog = RunPickerDialog(records, self.language, self)
            if dialog.exec() != QDialog.Accepted:
                return ""
            record = dialog.selected()
            return str(journal_of(record)) if record is not None else ""

        catalog = self.catalog_edit.text().strip()
        if not catalog:
            QMessageBox.information(self, APP_NAME, self._nothing_recorded())
            return ""
        start = self.last_journal or str(runs_directory(Path(catalog)))
        path, _filter = QFileDialog.getOpenFileName(
            self,
            tr("pick_journal", self.language),
            start,
            "Journal (*{s});;All files (*)".format(s=JOURNAL_SUFFIX),
        )
        return path

    def _confirm_undo(self, journal: str) -> bool:
        answer = QMessageBox.warning(
            self,
            APP_NAME,
            tr("confirm_undo", self.language).format(j=journal),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        return answer == QMessageBox.Yes

    def _undo_finished(self, result) -> None:
        self._busy(False, tr("done", self.language))
        self.say(render_result(result, self.language))
        # The catalog on disk is a different file now; nothing planned against
        # the old one is still true.
        self.plan = None
        self.apply_button.setEnabled(False)
        box = QMessageBox.information if result.success else QMessageBox.warning
        box(
            self,
            APP_NAME,
            tr("undo_done" if result.success else "undo_failed", self.language).format(
                n=result.files_moved, e="\n".join(result.errors)
            ),
        )
        if self.catalog_edit.text().strip():
            self.load_catalog()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        """Never tear the window down while a worker is still running."""
        wait_for_threads(self._threads)
        self.remember_state()
        super().closeEvent(event)

    # -- remembering what was set ------------------------------------------

    def collect_state(self) -> Dict[str, object]:
        """The settings worth carrying into the next session.

        See :mod:`lrcompanion.gui.state` for the two that are deliberately
        left out.
        """
        state = {
            "language": self.language,
            "catalog": self.catalog_edit.text().strip(),
            "placement": "new-tree" if self.target_new_tree.isChecked() else "in-place",
            "target_root": self.target_edit.text().strip(),
            "preset": self.preset_combo.currentText(),
            "custom_structure": self.custom_edit.text().strip(),
            "include_extensions": self.include_edit.text().strip(),
            "exclude_extensions": self.exclude_edit.text().strip(),
            "conflict": self.conflict_combo.currentText(),
            "on_missing_date": self.missing_combo.currentText(),
            "subfolder_action": self.subfolder_combo.currentText(),
            "dated_folder_action": self.dated_combo.currentText(),
            "mismatch_action": self.mismatch_combo.currentText(),
            "move_sidecars": self.sidecars_check.isChecked(),
            "ascii_only": self.ascii_check.isChecked(),
            "cumulative_dates": self.cumulative_check.isChecked(),
            "collect_orphans": self.orphans_check.isChecked(),
            "orphan_folder": self.orphan_edit.text().strip(),
        }
        # Geometry is only worth keeping once the window has actually been
        # shown. Read before that, Qt hands back its defaults and zero-height
        # sections -- which then come back as a 640x480 window with two panes
        # collapsed, and the page looks broken.
        if self._was_shown:
            state["window"] = [self.width(), self.height()]
            state["splitter"] = self.splitter.sizes()
        # Which tab is open is not geometry: Qt answers that correctly whether
        # the window has been on screen or not.
        state["tab"] = self.tabs.currentIndex()
        return state

    def remember_state(self) -> bool:
        return save_state(self.collect_state())

    def _apply_state(self) -> None:
        """Put the remembered settings into the widgets.

        Every value is checked against what the widget actually offers: a
        remembered action that a later revision renamed must leave the default
        standing rather than an empty combo box.
        """
        state = self.state
        if not state:
            return

        self._restore_text(self.catalog_edit, state.get("catalog"))
        self._restore_text(self.target_edit, state.get("target_root"))
        if state.get("placement") == "new-tree":
            self.target_new_tree.setChecked(True)
        self._restore_text(self.include_edit, state.get("include_extensions"))
        self._restore_text(self.exclude_edit, state.get("exclude_extensions"))
        self._restore_text(self.custom_edit, state.get("custom_structure"))
        self._restore_choice(self.preset_combo, state.get("preset"))
        self._restore_choice(self.conflict_combo, state.get("conflict"))
        self._restore_choice(self.missing_combo, state.get("on_missing_date"))
        self._restore_choice(self.subfolder_combo, state.get("subfolder_action"))
        self._restore_choice(self.dated_combo, state.get("dated_folder_action"))
        self._restore_choice(self.mismatch_combo, state.get("mismatch_action"))
        if isinstance(state.get("move_sidecars"), bool):
            self.sidecars_check.setChecked(state["move_sidecars"])
        if isinstance(state.get("ascii_only"), bool):
            self.ascii_check.setChecked(state["ascii_only"])
        if isinstance(state.get("cumulative_dates"), bool):
            self.cumulative_check.setChecked(state["cumulative_dates"])
        if isinstance(state.get("collect_orphans"), bool):
            self.orphans_check.setChecked(state["collect_orphans"])
        self._restore_text(self.orphan_edit, state.get("orphan_folder"))
        # The backup switch is never restored: see gui/state.py.
        self.backup_check.setChecked(True)

        size = state.get("window")
        if isinstance(size, list) and len(size) == 2:
            available = QGuiApplication.primaryScreen()
            bounds = available.availableGeometry() if available else None
            width, height = int(size[0]), int(size[1])
            if bounds is not None:
                width = min(width, bounds.width())
                height = min(height, bounds.height())
            if width >= 720 and height >= 420:
                self.resize(width, height)
        tab = state.get("tab")
        if isinstance(tab, int) and 0 <= tab < self.tabs.count():
            self.tabs.setCurrentIndex(tab)
        sizes = state.get("splitter")
        if isinstance(sizes, list) and len(sizes) == self.splitter.count():
            if all(isinstance(value, int) for value in sizes) and sum(sizes) > 0:
                self.splitter.setSizes(sizes)

    @staticmethod
    def _restore_text(widget, value) -> None:
        if isinstance(value, str) and value:
            widget.setText(value)

    @staticmethod
    def _restore_choice(combo: QComboBox, value) -> None:
        """Only select what the combo really offers."""
        if not isinstance(value, str):
            return
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def wait_for_workers(self, milliseconds: int = 30000) -> None:
        """Block until no worker thread is running. Used by the tests."""
        wait_for_threads(self._threads, milliseconds)

    # -- help ---------------------------------------------------------------

    def about_html(self) -> str:
        """What the About box says. Separate from showing it, so it is testable."""
        return (
            "<h3>{n}</h3>"
            "<p><b>{r}</b> &middot; build {b}</p>"
            "<p>{what}</p>"
            "<p>{promise}</p>"
            "<p>{licence}<br>"
            '<a href="{url}">{url}</a></p>'
        ).format(
            n=APP_NAME,
            r=REVISION,
            b=__build_date__,
            what=tr("about_what", self.language),
            promise=tr("about_promise", self.language),
            licence=tr("about_licence", self.language),
            url=APP_URL,
        )

    def show_about(self) -> None:
        """What the tool does, what it promises, and where it came from."""
        box = QMessageBox(self)
        box.setWindowTitle(tr("about", self.language))
        box.setIconPixmap(_logo_pixmap(96, self.palette().windowText().color()))
        box.setTextFormat(Qt.RichText)
        box.setText(self.about_html())
        box.exec()

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


def run_gui(catalog: str = "", language: Optional[str] = None, debug: bool = False) -> int:
    """Entry point used by ``lrfc gui``."""
    setup_logging(debug=debug, quiet=True, tag="gui")
    application = QApplication.instance() or QApplication(sys.argv)
    # Set on the application, not only the window: that is what the macOS Dock
    # and the Windows task bar read.
    application.setWindowIcon(window_icon())
    window = MainWindow(catalog=catalog, language=language)
    window.show()
    return application.exec()
