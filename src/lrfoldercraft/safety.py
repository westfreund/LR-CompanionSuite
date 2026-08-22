"""Pre-flight checks run before anything is written.

Every check returns a :class:`Check`. A single ``level="error"`` result stops
the run; warnings are reported and require confirmation in interactive front
ends. The checks are deliberately cheap so they can also be shown live in the
TUI while the user is still assembling a run.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .catalog.db import is_locked, lock_file_for, sidecar_paths
from .logging_setup import get_logger, step
from .planner import Plan

log = get_logger("safety")

OK = "ok"
WARNING = "warning"
ERROR = "error"


@dataclass
class Check:
    """Outcome of one pre-flight check, in both project languages."""

    name: str
    level: str
    message_en: str
    message_de: str

    def message(self, language: str = "en") -> str:
        return self.message_de if language == "de" else self.message_en

    @property
    def failed(self) -> bool:
        return self.level == ERROR


@dataclass
class PreflightResult:
    checks: List[Check]

    @property
    def ok(self) -> bool:
        return not any(c.failed for c in self.checks)

    @property
    def errors(self) -> List[Check]:
        return [c for c in self.checks if c.level == ERROR]

    @property
    def warnings(self) -> List[Check]:
        return [c for c in self.checks if c.level == WARNING]


def preflight(plan: Plan) -> PreflightResult:
    """Run every check relevant for *plan* and return the collected results."""
    step("Running pre-flight checks")
    checks: List[Check] = []
    catalog = Path(plan.catalog_path)

    checks.append(_check_lock(catalog))
    checks.append(_check_catalog_writable(catalog))
    checks.append(_check_side_files(catalog))
    checks.append(_check_id_counter_type(catalog))
    checks.append(_check_target_writable(plan))
    checks.append(_check_free_space(plan))
    checks.append(_check_backup_space(plan, catalog))
    checks.append(_check_work_present(plan))
    missing = _check_missing_sources(plan)
    if missing is not None:
        checks.append(missing)

    result = PreflightResult(checks=checks)
    for check in checks:
        logger = (
            log.error
            if check.level == ERROR
            else (log.warning if check.level == WARNING else log.info)
        )
        logger("Pre-flight [%s] %s: %s", check.level.upper(), check.name, check.message_en)
    return result


def _check_lock(catalog: Path) -> Check:
    if is_locked(catalog):
        return Check(
            "lightroom-closed",
            ERROR,
            "Lightroom has the catalog open ({f} exists). Quit Lightroom Classic first.".format(
                f=lock_file_for(catalog).name
            ),
            "Lightroom hat den Katalog geoeffnet ({f} vorhanden). Bitte "
            "Lightroom Classic zuerst beenden.".format(f=lock_file_for(catalog).name),
        )
    return Check(
        "lightroom-closed",
        OK,
        "No Lightroom lock file -- the catalog is free.",
        "Keine Lightroom-Sperrdatei -- der Katalog ist frei.",
    )


def _check_catalog_writable(catalog: Path) -> Check:
    if not catalog.exists():
        return Check(
            "catalog-writable",
            ERROR,
            "Catalog does not exist: {p}".format(p=catalog),
            "Katalog existiert nicht: {p}".format(p=catalog),
        )
    if not os.access(str(catalog), os.W_OK):
        return Check(
            "catalog-writable",
            ERROR,
            "No write permission for the catalog file.",
            "Keine Schreibrechte fuer die Katalogdatei.",
        )
    return Check(
        "catalog-writable",
        OK,
        "Catalog is writable.",
        "Katalog ist beschreibbar.",
    )


def _check_side_files(catalog: Path) -> Check:
    """Report on ``-wal`` / ``-shm`` / ``-journal`` without inviting damage.

    Lightroom catalogs run in **WAL mode**, so ``<catalog>.lrcat-wal`` and
    ``-shm`` are entirely normal working files, not leftovers. Deleting a
    non-empty write-ahead log throws away committed transactions -- an earlier
    revision of this check called them "stale" and suggested clearing them,
    which was wrong and dangerous. A ``-journal`` file is different: it means a
    rollback-journal transaction was interrupted.
    """
    journal = [p for p in sidecar_paths(catalog) if p.name.endswith("-journal")]
    if journal:
        return Check(
            "catalog-side-files",
            WARNING,
            "{n} exists -- a transaction was interrupted. Open and close the "
            "catalog in Lightroom once so it can recover. Do not delete the "
            "file.".format(n=journal[0].name),
            "{n} ist vorhanden -- eine Transaktion wurde unterbrochen. Katalog "
            "einmal in Lightroom oeffnen und schliessen, damit er sich erholt. "
            "Die Datei nicht loeschen.".format(n=journal[0].name),
        )

    wal = [p for p in sidecar_paths(catalog) if p.name.endswith("-wal")]
    pending = sum(p.stat().st_size for p in wal)
    if pending:
        return Check(
            "catalog-side-files",
            OK,
            "Write-ahead log holds {n:,} byte(s) the catalog depends on. It is "
            "checkpointed into the catalog after the run. Never delete "
            "it.".format(n=pending),
            "Das Write-Ahead-Log enthaelt {n:,} Byte, auf die der Katalog "
            "angewiesen ist. Es wird nach dem Lauf in den Katalog "
            "uebernommen. Niemals loeschen.".format(n=pending),
        )
    return Check(
        "catalog-side-files",
        OK,
        "No interrupted transaction; the write-ahead log is empty.",
        "Keine unterbrochene Transaktion; das Write-Ahead-Log ist leer.",
    )


def _check_id_counter_type(catalog: Path) -> Check:
    """Detect an id counter whose SQLite storage class was changed to TEXT.

    Lightroom stores ``Adobe_entityIDCounter`` as a REAL. Revisions 1.0.0 to
    1.0.4 of this tool wrote it back as a string, which reads identically,
    passes every integrity check, survives Lightroom's own catalog repair --
    and makes Lightroom refuse to open the catalog, repairing it into a
    byte-identical file forever. A catalog in that state is already broken
    before this tool touches it again, so say so.
    """
    try:
        connection = sqlite3.connect("file:{p}?mode=ro&immutable=1".format(p=catalog), uri=True)
        row = connection.execute(
            "SELECT typeof(value) FROM Adobe_variablesTable WHERE name = 'Adobe_entityIDCounter'"
        ).fetchone()
        connection.close()
    except sqlite3.Error as exc:  # pragma: no cover - reported by other checks
        return Check(
            "id-counter-type",
            OK,
            "Could not read the id counter ({e}).".format(e=exc),
            "ID-Zaehler nicht lesbar ({e}).".format(e=exc),
        )

    if row is None or row[0] in ("real", "integer"):
        return Check(
            "id-counter-type",
            OK,
            "Id counter has Lightroom's numeric storage class.",
            "ID-Zaehler hat Lightrooms numerische Speicherklasse.",
        )

    repair = (
        "UPDATE Adobe_variablesTable SET value = CAST(value AS REAL) "
        "WHERE name = 'Adobe_entityIDCounter';"
    )
    return Check(
        "id-counter-type",
        WARNING,
        "Adobe_entityIDCounter is stored as {t}, not a number. Lightroom will "
        "refuse to open this catalog. It was damaged by LR-FolderCraft 1.0.0 "
        "to 1.0.4. Repair it with: {sql}".format(t=row[0], sql=repair),
        "Adobe_entityIDCounter ist als {t} gespeichert, nicht als Zahl. "
        "Lightroom wird diesen Katalog nicht oeffnen. Beschaedigt durch "
        "LR-FolderCraft 1.0.0 bis 1.0.4. Reparatur: {sql}".format(t=row[0], sql=repair),
    )


def _existing_ancestor(path: Path) -> Path:
    """Nearest existing folder at or above *path*."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


