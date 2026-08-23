"""Turn a catalog plus a :class:`~lrfoldercraft.config.Settings` into a Plan.

The planner never touches the filesystem or the catalog beyond reading. Its
output is a fully materialised list of intended moves that can be reviewed,
exported and only then executed. Everything the executor needs to know --
including conflicts, sidecars and cross-volume transfers -- is decided here.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .catalog.model import Folder, Photo, RootFolder, lr_path_from_root
from .catalog.reader import CatalogReader
from .config import Settings
from .folders import (
    KEEP,
    LEAVE,
    MOVE_OUT,
    REFILE,
    RELOCATE,
    RESORT,
    SORT_INSIDE,
    FolderCase,
    classify,
    first_matching_rule,
    folder_label,
    usable_action,
)
from .logging_setup import get_logger, step
from .orphans import Orphan, find_orphans
from .rules import (
    TokenContext,
    render_structure,
    sanitise_segment,
    structure_date_granularity,
    structure_requires_date,
)

log = get_logger("planner")

#: Asked once per folder that could reasonably be handled either way. Returning
#: ``None`` accepts the configured default. Front ends supply this; no core
#: module prompts on its own.
FolderDecider = Callable[[FolderCase], Optional[str]]

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
    SKIP_NO_DATE: ("skipped, no usable date", "übersprungen, kein Datum"),
    SKIP_CONFLICT: ("skipped, target name taken", "übersprungen, Zielname belegt"),
    SKIP_FILTERED: ("skipped by extension filter", "durch Endungsfilter ausgeschlossen"),
    SKIP_MISSING_SOURCE: ("skipped, file missing on disk", "übersprungen, Datei fehlt"),
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
    #: Index into :attr:`Plan.scopes`.
    scope: int = 0

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
    orphans: int = 0
    orphan_bytes: int = 0
    virtual_copies_carried: int = 0
    new_folders: int = 0
    bytes_to_move: int = 0
    cross_volume_bytes: int = 0

    @property
    def touched(self) -> int:
        return self.to_move + self.to_rename


@dataclass
class RootScope:
    """One source root folder and where its photos are sorted to.

    A catalog can hold several root folders, possibly on different drives. Each
    gets its own anchor, because "the folder every selected photo sits under"
    only means something within one root. With ``new-tree`` placement all source
    roots share a single scope: everything is consolidated into the new tree.
    """

    root_folder: RootFolder
    anchor_segments: Tuple[str, ...]
    #: Filesystem path the structure is built under.
    target_root_path: str
    #: Catalog ``AgLibraryRootFolder`` id the target folders belong to. Filled
    #: in during execution, because a new tree has no row until it is created.
    target_root_id: Optional[int] = None
    cross_volume: bool = False

    @property
    def name(self) -> str:
        return self.root_folder.name


@dataclass
class Plan:
    """The complete, reviewable result of planning a run."""

    settings: Settings
    catalog_path: str
    placement: str
    scopes: List[RootScope] = field(default_factory=list)
    #: Source root folder id -> index into :attr:`scopes`.
    scope_of: Dict[int, int] = field(default_factory=dict)
    moves: List[PlannedMove] = field(default_factory=list)
    #: ``(scope index, segments)`` for every target folder that will hold files.
    new_folders: List[Tuple[int, Tuple[str, ...]]] = field(default_factory=list)
    source_folder_ids: Tuple[int, ...] = ()
    folder_cases: List[FolderCase] = field(default_factory=list)
    #: Files found on disk that the catalog does not reference, and where they
    #: would be collected. Empty unless ``settings.collect_orphans`` is set.
    orphans: List[Orphan] = field(default_factory=list)
    #: Directories the sweep could not read, with the reason.
    orphans_unreadable: List[str] = field(default_factory=list)
    stats: PlanStats = field(default_factory=PlanStats)
    warnings: List[str] = field(default_factory=list)
    created_at: str = ""

    # -- convenience for the common single-root case ---------------------

    @property
    def root_folder(self) -> RootFolder:
        return self.scopes[0].root_folder

    @property
    def anchor_segments(self) -> Tuple[str, ...]:
        return self.scopes[0].anchor_segments

    @property
    def target_root_path(self) -> str:
        return self.scopes[0].target_root_path

    @property
    def spans_several_roots(self) -> bool:
        return len({id(s) for s in self.scopes}) > 1

    def scope_for(self, move: PlannedMove) -> RootScope:
        return self.scopes[move.scope]

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


#: Prefix macOS uses for AppleDouble companion files.
APPLEDOUBLE_PREFIX = "._"


def appledouble_name(filename: str) -> str:
    """Name of the AppleDouble companion belonging to *filename*."""
    return APPLEDOUBLE_PREFIX + filename


def discover_companions(photo: Photo, index: Optional[DirectoryIndex] = None) -> List[str]:
    """Return files that are physically *part of* the photo, not sidecars.

    On filesystems that cannot store extended attributes and resource forks
    natively -- exFAT and FAT, which is what most external photo drives use --
    macOS keeps them in an AppleDouble companion named ``._<filename>``.

    **On macOS the kernel moves that companion itself.** Measured on an exFAT
    volume: writing an extended attribute to ``X.dat`` created ``._X.dat``, and
    after ``os.replace("X.dat", "sub/X.dat")`` the companion had moved to
    ``sub/`` on its own with the attributes still readable on the moved file.
    Moving it explicitly would collide with the file macOS has already put at
    the target -- which is exactly what aborted the first live run against the
    reference library.

    Other platforms have no such emulation: there ``._X`` is an ordinary file
    that a rename leaves behind, orphaning the macOS metadata of a drive that
    will eventually be plugged back into a Mac. So it is moved explicitly, and
    unconditionally -- ``--no-sidecars`` governs genuine sidecar documents such
    as XMP, not the other half of a file.
    """
    if sys.platform == "darwin":
        return []
    index = index or DirectoryIndex()
    directory = str(Path(photo.absolute_path).parent)
    actual = index.find(directory, appledouble_name(photo.filename))
    return [actual] if actual else []


def discover_sidecars(
    photo: Photo, settings: Settings, index: Optional[DirectoryIndex] = None
) -> List[str]:
    """Return absolute paths of sidecar files that must travel with *photo*.

    Two naming conventions are recognised, both of which occur in the wild:
    ``IMG_1234.xmp`` (Adobe's own) and ``IMG_1234.CR2.xmp`` (many third party
    converters). Extensions Lightroom itself recorded in
    ``AgLibraryFile.sidecarExtensions`` are always included. The photo's own
    file is never reported as its own sidecar.

    AppleDouble companions are handled separately by :func:`discover_companions`
    because they are part of the file rather than a document beside it.
    """
    if not settings.move_sidecars:
        return []
    index = index or DirectoryIndex()
    source = Path(photo.absolute_path)
    directory = str(source.parent)
    extensions: Set[str] = {e.lower().lstrip(".") for e in settings.extra_sidecar_extensions}
    extensions.update(e.lower().lstrip(".") for e in photo.sidecar_list)
    extensions.discard("")

    seen: Set[str] = {photo.filename.lower(), appledouble_name(photo.filename).lower()}
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
    settings: Settings,
    root: RootFolder,
    photos: Sequence[Photo],
    folders: Optional[Dict[int, Folder]] = None,
) -> Tuple[str, ...]:
    """Decide below which folder the new structure is built, within one root.

    ``in-place``  the deepest folder that already contains every selected photo
                  of this root -- for the common "one year folder" case that is
                  exactly that year folder, so the day folders appear inside it.
    ``new-tree``  the structure starts at the configured target root, so the
                  anchor below the (new) root folder is empty.
    """
    if settings.placement == "new-tree":
        return ()

    if settings.anchor_folder_id is not None:
        # Look the folder up in the catalog, not among the photos: an anchor
        # folder usually holds no files of its own, only subfolders.
        folder = (folders or {}).get(settings.anchor_folder_id)
        if folder is None:
            raise PlanError(
                "anchor folder id {i} not found in the catalog".format(i=settings.anchor_folder_id)
            )
        if folder.root_folder != root.id_local:
            raise PlanError(
                "anchor folder id {i} belongs to a different root folder".format(
                    i=settings.anchor_folder_id
                )
            )
        return folder.segments

    return common_prefix(
        tuple(p.folder_path_from_root.strip("/").split("/"))
        if p.folder_path_from_root.strip("/")
        else ()
        for p in photos
    )


def build_scopes(
    reader: CatalogReader,
    settings: Settings,
    prepared: Sequence[Tuple[Photo, Optional[Tuple[str, ...]], str]],
) -> Tuple[List[RootScope], Dict[int, int]]:
    """Build one scope per source root folder, or a single shared one.

    Returns the scopes and a mapping from source root folder id to scope index.
    With ``new-tree`` every source root shares one scope, because everything is
    consolidated into the new tree regardless of where it came from.
    """
    roots = {r.id_local: r for r in reader.root_folders()}
    folders = {f.id_local: f for f in reader.folders()}
    by_root: Dict[int, List[Photo]] = {}
    for photo, _segments, _reason in prepared:
        by_root.setdefault(photo.root_folder_id, []).append(photo)

    scopes: List[RootScope] = []
    scope_of: Dict[int, int] = {}

    if settings.placement == "new-tree":
        target = str(Path(settings.target_root or "").expanduser())
        first = roots[sorted(by_root)[0]]
        scope = RootScope(root_folder=first, anchor_segments=(), target_root_path=target)
        scopes.append(scope)
        for root_id in by_root:
            scope_of[root_id] = 0
        return scopes, scope_of

    for root_id in sorted(by_root):
        root = roots[root_id]
        photos = by_root[root_id]
        anchor = resolve_anchor(settings, root, photos, folders)
        anchor = _normalise_anchor(
            anchor,
            settings,
            [entry for entry in prepared if entry[0].root_folder_id == root_id],
        )
        scope_of[root_id] = len(scopes)
        scopes.append(
            RootScope(
                root_folder=root,
                anchor_segments=anchor,
                target_root_path=root.normalised_path,
                target_root_id=root.id_local,
            )
        )
    return scopes, scope_of


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
        original_folder_label=folder_label(_last_segment(photo.folder_path_from_root)),
        language=settings.language,
    )
    return (
        render_structure(settings.effective_structure, context, ascii_only=settings.ascii_only),
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


def build_folder_cases(
    reader: CatalogReader,
    settings: Settings,
    prepared: Sequence[Tuple[Photo, Optional[Tuple[str, ...]], str]],
    decide: Optional[FolderDecider] = None,
    anchors: Optional[Dict[int, Tuple[str, ...]]] = None,
) -> Dict[int, FolderCase]:
    """Classify every source folder and settle what happens to it.

    Precedence, strongest first: an explicit per-folder entry in
    ``settings.folder_actions``; the operator's answer via *decide*; the
    configured default for the folder's kind.
    """
    folders = {f.id_local: f for f in reader.folders()}
    cases: Dict[int, FolderCase] = {}
    wanted = structure_date_granularity(settings.effective_structure)

    for photo, _segments, _reason in prepared:
        folder = folders.get(photo.folder_id)
        if folder is None:  # pragma: no cover - a file must have its folder
            continue
        case = cases.get(photo.folder_id)
        if case is None:
            case = classify(
                name=folder.name,
                folder_id=folder.id_local,
                path_from_root=folder.path_from_root,
                segments=folder.segments,
                wanted_granularity=wanted,
            )
            # The anchor folder is the container the run sorts *into*; it is
            # not one of the subfolders whose fate is in question, so it is
            # never offered as a decision and always behaves as consolidate.
            case.is_anchor = case.segments == (anchors or {}).get(photo.root_folder_id, ())
            cases[photo.folder_id] = case
        case.photo_count += 1
        if case.folder_date is not None:
            when = resolve_date(photo, settings)
            if when is not None and case.folder_date.matches(when.date()):
                case.matching_photos += 1
            else:
                case.mismatched_photos += 1

    rules = settings.parsed_folder_rules
    for case in cases.values():
        override = settings.folder_actions.get(case.folder_id)
        if override:
            case.action, case.action_source = usable_action(override, case), "override"
            continue

        # A rule is the operator speaking about a whole class of folders at
        # once, so it settles the matter and no question is asked. Folders no
        # rule speaks about still fall through to the interactive decision.
        hit = first_matching_rule(case, rules)
        if hit is not None:
            position, rule = hit
            case.action = usable_action(rule.action, case)
            case.action_source = "rule"
            case.matched_rule = "{n}. {p}".format(n=position, p=rule.pattern)
            continue

        case.action = settings.dated_folder_action if case.is_dated else settings.subfolder_action
        case.action_source = "default"
        if decide is not None and case.needs_a_decision:
            chosen = decide(case)
            if chosen:
                case.action, case.action_source = usable_action(chosen, case), "operator"
    return cases


def _consolidates(case: Optional[FolderCase], settings: Settings, photo: Photo) -> bool:
    """True when this photo will be moved below the run's shared anchor."""
    if case is None:
        return True
    if case.action in (LEAVE, SORT_INSIDE, RESORT):
        return False
    if case.action == RELOCATE:
        # It moves below the target root, but keeps its own path rather than
        # joining the shared anchor.
        return False
    if case.action == REFILE:
        # It does join the anchor, under a name of its own.
        return True
    if case.action == KEEP:
        when = resolve_date(photo, settings)
        matches = (
            case.folder_date is not None
            and when is not None
            and case.folder_date.matches(when.date())
        )
        if matches:
            return False
        return settings.mismatch_action == MOVE_OUT
    return True


