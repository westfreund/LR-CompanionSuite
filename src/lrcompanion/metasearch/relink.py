"""Pointing a copied catalog at where the photographs actually are.

A Lightroom catalog stores the location of its photographs as an absolute path
in ``AgLibraryRootFolder.absolutePath``. Drives get renamed and libraries get
moved, and the catalog does not notice: it keeps naming a volume that no longer
exists. Opened on its own machine that is a nuisance; handed to somebody as a
reduced export it looks like the export is broken.

This finds the real location -- and, importantly, **proves** it before using
it. A candidate counts only when every folder sampled from the catalog is
really there. Repointing to a directory that merely looks plausible would be
guessing, and guessing about where somebody's photographs are is not something
this tool does.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import List, NamedTuple, Optional

from ..logging_setup import get_logger

log = get_logger("metasearch.relink")

#: How many files are checked before a candidate is believed. One could be a
#: coincidence; six photographs with the same names in the same folders are
#: not.
SAMPLE_FILES = 6

#: How far above the catalog to look. The photographs usually sit beside it or
#: a level or two up; beyond that the search stops being a search.
LEVELS_UP = 4


class Relinked(NamedTuple):
    """One root folder that was pointed somewhere else."""

    root_id: int
    was: str
    now: str
    checked: int


def _samples(db: sqlite3.Connection, root_id: int) -> List[str]:
    """Paths of real photographs below the root, relative to it.

    Files rather than folders. A library whose photographs all sit in the root
    folder has no subfolders to check -- and a folder that happens to have the
    right name is weaker proof than a photograph that is actually there.
    """
    return [
        "{p}{b}.{e}".format(p=row[0] or "", b=row[1], e=row[2])
        for row in db.execute(
            "select fo.pathFromRoot, f.baseName, f.extension"
            " from AgLibraryFile f join AgLibraryFolder fo on fo.id_local = f.folder"
            " where fo.rootFolder = ? limit ?",
            (root_id, SAMPLE_FILES),
        )
    ]


def _holds(candidate: Path, samples: List[str]) -> bool:
    """True only when every sampled photograph is really inside *candidate*."""
    if not samples or not candidate.is_dir():
        return False
    return all((candidate / sample).exists() for sample in samples)


def find_root(stated: str, catalog: Path, samples: List[str]) -> Optional[Path]:
    """Where the photographs of *stated* actually are, or None.

    Looks in the catalog's own directory and a few above it, trying each tail
    of the stated path against them -- a library moved from
    ``/Volumes/Old/Andy/shootings`` to ``/Volumes/New/lr/Andy/shootings`` is
    found because the tail still matches, and it is only accepted once the
    folders check out.
    """
    tail = [part for part in stated.strip("/").split("/") if part]
    here = catalog.resolve().parent
    seen = set()
    for level in range(LEVELS_UP + 1):
        base = here
        for _ in range(level):
            base = base.parent
        for take in range(len(tail) + 1):
            candidate = base.joinpath(*tail[len(tail) - take :]) if take else base
            if candidate in seen:
                continue
            seen.add(candidate)
            if _holds(candidate, samples):
                return candidate
    return None


def relink(db: sqlite3.Connection, source_catalog: Path) -> List[Relinked]:
    """Repoint every root folder of *db* whose stated path has gone.

    *db* must be a catalog this tool owns -- a copy. The original is never
    opened for writing, here or anywhere else.
    """
    changed: List[Relinked] = []
    for root_id, stated in db.execute(
        "select id_local, absolutePath from AgLibraryRootFolder"
    ).fetchall():
        if not stated or os.path.isdir(stated):
            continue
        samples = _samples(db, root_id)
        found = find_root(stated, source_catalog, samples)
        if found is None:
            log.info("Could not find where %s really is", stated)
            continue
        # Lightroom stores the root with a trailing separator; without it the
        # paths it builds come out missing one.
        now = str(found)
        if not now.endswith(os.sep):
            now += os.sep
        db.execute(
            "update AgLibraryRootFolder set absolutePath = ? where id_local = ?",
            (now, root_id),
        )
        log.info("Repointed %s to %s", stated, now)
        changed.append(Relinked(int(root_id), stated, now, len(samples)))
    return changed