def _check_target_writable(plan: Plan) -> Check:
    """Every scope's target must be writable, or creatable below one that is."""
    to_create = []
    for scope in plan.scopes:
        root = Path(scope.target_root_path)
        probe = _existing_ancestor(root)
        if not probe.exists():
            return Check(
                "target-writable",
                ERROR,
                "Target location {p} does not exist and cannot be created.".format(p=root),
                "Zielort {p} existiert nicht und kann nicht angelegt werden.".format(p=root),
            )
        if not os.access(str(probe), os.W_OK):
            return Check(
                "target-writable",
                ERROR,
                "No write permission for {p}.".format(p=probe),
                "Keine Schreibrechte fuer {p}.".format(p=probe),
            )
        if probe != root:
            to_create.append((root, probe))
    if to_create:
        root, probe = to_create[0]
        more = " (+{n} more)".format(n=len(to_create) - 1) if len(to_create) > 1 else ""
        return Check(
            "target-writable",
            OK,
            "Target {r} does not exist yet and will be created below {p}.{m}".format(
                r=root, p=probe, m=more
            ),
            "Ziel {r} existiert noch nicht und wird unterhalb von {p} angelegt.{m}".format(
                r=root, p=probe, m=more
            ),
        )
    return Check(
        "target-writable",
        OK,
        "{n} target location(s) exist and are writable.".format(n=len(plan.scopes)),
        "{n} Zielort(e) vorhanden und beschreibbar.".format(n=len(plan.scopes)),
    )