def _render_at(photo: Photo, settings: Settings, when: datetime) -> Tuple[str, ...]:
    """Render the structure for *photo* as if it had been taken at *when*."""
    original = _last_segment(photo.folder_path_from_root)
    context = TokenContext(
        when=when,
        camera=photo.camera_model,
        camera_serial=photo.camera_serial,
        lens=photo.lens,
        file_format=photo.file_format,
        extension=photo.extension,
        original_folder=original,
        original_folder_label=folder_label(original),
        language=settings.language,
    )
    return render_structure(settings.effective_structure, context, ascii_only=settings.ascii_only)


def _keeps_the_session_together(
    photo: Photo, case: FolderCase, settings: Settings
) -> Optional[Tuple[str, ...]]:
    """Segments that file a stray photo under its *folder's* date, or ``None``.

    A shoot that runs past midnight leaves photos whose own date disagrees with
    the folder that names the session. Rebuilding such a folder by each photo's
    own date would tear the session in two, which is precisely what
    ``mismatch-action=leave`` says must not happen -- so those photos follow the
    folder's date instead of their own.
    """
    if settings.mismatch_action != LEAVE or case.folder_date is None:
        return None
    if case.folder_date.day is None:
        return None
    when = resolve_date(photo, settings)
    if when is not None and case.folder_date.matches(when.date()):
        return None
    return _render_at(
        photo,
        settings,
        datetime(case.folder_date.year, case.folder_date.month or 1, case.folder_date.day),
    )


