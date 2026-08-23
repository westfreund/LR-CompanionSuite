"""Files that sit in the library's folders but are not in the catalog.

A library that has been worked in for years collects them: an export nobody
imported, a Photoshop round trip, a stale ``.xmp`` whose raw file was deleted,
a stray ``.png``. They are invisible to Lightroom and they are the reason a
reorganised tree still has odds and ends lying about afterwards.

Collecting them into one clearly named folder makes the result tidy without
deciding anything on the operator's behalf: nothing is deleted, the path each
file came from is preserved inside the collection folder, and the whole thing
is journalled like any other move, so undoing a run puts them back too.

What is emphatically **not** an orphan:

* a file the catalog references from any root -- including one that a later
  part of the same run is about to move;
* a sidecar belonging to a catalogued photo, which travels with it;
* Lightroom's own furniture: the catalog, its side files, its previews and
  its data directory;
* the collection folder itself, or a run's target tree.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List, Sequence, Set, Tuple

from .logging_setup import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .config import Settings
    from .planner import PlannedMove, RootScope

log = get_logger("orphans")

#: Directory names that belong to Lightroom or the operating system and must
#: never be walked into, let alone moved.
SKIP_DIRECTORIES = (
    ".Spotlight-V100",
    ".TemporaryItems",
    ".Trashes",
    ".fseventsd",
    "@eaDir",
)

#: Suffixes marking a directory as Lightroom's own working data.
SKIP_DIRECTORY_SUFFIXES = (".lrdata", ".lrcat-data")

#: Files that are part of the catalog or of the filesystem's bookkeeping.
SKIP_SUFFIXES = (
    ".lrcat",
    ".lrcat-wal",
    ".lrcat-shm",
    ".lrcat-journal",
    ".lrprev",
    ".lock",
)

#: Names never worth moving: the filesystem's own scribbles.
SKIP_NAMES = (".DS_Store", "Thumbs.db", "desktop.ini")


@dataclass
class Orphan:
    """One file on disk that the catalog knows nothing about."""

    source_path: str
    target_path: str
    size_bytes: int = 0
    #: Path below the source root, kept so the collection folder shows origin.
    relative_path: str = ""


@dataclass
class OrphanScan:
    """What a sweep of the source roots turned up."""

    orphans: List[Orphan] = field(default_factory=list)
    #: Directories that could not be read, with the reason.
    unreadable: List[str] = field(default_factory=list)
    scanned_files: int = 0

    @property
    def total_bytes(self) -> int:
        return sum(orphan.size_bytes for orphan in self.orphans)


def _is_skipped_directory(name: str) -> bool:
    return name in SKIP_DIRECTORIES or name.lower().endswith(SKIP_DIRECTORY_SUFFIXES)


def _is_skipped_file(name: str) -> bool:
    if name in SKIP_NAMES or name.startswith("._"):
        return True
    lowered = name.lower()
    return lowered.endswith(SKIP_SUFFIXES)


def find_orphans(
    scopes: Sequence[RootScope],
    moves: Iterable[PlannedMove],
    known_paths: Set[str],
    settings: Settings,
) -> OrphanScan:
    """Walk the source roots and report what the catalog does not account for.

    *known_paths* holds every path the catalog references. Sidecars are
    recognised from the catalogued photo they sit beside rather than from the
    moves, because a photo already in the right place makes no move -- and a
    second run would otherwise sweep up the sidecars of everything the first
    run had sorted.
    """
    scan = OrphanScan()
    if not settings.collect_orphans:
        return scan

    spoken_for = {_key(path) for path in known_paths}
    for move in moves:
        spoken_for.add(_key(move.source_path))
        spoken_for.add(_key(move.target_path))
        for source, _target in move.sidecars:
            spoken_for.add(_key(source))

    sidecar_extensions = {
        extension.lower().lstrip(".") for extension in settings.extra_sidecar_extensions
    }
    sidecar_extensions.discard("")

    folder_name = settings.orphan_folder.strip() or "_not-in-catalog"
    for scope in scopes:
        root = Path(scope.root_folder.absolute_path)
        collection = root / folder_name
        # A run may be sorting into a tree below the source root; its files are
        # the very ones being placed and must not be swept up behind it. When
        # sorting in place the two are the same directory, and protecting it
        # would call off the sweep before it began.
        protected = {_key(str(collection))}
        target = _key(scope.target_root_path)
        if target != _key(str(root)):
            protected.add(target)
        _walk_root(root, collection, protected, spoken_for, sidecar_extensions, scan)

    log.info(
        "Orphan sweep: %d file(s) examined, %d not in the catalog",
        scan.scanned_files,
        len(scan.orphans),
    )
    return scan


def _belongs_to_a_catalogued_photo(
    path: str, spoken_for: Set[str], sidecar_extensions: Set[str]
) -> bool:
    """True when *path* is a sidecar of a photo the catalog holds.

    Both conventions in the wild are covered: ``IMG_1234.xmp`` beside
    ``IMG_1234.CR2``, and ``IMG_1234.CR2.xmp``.
    """
    stem, extension = os.path.splitext(path)
    if extension.lower().lstrip(".") not in sidecar_extensions:
        return False
    if _key(stem) in spoken_for:  # IMG_1234.CR2.xmp
        return True
    # IMG_1234.xmp -- any catalogued photo in the same folder with that stem.
    prefix = _key(stem) + "."
    return any(known.startswith(prefix) and "/" not in known[len(prefix) :] for known in spoken_for)


def _walk_root(
    root: Path,
    collection: Path,
    protected: Set[str],
    spoken_for: Set[str],
    sidecar_extensions: Set[str],
    scan: OrphanScan,
) -> None:
    for dirpath, dirnames, filenames in os.walk(str(root)):
        if _key(dirpath) in protected:
            dirnames[:] = []
            continue
        dirnames[:] = [
            name
            for name in dirnames
            if not _is_skipped_directory(name)
            and _key(os.path.join(dirpath, name)) not in protected
        ]
        for name in filenames:
            if _is_skipped_file(name):
                continue
            path = os.path.join(dirpath, name)
            scan.scanned_files += 1
            if _key(path) in spoken_for:
                continue
            if _belongs_to_a_catalogued_photo(path, spoken_for, sidecar_extensions):
                continue
            relative = os.path.relpath(path, str(root))
            try:
                size = os.stat(path).st_size
            except OSError as error:
                scan.unreadable.append("{p}: {e}".format(p=path, e=error))
                continue
            scan.orphans.append(
                Orphan(
                    source_path=path,
                    target_path=str(collection / relative),
                    size_bytes=size,
                    relative_path=relative,
                )
            )


def _key(path: str) -> str:
    """Compare paths the way the filesystem does, case included or not."""
    return os.path.normcase(os.path.normpath(path))


def collection_directories(orphans: Sequence[Orphan]) -> List[str]:
    """Every directory the collection needs, parents before children."""
    wanted: Dict[str, None] = {}
    for orphan in orphans:
        parent = os.path.dirname(orphan.target_path)
        while parent and parent not in wanted:
            wanted[parent] = None
            parent = os.path.dirname(parent)
    return sorted(wanted, key=lambda p: len(Path(p).parts))


def describe(scan: OrphanScan, language: str = "en") -> Tuple[str, str]:
    """A one-line summary and the collection folder, for reports."""
    if language == "de":
        return (
            "{n} Datei(en) auf der Platte, die der Katalog nicht kennt".format(n=len(scan.orphans)),
            "",
        )
    return (
        "{n} file(s) on disk that the catalog does not know".format(n=len(scan.orphans)),
        "",
    )
