"""Rendering of catalog info, plans and run results.

Everything here is pure formatting with no third party requirement, so the
CLI stays usable on a bare Python installation. Text output is bilingual:
pass ``language="de"`` for German.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from .catalog.model import CatalogInfo
from .executor import RunResult
from .folders import label as action_label
from .folders import summarise
from .planner import STATUS_LABELS, Plan
from .rules import describe_structure, token_help
from .safety import PreflightResult
from .version import REVISION, long_banner

T = {
    "catalog": ("Catalog", "Katalog"),
    "schema": ("Schema version", "Schemaversion"),
    "root_folders": ("Root folders", "Stammordner"),
    "folders": ("Folders", "Ordner"),
    "files": ("Files", "Dateien"),
    "images": ("Images (incl. virtual copies)", "Bilder (inkl. virtueller Kopien)"),
    "vcopies": ("Virtual copies", "Virtuelle Kopien"),
    "no_date": ("Without capture date", "Ohne Aufnahmedatum"),
    "span": ("Capture range", "Aufnahmezeitraum"),
    "cameras": ("Cameras", "Kameras"),
    "formats": ("File formats", "Dateiformate"),
    "plan": ("PLAN", "PLAN"),
    "structure": ("Structure", "Struktur"),
    "example": ("Example", "Beispiel"),
    "placement": ("Placement", "Platzierung"),
    "target_root": ("Target root", "Zielwurzel"),
    "anchor": ("Anchor folder", "Ankerordner"),
    "summary": ("Summary", "Zusammenfassung"),
    "to_move": ("To be moved", "Zu verschieben"),
    "to_rename": ("Moved and renamed", "Verschoben und umbenannt"),
    "in_place": ("Already in place", "Bereits am Ziel"),
    "skipped": ("Skipped", "Uebersprungen"),
    "new_folders": ("New folders", "Neue Ordner"),
    "sidecars": ("Sidecar files", "Sidecar-Dateien"),
    "carried_vc": ("Virtual copies carried along", "Mitgefuehrte virtuelle Kopien"),
    "volume": ("Data volume", "Datenvolumen"),
    "warnings": ("Warnings", "Warnungen"),
    "target_folders": ("Target folders", "Zielordner"),
    "sample": ("Sample moves", "Beispielhafte Verschiebungen"),
    "preflight": ("PRE-FLIGHT CHECKS", "VORPRUEFUNGEN"),
    "result": ("RESULT", "ERGEBNIS"),
    "dry_run": ("Dry run -- nothing was changed", "Trockenlauf -- nichts wurde geaendert"),
    "moved": ("Files moved", "Verschobene Dateien"),
    "renamed": ("Files renamed", "Umbenannte Dateien"),
    "created": ("Folders created", "Angelegte Ordner"),
    "pruned": ("Empty folders removed", "Entfernte leere Ordner"),
    "backup": ("Catalog backup", "Katalog-Backup"),
    "journal": ("Journal", "Journal"),
    "verification": ("Verification", "Pruefung"),
    "passed": ("passed", "bestanden"),
    "errors": ("Errors", "Fehler"),
    "rolled_back": ("Rolled back", "Zurueckgesetzt"),
    "tokens": ("TEMPLATE TOKENS", "TEMPLATE-PLATZHALTER"),
    "presets": ("PRESETS", "VORLAGEN"),
    "duration": ("Duration", "Dauer"),
    "more": ("more", "weitere"),
    "folders_found": ("EXISTING FOLDERS", "VORGEFUNDENE ORDNER"),
    "decision": ("decision", "Entscheidung"),
    "from_default": ("default", "Vorgabe"),
    "from_override": ("set explicitly", "ausdruecklich gesetzt"),
    "from_operator": ("chosen by you", "von Ihnen gewaehlt"),
    "anchor_folder": ("the run's anchor", "Ankerordner des Laufs"),
    "scopes": ("ROOT FOLDERS", "STAMMORDNER"),
}


def t(key: str, language: str) -> str:
    en, de = T[key]
    return de if language == "de" else en


def _rule(char: str = "-", width: int = 78) -> str:
    return char * width


def human_bytes(count: int) -> str:
    value = float(count)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            if unit == "B":
                return "{v:.0f} B".format(v=value)
            return "{v:.1f} {u}".format(v=value, u=unit)
        value /= 1024
    return "{v:.1f} TiB".format(v=value)


# ---------------------------------------------------------------------------
# Catalog info
# ---------------------------------------------------------------------------


def render_info(info: CatalogInfo, language: str = "en") -> str:
    lines = [long_banner(), _rule("="), ""]
    rows: List[Tuple[str, str]] = [
        (t("catalog", language), info.path),
        (t("schema", language), str(info.schema_version or "?")),
        (t("root_folders", language), str(info.root_folders)),
        (t("folders", language), str(info.folders)),
        (t("files", language), "{n:,}".format(n=info.files)),
        (t("images", language), "{n:,}".format(n=info.images)),
        (t("vcopies", language), "{n:,}".format(n=info.virtual_copies)),
        (t("no_date", language), "{n:,}".format(n=info.missing_capture_time)),
        (
            t("span", language),
            "{a} .. {b}".format(a=info.earliest_capture or "?", b=info.latest_capture or "?"),
        ),
    ]
    lines.extend(_kv_block(rows))
    if info.cameras:
        lines.append("")
        lines.append(t("cameras", language) + ":")
        for name, count in info.cameras:
            lines.append("  {n:<40} {c:>8,}".format(n=name[:40], c=count))
    if info.file_formats:
        lines.append("")
        lines.append(t("formats", language) + ":")
        for name, count in info.file_formats:
            lines.append("  {n:<40} {c:>8,}".format(n=name[:40], c=count))
    return "\n".join(lines)


def _kv_block(rows: Sequence[Tuple[str, str]]) -> List[str]:
    width = max((len(k) for k, _ in rows), default=0)
    return ["  {k:<{w}} : {v}".format(k=k, w=width, v=v) for k, v in rows]


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def render_plan(
    plan: Plan,
    language: str = "en",
    max_folders: int = 25,
    max_samples: int = 10,
    show_all: bool = False,
) -> str:
    stats = plan.stats
    lines = [
        long_banner(),
        _rule("="),
        "{h}  ({r})".format(h=t("plan", language), r=REVISION),
        _rule("="),
        "",
    ]
    lines.extend(
        _kv_block(
            [
                (t("catalog", language), plan.catalog_path),
                (t("structure", language), "/".join(plan.settings.structure)),
                (t("example", language), describe_structure(plan.settings.structure, language)),
                (t("placement", language), plan.placement),
                (t("target_root", language), plan.scopes[0].target_root_path),
                (
                    t("anchor", language),
                    "/".join(plan.scopes[0].anchor_segments) or "(root)",
                ),
            ]
        )
    )
    if len(plan.scopes) > 1:
        lines += ["", t("scopes", language) + ":"]
        for index, scope in enumerate(plan.scopes):
            lines.append("  [{i}] {r}".format(i=index, r=scope.root_folder.absolute_path))
            lines.append(
                "      {a} {p}".format(
                    a=t("anchor", language),
                    p="/".join(scope.anchor_segments) or "(root)",
                )
            )

    lines += ["", t("summary", language) + ":"]
    lines.extend(
        _kv_block(
            [
                (t("to_move", language), "{n:,}".format(n=stats.to_move)),
                (t("to_rename", language), "{n:,}".format(n=stats.to_rename)),
                (t("in_place", language), "{n:,}".format(n=stats.already_in_place)),
                (
                    t("skipped", language),
                    "{n:,}".format(
                        n=stats.skipped_no_date
                        + stats.skipped_conflict
                        + stats.skipped_filtered
                        + stats.missing_source
                    ),
                ),
                (t("new_folders", language), "{n:,}".format(n=stats.new_folders)),
                (t("sidecars", language), "{n:,}".format(n=stats.sidecars)),
                (t("carried_vc", language), "{n:,}".format(n=stats.virtual_copies_carried)),
                (t("volume", language), human_bytes(stats.bytes_to_move)),
            ]
        )
    )

    breakdown = _status_breakdown(plan)
    if breakdown:
        lines.append("")
        for status, count in breakdown:
            label_en, label_de = STATUS_LABELS.get(status, (status, status))
            lines.append(
                "  {c:>8,}  {l}".format(c=count, l=label_de if language == "de" else label_en)
            )

    if plan.warnings:
        lines += ["", t("warnings", language) + ":"]
        for warning in plan.warnings:
            lines.append("  ! " + warning)

    folders = plan.folder_summary()
    if folders:
        lines += ["", "{h} ({n}):".format(h=t("target_folders", language), n=len(folders))]
        shown = folders if show_all else folders[:max_folders]
        for name, count in shown:
            lines.append("  {n:<52} {c:>7,}".format(n=name[:52], c=count))
        if len(folders) > len(shown):
            lines.append("  ... {n} {m}".format(n=len(folders) - len(shown), m=t("more", language)))

    cases = [c for c in plan.folder_cases if c.photo_count]
    if cases:
        lines += ["", "{h} ({n}):".format(h=t("folders_found", language), n=len(cases))]
        source = {
            "default": t("from_default", language),
            "override": t("from_override", language),
            "operator": t("from_operator", language),
        }
        for case in cases:
            if case.is_anchor:
                detail = t("anchor_folder", language)
            else:
                detail = "{a} ({s})".format(
                    a=action_label(case.action, language),
                    s=source.get(case.action_source, case.action_source),
                )
            extra = ""
            if case.is_dated and case.mismatched_photos:
                extra = (
                    ", {n} mit abweichendem Datum"
                    if language == "de"
                    else ", {n} with a different date"
                ).format(n=case.mismatched_photos)
            lines.append(
                "  {p:<34} {n:>5}{e}".format(
                    p=(case.path_from_root or ".")[:34], n=case.photo_count, e=extra
                )
            )
            lines.append("      {d}".format(d=detail))
        for line in summarise(cases, language):
            lines.append("  = " + line)

    samples = plan.active_moves
    if samples and not show_all:
        lines += ["", t("sample", language) + ":"]
        for move in samples[:max_samples]:
            lines.append("  {s}".format(s=move.source_path))
            lines.append("    -> {t}".format(t=move.target_path))
    return "\n".join(lines)


def _status_breakdown(plan: Plan) -> List[Tuple[str, int]]:
    counts: Dict[str, int] = {}
    for move in plan.moves:
        counts[move.status] = counts.get(move.status, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])


def plan_to_dict(plan: Plan) -> Dict[str, Any]:
    """Full machine readable representation of a plan."""
    return {
        "tool": {"revision": REVISION},
        "catalog": plan.catalog_path,
        "created_at": plan.created_at,
        "settings": plan.settings.to_dict(),
        "scopes": [
            {
                "root_id": sc.root_folder.id_local,
                "root_name": sc.root_folder.name,
                "root_path": sc.root_folder.absolute_path,
                "anchor": list(sc.anchor_segments),
                "target_root": sc.target_root_path,
                "cross_volume": sc.cross_volume,
            }
            for sc in plan.scopes
        ],
        "placement": plan.placement,
        "target_root": plan.target_root_path,
        "anchor": list(plan.anchor_segments),
        "stats": asdict(plan.stats),
        "warnings": list(plan.warnings),
        "new_folders": [
            {"scope": index, "path": "/".join(segments)} for index, segments in plan.new_folders
        ],
        "folders": [
            {
                "id": c.folder_id,
                "path": c.path_from_root,
                "kind": c.kind,
                "photos": c.photo_count,
                "matching": c.matching_photos,
                "mismatched": c.mismatched_photos,
                "action": c.action,
                "action_source": c.action_source,
                "is_anchor": c.is_anchor,
            }
            for c in plan.folder_cases
        ],
        "moves": [
            {
                "file_id": m.file_id,
                "status": m.status,
                "reason": m.reason,
                "source": m.source_path,
                "target": m.target_path,
                "target_folder": "/".join(m.target_segments),
                "renamed_to": m.target_filename if m.renamed else None,
                "sidecars": [{"source": s, "target": d} for s, d in m.sidecars],
                "virtual_copies": m.virtual_copy_count,
                "capture_time": m.capture_time,
                "camera": m.camera,
                "size_bytes": m.size_bytes,
                "scope": m.scope,
            }
            for m in plan.moves
        ],
    }


def render_plan_json(plan: Plan) -> str:
    return json.dumps(plan_to_dict(plan), indent=2, ensure_ascii=False)


def render_plan_csv(plan: Plan) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "file_id",
            "status",
            "reason",
            "source",
            "target",
            "target_folder",
            "renamed_to",
            "virtual_copies",
            "capture_time",
            "camera",
            "size_bytes",
        ]
    )
    for m in plan.moves:
        writer.writerow(
            [
                m.file_id,
                m.status,
                m.reason,
                m.source_path,
                m.target_path,
                "/".join(m.target_segments),
                m.target_filename if m.renamed else "",
                m.virtual_copy_count,
                m.capture_time or "",
                m.camera or "",
                m.size_bytes,
            ]
        )
    return buffer.getvalue()


def write_plan_files(plan: Plan, directory: Path, stem: str) -> List[Path]:
    """Write ``<stem>.json`` and ``<stem>.csv`` into *directory*."""
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "{s}.json".format(s=stem)
    csv_path = directory / "{s}.csv".format(s=stem)
    json_path.write_text(render_plan_json(plan), encoding="utf-8")
    csv_path.write_text(render_plan_csv(plan), encoding="utf-8")
    return [json_path, csv_path]


# ---------------------------------------------------------------------------
# Pre-flight and results
# ---------------------------------------------------------------------------


def render_preflight(checks: PreflightResult, language: str = "en") -> str:
    lines = [t("preflight", language), _rule()]
    symbols = {"ok": "[ ok ]", "warning": "[warn]", "error": "[FAIL]"}
    for check in checks.checks:
        lines.append(
            "{s} {n:<22} {m}".format(
                s=symbols.get(check.level, "[ ?? ]"),
                n=check.name,
                m=check.message(language),
            )
        )
    return "\n".join(lines)


def render_result(result: RunResult, language: str = "en") -> str:
    lines = [t("result", language), _rule("=")]
    if result.dry_run:
        lines.append(t("dry_run", language))
    rows: List[Tuple[str, str]] = [
        (t("catalog", language), result.catalog),
        (t("moved", language), "{n:,}".format(n=result.files_moved)),
        (t("renamed", language), "{n:,}".format(n=result.files_renamed)),
        (t("sidecars", language), "{n:,}".format(n=result.sidecars_moved)),
        (t("created", language), "{n:,}".format(n=result.folders_created)),
        (t("pruned", language), "{n:,}".format(n=result.folders_pruned)),
        (t("volume", language), human_bytes(result.bytes_moved)),
    ]
    if result.backup_path:
        rows.append((t("backup", language), result.backup_path))
    if result.journal_path:
        rows.append((t("journal", language), result.journal_path))
    rows.append(
        (
            t("verification", language),
            t("passed", language)
            if not result.verification
            else "{n} problem(s)".format(n=len(result.verification)),
        )
    )
    if result.rolled_back:
        rows.append((t("rolled_back", language), "yes"))
    lines.extend(_kv_block(rows))
    if result.verification:
        lines += ["", t("verification", language) + ":"]
        lines += ["  ! " + p for p in result.verification]
    if result.errors:
        lines += ["", t("errors", language) + ":"]
        lines += ["  ! " + e for e in result.errors]
    return "\n".join(lines)


def result_to_dict(result: RunResult) -> Dict[str, Any]:
    return asdict(result)


# ---------------------------------------------------------------------------
# Help surfaces
# ---------------------------------------------------------------------------


def render_tokens(language: str = "en") -> str:
    lines = [t("tokens", language), _rule()]
    for token, example, description in token_help(language):
        lines.append("  {t:<16} {e:<32} {d}".format(t=token, e=example[:32], d=description))
    return "\n".join(lines)


def render_presets(language: str = "en") -> str:
    from .rules import PRESET_DESCRIPTIONS, PRESETS

    lines = [t("presets", language), _rule()]
    for name in PRESETS:
        en, de = PRESET_DESCRIPTIONS.get(name, (name, name))
        lines.append(
            "  {n:<24} {e:<28} {d}".format(
                n=name,
                e=describe_structure(PRESETS[name], language),
                d=de if language == "de" else en,
            )
        )
    return "\n".join(lines)
