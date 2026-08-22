"""Turn a catalog plus a :class:`~lrfoldercraft.config.Settings` into a Plan.

The planner never touches the filesystem or the catalog beyond reading. Its
output is a fully materialised list of intended moves that can be reviewed,
exported and only then executed. Everything the executor needs to know --
including conflicts, sidecars and cross-volume transfers -- is decided here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .catalog.model import Photo, RootFolder, lr_path_from_root
from .catalog.reader import CatalogReader
from .config import Settings
from .logging_setup import get_logger, step
from .rules import (
    TokenContext,
    render_structure,
    sanitise_segment,
    structure_requires_date,
)

log = get_logger("planner")

# -- move statuses ----------------------------------------------------------

MOVE = "move"
RENAMED = "renamed"
STAY = "stay"
SKIP_NO_DATE = "skip-no-date"
SKIP_CONFLICT = "skip-conflict"
SKIP_FILTERED = "skip-filtered"
SKIP_MISSING_SOURCE = "skip-missing-source"

#: Statuses that cause a file to actually be touched.
ACTIVE_STATUSES = (MOVE, RENAMED)

STATUS_LABELS = {
    MOVE: ("will be moved", "wird verschoben"),
    RENAMED: ("will be moved and renamed", "wird verschoben und umbenannt"),
    STAY: ("already in place", "bereits am Ziel"),
    SKIP_NO_DATE: ("skipped, no usable date", "uebersprungen, kein Datum"),
    SKIP_CONFLICT: ("skipped, target name taken", "uebersprungen, Zielname belegt"),
    SKIP_FILTERED: ("skipped by extension filter", "durch Endungsfilter ausgeschlossen"),
    SKIP_MISSING_SOURCE: ("skipped, file missing on disk", "uebersprungen, Datei fehlt"),
}


class PlanError(RuntimeError):
    """Raised when a plan cannot be produced at all."""


@dataclass
class PlannedMove:
    """One file's intended fate."""

    file_id: int
    filename: str
    source_path: str
    target_path: str
    target_segments: Tuple[str, ...]
    status: str
    reason: str = ""
    target_filename: str = ""
    sidecars: Tuple[Tuple[str, str], ...] = ()
    virtual_copy_count: int = 0
    capture_time: Optional[str] = None
    camera: Optional[str] = None
    size_bytes: int = 0
    cross_volume: bool = False
    source_folder_id: int = 0

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def renamed(self) -> bool:
        return self.status == RENAMED


@dataclass
class PlanStats:
    """Aggregate numbers shown in every report."""

    total: int = 0
    to_move: int = 0
    to_rename: int = 0
    already_in_place: int = 0
    skipped_no_date: int = 0
    skipped_conflict: int = 0
    skipped_filtered: int = 0
    missing_source: int = 0
    sidecars: int = 0
    virtual_copies_carried: int = 0
    new_folders: int = 0
    bytes_to_move: int = 0
    cross_volume_bytes: int = 0

    @property
    def touched(self) -> int:
        return self.to_move + self.to_rename


@dataclass
class Plan:
    """The complete, reviewable result of planning a run."""

    settings: Settings
    catalog_path: str
    root_folder: RootFolder
    anchor_segments: Tuple[str, ...]
    target_root_path: str
    placement: str
    moves: List[PlannedMove] = field(default_factory=list)
    new_folder_segments: List[Tuple[str, ...]] = field(default_factory=list)
    source_folder_ids: Tuple[int, ...] = ()
    stats: PlanStats = field(default_factory=PlanStats)
    warnings: List[str] = field(default_factory=list)
    created_at: str = ""

    @property
    def active_moves(self) -> List[PlannedMove]:
        return [m for m in self.moves if m.is_active]

    @property
    def has_work(self) -> bool:
        return bool(self.active_moves)

    def folder_summary(self) -> List[Tuple[str, int]]:
        """``(relative target folder, file count)`` for every active target."""
        counts: Dict[str, int] = {}
        for move in self.active_moves:
            key = "/".join(move.target_segments) or "."
            counts[key] = counts.get(key, 0) + 1
        return sorted(counts.items())


# ---------------------------------------------------------------------------
# Date resolution
# ---------------------------------------------------------------------------