def _segments_for(
    photo: Photo,
    case: Optional[FolderCase],
    settings: Settings,
    anchor: Tuple[str, ...],
    structure_segments: Tuple[str, ...],
    current: Tuple[str, ...],
) -> Tuple[str, ...]:
    """Where this photo should end up, given its folder's decision.

    Every action reduces to a choice of target segments; returning the photo's
    current folder is how "leave it alone" is expressed, because the planner
    then recognises it as already in place.
    """
    if case is None or case.is_anchor:
        # The anchor folder holds the photos the run exists to sort. "Leave
        # subfolders alone" must not silently mean "do nothing at all".
        return anchor + structure_segments

    if case.action == LEAVE:
        return current
    if case.action == SORT_INSIDE:
        return case.segments + structure_segments
    if case.action == REFILE:
        # File it where the structure says, but let the folder keep its name:
        # the descriptive text is appended to the deepest level. A plain
        # "2026-06-28" and a "2026-06-28 Makro Blume im Garten" then sit side
        # by side under the same month, which is the point -- merging them
        # would throw away the only thing that distinguishes the session.
        together = _keeps_the_session_together(photo, case, settings)
        segments = together if together is not None else structure_segments
        if case.label and segments:
            named = sanitise_segment(
                "{last} {label}".format(last=segments[-1], label=case.label),
                ascii_only=settings.ascii_only,
            )
            segments = segments[:-1] + (named,)
        return anchor + segments

    if case.action == RELOCATE:
        # Unchanged means unchanged: the folder keeps its name, its contents and
        # its own sub-structure, and lands under the run's target root at the
        # same relative path. No structure is rendered, and the anchor is
        # deliberately ignored -- prefixing it would bury the folder one level
        # deeper than "move this there" can reasonably mean. Sorting in place
        # therefore leaves the folder exactly where it is.
        return case.segments

    if case.action == RESORT:
        # Rebuild the folder where it stands: the structure replaces the folder
        # itself, below the same parent. This is what splits
        # "raw2026/2026-06-28 Makro Blume im Garten" into
        # "raw2026/2026-06-28/Makro Blume im Garten" instead of dragging the
        # photos out of raw2026 entirely.
        together = _keeps_the_session_together(photo, case, settings)
        return case.segments[:-1] + (together if together is not None else structure_segments)
    if case.action == KEEP:
        when = resolve_date(photo, settings)
        matches = (
            case.folder_date is not None
            and when is not None
            and case.folder_date.matches(when.date())
        )
        if matches:
            return current
        if settings.mismatch_action == LEAVE:
            return current
        return anchor + structure_segments
    return anchor + structure_segments


