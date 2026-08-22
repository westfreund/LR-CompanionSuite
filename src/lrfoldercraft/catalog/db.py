"""Low level SQLite access to a Lightroom Classic catalog.

Safety rules encoded here:

* A catalog that Lightroom currently has open (``*.lrcat.lock`` present) is
  never touched -- not even read-write-capable connections are handed out.
* Read access always uses SQLite URI mode ``ro`` so an accidental write is
  refused by the driver itself.
* Write access is explicit, transactional, and refuses catalogs whose schema
  version is outside the supported range unless the caller forces it.
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from ..logging_setup import get_logger
from ..version import SUPPORTED_CATALOG_VERSION_RANGE, VERIFIED_CATALOG_VERSIONS

log = get_logger("catalog.db")

#: Tables that must exist for a file to be accepted as a Lightroom catalog.
REQUIRED_TABLES = (
    "Adobe_images",
    "Adobe_variablesTable",
    "AgLibraryFile",
    "AgLibraryFolder",
    "AgLibraryRootFolder",
)

ENTITY_ID_COUNTER = "Adobe_entityIDCounter"


class CatalogError(RuntimeError):
    """Raised for any problem with the catalog file itself."""


class CatalogLockedError(CatalogError):
    """Raised when Lightroom appears to have the catalog open."""


def lock_file_for(catalog_path: Path) -> Path:
    """Return the path of Lightroom's lock file for *catalog_path*."""
    return catalog_path.with_name(catalog_path.name + ".lock")


def sidecar_paths(catalog_path: Path) -> list[Path]:
    """Return catalog side files that belong to the same logical catalog."""
    candidates = [
        catalog_path.with_name(catalog_path.name + suffix)
        for suffix in ("-wal", "-shm", "-journal")
    ]
    return [p for p in candidates if p.exists()]


def is_locked(catalog_path: Path) -> bool:
    """True if Lightroom's lock file exists next to the catalog."""
    return lock_file_for(Path(catalog_path)).exists()


