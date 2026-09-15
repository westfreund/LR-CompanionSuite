"""Find catalogs, read them, and put what they hold into the index.

Reading only. No catalog is opened writable, no photograph is touched, and a
catalog Lightroom currently has open is reported and left alone rather than
read behind its back.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import os
from pathlib import Path
from typing import Callable, Iterator, NamedTuple, Optional

from ..catalog.db import is_locked, open_catalog
from ..logging_setup import get_logger
from .store import Index
from .volumes import describe, mount_point

log = get_logger("index.scan")

#: AppleDouble companions and Lightroom's own working directories. Walking into
#: a previews bundle costs minutes and yields nothing.
SKIP_DIRECTORIES = {".lrdata", ".lrprev", "Lightroom Catalog Previews.lrdata"}

#: How many image UUIDs make up a catalog's fingerprint. A *sample* rather than
#: all of them on purpose: a catalog that has grown since the copy was taken
#: still has to match the copy. Taking all of them would have missed the pair of
#: FineArt catalogs that differ by two photographs out of 3,296.
#:
#: Drawn in *insertion* order, not UUID order. Sorting by UUID scatters new
#: photographs evenly through the sample, so whether a grown copy still matched
#: came down to luck -- it happened to work on the real catalogs and failed the
#: moment a test added one photograph to a library of three. The oldest
#: photographs are the ones a copy and its original still share.
FINGERPRINT_SAMPLE = 500

PHOTO_QUERY = """
select i.id_local, i.id_global, rf.absolutePath, fo.pathFromRoot,
       f.baseName, f.extension, i.captureTime,
       cm.value, ln.value,
       e.isoSpeedRating, e.focalLength, e.aperture, e.shutterSpeed,
       i.fileWidth, i.fileHeight, i.fileFormat, i.rating, i.colorLabels,
       e.gpsLatitude, e.gpsLongitude, i.masterImage
