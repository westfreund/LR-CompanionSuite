"""Plain data objects mirroring the parts of the catalog we care about.

Only a small, well understood slice of the Lightroom schema is modelled:

``AgLibraryRootFolder``  -> :class:`RootFolder`
``AgLibraryFolder``      -> :class:`Folder`
``AgLibraryFile`` joined with ``Adobe_images`` and the harvested EXIF tables
                         -> :class:`Photo`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import PurePosixPath
from typing import Optional, Tuple


@dataclass(frozen=True)
class RootFolder:
    """A row of ``AgLibraryRootFolder`` -- a top level location in the catalog."""

    id_local: int
    id_global: str
    absolute_path: str
    name: str
    relative_path_from_catalog: Optional[str]

    @property
    def normalised_path(self) -> str:
        """Absolute path without the trailing slash Lightroom stores."""
        return self.absolute_path.rstrip("/")


@dataclass(frozen=True)
class Folder:
    """A row of ``AgLibraryFolder``.

    ``path_from_root`` is Lightroom's own convention: the empty string for the
    root folder itself, otherwise a POSIX style relative path *with* a trailing
    slash, e.g. ``2019-01-03/`` or ``2019/01/03/``.
    """

    id_local: int
    id_global: str
    parent_id: Optional[int]
    path_from_root: str
    root_folder: int
    visibility: Optional[int] = None

    @property
    def segments(self) -> Tuple[str, ...]:
        """Path components below the root folder."""
        stripped = self.path_from_root.strip("/")
        return tuple(stripped.split("/")) if stripped else ()

    @property
    def depth(self) -> int:
        return len(self.segments)

    @property
    def name(self) -> str:
        segments = self.segments
        return segments[-1] if segments else ""


@dataclass(frozen=True)
class Photo:
    """One physical file on disk plus the master image metadata attached to it.

    Virtual copies are *not* separate photos here: they share the same
    ``AgLibraryFile`` row, therefore moving the file automatically carries all
    of its virtual copies, develop history and collection memberships along.
    ``virtual_copy_count`` records how many exist, purely for reporting.
    """

    file_id: int
    file_id_global: str
    base_name: str
    extension: str
    filename: str
    folder_id: int
    root_folder_id: int
    folder_path_from_root: str
    root_absolute_path: str
    sidecar_extensions: Optional[str]

    image_id: Optional[int] = None
    capture_time_raw: Optional[str] = None
    file_format: Optional[str] = None
    camera_model: Optional[str] = None
    camera_serial: Optional[str] = None
    lens: Optional[str] = None
    exif_year: Optional[int] = None
    exif_month: Optional[int] = None
    exif_day: Optional[int] = None
    virtual_copy_count: int = 0

    @property
    def absolute_path(self) -> str:
        """Current absolute path of the file on disk (POSIX separators)."""
        root = self.root_absolute_path.rstrip("/")
        sub = self.folder_path_from_root.strip("/")
        parts = [root]
        if sub:
            parts.append(sub)
        parts.append(self.filename)
        return "/".join(parts)

    @property
    def capture_time(self) -> Optional[datetime]:
        """Parsed ``Adobe_images.captureTime``.

        Lightroom stores a local, timezone-less ISO-8601 string such as
        ``2019-01-03T17:42:29.18``. Length varies with fractional digits, and
        very old imports may carry date-only values.
        """
        return parse_capture_time(self.capture_time_raw)

    @property
    def sidecar_list(self) -> Tuple[str, ...]:
        """Sidecar extensions Lightroom recorded for this file (may be empty)."""
        if not self.sidecar_extensions:
            return ()
        raw = self.sidecar_extensions.replace(";", ",")
        return tuple(part.strip() for part in raw.split(",") if part.strip())


@dataclass
class CatalogInfo:
    """Summary of a catalog, produced by :meth:`CatalogReader.info`."""

    path: str
    schema_version: Optional[str]
    entity_id_counter: Optional[float]
    root_folders: int = 0
    folders: int = 0
    files: int = 0
    images: int = 0
    virtual_copies: int = 0
    missing_capture_time: int = 0
    earliest_capture: Optional[str] = None
    latest_capture: Optional[str] = None
    cameras: Tuple[Tuple[str, int], ...] = field(default_factory=tuple)
    file_formats: Tuple[Tuple[str, int], ...] = field(default_factory=tuple)


def parse_capture_time(raw: Optional[str]) -> Optional[datetime]:
    """Parse Lightroom's capture time string, tolerating its known variants."""
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    # Normalise a trailing timezone designator; Lightroom stores local time.
    if text.endswith("Z"):
        text = text[:-1]
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
        "%Y-%m",
        "%Y",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    # Values with an explicit offset, e.g. 2019-01-03T17:42:29+01:00.
    for cut in (len("YYYY-MM-DDTHH:MM:SS"),):
        try:
            return datetime.strptime(text[:cut], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return None


def lr_path_from_root(segments: Tuple[str, ...]) -> str:
    """Build a Lightroom ``pathFromRoot`` value from path *segments*."""
    if not segments:
        return ""
    return str(PurePosixPath(*segments)) + "/"