class CatalogConnection:
    """Thin wrapper around :class:`sqlite3.Connection` for a catalog."""

    def __init__(self, path: Path, connection: sqlite3.Connection, writable: bool):
        self.path = path
        self.connection = connection
        self.writable = writable
        connection.row_factory = sqlite3.Row

    # -- introspection -------------------------------------------------

    def query(self, sql: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
        log.debug("SQL query: %s | params=%r", " ".join(sql.split()), params)
        return self.connection.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: tuple[object, ...] = ()) -> Optional[sqlite3.Row]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: tuple[object, ...] = ()) -> object:
        row = self.query_one(sql, params)
        return row[0] if row is not None else None

    def variable(self, name: str) -> Optional[str]:
        """Read a value from ``Adobe_variablesTable``."""
        row = self.query_one("SELECT value FROM Adobe_variablesTable WHERE name = ?", (name,))
        return None if row is None else row[0]

    def schema_version(self) -> Optional[str]:
        """Return the catalog schema version, e.g. ``18.0.0``."""
        row = self.query_one(
            "SELECT value FROM Adobe_variablesTable "
            "WHERE name = 'Adobe_DBVersion' OR value LIKE '__._._'"
        )
        if row is not None and isinstance(row[0], str) and row[0].count(".") == 2:
            return row[0]
        for candidate in self.query(
            "SELECT value FROM Adobe_variablesTable WHERE typeof(value)='text'"
        ):
            value = candidate[0]
            if isinstance(value, str) and value.count(".") == 2 and value[0].isdigit():
                return value
        return None

    def integrity_ok(self) -> bool:
        """Run SQLite's own integrity check."""
        result = self.scalar("PRAGMA integrity_check")
        log.debug("PRAGMA integrity_check -> %r", result)
        return result == "ok"

    # -- id allocation -------------------------------------------------

    def peek_entity_id_counter(self) -> float:
        raw = self.variable(ENTITY_ID_COUNTER)
        if raw is None:
            raise CatalogError("Adobe_entityIDCounter missing -- refusing to invent row ids")
        return float(raw)

    def allocate_ids(self, count: int) -> list[int]:
        """Reserve *count* new ``id_local`` values and advance the counter.

        Lightroom hands out row ids from a single catalog-wide counter stored
        in ``Adobe_variablesTable``. Allocating from the same counter is what
        keeps a rewritten catalog collision free once Lightroom reopens it.
        """
        if not self.writable:
            raise CatalogError("cannot allocate ids on a read-only connection")
        if count <= 0:
            return []
        start = int(self.peek_entity_id_counter())
        ids = list(range(start, start + count))
        new_value = float(start + count)
        self.connection.execute(
            "UPDATE Adobe_variablesTable SET value = ? WHERE name = ?",
            (repr(new_value), ENTITY_ID_COUNTER),
        )
        log.debug("Allocated ids %d..%d, counter -> %s", ids[0], ids[-1], new_value)
        return ids

    @staticmethod
    def new_id_global() -> str:
        """Return an id_global in Lightroom's uppercase, dashed UUID format."""
        return str(uuid.uuid4()).upper()

    # -- lifecycle -----------------------------------------------------

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> CatalogConnection:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _validate(conn: CatalogConnection, allow_unsupported: bool) -> None:
    names = {row[0] for row in conn.query("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = [table for table in REQUIRED_TABLES if table not in names]
    if missing:
        raise CatalogError(
            "not a Lightroom Classic catalog -- missing tables: " + ", ".join(missing)
        )

    version = conn.schema_version()
    log.info("Catalog schema version: %s", version or "unknown")
    if version in VERIFIED_CATALOG_VERSIONS:
        return
    major: Optional[int] = None
    if version:
        try:
            major = int(version.split(".")[0])
        except ValueError:
            major = None
    low, high = SUPPORTED_CATALOG_VERSION_RANGE
    if major is None or not (low <= major <= high):
        message = (
            "catalog schema version {v!r} is outside the supported range {low}.x-{high}.x".format(
                v=version, low=low, high=high
            )
        )
        if not allow_unsupported:
            raise CatalogError(message + " (use --allow-unsupported-catalog to override)")
        log.warning("%s -- continuing because the override was given", message)
    else:
        log.warning(
            "Catalog schema %s was not explicitly verified for this revision "
            "(verified: %s). Proceeding, but check the result in Lightroom.",
            version,
            ", ".join(VERIFIED_CATALOG_VERSIONS),
        )


@contextmanager
def open_catalog(
    catalog_path: str | Path,
    writable: bool = False,
    allow_unsupported: bool = False,
    ignore_lock: bool = False,
) -> Iterator[CatalogConnection]:
    """Open *catalog_path* and yield a :class:`CatalogConnection`.

    Args:
        catalog_path: path to the ``.lrcat`` file.
        writable: open read-write; the caller is responsible for committing.
        allow_unsupported: accept schema versions outside the tested range.
        ignore_lock: proceed even though a Lightroom lock file exists.
                     Strongly discouraged; exposed for forensic inspection.
    """
    path = Path(catalog_path).expanduser().resolve()
    if not path.exists():
        raise CatalogError("catalog not found: {p}".format(p=path))
    if path.suffix.lower() != ".lrcat":
        log.warning("File %s does not have an .lrcat extension", path.name)

    if is_locked(path):
        message = (
            "catalog is locked by Lightroom ({lock}). Close Lightroom Classic "
            "before running LR-FolderCraft.".format(lock=lock_file_for(path).name)
        )
        if not ignore_lock:
            raise CatalogLockedError(message)
        log.warning("%s -- continuing because --ignore-lock was given", message)

    leftovers = sidecar_paths(path)
    if leftovers:
        log.warning(
            "Catalog has uncommitted side files: %s. Open and close the catalog "
            "in Lightroom once so it can flush them.",
            ", ".join(p.name for p in leftovers),
        )

    if writable:
        log.info("Opening catalog READ-WRITE: %s", path)
        raw = sqlite3.connect("file:{p}".format(p=_uri_escape(path)), uri=True, timeout=30.0)
    else:
        log.info("Opening catalog read-only: %s", path)
        raw = _connect_readonly(path)

    conn = CatalogConnection(path, raw, writable)
    try:
        if writable:
            raw.execute("PRAGMA foreign_keys = OFF")
        _validate(conn, allow_unsupported)
        yield conn
    finally:
        conn.close()
        log.debug("Catalog connection closed: %s", path)


def _connect_readonly(path: Path) -> sqlite3.Connection:
    """Open *path* read-only, working around filesystems without POSIX locks.

    Plain ``mode=ro`` needs a shared lock on the database file. Some volumes --
    notably exFAT/FAT media, which is where external photo archives usually
    live -- do not provide advisory locking, and SQLite then fails with
    "unable to open database file". Falling back to ``immutable=1`` skips
    locking entirely. That is only safe while nobody writes to the catalog,
    which the lock-file check above has already established.

    The probe query matters: :func:`sqlite3.connect` is lazy and opens nothing,
    so a volume that cannot provide the lock raises on the first *statement*,
    not on connecting. Without forcing a statement here the fallback would
    never run and the failure would surface deep inside a caller instead.
    """
    escaped = _uri_escape(path)
    connection: Optional[sqlite3.Connection] = None
    try:
        connection = sqlite3.connect("file:{p}?mode=ro".format(p=escaped), uri=True, timeout=30.0)
        connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
        return connection
    except sqlite3.Error as exc:
        if connection is not None:
            try:
                connection.close()
            except sqlite3.Error:  # pragma: no cover - closing a dead handle
                pass
        log.debug("mode=ro failed (%s); retrying with immutable=1", exc)

    connection = sqlite3.connect(
        "file:{p}?mode=ro&immutable=1".format(p=escaped), uri=True, timeout=30.0
    )
    connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
    log.info(
        "Filesystem does not support read-only SQLite locking; opened %s "
        "with immutable=1 (safe: Lightroom is not holding the catalog).",
        path.name,
    )
    return connection


def _uri_escape(path: Path) -> str:
    """Escape a filesystem path for use inside an SQLite URI."""
    text = str(path)
    return text.replace("?", "%3f").replace("#", "%23")