def resolve_date(photo: Photo, settings: Settings) -> Optional[datetime]:
    """Return the timestamp that drives the date tokens for *photo*.

    Sources are tried in the order configured in ``settings.date_source``:

    ``capture``      Lightroom's ``Adobe_images.captureTime`` -- the value the
                     user sees and edits in the Metadata panel. Preferred,
                     because a corrected capture time must win.
    ``exif-fields``  the harvested ``dateYear/dateMonth/dateDay`` columns.
    ``file-mtime``   the file's modification time; last resort only.
    """
    for source in settings.date_source:
        if source == "capture":
            when = photo.capture_time
            if when is not None:
                return when
        elif source == "exif-fields":
            if photo.exif_year:
                try:
                    return datetime(
                        int(photo.exif_year),
                        int(photo.exif_month or 1),
                        int(photo.exif_day or 1),
                    )
                except ValueError:
                    log.debug(
                        "Invalid harvested EXIF date for file %d: %r-%r-%r",
                        photo.file_id,
                        photo.exif_year,
                        photo.exif_month,
                        photo.exif_day,
                    )
        elif source == "file-mtime":
            try:
                return datetime.fromtimestamp(os.stat(photo.absolute_path).st_mtime)
            except OSError:
                continue
    return None


# ---------------------------------------------------------------------------
# Sidecars
# ---------------------------------------------------------------------------