def _check_free_space(plan: Plan) -> Check:
    """Free space only matters where files cross a volume boundary.

    Summed per target volume: two scopes may copy onto the same drive, and each
    checking on its own would not notice that together they do not fit.
    """
    needed: Dict[str, int] = {}
    for move in plan.active_moves:
        if not move.cross_volume:
            continue
        target = str(_existing_ancestor(Path(plan.scopes[move.scope].target_root_path)))
        needed[target] = needed.get(target, 0) + move.size_bytes
    if not needed:
        return Check(
            "free-space",
            OK,
            "Same-volume move -- no additional space required.",
            "Verschieben auf demselben Volume -- kein zusaetzlicher Platz noetig.",
        )
    for target, size in sorted(needed.items()):
        free = shutil.disk_usage(target).free
        margin = int(size * 1.05)
        if free < margin:
            return Check(
                "free-space",
                ERROR,
                "Need about {n:.1f} GiB on {t}, only {f:.1f} GiB free.".format(
                    n=margin / 1024**3, t=target, f=free / 1024**3
                ),
                "Benoetigt werden rund {n:.1f} GiB auf {t}, frei sind nur {f:.1f} GiB.".format(
                    n=margin / 1024**3, t=target, f=free / 1024**3
                ),
            )
    total = sum(needed.values())
    return Check(
        "free-space",
        OK,
        "Room for {n:.1f} GiB across {v} target volume(s).".format(
            n=total / 1024**3, v=len(needed)
        ),
        "Platz fuer {n:.1f} GiB auf {v} Ziel-Volume(s).".format(n=total / 1024**3, v=len(needed)),
    )


def _check_backup_space(plan: Plan, catalog: Path) -> Check:
    if not plan.settings.backup_catalog:
        return Check(
            "backup-space",
            WARNING,
            "Catalog backup is disabled. Rolling back a failed run will be much harder.",
            "Katalog-Backup ist deaktiviert. Ein Ruecksetzen nach Fehlern wird "
            "dadurch erheblich schwieriger.",
        )
    backup_dir = plan.settings.resolved_backup_dir()
    probe = backup_dir
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        free = shutil.disk_usage(str(probe)).free
    except OSError:
        return Check(
            "backup-space",
            ERROR,
            "Cannot determine free space for the backup directory {p}.".format(p=backup_dir),
            "Freier Speicher fuer das Backup-Verzeichnis {p} nicht ermittelbar.".format(
                p=backup_dir
            ),
        )
    needed = catalog.stat().st_size
    if free < needed * 1.2:
        return Check(
            "backup-space",
            ERROR,
            "Catalog backup needs about {n:.0f} MiB in {p}, only {f:.0f} MiB free.".format(
                n=needed / 1024**2, p=backup_dir, f=free / 1024**2
            ),
            "Katalog-Backup benoetigt rund {n:.0f} MiB in {p}, frei sind nur {f:.0f} MiB.".format(
                n=needed / 1024**2, p=backup_dir, f=free / 1024**2
            ),
        )
    return Check(
        "backup-space",
        OK,
        "Room for the {n:.0f} MiB catalog backup in {p}.".format(n=needed / 1024**2, p=backup_dir),
        "Platz fuer das {n:.0f} MiB grosse Katalog-Backup in {p}.".format(
            n=needed / 1024**2, p=backup_dir
        ),
    )


def _check_work_present(plan: Plan) -> Check:
    if not plan.has_work:
        return Check(
            "work-present",
            WARNING,
            "Nothing to do -- every selected file is already in its target folder.",
            "Nichts zu tun -- alle ausgewaehlten Dateien liegen bereits am Ziel.",
        )
    return Check(
        "work-present",
        OK,
        "{n} file(s) queued for moving.".format(n=plan.stats.touched),
        "{n} Datei(en) zum Verschieben vorgemerkt.".format(n=plan.stats.touched),
    )


def _check_missing_sources(plan: Plan) -> Optional[Check]:
    n = plan.stats.missing_source
    if not n:
        return None
    return Check(
        "missing-sources",
        WARNING,
        "{n} catalog entries point to files that are not on disk; they stay untouched.".format(n=n),
        "{n} Katalogeintraege verweisen auf nicht vorhandene Dateien; sie "
        "bleiben unangetastet.".format(n=n),
    )
