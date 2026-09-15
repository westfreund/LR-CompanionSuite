"""Turning a search result into catalogs Lightroom can merge.

The obvious way to build a catalog from a selection is to write one. That means
recreating develop settings, collections, stacks, previews and a hundred
columns whose meaning is Adobe's business -- and getting any of it wrong
produces a catalog that opens and is subtly wrong, which is the worst outcome
available.

So this goes the other way round. It **copies** the source catalog and removes
from the copy every photograph that was not selected. Whatever survives was
written by Lightroom itself and is therefore right by construction: develop
settings, keywords, collections, ratings, all of it. The original is opened
only to be copied, and never written to.

One reduced catalog comes out per source catalog. Lightroom's own *Import from
Another Catalog* merges them, which is a thing it does well and this tool has
no business reimplementing.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Callable, NamedTuple, Optional

from ..logging_setup import get_logger
from .store import Index

log = get_logger("index.subset")

#: Columns that name a photograph. Found by inspection rather than listed,
#: because the list is 46 tables long in one catalog and a different length in
#: the next -- a hard-coded list would rot with the first Lightroom release.
IMAGE_COLUMNS = ("image", "photo")


class Reduced(NamedTuple):
    """One catalog that came out of the reduction."""

    source: Path
    target: Path
    kept: int
    removed: int
    bytes_before: int
    bytes_after: int


class SubsetError(Exception):
    """The reduction could not be carried out."""


def _copy_with_journal(source: Path, target: Path) -> None:
    """Copy the catalog *and* its write-ahead log.

    A catalog in WAL mode keeps recently committed data in ``<name>.lrcat-wal``
    until it is checkpointed. Copying only the ``.lrcat`` therefore takes a
    version of the library that is missing whatever Lightroom did last -- work
    that is not lost, because the original keeps it, but silently absent from
    the copy. That is the quietest kind of wrong.
    """
    shutil.copy2(str(source), str(target))
    for suffix in ("-wal", "-shm"):
        companion = source.with_name(source.name + suffix)
        if companion.exists():
            shutil.copy2(str(companion), str(target.with_name(target.name + suffix)))


def _tables_referring_to_images(db: sqlite3.Connection) -> list[tuple[str, str]]:
    found = []
    for (table,) in db.execute("select name from sqlite_master where type = 'table'").fetchall():
        for row in db.execute('pragma table_info("{t}")'.format(t=table)):
            if row[1] in IMAGE_COLUMNS:
                found.append((table, row[1]))
    return found


def _expand_to_masters(db: sqlite3.Connection, keep: set[int]) -> set[int]:
    """A virtual copy cannot live without the photograph it is a copy of."""
    complete = set(keep)
    for (master,) in db.execute(
        "select distinct masterImage from Adobe_images"
        " where masterImage is not null and id_local in ({m})".format(
            m=",".join(str(int(i)) for i in keep) or "null"
        )
    ):
        if master is not None:
            complete.add(int(master))
    return complete


def reduce_catalog(
    source: Path,
    target: Path,
    keep_ids: set[int],
    progress: Optional[Callable[[str], None]] = None,
) -> Reduced:
    """Copy *source* to *target* and remove everything but *keep_ids*."""
    source = Path(source)
    target = Path(target)
    if not source.exists():
        raise SubsetError("catalog not found: {p}".format(p=source))
    if target.exists():
        raise SubsetError("refusing to overwrite {p}".format(p=target))
    if not keep_ids:
        raise SubsetError("nothing selected from {p}".format(p=source.name))

    target.parent.mkdir(parents=True, exist_ok=True)
    if progress:
        progress("copying {n}".format(n=source.name))
    _copy_with_journal(source, target)
    before = target.stat().st_size

    db = sqlite3.connect(str(target))
    try:
        # Fold the write-ahead log into the database proper, so what follows
        # sees everything Lightroom had committed and the result is one file.
        db.execute("pragma wal_checkpoint(truncate)")
        # The copy is ours alone, and the deletions are deliberately not in the
        # order any foreign key would like. Lightroom does not rely on SQLite
        # to enforce them.
        db.execute("pragma foreign_keys = off")

        total = int(db.execute("select count(*) from Adobe_images").fetchone()[0])
        keep = _expand_to_masters(db, keep_ids)

        db.execute("create temporary table _keep (id integer primary key)")
        db.executemany("insert or ignore into _keep (id) values (?)", [(int(i),) for i in keep])

        for table, column in _tables_referring_to_images(db):
            if progress:
                progress("thinning {t}".format(t=table))
            db.execute(
                'delete from "{t}" where "{c}" is not null'
                ' and "{c}" not in (select id from _keep)'.format(t=table, c=column)
            )

        db.execute("delete from Adobe_images where id_local not in (select id from _keep)")

        # What is left of the file and folder tree once the photographs are gone.
        db.execute(
            "delete from AgLibraryFile where id_local not in"
            " (select rootFile from Adobe_images where rootFile is not null)"
        )
        # Folders nest, so emptying them is repeated until nothing more falls out.
        while True:
            removed = db.execute(
                "delete from AgLibraryFolder where id_local not in"
                " (select folder from AgLibraryFile where folder is not null)"
                " and id_local not in"
                " (select parentId from AgLibraryFolder where parentId is not null)"
            ).rowcount
            if removed <= 0:
                break
        db.execute(
            "delete from AgLibraryRootFolder where id_local not in"
            " (select rootFolder from AgLibraryFolder where rootFolder is not null)"
        )

        kept = int(db.execute("select count(*) from Adobe_images").fetchone()[0])
        db.commit()
        if progress:
            progress("compacting")
        db.execute("vacuum")
        db.commit()
        # Leave one file behind, not three. Lightroom will make its own journal
        # when it opens the catalog.
        db.execute("pragma journal_mode = delete")
    except Exception as exc:  # noqa: BLE001 - the copy is worthless if this failed
        db.close()
        target.unlink(missing_ok=True)
        raise SubsetError("could not reduce {n}: {e}".format(n=source.name, e=exc)) from exc
    finally:
        try:
            db.close()
        except Exception:  # noqa: BLE001 - already closed on the error path
            pass

    # The shared-memory file outlives the connection that made it. Left behind
    # it is harmless but untidy, and it makes the result look like three files
    # when it is one.
    for suffix in ("-wal", "-shm"):
        target.with_name(target.name + suffix).unlink(missing_ok=True)

    after = target.stat().st_size
    log.info("Reduced %s: %d of %d photographs kept", source.name, kept, total)
    return Reduced(source, target, kept, total - kept, before, after)


def selection_by_catalog(index: Index, photo_ids: list[int]) -> dict[int, set[int]]:
    """Group chosen index rows by the catalog they came from."""
    grouped: dict[int, set[int]] = {}
    marks = ",".join("?" for _ in photo_ids)
    for catalog_id, local_id in index.db.execute(
        "select catalog, local_id from photos where id in ({m})".format(m=marks),
        [int(i) for i in photo_ids],
    ):
        grouped.setdefault(int(catalog_id), set()).add(int(local_id))
    return grouped


def build(
    index: Index,
    photo_ids: list[int],
    target_directory: str | Path,
    progress: Optional[Callable[[str], None]] = None,
) -> list[Reduced]:
    """Reduce every catalog the selection touches, into *target_directory*."""
    directory = Path(target_directory).expanduser()
    grouped = selection_by_catalog(index, photo_ids)
    if not grouped:
        raise SubsetError("the selection is empty")

    results = []
    used: set[str] = set()
    for catalog_id, local_ids in grouped.items():
        row = index.db.execute(
            "select full_path, name from catalogs where id = ?", (catalog_id,)
        ).fetchone()
        if row is None:  # pragma: no cover - the index would have to be corrupt
            continue
        source = Path(row[0])
        if not source.exists():
            log.warning("Skipping %s: the drive is not attached", source)
            results.append(Reduced(source, Path(""), 0, 0, 0, 0))
            continue
        # Two libraries may be called the same thing; the file names must not
        # collide in the target directory.
        stem = row[1]
        candidate = stem
        suffix = 2
        while candidate in used:
            candidate = "{s}-{n}".format(s=stem, n=suffix)
            suffix += 1
        used.add(candidate)
        results.append(
            reduce_catalog(source, directory / "{c}.lrcat".format(c=candidate), local_ids, progress)
        )
    return results