class DirectoryIndex:
    """Cached, case-insensitive directory listings.

    Two reasons this exists instead of a plain ``Path.exists()`` per probe:

    * macOS, Windows and exFAT are case insensitive, so probing both
      ``name.xmp`` and ``name.XMP`` reports the *same* file twice. Matching
      against a real listing returns the one true on-disk spelling.
    * a year folder holding ten thousand files would otherwise be stat'ed
      several times per photo.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, str]] = {}

    def names(self, directory: str) -> Dict[str, str]:
        """Map lower-cased file name -> actual file name for *directory*."""
        cached = self._cache.get(directory)
        if cached is None:
            cached = {}
            try:
                for name in os.listdir(directory):
                    cached.setdefault(name.lower(), name)
            except OSError as exc:
                log.debug("Cannot list %s: %s", directory, exc)
            self._cache[directory] = cached
        return cached

    def find(self, directory: str, name: str) -> Optional[str]:
        """Absolute path of *name* in *directory*, whatever its actual case."""
        actual = self.names(directory).get(name.lower())
        return os.path.join(directory, actual) if actual else None


def discover_sidecars(
    photo: Photo, settings: Settings, index: Optional[DirectoryIndex] = None
) -> List[str]:
    """Return absolute paths of sidecar files that must travel with *photo*.

    Two naming conventions are recognised, both of which occur in the wild:
    ``IMG_1234.xmp`` (Adobe's own) and ``IMG_1234.CR2.xmp`` (many third party
    converters). Extensions Lightroom itself recorded in
    ``AgLibraryFile.sidecarExtensions`` are always included. The photo's own
    file is never reported as its own sidecar.
    """
    if not settings.move_sidecars:
        return []
    index = index or DirectoryIndex()
    source = Path(photo.absolute_path)
    directory = str(source.parent)
    extensions: Set[str] = {e.lower().lstrip(".") for e in settings.extra_sidecar_extensions}
    extensions.update(e.lower().lstrip(".") for e in photo.sidecar_list)
    extensions.discard("")

    seen: Set[str] = {photo.filename.lower()}
    found: List[str] = []
    for ext in sorted(extensions):
        for candidate_name in (
            "{b}.{e}".format(b=photo.base_name, e=ext),
            "{b}.{e}".format(b=source.name, e=ext),
        ):
            if candidate_name.lower() in seen:
                continue
            actual = index.find(directory, candidate_name)
            if actual is None:
                continue
            seen.add(Path(actual).name.lower())
            found.append(actual)
    return found


# ---------------------------------------------------------------------------
# Anchor resolution
# ---------------------------------------------------------------------------


def common_prefix(paths: Iterable[Tuple[str, ...]]) -> Tuple[str, ...]:
    """Longest common leading path segments of *paths*."""
    items = list(paths)
    if not items:
        return ()
    prefix = list(items[0])
    for segments in items[1:]:
        keep = 0
        for a, b in zip(prefix, segments):
            if a != b:
                break
            keep += 1
        prefix = prefix[:keep]
        if not prefix:
            break
    return tuple(prefix)


def resolve_anchor(
    reader: CatalogReader,
    settings: Settings,
    photos: Sequence[Photo],
) -> Tuple[RootFolder, Tuple[str, ...]]:
    """Decide below which folder the new structure is built.

    ``in-place``  the deepest folder that already contains every selected
                  photo -- for the common "one year folder" case that is
                  exactly that year folder, so the day folders appear inside it.
    ``new-tree``  the structure starts at the configured target root, so the
                  anchor below the (new) root folder is empty.
    """
    roots = {p.root_folder_id for p in photos}
    if len(roots) > 1:
        raise PlanError(
            "selected photos span {n} root folders; restrict the selection with "
            "--root-folder or --folder".format(n=len(roots))
        )
    root_id = next(iter(roots))
    root = next(r for r in reader.root_folders() if r.id_local == root_id)

    if settings.placement == "new-tree":
        return root, ()

    if settings.anchor_folder_id is not None:
        folder = next(
            (f for f in reader.folders(root_id) if f.id_local == settings.anchor_folder_id),
            None,
        )
        if folder is None:
            raise PlanError(
                "anchor folder id {i} not found in root folder {r}".format(
                    i=settings.anchor_folder_id, r=root.name
                )
            )
        return root, folder.segments

    anchor = common_prefix(
        tuple(p.folder_path_from_root.strip("/").split("/"))
        if p.folder_path_from_root.strip("/")
        else ()
        for p in photos
    )
    return root, anchor


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


#: Marker used while preparing photos, before the plan rows are built.
_FILTERED = "filtered"
_NO_DATE_SKIP = "no-date-skip"


def _structure_segments(
    photo: Photo, settings: Settings, needs_date: bool
) -> Tuple[Optional[Tuple[str, ...]], str]:
    """Render the structure for one photo.

    Returns ``(segments, reason)``. ``segments`` is ``None`` when the photo has
    no usable date and ``on-missing-date=skip``; *reason* then carries the
    marker :data:`_NO_DATE_SKIP`.
    """
    when = resolve_date(photo, settings)
    if when is None and needs_date:
        if settings.on_missing_date == "skip":
            return None, _NO_DATE_SKIP
        if settings.on_missing_date == "abort":
            raise PlanError(
                "file {f} has no usable capture date (on-missing-date=abort)".format(
                    f=photo.absolute_path
                )
            )
        return (
            (sanitise_segment(settings.unsorted_folder),),
            "no capture date -> unsorted folder",
        )
    context = TokenContext(
        when=when,
        camera=photo.camera_model,
        camera_serial=photo.camera_serial,
        lens=photo.lens,
        file_format=photo.file_format,
        extension=photo.extension,
        original_folder=_last_segment(photo.folder_path_from_root),
        language=settings.language,
    )
    return (
        render_structure(settings.structure, context, ascii_only=settings.ascii_only),
        "",
    )


def _normalise_anchor(
    anchor: Tuple[str, ...],
    settings: Settings,
    prepared: Sequence[Tuple[Photo, Optional[Tuple[str, ...]], str]],
) -> Tuple[str, ...]:
    """Strip an anchor tail that the structure itself would produce.

    Without this, running the tool a second time on an already sorted library
    would nest the structure inside itself. After a first run with
    ``{camera}/{yyyy}/{mm}/{dd}`` every photo of one camera and year shares
    ``canon-eos-70d/2019`` as its common parent folder -- so a naive second run
    would build ``canon-eos-70d/2019/canon-eos-70d/2019/01/03``.

    The overlap is only ever a *prefix* of the rendered structure, and how much
    of it survives as a common parent depends on how varied the library is. So
    the longest k is found for which the last k anchor segments equal the first
    k rendered segments of **every** photo, and those k are dropped. A source
    folder that merely looks date-ish (``raw2019``) does not match and is kept.
    """
    if settings.placement != "in-place" or settings.anchor_folder_id is not None:
        return anchor
    if not anchor:
        return anchor
    candidates = [segs for _, segs, reason in prepared if segs and not reason]
    if not candidates:
        return anchor

    limit = min(len(anchor), min(len(segs) for segs in candidates))
    for k in range(limit, 0, -1):
        tail = tuple(anchor[-k:])
        if all(tuple(segs[:k]) == tail for segs in candidates):
            log.info(
                "Anchor %r already contains the first %d level(s) of the "
                "structure; using %r instead",
                "/".join(anchor),
                k,
                "/".join(anchor[:-k]) or "(root)",
            )
            return anchor[:-k]
    return anchor


def build_plan(reader: CatalogReader, settings: Settings) -> Plan:
    """Produce a :class:`Plan` for *settings* against the catalog behind *reader*."""
    settings.validate()
    step(
        "Planning run: structure=%s placement=%s",
        "/".join(settings.structure),
        settings.placement,
    )

    photos = list(
        reader.photos(
            folder_ids=settings.folder_ids or None,
            root_folder_ids=(settings.root_folder_id,) if settings.root_folder_id else None,
        )
    )
    if not photos:
        raise PlanError("no photos matched the selection")
    step("Selected %d file(s) from the catalog", len(photos))

    needs_date = structure_requires_date(settings.structure)
    prepared: List[Tuple[Photo, Optional[Tuple[str, ...]], str]] = []
    for photo in photos:
        if not settings.accepts_extension(photo.extension):
            prepared.append((photo, None, _FILTERED))
            continue
        segments, reason = _structure_segments(photo, settings, needs_date)
        prepared.append((photo, segments, reason))

    root, anchor = resolve_anchor(reader, settings, photos)
    anchor = _normalise_anchor(anchor, settings, prepared)
    step(
        "Anchor resolved: root=%s anchor=%r placement=%s",
        root.name,
        "/".join(anchor),
        settings.placement,
    )

    if settings.placement == "new-tree":
        target_root_path = str(Path(settings.target_root or "").expanduser())
    else:
        target_root_path = root.normalised_path

    plan = Plan(
        settings=settings,
        catalog_path=str(reader.conn.path),
        root_folder=root,
        anchor_segments=anchor,
        target_root_path=target_root_path,
        placement=settings.placement,
        source_folder_ids=tuple(sorted({p.folder_id for p in photos})),
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    source_device = _device_of(root.normalised_path)
    target_device = _device_of(target_root_path)
    cross_volume = (
        source_device is not None and target_device is not None and source_device != target_device
    )
    if cross_volume:
        plan.warnings.append(
            "Target is on a different volume than the source; files are copied "
            "and verified, then the originals are removed. This takes much "
            "longer than a same-volume move."
        )

    # Claimed target paths -> the file that claimed them first.
    claimed: Dict[str, int] = {}
    folder_segments_seen: Set[Tuple[str, ...]] = set()
    index = DirectoryIndex()

    for photo, segments, reason in prepared:
        move = _plan_one(
            photo=photo,
            settings=settings,
            anchor=anchor,
            target_root_path=target_root_path,
            structure_segments=segments,
            date_reason=reason,
            claimed=claimed,
            cross_volume=cross_volume,
            index=index,
        )
        plan.moves.append(move)
        if move.is_active:
            folder_segments_seen.add(move.target_segments)

    plan.new_folder_segments = sorted(folder_segments_seen)
    _fill_stats(plan)
    _add_warnings(plan)
    step(
        "Plan complete: %d move(s), %d already in place, %d skipped, %d target folder(s)",
        plan.stats.touched,
        plan.stats.already_in_place,
        plan.stats.total - plan.stats.touched - plan.stats.already_in_place,
        len(plan.new_folder_segments),
    )
    return plan


def _plan_one(
    photo: Photo,
    settings: Settings,
    anchor: Tuple[str, ...],
    target_root_path: str,
    structure_segments: Optional[Tuple[str, ...]],
    date_reason: str,
    claimed: Dict[str, int],
    cross_volume: bool,
    index: Optional[DirectoryIndex] = None,
) -> PlannedMove:
    source_path = photo.absolute_path
    base = PlannedMove(
        file_id=photo.file_id,
        filename=photo.filename,
        source_path=source_path,
        target_path=source_path,
        target_segments=(),
        status=STAY,
        target_filename=photo.filename,
        virtual_copy_count=photo.virtual_copy_count,
        capture_time=photo.capture_time_raw,
        camera=photo.camera_model,
        cross_volume=cross_volume,
        source_folder_id=photo.folder_id,
    )

    if date_reason == _FILTERED:
        base.status = SKIP_FILTERED
        base.reason = "extension .{e} excluded".format(e=photo.extension)
        return base

    try:
        base.size_bytes = os.stat(source_path).st_size
    except OSError:
        base.status = SKIP_MISSING_SOURCE
        base.reason = "file not found on disk"
        return base

    if structure_segments is None:
        base.status = SKIP_NO_DATE
        base.reason = "no capture date and on-missing-date=skip"
        return base

    base.reason = date_reason
    segments = anchor + structure_segments
    base.target_segments = segments
    target_dir = _join(target_root_path, segments)
    target_path = "{d}/{f}".format(d=target_dir, f=photo.filename)

    same_place = (
        settings.placement == "in-place" and tuple(_split(photo.folder_path_from_root)) == segments
    )
    if same_place and os.path.normpath(target_path) == os.path.normpath(source_path):
        base.status = STAY
        base.target_path = source_path
        base.reason = "already in the target folder"
        return base

    target_filename, status, reason = _resolve_conflict(
        target_dir=target_dir,
        filename=photo.filename,
        base_name=photo.base_name,
        extension=photo.extension,
        source_path=source_path,
        file_id=photo.file_id,
        settings=settings,
        claimed=claimed,
    )
    if status == SKIP_CONFLICT:
        base.status = SKIP_CONFLICT
        base.reason = reason
        base.target_path = target_path
        return base

    target_path = "{d}/{f}".format(d=target_dir, f=target_filename)
    claimed[_key(target_path)] = photo.file_id
    base.target_filename = target_filename
    base.target_path = target_path
    base.status = RENAMED if target_filename != photo.filename else MOVE
    if base.status == RENAMED:
        base.reason = reason or "target name already taken"

    sidecars = discover_sidecars(photo, settings, index)
    if sidecars:
        target_stem = _stem(target_filename)
        pairs: List[Tuple[str, str]] = []
        for sidecar in sidecars:
            name = Path(sidecar).name
            # Keep the sidecar glued to its (possibly renamed) master file:
            # IMG.xmp -> IMG_1.xmp and IMG.CR2.xmp -> IMG_1.CR2.xmp.
            if name.lower().startswith(photo.base_name.lower()):
                suffix = name[len(photo.base_name) :]
                name = "{n}{s}".format(n=target_stem, s=suffix)
            sidecar_target = "{d}/{n}".format(d=target_dir, n=name)
            if _key(sidecar_target) in claimed:
                log.warning(
                    "Sidecar target %s is already claimed; leaving %s in place",
                    sidecar_target,
                    sidecar,
                )
                continue
            claimed[_key(sidecar_target)] = photo.file_id
            pairs.append((sidecar, sidecar_target))
        base.sidecars = tuple(pairs)
    return base


def _stem(filename: str) -> str:
    """File name without its last extension."""
    return filename.rsplit(".", 1)[0] if "." in filename else filename


def _resolve_conflict(
    target_dir: str,
    filename: str,
    base_name: str,
    extension: str,
    source_path: str,
    file_id: int,
    settings: Settings,
    claimed: Dict[str, int],
) -> Tuple[str, str, str]:
    """Return ``(filename, status, reason)`` after conflict resolution."""
    candidate = "{d}/{f}".format(d=target_dir, f=filename)
    taken_by = claimed.get(_key(candidate))
    on_disk = os.path.exists(candidate) and os.path.normpath(candidate) != os.path.normpath(
        source_path
    )
    if taken_by is None and not on_disk:
        return filename, MOVE, ""

    who = "another file in this run" if taken_by is not None else "an existing file on disk"
    if settings.conflict == "skip":
        return filename, SKIP_CONFLICT, "target name taken by {w}".format(w=who)
    if settings.conflict == "abort":
        raise PlanError(
            "name collision at {c} (taken by {w}); rerun with --conflict rename or skip".format(
                c=candidate, w=who
            )
        )

    suffix = ".{e}".format(e=extension) if extension else ""
    for counter in range(1, 1000):
        renamed = "{b}_{n}{s}".format(b=base_name, n=counter, s=suffix)
        candidate = "{d}/{f}".format(d=target_dir, f=renamed)
        if _key(candidate) in claimed or os.path.exists(candidate):
            continue
        return renamed, RENAMED, "renamed, original name taken by {w}".format(w=who)
    return filename, SKIP_CONFLICT, "could not find a free name after 999 attempts"


def _fill_stats(plan: Plan) -> None:
    stats = plan.stats
    stats.total = len(plan.moves)
    stats.new_folders = len(plan.new_folder_segments)
    for move in plan.moves:
        if move.status == MOVE:
            stats.to_move += 1
        elif move.status == RENAMED:
            stats.to_rename += 1
        elif move.status == STAY:
            stats.already_in_place += 1
        elif move.status == SKIP_NO_DATE:
            stats.skipped_no_date += 1
        elif move.status == SKIP_CONFLICT:
            stats.skipped_conflict += 1
        elif move.status == SKIP_FILTERED:
            stats.skipped_filtered += 1
        elif move.status == SKIP_MISSING_SOURCE:
            stats.missing_source += 1
        if move.is_active:
            stats.sidecars += len(move.sidecars)
            stats.virtual_copies_carried += move.virtual_copy_count
            stats.bytes_to_move += move.size_bytes
            if move.cross_volume:
                stats.cross_volume_bytes += move.size_bytes


def _add_warnings(plan: Plan) -> None:
    stats = plan.stats
    if stats.missing_source:
        plan.warnings.append(
            "{n} file(s) referenced by the catalog are missing on disk and are "
            "left untouched. Reconnect them in Lightroom first.".format(n=stats.missing_source)
        )
    if stats.skipped_conflict:
        plan.warnings.append(
            "{n} file(s) were skipped because their target name was already taken.".format(
                n=stats.skipped_conflict
            )
        )
    if stats.skipped_no_date:
        plan.warnings.append(
            "{n} file(s) have no usable capture date.".format(n=stats.skipped_no_date)
        )
    if stats.to_rename:
        plan.warnings.append(
            "{n} file(s) will be renamed to avoid a collision; the catalog is "
            "updated accordingly.".format(n=stats.to_rename)
        )
    if plan.placement == "new-tree":
        plan.warnings.append(
            "Placement 'new-tree' registers {p} as an additional root folder in "
            "the catalog.".format(p=plan.target_root_path)
        )
    if stats.cross_volume_bytes:
        plan.warnings.append(
            "{gb:.1f} GiB have to cross a volume boundary.".format(
                gb=stats.cross_volume_bytes / (1024**3)
            )
        )


# -- small helpers ----------------------------------------------------------


def _split(path_from_root: str) -> List[str]:
    stripped = (path_from_root or "").strip("/")
    return stripped.split("/") if stripped else []


def _last_segment(path_from_root: str) -> str:
    parts = _split(path_from_root)
    return parts[-1] if parts else ""


def _join(root: str, segments: Sequence[str]) -> str:
    base = root.rstrip("/")
    if not segments:
        return base
    return "{b}/{s}".format(b=base, s=str(PurePosixPath(*segments)))


def _key(path: str) -> str:
    """Case-insensitive comparison key.

    macOS (HFS+/APFS default) and Windows are case insensitive, and exFAT --
    the usual filesystem on external photo drives -- is too. Treating names
    case sensitively here would let two files collide silently on the target.
    """
    return os.path.normpath(path).lower()


def _device_of(path: str) -> Optional[int]:
    """``st_dev`` of the nearest existing ancestor of *path*."""
    current = Path(path)
    for candidate in [current] + list(current.parents):
        try:
            return os.stat(str(candidate)).st_dev
        except OSError:
            continue
    return None


def lr_folder_paths(plan: Plan) -> List[str]:
    """``pathFromRoot`` values the executor has to make sure exist."""
    return sorted({lr_path_from_root(segs) for segs in plan.new_folder_segments})
