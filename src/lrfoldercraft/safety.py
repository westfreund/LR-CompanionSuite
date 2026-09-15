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
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from .catalog.db import is_locked, lock_file_for, sidecar_paths
from .logging_setup import get_logger, step
from .planner import Plan
from .version import VERIFIED_CATALOG_VERSIONS

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .config import Settings

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
    checks.append(_check_unfinished_run(catalog))
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
            "Lightroom hat den Katalog geöffnet ({f} vorhanden). Bitte "
            "Lightroom Classic zuerst beenden.".format(f=lock_file_for(catalog).name),
        )
    return Check(
        "lightroom-closed",
        OK,
        "No Lightroom lock file -- the catalog is free.",
        "Keine Lightroom-Sperrdatei -- der Katalog ist frei.",
    )


def _check_unfinished_run(catalog: Path) -> Check:
    """Refuse to start while an earlier run is lying half done.

    A run cut short leaves the catalog describing one layout and some files at
    another. Planning on top of that produces a plan for a library that does
    not exist, and applying it makes the tangle worse. Finishing the earlier
    run first is not optional.
    """
    from .resume import find_interruptions

    try:
        interruptions = find_interruptions(catalog)
    except Exception as error:  # noqa: BLE001 - reported, never raised on
        return Check(
            "unfinished-run",
            WARNING,
            "Could not check for interrupted runs: {e}".format(e=error),
            "Abgebrochene Läufe nicht prüfbar: {e}".format(e=error),
        )
    if not interruptions:
        return Check(
            "unfinished-run",
            OK,
            "No interrupted run is waiting to be finished.",
            "Kein abgebrochener Lauf wartet auf Abschluss.",
        )
    first = interruptions[0]
    return Check(
        "unfinished-run",
        ERROR,
        "An earlier run was cut short and is still half done. {d} Finish it "
        "first: lrfc resume {j}".format(d=first.describe("en"), j=first.journal_path),
        "Ein früherer Lauf wurde abgebrochen und liegt halb fertig. {d} Bitte "
        "zuerst abschließen: lrfc resume {j}".format(d=first.describe("de"), j=first.journal_path),
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
            "Keine Schreibrechte für die Katalogdatei.",
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
            "einmal in Lightroom öffnen und schließen, damit er sich erholt. "
            "Die Datei nicht löschen.".format(n=journal[0].name),
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
            "Das Write-Ahead-Log enthält {n:,} Byte, auf die der Katalog "
            "angewiesen ist. Es wird nach dem Lauf in den Katalog "
            "übernommen. Niemals löschen.".format(n=pending),
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
            "ID-Zähler nicht lesbar ({e}).".format(e=exc),
        )

    if row is None or row[0] in ("real", "integer"):
        return Check(
            "id-counter-type",
            OK,
            "Id counter has Lightroom's numeric storage class.",
            "ID-Zähler hat Lightrooms numerische Speicherklasse.",
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
        "Lightroom wird diesen Katalog nicht öffnen. Beschädigt durch "
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

        # With in-place placement the target *is* the catalog's own root folder,
        # so a missing one means the catalog is disconnected from its photos --
        # usually a drive mounted under a different name. Reporting that as a
        # permission problem on some distant parent directory helps nobody.
        if plan.placement == "in-place" and not root.exists():
            return Check(
                "target-writable",
                ERROR,
                "The catalog's root folder {r} does not exist. The drive is "
                "probably mounted under a different name, or the folder was "
                "moved. Reconnect it in Lightroom first (right-click the "
                "folder, Find Missing Folder), then run again.".format(r=root),
                "Der Stammordner {r} des Katalogs existiert nicht. Vermutlich "
                "ist das Laufwerk unter einem anderen Namen eingehängt oder "
                "der Ordner wurde verschoben. Bitte zuerst in Lightroom neu "
                "verknüpfen (Rechtsklick auf den Ordner, Fehlenden Ordner "
                "suchen) und dann erneut ausführen.".format(r=root),
            )

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
                "Keine Schreibrechte für {p}.".format(p=probe),
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
    for orphan in plan.orphans:
        # The collection folder sits in the target tree, so a target on another
        # drive means these are copied too.
        if not orphan.cross_volume:
            continue
        target = str(_existing_ancestor(Path(orphan.target_path).parent))
        needed[target] = needed.get(target, 0) + orphan.size_bytes
    if not needed:
        return Check(
            "free-space",
            OK,
            "Same-volume move -- no additional space required.",
            "Verschieben auf demselben Volume -- kein zusätzlicher Platz nötig.",
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
                "Benötigt werden rund {n:.1f} GiB auf {t}, frei sind nur {f:.1f} GiB.".format(
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
        "Platz für {n:.1f} GiB auf {v} Ziel-Volume(s).".format(n=total / 1024**3, v=len(needed)),
    )


def _check_backup_space(plan: Plan, catalog: Path) -> Check:
    if not plan.settings.backup_catalog:
        return Check(
            "backup-space",
            WARNING,
            "Catalog backup is disabled. Rolling back a failed run will be much harder.",
            "Katalog-Backup ist deaktiviert. Ein Rücksetzen nach Fehlern wird "
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
            "Freier Speicher für das Backup-Verzeichnis {p} nicht ermittelbar.".format(
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
            "Katalog-Backup benötigt rund {n:.0f} MiB in {p}, frei sind nur {f:.0f} MiB.".format(
                n=needed / 1024**2, p=backup_dir, f=free / 1024**2
            ),
        )
    return Check(
        "backup-space",
        OK,
        "Room for the {n:.0f} MiB catalog backup in {p}.".format(n=needed / 1024**2, p=backup_dir),
        "Platz für das {n:.0f} MiB große Katalog-Backup in {p}.".format(
            n=needed / 1024**2, p=backup_dir
        ),
    )


def _check_work_present(plan: Plan) -> Check:
    if not plan.has_work:
        return Check(
            "work-present",
            WARNING,
            "Nothing to do -- every selected file is already in its target folder.",
            "Nichts zu tun -- alle ausgewählten Dateien liegen bereits am Ziel.",
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

    # A few missing files are a fact of life in a large library. *Every* file
    # missing is a different thing entirely: the catalog has lost track of
    # where its photos are, and sorting it would be meaningless.
    if plan.stats.total and n == plan.stats.total:
        return Check(
            "missing-sources",
            ERROR,
            "None of the {n} selected files exist at the paths the catalog "
            "records. The catalog is not connected to its photos -- reconnect "
            "the folder in Lightroom first (right-click, Find Missing "
            "Folder).".format(n=n),
            "Keine der {n} ausgewählten Dateien liegt an dem Pfad, den der "
            "Katalog vermerkt. Der Katalog ist nicht mit seinen Fotos "
            "verbunden -- bitte zuerst in Lightroom neu verknüpfen "
            "(Rechtsklick, Fehlenden Ordner suchen).".format(n=n),
        )

    return Check(
        "missing-sources",
        WARNING,
        "{n} of {t} catalog entries point to files that are not on disk; they "
        "stay untouched.".format(n=n, t=plan.stats.total),
        "{n} von {t} Katalogeinträgen verweisen auf nicht vorhandene Dateien; "
        "sie bleiben unangetastet.".format(n=n, t=plan.stats.total),
    )


# ---------------------------------------------------------------------------
# Preconditions: what an operator must confirm before the first run
# ---------------------------------------------------------------------------


def preconditions(catalog: Path, settings: Settings) -> PreflightResult:
    """The state of the three things that have to be true before any run.

    Separate from :func:`preflight` on purpose: these are questions about the
    library and about what the operator has done, and they can be answered
    before a plan exists -- so an interface can put them up front rather than
    after the work is already described.

    Each check reports **what was actually found**. A dialog that merely
    recites three rules gets clicked away; one that says "schema 19.0.0,
    verified" and "51,049 of 51,049 files found" is worth reading.
    """
    catalog = Path(catalog)
    return PreflightResult(
        checks=[
            _check_lock(catalog),
            _precondition_schema(catalog),
            _precondition_paths_resolve(catalog),
            _precondition_backup(catalog, settings),
        ]
    )


def _roots_with_counts(catalog: Path):
    """Every root folder with how many files the catalog files under it."""
    from .catalog.db import open_catalog

    with open_catalog(catalog, allow_unsupported=True, ignore_lock=True) as connection:
        version = connection.schema_version()
        rows = connection.query(
            "SELECT rf.absolutePath AS path, COUNT(f.id_local) AS files "
            "FROM AgLibraryRootFolder rf "
            "LEFT JOIN AgLibraryFolder fo ON fo.rootFolder = rf.id_local "
            "LEFT JOIN AgLibraryFile f ON f.folder = fo.id_local "
            "GROUP BY rf.id_local, rf.absolutePath"
        )
    return version, [(row["path"], row["files"]) for row in rows]


def _precondition_schema(catalog: Path) -> Check:
    """Has this catalog been opened by the installed Lightroom Classic?"""
    try:
        version, _roots = _roots_with_counts(catalog)
    except Exception as error:  # noqa: BLE001 - reported, never raised on
        return Check(
            "catalog-version",
            WARNING,
            "Could not read the catalog version: {e}".format(e=error),
            "Katalogversion nicht lesbar: {e}".format(e=error),
        )
    if version in VERIFIED_CATALOG_VERSIONS:
        return Check(
            "catalog-version",
            OK,
            "Catalog schema {v}, a version this revision was verified against.".format(v=version),
            "Katalogschema {v} -- eine Version, gegen die diese Revision verifiziert wurde.".format(
                v=version
            ),
        )
    return Check(
        "catalog-version",
        WARNING,
        "Catalog schema {v} has not been verified with this revision. Open the "
        "catalog once in your installed Lightroom Classic first, so it is "
        "converted before it is reorganised.".format(v=version),
        "Katalogschema {v} wurde mit dieser Revision nicht verifiziert. Bitte "
        "den Katalog zuerst einmal im installierten Lightroom Classic öffnen, "
        "damit er vor dem Umsortieren konvertiert wird.".format(v=version),
    )


def _precondition_paths_resolve(catalog: Path) -> Check:
    """Is every root folder connected, or is the library looking elsewhere?"""
    try:
        _version, roots = _roots_with_counts(catalog)
    except Exception as error:  # noqa: BLE001 - reported, never raised on
        return Check(
            "folders-connected",
            WARNING,
            "Could not examine the root folders: {e}".format(e=error),
            "Wurzelordner nicht prüfbar: {e}".format(e=error),
        )

    holding = [(path, count) for path, count in roots if count]
    broken = [path for path, _count in holding if not Path(path).is_dir()]
    if broken:
        names = ", ".join(broken[:3])
        return Check(
            "folders-connected",
            ERROR,
            "{n} root folder(s) do not exist at the path the catalog records: {p}. "
            "Reconnect them in Lightroom (right-click the folder, Find Missing "
            "Folder) before running.".format(n=len(broken), p=names),
            "{n} Wurzelordner liegen nicht an dem Pfad, den der Katalog nennt: {p}. "
            "Bitte in Lightroom neu verknüpfen (Rechtsklick auf den Ordner, "
            "Fehlenden Ordner suchen), bevor der Lauf startet.".format(n=len(broken), p=names),
        )
    total = sum(count for _path, count in holding)
    return Check(
        "folders-connected",
        OK,
        "All {n} root folder(s) holding files exist on disk ({f:,} files).".format(
            n=len(holding), f=total
        ),
        "Alle {n} Wurzelordner mit Dateien existieren auf der Platte ({f:,} Dateien).".format(
            n=len(holding), f=total
        ),
    )


def _precondition_backup(catalog: Path, settings: Settings) -> Check:
    """Is there a copy of this catalog that is not the one about to be changed?"""
    directory = settings.resolved_backup_dir()
    stem = catalog.stem
    try:
        copies = sorted(
            (p for p in directory.glob("{s}-*.lrcat".format(s=stem)) if p.is_file()),
            key=lambda p: p.stat().st_mtime,
        )
    except OSError:
        copies = []
    if copies:
        newest = copies[-1]
        when = datetime.fromtimestamp(newest.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        return Check(
            "backup-present",
            OK,
            "A previous backup of this catalog exists, from {w}. This run makes "
            "its own before touching anything.".format(w=when),
            "Eine frühere Sicherung dieses Katalogs von {w} ist vorhanden. Dieser "
            "Lauf legt vor jeder Änderung eine eigene an.".format(w=when),
        )
    return Check(
        "backup-present",
        WARNING,
        "No earlier backup of this catalog in {d}. The run makes one before "
        "touching anything, but a copy of the photos on a different drive is "
        "yours to make.".format(d=directory),
        "Keine frühere Sicherung dieses Katalogs in {d}. Der Lauf legt vor jeder "
        "Änderung eine an, aber eine Kopie der Bilddaten auf einem anderen "
        "Laufwerk müssen Sie selbst anlegen.".format(d=directory),
    )