def build_plan(
    reader: CatalogReader,
    settings: Settings,
    decide: Optional[FolderDecider] = None,
) -> Plan:
    """Produce a :class:`Plan` for *settings* against the catalog behind *reader*."""
    settings.validate()
    step(
        "Planning run: structure=%s placement=%s",
        "/".join(settings.effective_structure),
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

    needs_date = structure_requires_date(settings.effective_structure)
    prepared: List[Tuple[Photo, Optional[Tuple[str, ...]], str]] = []
    for photo in photos:
        if not settings.accepts_extension(photo.extension):
            prepared.append((photo, None, _FILTERED))
            continue
        segments, reason = _structure_segments(photo, settings, needs_date)
        prepared.append((photo, segments, reason))

    # Anchors must be known before any folder decision is taken, so that the
    # anchor folder of each root is never itself put up for one.
    scopes, scope_of = build_scopes(reader, settings, prepared)
    anchors = {root_id: scopes[index].anchor_segments for root_id, index in scope_of.items()}

    cases = build_folder_cases(reader, settings, prepared, decide, anchors=anchors)
    if cases:
        step(
            "Classified %d source folder(s): %s",
            len(cases),
            ", ".join(
                "{p}={a}".format(p=c.path_from_root or ".", a=c.action)
                for c in sorted(cases.values(), key=lambda c: c.path_from_root)
            )[:400],
        )
    for scope in scopes:
        step(
            "Scope: root=%s anchor=%r target=%s",
            scope.root_folder.name,
            "/".join(scope.anchor_segments),
            scope.target_root_path,
        )

    plan = Plan(
        settings=settings,
        catalog_path=str(reader.conn.path),
        placement=settings.placement,
        scopes=scopes,
        scope_of=scope_of,
        source_folder_ids=tuple(sorted({p.folder_id for p in photos})),
        folder_cases=sorted(cases.values(), key=lambda c: c.path_from_root),
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    for scope in scopes:
        source_device = _device_of(scope.root_folder.normalised_path)
        target_device = _device_of(scope.target_root_path)
        scope.cross_volume = (
            source_device is not None
            and target_device is not None
            and source_device != target_device
        )
    if any(scope.cross_volume for scope in scopes):
        plan.warnings.append(
            "Target is on a different volume than the source; files are copied "
            "and verified, then the originals are removed. This takes much "
            "longer than a same-volume move."
        )
    if len(scopes) > 1:
        plan.warnings.append(
            "The selection spans {n} root folders. Each is sorted below its own "
            "anchor, in one transaction.".format(n=len(scopes))
        )

    # Claimed target paths -> the file that claimed them first.
    claimed: Dict[str, int] = {}
    folder_segments_seen: Set[Tuple[int, Tuple[str, ...]]] = set()
    index = DirectoryIndex()

    for photo, segments, reason in prepared:
        scope_index = scope_of[photo.root_folder_id]
        scope = scopes[scope_index]
        move = _plan_one(
            photo=photo,
            settings=settings,
            anchor=scope.anchor_segments,
            target_root_path=scope.target_root_path,
            structure_segments=segments,
            date_reason=reason,
            claimed=claimed,
            cross_volume=scope.cross_volume,
            index=index,
            case=cases.get(photo.folder_id),
        )
        move.scope = scope_index
        plan.moves.append(move)
        if move.is_active:
            folder_segments_seen.add((scope_index, move.target_segments))

    plan.new_folders = sorted(folder_segments_seen)

    # Only after every move is known: a sidecar is not an orphan, and neither
    # is a file this run is about to move.
    known = {photo.absolute_path for photo in photos}
    scan = find_orphans(scopes, plan.moves, known, settings)
    plan.orphans = scan.orphans
    plan.orphans_unreadable = scan.unreadable
    plan.stats.orphans = len(scan.orphans)
    plan.stats.orphan_bytes = scan.total_bytes
    if scan.orphans:
        step("Found %d file(s) on disk that the catalog does not know", len(scan.orphans))

    _fill_stats(plan)
    _add_warnings(plan)
    step(
        "Plan complete: %d move(s), %d already in place, %d skipped, %d target folder(s)",
        plan.stats.touched,
        plan.stats.already_in_place,
        plan.stats.total - plan.stats.touched - plan.stats.already_in_place,
        len(plan.new_folders),
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
    case: Optional[FolderCase] = None,
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
    current = tuple(_split(photo.folder_path_from_root))

    # "Leave" means leave, whatever the run is doing around it. Expressing it
    # as "the same path, under the target root" made it identical to relocate
    # as soon as the target root differed -- so a folder the operator had
    # explicitly excluded was carried into the new tree anyway.
    if case is not None and case.action == LEAVE and not case.is_anchor:
        base.status = STAY
        base.target_path = source_path
        base.target_segments = current
        base.reason = "folder decision: leave"
        return base

    segments = _segments_for(photo, case, settings, anchor, structure_segments, current)
    if case is not None and segments == current and not base.reason and not case.is_anchor:
        base.reason = "folder decision: {a}".format(a=case.action)
    base.target_segments = segments
    target_dir = _join(target_root_path, segments)
    target_path = "{d}/{f}".format(d=target_dir, f=photo.filename)

    # Whether a photo already sits where it belongs is a question about paths,
    # not about the placement mode. Tying it to in-place made a repeated
    # new-tree run plan every file as a move onto itself, which then tripped
    # the "never overwrite an existing file" guard and rolled the run back.
    if os.path.normpath(target_path) == os.path.normpath(source_path):
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

    pairs: List[Tuple[str, str]] = []

    # AppleDouble companions follow the file under its (possibly new) name.
    for companion in discover_companions(photo, index):
        companion_target = "{d}/{n}".format(d=target_dir, n=appledouble_name(target_filename))
        if _key(companion_target) in claimed:
            log.warning(
                "AppleDouble target %s is already claimed; leaving %s in place",
                companion_target,
                companion,
            )
            continue
        claimed[_key(companion_target)] = photo.file_id
        pairs.append((companion, companion_target))

    sidecars = discover_sidecars(photo, settings, index)
    if sidecars:
        target_stem = _stem(target_filename)
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
    stats.new_folders = len(plan.new_folders)
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
    return sorted({lr_path_from_root(segs) for _scope, segs in plan.new_folders})
