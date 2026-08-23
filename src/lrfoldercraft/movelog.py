"""A human readable record of one run, written beside the library.

The journal in the backup directory exists so a failed run can be undone; it is
machine readable and lives where a user will never look. This is the other
half: a plain text list of what moved where, named after the tool, the date and
the catalog, and left next to the ``.lrcat`` file so that it is found months
later by whoever wonders where a photo went.

Writing it must never cost a run. A full disk, a read-only volume or a catalog
on a share the user cannot write to are all reasons to skip the log and say so,
never to fail a migration that has already succeeded.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .logging_setup import get_logger
from .version import APP_NAME, __build_date__, __version__

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .config import Settings
    from .executor import RunResult
    from .planner import Plan

log = get_logger("movelog")

#: Written beside the catalog, so it sorts by date next to its siblings.
NAME_TEMPLATE = "{app}_{stamp}_{catalog}.log"


def move_log_path(catalog: Path, when: datetime, directory: Optional[Path] = None) -> Path:
    """Where the record for a run against *catalog* belongs."""
    return (directory or catalog.parent) / NAME_TEMPLATE.format(
        app=APP_NAME.replace(" ", "-"),
        stamp=when.strftime("%Y-%m-%d_%H%M%S"),
        catalog=catalog.stem,
    )


def write_move_log(
    plan: Plan,
    result: RunResult,
    settings: Settings,
    when: Optional[datetime] = None,
) -> Optional[Path]:
    """Write the record and return its path, or ``None`` if it could not be written."""
    if not settings.move_log:
        return None
    catalog = Path(plan.catalog_path)
    directory = Path(settings.move_log_dir) if settings.move_log_dir else None
    path = move_log_path(catalog, when or datetime.now(), directory)
    try:
        path.write_text(render_move_log(plan, result, settings), encoding="utf-8")
    except OSError as error:
        # The run is already done and verified. Losing its record is a
        # disappointment, not a failure.
        log.warning("Could not write the move log to %s: %s", path, error)
        result.notes.append("move log could not be written to {p}: {e}".format(p=path, e=error))
        return None
    log.info("Move log written to %s", path)
    return path


def render_move_log(plan: Plan, result: RunResult, settings: Settings) -> str:
    """The record's text, in the language the run was made in."""
    german = settings.language == "de"
    lines = [
        "{app} {v} (Build {b})".format(app=APP_NAME, v=__version__, b=__build_date__),
        "=" * 72,
        "",
        _pair("Katalog" if german else "Catalog", plan.catalog_path),
        _pair("Begonnen" if german else "Started", result.started_at),
        _pair("Beendet" if german else "Finished", result.finished_at),
        _pair("Ergebnis" if german else "Outcome", _outcome(result, german)),
        _pair("Struktur" if german else "Structure", "/".join(settings.structure)),
        _pair("Platzierung" if german else "Placement", settings.placement),
    ]
    if settings.folder_rules:
        lines.append(_pair("Regeln" if german else "Rules", "").rstrip())
        for position, rule in enumerate(settings.folder_rules, start=1):
            lines.append("    {n}. {r}".format(n=position, r=rule))
    for scope in plan.scopes:
        lines.append(_pair("Zielwurzel" if german else "Target root", scope.target_root_path))
    if result.backup_path:
        lines.append(_pair("Katalogsicherung" if german else "Catalog backup", result.backup_path))
    if result.journal_path:
        lines.append(_pair("Journal", result.journal_path))

    lines += ["", "-" * 72, ""]
    lines.append("VERSCHOBENE DATEIEN" if german else "MOVED FILES")
    lines.append("")
    moved = [m for m in plan.moves if m.is_active]
    if not moved:
        lines.append("    (keine)" if german else "    (none)")
    for move in moved:
        lines.append("    {s}".format(s=move.source_path))
        lines.append("      -> {t}".format(t=move.target_path))
        for source, target in move.sidecars:
            lines.append("      -> {t}  ({w})".format(t=target, w=Path(source).suffix.lstrip(".")))

    lines += ["", "-" * 72, ""]
    lines.append("ZUSAMMENFASSUNG" if german else "SUMMARY")
    lines.append("")
    for label, value in _summary(result, german):
        lines.append("    {la:<28}{v}".format(la=label, v=value))

    if result.errors:
        lines += ["", "FEHLER" if german else "ERRORS", ""]
        lines += ["    " + error for error in result.errors]
    if result.notes:
        lines += ["", "HINWEISE" if german else "NOTES", ""]
        lines += ["    " + note for note in result.notes]
    if result.verification:
        lines += ["", "PRUEFUNG" if german else "VERIFICATION", ""]
        lines += ["    " + line for line in result.verification]

    lines.append("")
    return "\n".join(lines)


def _pair(label: str, value: str) -> str:
    return "{la:<20}{v}".format(la=label + ":", v=value)


def _outcome(result: RunResult, german: bool) -> str:
    if result.rolled_back:
        return "zurückgerollt" if german else "rolled back"
    if result.success:
        return "erfolgreich" if german else "success"
    return "fehlgeschlagen" if german else "failed"


def _summary(result: RunResult, german: bool):
    labels = (
        ("Verschobene Dateien" if german else "Files moved", result.files_moved),
        ("Umbenannt" if german else "Renamed", result.files_renamed),
        ("Beidateien" if german else "Sidecars", result.sidecars_moved),
        ("Neue Ordner" if german else "Folders created", result.folders_created),
        ("Entfernte Ordner" if german else "Folders pruned", result.folders_pruned),
        ("Datenvolumen (Bytes)" if german else "Bytes moved", result.bytes_moved),
    )
    return [(label, "{v:,}".format(v=value)) for label, value in labels]