from Adobe_images i
join AgLibraryFile f on f.id_local = i.rootFile
join AgLibraryFolder fo on fo.id_local = f.folder
join AgLibraryRootFolder rf on rf.id_local = fo.rootFolder
left join AgHarvestedExifMetadata e on e.image = i.id_local
left join AgInternedExifCameraModel cm on cm.id_local = e.cameraModelRef
left join AgInternedExifLens ln on ln.id_local = e.lensRef
"""

KEYWORD_QUERY = """
select ki.image, k.name
from AgLibraryKeywordImage ki
join AgLibraryKeyword k on k.id_local = ki.tag
where k.name is not null
"""


class Outcome(NamedTuple):
    """What became of one catalog during a scan."""

    path: Path
    state: str  # 'read' | 'copy' | 'locked' | 'failed' | 'empty'
    images: int = 0
    detail: str = ""


def find_catalogs(roots: list[str | Path]) -> list[Path]:
    """Every ``.lrcat`` below *roots*, newest-looking name last."""
    found: list[Path] = []
    for root in roots:
        base = Path(root).expanduser()
        if base.is_file() and base.suffix.lower() == ".lrcat":
            found.append(base.resolve())
            continue
        for directory, subdirectories, files in os.walk(str(base), followlinks=False):
            subdirectories[:] = [
                d
                for d in subdirectories
                if not any(d.endswith(s) or d == s for s in SKIP_DIRECTORIES)
            ]
            for name in files:
                # AppleDouble companions carry the same name with a "._" prefix
                # and are not databases.
                if name.startswith("._") or not name.lower().endswith(".lrcat"):
                    continue
                found.append(Path(directory) / name)
    return sorted(set(found))


def _where(path: Path) -> str:
    """Name the catalog by its folder too.

    Copies usually share the file name -- saying "a copy of FineArt.lrcat"
    when both are called that tells the reader nothing.
    """
    return "{d}/{n}".format(d=path.parent.name, n=path.name)


def _f_number(apex: Optional[float]) -> Optional[float]:
    """Lightroom stores aperture in APEX; people read f-numbers."""
    if apex is None:
        return None
    try:
        return round(2 ** (float(apex) / 2), 2)
    except (ValueError, OverflowError):  # pragma: no cover - corrupt value
        return None


def _seconds(apex: Optional[float]) -> Optional[float]:
    """Likewise the shutter speed: APEX in, seconds out."""
    if apex is None:
        return None
    try:
        return 2 ** (-float(apex))
    except (ValueError, OverflowError):  # pragma: no cover - corrupt value
        return None


def _sameness(capture, camera, base_name, width, height) -> Optional[str]:
    """The key two copies of the same photograph share.

    Capture time, camera, file name and pixel size together. Any one of them
    repeats across a library; all four together do not, unless the photograph
    really is the same one. Answerable from the catalog alone, so it works with
    the drive in a cupboard.
    """
    if not base_name:
        return None
    material = "|".join(
        [
            str(capture or "")[:19],
            str(camera or ""),
            str(base_name).lower(),
            str(int(width or 0)),
            str(int(height or 0)),
        ]
    )
    return hashlib.sha1(material.encode("utf-8")).hexdigest()


def sample(connection) -> list:
    """The UUIDs of this catalog's oldest photographs.

    Insertion order, not UUID order: photographs added after a copy was taken
    sort randomly among the others when ordered by UUID, so whether a grown
    copy was still recognisable came down to luck. The oldest photographs are
    what a copy and its original still have in common.
    """
    return [
        str(row[0])
        for row in connection.query(
            "select id_global from Adobe_images order by id_local limit ?",
            (FINGERPRINT_SAMPLE,),
        )
    ]


def fingerprint(uuids: list) -> str:
    """A short name for a sample, stored so a person can compare two rows."""
    if not uuids:
        return ""
    return hashlib.sha256("".join(uuids).encode("utf-8")).hexdigest()


def _rows(connection) -> Iterator[tuple]:
    """Every photograph in the catalog, shaped for the index."""
    keywords: dict[int, list[str]] = {}
    for image, name in connection.query(KEYWORD_QUERY):
        keywords.setdefault(image, []).append(name)

    for row in connection.query(PHOTO_QUERY):
        (
            local_id,
            uuid,
            absolute,
            relative,
            base_name,
            extension,
            capture,
            camera,
            lens,
            iso,
            focal,
            aperture,
            shutter,
            width,
            height,
            file_format,
            rating,
            colour,
            latitude,
            longitude,
            master,
        ) = row
        folder = "{a}{r}".format(a=absolute or "", r=relative or "")
        is_copy = 1 if master is not None else 0
        yield (
            local_id,
            uuid,
            folder,
            base_name,
            extension,
            capture,
            camera,
            lens,
            int(iso) if iso is not None else None,
            float(focal) if focal is not None else None,
            _f_number(aperture),
            _seconds(shutter),
            int(width) if width is not None else None,
            int(height) if height is not None else None,
            file_format,
            int(rating) if rating is not None else None,
            colour or None,
            latitude,
            longitude,
            is_copy,
            # A virtual copy shares its file with its master; counting it as a
            # duplicate would report every edited photograph as one.
            None if is_copy else _sameness(capture, camera, base_name, width, height),
            keywords.get(local_id, []),
        )


@contextlib.contextmanager
def _without_schema_warnings():
    """Keep one warning out of a read-only scan.

    Opening a catalog whose schema was not explicitly verified says "check the
    result in Lightroom", which is sound advice when something is about to be
    written and nonsense when nothing is. The version is recorded per catalog
    in the index instead, where a reader can act on it.
    """
    from ..logging_setup import get_logger as _named

    logger = _named("catalog.db")
    previous = logger.level
    logger.setLevel(logging.ERROR)
    try:
        yield
    finally:
        logger.setLevel(previous)


def scan(
    roots: list[str | Path],
    index: Index,
    progress: Optional[Callable[[int, int, str], None]] = None,
    include_locked: bool = False,
) -> list[Outcome]:
    """Read every catalog below *roots* into *index*.

    Returns one :class:`Outcome` per catalog found, including the ones that
    were skipped -- a scan that silently omits a library is worse than one that
    fails, because the gap is invisible afterwards.
    """
    catalogs = find_catalogs(roots)
    outcomes: list[Outcome] = []

    for number, path in enumerate(catalogs, start=1):
        if progress:
            progress(number, len(catalogs), path.name)

        if is_locked(path) and not include_locked:
            outcomes.append(Outcome(path, "locked", 0, "Lightroom has this catalog open"))
            continue

        volume = describe(path)
        try:
            relative = str(path.relative_to(mount_point(path)))
        except ValueError:  # pragma: no cover - path not below its own mount
            relative = str(path)

        try:
            # allow_unsupported: the index reads a handful of long-stable
            # tables, so an older or newer schema is no reason to refuse.
            with (
                _without_schema_warnings(),
                open_catalog(path, writable=False, allow_unsupported=True) as connection,
            ):
                uuids = sample(connection)
                mark = fingerprint(uuids)
                images = int(connection.scalar("select count(*) from Adobe_images") or 0)
                keyword_count = int(
                    connection.scalar(
                        "select count(*) from AgLibraryKeyword where name is not null"
                    )
                    or 0
                )
                version = str(connection.variable("Adobe_DBVersion") or "")

                if not images:
                    outcomes.append(Outcome(path, "empty", 0, "no photographs"))
                    continue

                index.remember_volume(volume)
                index.forget_catalog(volume.identity, relative)
                catalog_id = index.add_catalog(
                    volume.identity,
                    relative,
                    str(path),
                    path.stem,
                    mark,
                    images,
                    keyword_count,
                    version,
                )
                index.add_photos(catalog_id, _rows(connection))
                # Stored before the twin is looked for, so that a later scan
                # can recognise a copy of this catalog too -- not only the ones
                # that happen to be found in the same run.
                index.remember_sample(catalog_id, uuids)
                index.db.commit()
        except Exception as exc:  # noqa: BLE001 - one bad catalog must not stop the scan
            # Undo the half-written catalog, or the index would list a library
            # it never managed to read and report it as holding no photographs.
            index.db.rollback()
            log.warning("Could not read %s: %s", path, exc)
            outcomes.append(Outcome(path, "failed", 0, str(exc)))
            continue

        twin = index.find_twin_excluding(uuids, catalog_id)
        if twin is not None:
            other = index.describe_catalog(twin)
            # The one with more photographs is the later state of the two. The
            # other is recorded as a copy, never deleted: which one is the
            # valid one is a person's decision, not this program's.
            if images > other["images"]:
                index.mark_superseded(twin, catalog_id, "a copy of {n}".format(n=_where(path)))
                outcomes.append(Outcome(path, "read", images))
                for position, older in enumerate(outcomes):
                    if str(older.path) == other["full_path"] and older.state == "read":
                        outcomes[position] = Outcome(
                            older.path,
                            "copy",
                            other["images"],
                            "copy of {n}".format(n=_where(path)),
                        )
            else:
                where = Path(other["full_path"])
                index.mark_superseded(catalog_id, twin, "a copy of {n}".format(n=_where(where)))
                outcomes.append(
                    Outcome(path, "copy", images, "copy of {n}".format(n=_where(where)))
                )
            index.db.commit()
            continue

        outcomes.append(Outcome(path, "read", images))

    return outcomes
