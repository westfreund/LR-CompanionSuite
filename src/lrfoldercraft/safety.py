"""Pre-flight checks run before anything is written.

Every check returns a :class:`Check`. A single ``level="error"`` result stops
the run; warnings are reported and require confirmation in interactive front
ends. The checks are deliberately cheap so they can also be shown live in the
TUI while the user is still assembling a run.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

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
    leftovers = sidecar_paths(catalog)
    if leftovers:
        names = ", ".join(p.name for p in leftovers)
        return Check(
            "catalog-side-files",
            WARNING,
            "Catalog side files present ({n}). Open and close the catalog in "
            "Lightroom once so it flushes them.".format(n=names),
            "Katalog-Seitendateien vorhanden ({n}). Katalog einmal in Lightroom "
            "oeffnen und schliessen, damit sie geleert werden.".format(n=names),
        )
    return Check(
        "catalog-side-files",
        OK,
        "No stale catalog side files.",
        "Keine verwaisten Katalog-Seitendateien.",
    )


def _check_target_writable(plan: Plan) -> Check:
    root = Path(plan.target_root_path)
    probe = root
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
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
    return Check(
        "target-writable",
        OK,
        "Target location is writable.",
        "Zielort ist beschreibbar.",
    )


def _check_free_space(plan: Plan) -> Check:
    """Free space only matters when files cross a volume boundary."""
    needed = plan.stats.cross_volume_bytes
    if not needed:
        return Check(
            "free-space",
            OK,
            "Same-volume move -- no additional space required.",
            "Verschieben auf demselben Volume -- kein zusaetzlicher Platz noetig.",
        )
    root = Path(plan.target_root_path)
    probe = root
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    free = shutil.disk_usage(str(probe)).free
    margin = int(needed * 1.05)
    if free < margin:
        return Check(
            "free-space",
            ERROR,
            "Need about {n:.1f} GiB on the target volume, only {f:.1f} GiB free.".format(
                n=margin / 1024**3, f=free / 1024**3
            ),
            "Benoetigt werden rund {n:.1f} GiB auf dem Ziel-Volume, frei sind "
            "nur {f:.1f} GiB.".format(n=margin / 1024**3, f=free / 1024**3),
        )
    return Check(
        "free-space",
        OK,
        "{f:.1f} GiB free on the target volume for {n:.1f} GiB of data.".format(
            f=free / 1024**3, n=needed / 1024**3
        ),
        "{f:.1f} GiB frei auf dem Ziel-Volume fuer {n:.1f} GiB Daten.".format(
            f=free / 1024**3, n=needed / 1024**3
        ),
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
