"""The Textual application.

Layout: a settings sidebar on the left, results on the right. Every long
running step (reading the catalog, planning, executing) runs in a worker
thread so the interface stays responsive; results are pushed back onto the
message loop with ``call_from_thread``.

The header always shows the revision and the build date, as required.
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
)

from ..catalog.db import CatalogError, open_catalog
from ..catalog.reader import CatalogReader
from ..config import (
    CONFLICT_MODES,
    MISSING_DATE_MODES,
    PLACEMENT_MODES,
    ConfigError,
    Settings,
)
from ..exceptions_report import collect_findings
from ..executor import ExecutionError, execute, undo
from ..folders import (
    DATED_FOLDER_ACTIONS,
    MISMATCH_ACTIONS,
    SUBFOLDER_ACTIONS,
)
from ..folders import (
    label as action_label,
)
from ..logging_setup import LOGGER_NAME, get_logger, setup_logging
from ..planner import Plan, PlanError, build_plan
from ..report import human_bytes, render_info, render_result
from ..rules import PRESET_DESCRIPTIONS, PRESETS, RuleError, describe_structure, parse_structure
from ..runs import history, journal_of
from ..safety import preconditions, preflight
from ..version import APP_NAME, REVISION, __build_date__

log = get_logger("tui")

TEXT = {
    # -- preconditions, history and undo --------------------------------
    "profile": ("Profile", "Profil"),
    "profile_name": ("profile name", "Profilname"),
    "profile_load": ("Load", "Laden"),
    "profile_save": ("Save", "Speichern"),
    "profile_needs_a_name": (
        "Type a name for the profile first.",
        "Bitte zuerst einen Namen für das Profil eingeben.",
    ),
    "profile_saved": ("Profile {n} saved to {p}", "Profil {n} gespeichert unter {p}"),
    "profile_loaded": ("Profile {n} loaded", "Profil {n} geladen"),
    "source": ("Source", "Quelle"),
    "root_folder": ("Root folder", "Stammordner"),
    "all_roots": ("All root folders", "Alle Stammordner"),
    "include_ext": ("Only these extensions", "Nur diese Endungen"),
    "exclude_ext": ("Skip these extensions", "Diese Endungen auslassen"),
    "rules": (
        "Folder rules, in order, comma separated",
        "Ordnerregeln, der Reihe nach, kommagetrennt",
    ),
    "cumulative": (
        "Every date level names the whole date",
        "Jede Datumsebene nennt das ganze Datum",
    ),
    "collect_orphans": (
        "Collect files not in the catalog",
        "Nicht im Katalog enthaltene Dateien einsammeln",
    ),
    "orphan_folder": ("Their folder", "Deren Ordner"),
    "findings_none": (
        "Nothing needs an answer.",
        "Nichts zu beantworten.",
    ),
    "preconditions_title": ("Before this run", "Vor diesem Lauf"),
    "preconditions_intro": (
        "This is what was found about the library. These decide whether the run can succeed:",
        "Das wurde über die Bibliothek festgestellt. Davon hängt ab, ob der Lauf gelingen kann:",
    ),
    "preconditions_ack": (
        "I have read this, Lightroom Classic is closed, and I have a backup",
        "Gelesen, Lightroom Classic ist geschlossen, eine Sicherung ist da",
    ),
    "preconditions_blocked": (
        "Something above prevents the run. Put it right first.",
        "Etwas davon verhindert den Lauf. Bitte zuerst beheben.",
    ),
    "history_title": ("Runs recorded for this catalog", "Aufgezeichnete Läufe dieses Katalogs"),
    "history_intro": (
        "Every run writes its record beside this catalog, so the runs of "
        "another library cannot be mistaken for these.",
        "Jeder Lauf legt seine Aufzeichnung neben diesen Katalog, damit die "
        "Läufe einer anderen Bibliothek nicht mit diesen verwechselt werden.",
    ),
    "history_when": ("When", "Wann"),
    "history_what": ("Structure", "Struktur"),
    "history_files": ("Files", "Dateien"),
    "history_state": ("State", "Zustand"),
    "history_can_undo": ("can be undone", "kann zurückgenommen werden"),
    "history_undone": ("undone {w}", "zurückgenommen {w}"),
    "history_failed": ("failed", "fehlgeschlagen"),
    "history_undo_this": ("Undo this run", "Diesen Lauf zurücknehmen"),
    "history_not_undoable": (
        "That run cannot be undone.",
        "Dieser Lauf lässt sich nicht zurücknehmen.",
    ),
    "history_empty": (
        "No runs recorded for this catalog yet.",
        "Für diesen Katalog sind noch keine Läufe aufgezeichnet.",
    ),
    "no_catalog_yet": ("Choose a catalog first.", "Bitte zuerst einen Katalog wählen."),
    "close": ("Close", "Schließen"),
    "undo_title": ("Undo a run", "Lauf rückgängig machen"),
    "undoing": ("Undoing the run…", "Lauf wird rückgängig gemacht…"),
    "confirm_undo": (
        "Reverse the run recorded in {j}? Every file it moved goes back, the "
        "folders it created are removed if empty, and the catalog is restored "
        "from that run's backup. Lightroom Classic must be closed.",
        "Den in {j} aufgezeichneten Lauf zurücknehmen? Jede verschobene Datei "
        "kehrt zurück, die angelegten Ordner werden entfernt, sofern leer, und "
        "der Katalog wird aus der Sicherung dieses Laufs zurückgespielt. "
        "Lightroom Classic muss geschlossen sein.",
    ),
    "undo_done": (
        "{n:,} file(s) put back, catalog restored.",
        "{n:,} Datei(en) zurückgestellt, Katalog wiederhergestellt.",
    ),
    "undo_failed": ("Only partly reversed: {e}", "Nur teilweise zurückgenommen: {e}"),
    "catalog": ("Catalog (.lrcat)", "Katalog (.lrcat)"),
    "load": ("Load catalog", "Katalog laden"),
    "structure": ("Folder structure", "Ordnerstruktur"),
    "preset": ("Preset", "Vorlage"),
    "custom": ("Custom template", "Eigenes Template"),
    "preview": ("Preview", "Vorschau"),
    "options": ("Options", "Optionen"),
    "placement": ("Placement", "Platzierung"),
    "target_root": ("Target root (new-tree)", "Zielwurzel (new-tree)"),
    "conflict": ("Name conflicts", "Namenskonflikte"),
    "missing": ("Without date", "Ohne Datum"),
    "sidecars": ("Move sidecar files", "Sidecar-Dateien mitnehmen"),
    "backup": ("Back up catalog first", "Katalog vorher sichern"),
    "ascii": ("ASCII-only folder names", "Ordnernamen nur ASCII"),
    "plan": ("Plan (dry run)", "Planen (Trockenlauf)"),
    "apply": ("Apply", "Ausführen"),
    "quit": ("Quit", "Beenden"),
    "no_catalog": ("No catalog loaded.", "Kein Katalog geladen."),
    "no_plan": ("Plan first.", "Bitte zuerst planen."),
    "folder": ("Target folder", "Zielordner"),
    "files": ("Files", "Dateien"),
    "planning": ("Planning...", "Plane..."),
    "loading": ("Reading catalog...", "Lese Katalog..."),
    "applying": ("Applying...", "Führe aus..."),
    "confirm_title": ("Confirm", "Bestätigen"),
    "confirm_body": (
        "{n:,} file(s) will be moved and the catalog will be modified.\n"
        "A verified backup of the catalog is written first.\n\n"
        "Make sure Lightroom Classic is closed.",
        "{n:,} Datei(en) werden verschoben und der Katalog wird verändert.\n"
        "Zuvor wird ein geprüftes Backup des Katalogs angelegt.\n\n"
        "Bitte sicherstellen, dass Lightroom Classic geschlossen ist.",
    ),
    "yes": ("Yes, apply", "Ja, ausführen"),
    "no": ("Cancel", "Abbrechen"),
    "lang": ("Language", "Sprache"),
    "existing": ("Existing folders", "Vorgefundene Ordner"),
    "subfolder_action": ("Topic subfolders", "Thematische Unterordner"),
    "dated_action": ("Dated folders", "Datierte Ordner"),
    "mismatch_action": ("Wrong date inside", "Falsches Datum darin"),
    "col_folder": ("Folder", "Ordner"),
    "col_photos": ("Photos", "Fotos"),
    "col_action": ("Decision", "Entscheidung"),
    "cycle_hint": (
        "Enter on a row cycles its decision and re-plans",
        "Enter auf einer Zeile wechselt die Entscheidung und plant neu",
    ),
}


def tr(key: str, language: str) -> str:
    en, de = TEXT[key]
    return de if language == "de" else en


class TuiLogHandler(logging.Handler):
    """Forwards package log records into the on-screen log pane."""

    def __init__(self, app: LRFolderCraftApp):
        super().__init__(level=logging.INFO)
        self.app_ref = app

    def emit(self, record: logging.LogRecord) -> None:
        if getattr(record, "file_only", False):
            return
        try:
            message = self.format(record)
        except Exception:  # pragma: no cover - never break the UI on a log line
            return
        colour = {
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold red",
        }.get(record.levelname, "dim")
        try:
            self.app_ref.call_from_thread(
                self.app_ref.write_log, "[{c}]{m}[/{c}]".format(c=colour, m=message)
            )
        except Exception:
            pass


class ConfirmScreen(ModalScreen[bool]):
    """Blocking yes/no dialog shown before anything is written.

    Escape declines. A modal that traps the operator until they find the right
    button is bad enough anywhere; in front of the one dialog that starts fifty
    thousand file moves it is worse than that.
    """

    BINDINGS = [Binding("escape", "decline", "Cancel", priority=True)]

    def action_decline(self) -> None:
        self.dismiss(False)

    def __init__(self, title: str, body: str, yes: str, no: str):
        super().__init__()
        self._title = title
        self._body = body
        self._yes = yes
        self._no = no

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("[bold]{t}[/bold]".format(t=self._title))
            yield Static(self._body)
            with Horizontal(id="dialog-buttons"):
                yield Button(self._yes, variant="warning", id="confirm-yes")
                yield Button(self._no, variant="primary", id="confirm-no")

    @on(Button.Pressed, "#confirm-yes")
    def _yes_pressed(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-no")
    def _no_pressed(self) -> None:
        self.dismiss(False)


def _split_list(text: str) -> tuple:
    """Comma separated entries, empties dropped."""
    return tuple(part.strip() for part in text.split(",") if part.strip())


def _split_rules(text: str) -> tuple:
    """Folder rules, comma separated, in the order they were written.

    A table would be nicer, but order is the only thing that matters here and a
    line of text carries it plainly: the first match wins, left to right.
    """
    return _split_list(text)


class PreconditionScreen(ModalScreen[bool]):
    """What was found about the library, and a deliberate yes.

    The same contract as in the window: a tick, not a click, and a finding that
    blocks cannot be acknowledged at all. Without this the text interface was
    the surface with the greatest effect and the smallest safety net.
    """

    BINDINGS = [Binding("escape", "decline", "Cancel", priority=True)]

    def __init__(self, result, language: str):
        super().__init__()
        self._result = result
        self._language = language

    def action_decline(self) -> None:
        self.dismiss(False)

    def compose(self) -> ComposeResult:
        blocked = not self._result.ok
        with Vertical(id="dialog"):
            yield Label("[bold]{t}[/bold]".format(t=tr("preconditions_title", self._language)))
            yield Static(tr("preconditions_intro", self._language))
            for check in self._result.checks:
                mark = {"ok": "[green]OK[/green]", "warning": "[yellow]![/yellow]"}.get(
                    check.level, "[red]X[/red]"
                )
                yield Static("{m} {t}".format(m=mark, t=check.message(self._language)))
            yield Checkbox(
                tr("preconditions_ack", self._language), value=False, id="ack", disabled=blocked
            )
            if blocked:
                yield Static("[red]{t}[/red]".format(t=tr("preconditions_blocked", self._language)))
            with Horizontal(id="dialog-buttons"):
                yield Button(
                    tr("yes", self._language), variant="warning", id="pre-yes", disabled=True
                )
                yield Button(tr("no", self._language), variant="primary", id="pre-no")

    @on(Checkbox.Changed, "#ack")
    def _ack_changed(self, event: Checkbox.Changed) -> None:
        # The refusal lives in the rule, not in whether the box is clickable:
        # a disabled checkbox can still be set from code.
        allowed = bool(event.value) and self._result.ok
        self.query_one("#pre-yes", Button).disabled = not allowed

    @on(Button.Pressed, "#pre-yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#pre-no")
    def _no(self) -> None:
        self.dismiss(False)


class HistoryScreen(ModalScreen[Optional[str]]):
    """The runs recorded beside this catalog; returns the journal to reverse."""

    BINDINGS = [Binding("escape", "close", "Close", priority=True)]

    def __init__(self, records, language: str):
        super().__init__()
        self._records = list(records)
        self._language = language

    def action_close(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("[bold]{t}[/bold]".format(t=tr("history_title", self._language)))
            yield Static(tr("history_intro", self._language))
            yield DataTable(id="runs", zebra_stripes=True, cursor_type="row")
            with Horizontal(id="dialog-buttons"):
                yield Button(
                    tr("history_undo_this", self._language), variant="warning", id="run-undo"
                )
                yield Button(tr("close", self._language), variant="primary", id="run-close")

    def on_mount(self) -> None:
        table = self.query_one("#runs", DataTable)
        table.add_columns(
            tr("history_when", self._language),
            tr("history_what", self._language),
            tr("history_files", self._language),
            tr("history_state", self._language),
        )
        for record in self._records:
            if record.undone_at:
                state = tr("history_undone", self._language).format(
                    w=record.undone_at.replace("T", " ")[:16]
                )
            elif record.success:
                state = tr("history_can_undo", self._language)
            else:
                state = tr("history_failed", self._language)
            table.add_row(
                record.started_at.replace("T", "  ")[:16],
                record.structure or "-",
                "{n:,}".format(n=record.files_moved),
                state,
            )

    @on(Button.Pressed, "#run-undo")
    def _undo(self) -> None:
        row = self.query_one("#runs", DataTable).cursor_row
        if not (0 <= row < len(self._records)):
            return
        record = self._records[row]
        if not record.can_be_undone:
            self.notify(tr("history_not_undoable", self._language), severity="warning")
            return
        self.dismiss(str(journal_of(record)))

    @on(Button.Pressed, "#run-close")
    def _close(self) -> None:
        self.dismiss(None)


class LRFolderCraftApp(App[int]):
    """Interactive front end for LR-FolderCraft."""

    CSS_PATH = "app.tcss"
    TITLE = APP_NAME
    SUB_TITLE = "{r} - build {d}".format(r=REVISION, d=__build_date__)

    # Textual reserves ctrl+p for its command palette and binds it with
    # priority, so an ordinary binding of the same key never fires -- and
    # neither did ctrl+r or f1. The footer advertised four shortcuts of which
    # only ctrl+l worked. The palette is switched off because this application
    # does not use it, and the bindings are declared with priority so they beat
    # whatever a focused input would otherwise swallow.
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+l", "load_catalog", "Load", priority=True),
        Binding("ctrl+p", "plan", "Plan", priority=True),
        Binding("ctrl+r", "apply", "Apply", priority=True),
        Binding("ctrl+z", "history", "History", priority=True),
        Binding("f1", "toggle_language", "EN/DE", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self, catalog: str = "", language: str = "en", debug: bool = False):
        super().__init__()
        self.language = language if language in ("en", "de") else "en"
        self.debug_mode = debug
        self.initial_catalog = catalog or ""
        self.plan: Optional[Plan] = None
        #: Per-folder decisions the operator made by cycling a table row.
        self.folder_overrides: dict[int, str] = {}
        self.settings = Settings()
        self._handler: Optional[TuiLogHandler] = None
        #: Catalog whose preconditions were acknowledged in this session.
        self._acknowledged = ""

    # -- layout ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with ScrollableContainer(id="sidebar"):
                yield Label(tr("catalog", self.language), classes="section")
                yield Input(
                    value=self.initial_catalog,
                    placeholder="/path/to/catalog.lrcat",
                    id="catalog-path",
                )
                yield Button(tr("load", self.language), id="btn-load", variant="primary")

                yield Label(tr("profile", self.language), classes="section")
                yield Input(placeholder=tr("profile_name", self.language), id="profile-name")
                with Horizontal(id="profile-buttons"):
                    yield Button(tr("profile_load", self.language), id="btn-profile-load")
                    yield Button(tr("profile_save", self.language), id="btn-profile-save")

                yield Label(tr("source", self.language), classes="section")
                yield Label(tr("root_folder", self.language), classes="hint")
                yield Select(
                    [(tr("all_roots", self.language), "")],
                    value="",
                    allow_blank=False,
                    id="root-folder",
                )
                yield Label(tr("include_ext", self.language), classes="hint")
                yield Input(placeholder="cr2, dng", id="include-ext")
                yield Label(tr("exclude_ext", self.language), classes="hint")
                yield Input(placeholder="tif, jpg", id="exclude-ext")

                yield Label(tr("structure", self.language), classes="section")
                yield Select(
                    [(name, name) for name in PRESETS],
                    value="day",
                    allow_blank=False,
                    id="preset",
                )
                yield Label(tr("custom", self.language), classes="hint")
                yield Input(placeholder="{camera_slug}/{yyyy}-{mm}-{dd}", id="custom")
                yield Static("", id="preview")

                yield Label(tr("options", self.language), classes="section")
                yield Label(tr("placement", self.language), classes="hint")
                yield Select(
                    [(m, m) for m in PLACEMENT_MODES],
                    value="in-place",
                    allow_blank=False,
                    id="placement",
                )
                yield Label(tr("target_root", self.language), classes="hint")
                yield Input(placeholder="/path/to/new/tree", id="target-root")
                yield Label(tr("conflict", self.language), classes="hint")
                yield Select(
                    [(m, m) for m in CONFLICT_MODES],
                    value="rename",
                    allow_blank=False,
                    id="conflict",
                )
                yield Label(tr("missing", self.language), classes="hint")
                yield Select(
                    [(m, m) for m in MISSING_DATE_MODES],
                    value="unsorted",
                    allow_blank=False,
                    id="missing",
                )
                yield Label(tr("existing", self.language), classes="section")
                yield Label(tr("subfolder_action", self.language), classes="hint")
                yield Select(
                    [(a, a) for a in SUBFOLDER_ACTIONS],
                    value="consolidate",
                    allow_blank=False,
                    id="subfolder-action",
                )
                yield Label(tr("dated_action", self.language), classes="hint")
                yield Select(
                    [(a, a) for a in DATED_FOLDER_ACTIONS],
                    value="keep",
                    allow_blank=False,
                    id="dated-action",
                )
                yield Label(tr("mismatch_action", self.language), classes="hint")
                yield Select(
                    [(a, a) for a in MISMATCH_ACTIONS],
                    value="move-out",
                    allow_blank=False,
                    id="mismatch-action",
                )

                yield Label(tr("rules", self.language), classes="hint")
                yield Input(
                    placeholder="_extern=leave, dated+label=refile, *=sort-inside", id="rules"
                )

                yield Checkbox(tr("sidecars", self.language), value=True, id="sidecars")
                yield Checkbox(tr("backup", self.language), value=True, id="backup")
                yield Checkbox(tr("ascii", self.language), value=False, id="ascii")
                yield Checkbox(tr("cumulative", self.language), value=False, id="cumulative")
                yield Checkbox(tr("collect_orphans", self.language), value=False, id="orphans")
                yield Label(tr("orphan_folder", self.language), classes="hint")
                yield Input(value=Settings().orphan_folder, id="orphan-folder")

                with Vertical(id="actions"):
                    yield Button(tr("plan", self.language), id="btn-plan", variant="success")
                    yield Button(tr("apply", self.language), id="btn-apply", variant="warning")

            with Vertical(id="main"):
                yield Static(tr("no_catalog", self.language), id="catalog-info")
                yield ProgressBar(id="progress", show_eta=False)
                yield Static("", id="summary")
                yield Static("", id="findings")
                yield Label(tr("cycle_hint", self.language), classes="hint")
                yield DataTable(id="cases", zebra_stripes=True, cursor_type="row")
                yield DataTable(id="folders", zebra_stripes=True, cursor_type="row")
                yield RichLog(id="log", markup=True, wrap=True, highlight=False)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#folders", DataTable)
        table.add_columns(tr("folder", self.language), tr("files", self.language))
        cases = self.query_one("#cases", DataTable)
        cases.add_columns(
            tr("col_folder", self.language),
            tr("col_photos", self.language),
            tr("col_action", self.language),
        )
        self._attach_log_handler()
        self._update_preview()
        self.write_log(
            "[bold]{n}[/bold] {r} - build {d}".format(n=APP_NAME, r=REVISION, d=__build_date__)
        )
        if self.initial_catalog:
            self.action_load_catalog()

    def _fill_root_folders(self, roots) -> None:
        """Offer the catalog's own roots, so a run can be limited to one."""
        select = self.query_one("#root-folder", Select)
        options = [(tr("all_roots", self.language), "")]
        options += [(path.rstrip("/")[-46:], str(identifier)) for identifier, path in roots]
        select.set_options(options)
        select.value = ""

    def _attach_log_handler(self) -> None:
        handler = TuiLogHandler(self)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        logging.getLogger(LOGGER_NAME).addHandler(handler)
        self._handler = handler

    # -- helpers --------------------------------------------------------

    def write_log(self, message: str) -> None:
        try:
            self.query_one("#log", RichLog).write(message)
        except Exception:
            pass

    def _busy(self, active: bool, total: int = 0) -> None:
        bar = self.query_one("#progress", ProgressBar)
        bar.set_class(active, "active")
        if active:
            bar.update(total=total or 100, progress=0)

    def _current_structure(self):
        custom = self.query_one("#custom", Input).value.strip()
        if custom:
            return parse_structure(custom)
        preset = self.query_one("#preset", Select).value
        return PRESETS[str(preset)]

    def _update_preview(self) -> None:
        widget = self.query_one("#preview", Static)
        try:
            structure = self._current_structure()
        except RuleError as exc:
            widget.update("[red]{e}[/red]".format(e=exc))
            return
        preset = str(self.query_one("#preset", Select).value)
        note = ""
        if not self.query_one("#custom", Input).value.strip():
            en, de = PRESET_DESCRIPTIONS.get(preset, ("", ""))
            note = "\n[dim]{d}[/dim]".format(d=de if self.language == "de" else en)
        widget.update(
            "[bold]{p}[/bold]{n}".format(p=describe_structure(structure, self.language), n=note)
        )

    def _collect_settings(self) -> Settings:
        settings = Settings()
        settings.catalog = self.query_one("#catalog-path", Input).value.strip()
        settings.structure = self._current_structure()
        settings.placement = str(self.query_one("#placement", Select).value)
        target_root = self.query_one("#target-root", Input).value.strip()
        settings.target_root = target_root or None
        settings.conflict = str(self.query_one("#conflict", Select).value)
        settings.on_missing_date = str(self.query_one("#missing", Select).value)
        settings.subfolder_action = str(self.query_one("#subfolder-action", Select).value)
        settings.dated_folder_action = str(self.query_one("#dated-action", Select).value)
        settings.mismatch_action = str(self.query_one("#mismatch-action", Select).value)
        settings.folder_actions = dict(self.folder_overrides)
        settings.folder_rules = _split_rules(self.query_one("#rules", Input).value)
        settings.include_extensions = _split_list(self.query_one("#include-ext", Input).value)
        settings.exclude_extensions = _split_list(self.query_one("#exclude-ext", Input).value)
        root = str(self.query_one("#root-folder", Select).value or "")
        settings.root_folder_id = int(root) if root else None
        settings.cumulative_dates = self.query_one("#cumulative", Checkbox).value
        settings.collect_orphans = self.query_one("#orphans", Checkbox).value
        settings.orphan_folder = (
            self.query_one("#orphan-folder", Input).value.strip() or Settings().orphan_folder
        )
        settings.move_sidecars = self.query_one("#sidecars", Checkbox).value
        settings.backup_catalog = self.query_one("#backup", Checkbox).value
        settings.ascii_only = self.query_one("#ascii", Checkbox).value
        settings.language = self.language
        settings.__post_init__()
        settings.validate()
        return settings

    # -- events ---------------------------------------------------------

    @on(Select.Changed, "#preset")
    @on(Input.Changed, "#custom")
    def _structure_changed(self) -> None:
        self._update_preview()

    @on(Button.Pressed, "#btn-load")
    def _load_pressed(self) -> None:
        self.action_load_catalog()

    @on(Button.Pressed, "#btn-profile-save")
    def _profile_save_pressed(self) -> None:
        name = self.query_one("#profile-name", Input).value.strip()
        if not name:
            self.notify(tr("profile_needs_a_name", self.language), severity="warning")
            return
        try:
            path = self._collect_settings().save_profile(name)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            self.notify(str(exc), severity="error", timeout=10)
            return
        self.write_log(tr("profile_saved", self.language).format(n=name, p=path))

    @on(Button.Pressed, "#btn-profile-load")
    def _profile_load_pressed(self) -> None:
        name = self.query_one("#profile-name", Input).value.strip()
        if not name:
            self.notify(tr("profile_needs_a_name", self.language), severity="warning")
            return
        try:
            settings = Settings.load_profile(name)
        except ConfigError as exc:
            self.notify(str(exc), severity="error", timeout=10)
            return
        self._apply_settings(settings)
        self.write_log(tr("profile_loaded", self.language).format(n=name))

    def _apply_settings(self, settings: Settings) -> None:
        """Put a profile's options into the widgets.

        The catalog, the target and the rules stay as they are: a profile does
        not carry them, and overwriting what the operator set for *this*
        library would be the opposite of helpful.
        """
        self.query_one("#include-ext", Input).value = ", ".join(settings.include_extensions)
        self.query_one("#exclude-ext", Input).value = ", ".join(settings.exclude_extensions)
        self.query_one("#conflict", Select).value = settings.conflict
        self.query_one("#missing", Select).value = settings.on_missing_date
        self.query_one("#subfolder-action", Select).value = settings.subfolder_action
        self.query_one("#dated-action", Select).value = settings.dated_folder_action
        self.query_one("#mismatch-action", Select).value = settings.mismatch_action
        self.query_one("#placement", Select).value = settings.placement
        self.query_one("#sidecars", Checkbox).value = settings.move_sidecars
        self.query_one("#ascii", Checkbox).value = settings.ascii_only
        self.query_one("#cumulative", Checkbox).value = settings.cumulative_dates
        self.query_one("#orphans", Checkbox).value = settings.collect_orphans
        self.query_one("#orphan-folder", Input).value = settings.orphan_folder
        spec = "/".join(settings.structure)
        for name, preset in PRESETS.items():
            if tuple(preset) == tuple(settings.structure):
                self.query_one("#preset", Select).value = name
                self.query_one("#custom", Input).value = ""
                break
        else:
            self.query_one("#custom", Input).value = spec
        self._update_preview()

    @on(Button.Pressed, "#btn-plan")
    def _plan_pressed(self) -> None:
        self.action_plan()

    @on(Button.Pressed, "#btn-apply")
    def _apply_pressed(self) -> None:
        self.action_apply()

    # -- actions ---------------------------------------------------------

    def action_toggle_language(self) -> None:
        self.language = "de" if self.language == "en" else "en"
        self.notify("Language: {l}".format(l=self.language.upper()))
        self._update_preview()

    def action_load_catalog(self) -> None:
        path = self.query_one("#catalog-path", Input).value.strip()
        if not path:
            self.notify(tr("no_catalog", self.language), severity="warning")
            return
        self._busy(True)
        self.write_log(tr("loading", self.language))
        self._load_worker(path)

    def action_plan(self) -> None:
        try:
            settings = self._collect_settings()
        except Exception as exc:  # noqa: BLE001 - shown to the user
            self.notify(str(exc), severity="error", timeout=8)
            return
        self._busy(True)
        self.write_log(tr("planning", self.language))
        self._plan_worker(settings)

    def action_apply(self) -> None:
        if self.plan is None:
            self.notify(tr("no_plan", self.language), severity="warning")
            return
        plan = self.plan
        if not plan.has_work:
            self.notify("Nothing to do.", severity="warning")
            return

        def proceed(confirmed: Optional[bool]) -> None:
            if not confirmed:
                return
            self._busy(True, total=plan.stats.touched)
            self.write_log(tr("applying", self.language))
            self._apply_worker(plan)

        def after_preconditions(accepted: Optional[bool]) -> None:
            if not accepted:
                return
            self._acknowledged = plan.catalog_path
            self.push_screen(
                ConfirmScreen(
                    tr("confirm_title", self.language),
                    tr("confirm_body", self.language).format(n=plan.stats.touched),
                    tr("yes", self.language),
                    tr("no", self.language),
                ),
                proceed,
            )

        # What was actually found about the library, before anything is written.
        if self._acknowledged != plan.catalog_path:
            try:
                found = preconditions(Path(plan.catalog_path), plan.settings)
            except Exception as exc:  # noqa: BLE001 - shown to the user
                self.notify(str(exc), severity="error", timeout=10)
                return
            self.push_screen(PreconditionScreen(found, self.language), after_preconditions)
            return

        self.push_screen(
            ConfirmScreen(
                tr("confirm_title", self.language),
                tr("confirm_body", self.language).format(n=plan.stats.touched),
                tr("yes", self.language),
                tr("no", self.language),
            ),
            proceed,
        )

    def action_history(self) -> None:
        """The runs recorded beside this catalog, and a way to reverse one."""
        catalog = self.query_one("#catalog-path", Input).value.strip()
        if not catalog:
            self.notify(tr("no_catalog_yet", self.language), severity="warning")
            return
        records = history(Path(catalog))
        if not records:
            self.notify(tr("history_empty", self.language), severity="warning")
            return

        def chosen(journal: Optional[str]) -> None:
            if not journal:
                return
            self._confirm_undo(journal)

        self.push_screen(HistoryScreen(records, self.language), chosen)

    def _confirm_undo(self, journal: str) -> None:
        def proceed(confirmed: Optional[bool]) -> None:
            if not confirmed:
                return
            self._busy(True)
            self.write_log(tr("undoing", self.language))
            self._undo_worker(journal)

        self.push_screen(
            ConfirmScreen(
                tr("undo_title", self.language),
                tr("confirm_undo", self.language).format(j=journal),
                tr("yes", self.language),
                tr("no", self.language),
            ),
            proceed,
        )

    # -- workers -----------------------------------------------------------

    @work(thread=True, exclusive=True, group="catalog")
    def _load_worker(self, path: str) -> None:
        try:
            with open_catalog(path) as conn:
                reader = CatalogReader(conn)
                info = render_info(reader.info(), self.language)
                roots = [(r.id_local, r.absolute_path) for r in reader.root_folders()]
            self.call_from_thread(self.query_one("#catalog-info", Static).update, info)
            self.call_from_thread(self._fill_root_folders, roots)
            self.call_from_thread(self.notify, "Catalog loaded.")
        except (CatalogError, OSError) as exc:
            self.call_from_thread(self.notify, str(exc), severity="error", timeout=10)
            self.call_from_thread(self.write_log, "[red]{e}[/red]".format(e=exc))
        finally:
            self.call_from_thread(self._busy, False)

    @work(thread=True, exclusive=True, group="catalog")
    def _plan_worker(self, settings: Settings) -> None:
        try:
            settings.dry_run = True
            with open_catalog(
                settings.catalog,
                allow_unsupported=settings.allow_unsupported_catalog,
            ) as conn:
                plan = build_plan(CatalogReader(conn), settings)
            checks = preflight(plan)
            self.call_from_thread(self._show_plan, plan, checks)
        except (CatalogError, PlanError, RuleError, OSError) as exc:
            self.call_from_thread(self.notify, str(exc), severity="error", timeout=10)
            self.call_from_thread(self.write_log, "[red]{e}[/red]".format(e=exc))
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(self.write_log, "[red]{t}[/red]".format(t=traceback.format_exc()))
            self.call_from_thread(self.notify, str(exc), severity="error", timeout=10)
        finally:
            self.call_from_thread(self._busy, False)

    @work(thread=True, exclusive=True, group="catalog")
    def _undo_worker(self, journal: str) -> None:
        try:
            result = undo(journal)
            self.call_from_thread(self.write_log, render_result(result, self.language))
            self.call_from_thread(
                self.notify,
                tr("undo_done" if result.success else "undo_failed", self.language).format(
                    n=result.files_moved, e="; ".join(result.errors)
                ),
                severity="information" if result.success else "warning",
                timeout=10,
            )
            # The catalog on disk is a different file now; nothing planned
            # against the old one is still true.
            self.plan = None
        except (ExecutionError, CatalogError, OSError) as exc:
            self.call_from_thread(self.notify, str(exc), severity="error", timeout=12)
            self.call_from_thread(self.write_log, "[red]{e}[/red]".format(e=exc))
        finally:
            self.call_from_thread(self._busy, False)

    @work(thread=True, exclusive=True, group="catalog")
    def _apply_worker(self, plan: Plan) -> None:
        def progress(done: int, total: int, message: str) -> None:
            self.call_from_thread(
                self.query_one("#progress", ProgressBar).update, progress=done, total=total
            )

        try:
            settings = plan.settings
            settings.dry_run = False
            result = execute(plan, settings, progress=progress)
            self.call_from_thread(
                self.query_one("#summary", Static).update,
                render_result(result, self.language),
            )
            self.call_from_thread(
                self.notify,
                "Done: {n:,} file(s) moved.".format(n=result.files_moved),
                timeout=10,
            )
            self.plan = None
        except ExecutionError as exc:
            self.call_from_thread(self.notify, str(exc), severity="error", timeout=15)
            self.call_from_thread(self.write_log, "[red]{e}[/red]".format(e=exc))
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(self.write_log, "[red]{t}[/red]".format(t=traceback.format_exc()))
            self.call_from_thread(self.notify, str(exc), severity="error", timeout=15)
        finally:
            self.call_from_thread(self._busy, False)

    # -- rendering ---------------------------------------------------------

    def _show_plan(self, plan: Plan, checks) -> None:
        self.plan = plan
        stats = plan.stats
        lines = [
            "[bold]{s}[/bold]  ->  {e}".format(
                s="/".join(plan.settings.effective_structure),
                e=describe_structure(plan.settings.effective_structure, self.language),
            ),
            "move {m:,}   rename {r:,}   in place {p:,}   skipped {s:,}".format(
                m=stats.to_move,
                r=stats.to_rename,
                p=stats.already_in_place,
                s=stats.skipped_no_date
                + stats.skipped_conflict
                + stats.skipped_filtered
                + stats.missing_source,
            ),
            "new folders {f:,}   sidecars {c:,}   virtual copies {v:,}   {b}".format(
                f=stats.new_folders,
                c=stats.sidecars,
                v=stats.virtual_copies_carried,
                b=human_bytes(stats.bytes_to_move),
            ),
        ]
        for check in checks.checks:
            if check.level == "error":
                lines.append(
                    "[red]FAIL {n}: {m}[/red]".format(n=check.name, m=check.message(self.language))
                )
            elif check.level == "warning":
                lines.append(
                    "[yellow]warn {n}: {m}[/yellow]".format(
                        n=check.name, m=check.message(self.language)
                    )
                )
        self.query_one("#summary", Static).update("\n".join(lines))

        # What the plan could not decide alone, each with the option that
        # governs it -- the same list the window shows in its own table.
        colours = {"error": "red", "warning": "yellow", "exception": "cyan", "note": "dim"}
        found = []
        for finding in collect_findings(plan, checks):
            head = "[{c}]{lvl}[/{c}]".format(
                c=colours.get(finding.level, "white"), lvl=finding.level.upper()
            )
            count = " {n:,}".format(n=finding.count) if finding.count else ""
            setting = ""
            if finding.setting:
                setting = "   [dim]{s}{v}[/dim]".format(
                    s=finding.setting,
                    v=" = " + finding.current(self.language)
                    if finding.current(self.language)
                    else "",
                )
            found.append(
                "{h}{c} {t}{s}".format(h=head, c=count, t=finding.text(self.language), s=setting)
            )
        self.query_one("#findings", Static).update(
            "\n".join(found) if found else tr("findings_none", self.language)
        )

        cases_table = self.query_one("#cases", DataTable)
        cases_table.clear()
        self._case_rows = []
        for case in plan.folder_cases:
            if not case.photo_count:
                continue
            decision = "-" if case.is_anchor else action_label(case.action, self.language)
            if case.is_dated and case.mismatched_photos:
                decision += " (+{n})".format(n=case.mismatched_photos)
            cases_table.add_row(
                (case.path_from_root or ".")[:40],
                "{n:,}".format(n=case.photo_count),
                decision,
            )
            self._case_rows.append(case)

        table = self.query_one("#folders", DataTable)
        table.clear()
        for name, count in plan.folder_summary():
            table.add_row(name, "{c:,}".format(c=count))
        self.notify(
            "Plan ready: {n:,} file(s), {f:,} folder(s).".format(
                n=stats.touched, f=stats.new_folders
            )
        )

    @on(DataTable.RowSelected, "#cases")
    def _cycle_folder_decision(self, event: DataTable.RowSelected) -> None:
        """Step one folder through its allowed decisions, then re-plan."""
        rows = getattr(self, "_case_rows", [])
        if not 0 <= event.cursor_row < len(rows):
            return
        case = rows[event.cursor_row]
        if case.is_anchor:
            self.notify(
                "Der Ankerordner steht nicht zur Wahl."
                if self.language == "de"
                else "The anchor folder is not up for a decision.",
                severity="warning",
            )
            return
        choices = DATED_FOLDER_ACTIONS if case.is_dated else SUBFOLDER_ACTIONS
        current = self.folder_overrides.get(case.folder_id, case.action)
        index = choices.index(current) if current in choices else 0
        chosen = choices[(index + 1) % len(choices)]
        self.folder_overrides[case.folder_id] = chosen
        self.notify(
            "{p}: {a}".format(p=case.path_from_root or ".", a=action_label(chosen, self.language))
        )
        self.action_plan()

    def on_unmount(self) -> None:
        if self._handler is not None:
            logging.getLogger(LOGGER_NAME).removeHandler(self._handler)


def run_tui(catalog: str = "", language: str = "en", debug: bool = False) -> int:
    """Entry point used by ``lrfc tui``."""
    setup_logging(debug=debug, quiet=True, tag="tui")
    app = LRFolderCraftApp(catalog=catalog, language=language, debug=debug)
    app.run()
    return 0
