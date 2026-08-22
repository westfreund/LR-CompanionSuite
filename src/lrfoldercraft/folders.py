"""Classification of the source folders a run touches.

A library that has grown over years rarely holds one flat folder. It holds
folders that already carry a date -- ``2019-04-15 Ostern in Tirol`` -- and
folders that carry a topic -- ``Urlaub``. Those deserve different treatment,
and which treatment is a judgement call, so this module only *classifies*.
Deciding is left to :mod:`lrfoldercraft.config` defaults, to a command line
flag, or to the operator answering per folder.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

# -- what a folder is -------------------------------------------------------

#: The folder name begins with a date, optionally followed by descriptive text.
DATED = "dated"
#: Any other folder: a topic, a shoot, an import batch.
PLAIN = "plain"

# -- what may be done with it ----------------------------------------------

#: Build the structure inside this folder, keeping it as a container.
SORT_INSIDE = "sort-inside"
#: Pull the photos up and sort them below the run's anchor.
CONSOLIDATE = "consolidate"
#: Do not touch the photos in this folder at all.
LEAVE = "leave"
#: A dated folder: keep it and leave the photos it correctly describes.
KEEP = "keep"

SUBFOLDER_ACTIONS = (SORT_INSIDE, CONSOLIDATE, LEAVE)
DATED_FOLDER_ACTIONS = (KEEP, CONSOLIDATE, SORT_INSIDE, LEAVE)

#: What to do with a photo inside a kept dated folder whose date does not match.
MOVE_OUT = "move-out"
MISMATCH_ACTIONS = (MOVE_OUT, LEAVE)

ACTION_LABELS = {
    SORT_INSIDE: (
        "sort by date inside this folder",
        "innerhalb dieses Ordners nach Datum sortieren",
    ),
    CONSOLIDATE: (
        "move the photos up and merge them",
        "Fotos herausholen und zusammenfuehren",
    ),
    LEAVE: ("leave the photos untouched", "Fotos unangetastet lassen"),
    KEEP: (
        "keep the folder and its matching photos",
        "Ordner mit seinen passenden Fotos behalten",
    ),
    MOVE_OUT: (
        "move the photo to its own date folder",
        "Foto in seinen eigenen Datumsordner verschieben",
    ),
}


def label(action: str, language: str = "en") -> str:
    en, de = ACTION_LABELS.get(action, (action, action))
    return de if language == "de" else en


# -- recognising a date in a folder name ------------------------------------

#: ``2019-04-15``, ``2019_04_15``, ``2019.04.15``, ``20190415`` at the start of
#: a name, followed by end-of-name or a separator before any descriptive text.
_DAY = re.compile(r"^(?P<y>\d{4})(?P<sep>[-_.])(?P<m>\d{2})(?P=sep)(?P<d>\d{2})(?![\d])")
_DAY_COMPACT = re.compile(r"^(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})(?![\d])")
_MONTH = re.compile(r"^(?P<y>\d{4})(?P<sep>[-_.])(?P<m>\d{2})(?![\d])")
_YEAR = re.compile(r"^(?P<y>\d{4})(?![\d])")

#: Granularity of a date found in a folder name.
DAY, MONTH, YEAR = "day", "month", "year"
#: A week sits between month and day; only a structure can have it.
WEEK = "week"

#: How fine each granularity is. A dated folder only counts as "already
#: expressing the structure" when it is at least as fine as the structure --
#: a folder called ``2019`` is no answer to a request for day folders.
FINENESS = {YEAR: 1, MONTH: 2, WEEK: 3, DAY: 4}


@dataclass(frozen=True)
class FolderDate:
    """A date recognised at the start of a folder name."""

    year: int
    month: Optional[int]
    day: Optional[int]
    granularity: str
    matched_text: str

    def matches(self, when: date) -> bool:
        """True when *when* falls inside the period this folder name names."""
        if when.year != self.year:
            return False
        if self.granularity == YEAR:
            return True
        if self.month is not None and when.month != self.month:
            return False
        if self.granularity == MONTH:
            return True
        return self.day is not None and when.day == self.day


def parse_folder_date(name: str) -> Optional[FolderDate]:
    """Recognise a leading date in *name*, or return ``None``.

    Deliberately conservative: the date must start the name and must not run
    straight into more digits, so ``2019-04-15 Ostern in Tirol`` and
    ``20190415_Hochzeit`` are recognised while ``20194`` and ``Sommer 2019``
    are not. Recognising a date in the middle of a name would guess at intent.
    """
    text = name.strip()
    for pattern, granularity in (
        (_DAY, DAY),
        (_DAY_COMPACT, DAY),
        (_MONTH, MONTH),
        (_YEAR, YEAR),
    ):
        match = pattern.match(text)
        if not match:
            continue
        groups = match.groupdict()
        try:
            year = int(groups["y"])
            month = int(groups["m"]) if groups.get("m") else None
            day = int(groups["d"]) if groups.get("d") else None
            if month is not None and not 1 <= month <= 12:
                continue
            if day is not None and not 1 <= day <= 31:
                continue
        except (TypeError, ValueError):
            continue
        return FolderDate(
            year=year,
            month=month,
            day=day,
            granularity=granularity,
            matched_text=match.group(0),
        )
    return None


def describes_only_a_date(name: str, folder_date: FolderDate) -> bool:
    """True when the name is *just* the date, with no descriptive text."""
    return name.strip() == folder_date.matched_text


# -- the classification a plan works with -----------------------------------


@dataclass
class FolderCase:
    """One source folder, what it looks like, and what will be done with it."""

    folder_id: int
    path_from_root: str
    segments: Tuple[str, ...]
    name: str
    kind: str
    photo_count: int = 0
    folder_date: Optional[FolderDate] = None
    matching_photos: int = 0
    mismatched_photos: int = 0
    action: str = CONSOLIDATE
    action_source: str = "default"
    #: Set when the folder is the run's anchor and therefore not a case at all.
    is_anchor: bool = False

    @property
    def is_dated(self) -> bool:
        return self.kind == DATED

    @property
    def needs_a_decision(self) -> bool:
        """True when a reasonable operator might choose differently."""
        return not self.is_anchor and self.photo_count > 0

    def describe(self, language: str = "en") -> str:
        if self.is_dated and self.folder_date is not None:
            what = ("datierter Ordner ({g})" if language == "de" else "dated folder ({g})").format(
                g=self.folder_date.granularity
            )
        else:
            what = "thematischer Ordner" if language == "de" else "topic folder"
        return "{p} - {w}, {n} {ph}".format(
            p=self.path_from_root or ".",
            w=what,
            n=self.photo_count,
            ph=("Fotos" if language == "de" else "photos"),
        )


def classify(
    name: str,
    folder_id: int,
    path_from_root: str,
    segments: Sequence[str],
    wanted_granularity: Optional[str] = None,
) -> FolderCase:
    """Build a :class:`FolderCase` for one folder, before photos are counted.

    A folder only counts as *dated* when the date in its name is at least as
    fine as *wanted_granularity*, the resolution the structure asks for. A
    folder named ``2019`` is no answer to a request for day folders, so it is
    treated as an ordinary topic folder and its photos get sorted properly.
    When the structure has no date tokens at all, an existing date in a folder
    name says nothing and is likewise ignored.
    """
    folder_date = parse_folder_date(name)
    if folder_date is not None and wanted_granularity is not None:
        if FINENESS[folder_date.granularity] < FINENESS[wanted_granularity]:
            folder_date = None
    elif folder_date is not None and wanted_granularity is None:
        folder_date = None
    return FolderCase(
        folder_id=folder_id,
        path_from_root=path_from_root,
        segments=tuple(segments),
        name=name,
        kind=DATED if folder_date is not None else PLAIN,
        folder_date=folder_date,
    )


def default_action(case: FolderCase, settings_actions: Dict[str, str]) -> str:
    """Pick the configured default action for *case*."""
    if case.is_dated:
        return settings_actions.get("dated", KEEP)
    return settings_actions.get("subfolder", CONSOLIDATE)


def summarise(cases: Sequence[FolderCase], language: str = "en") -> List[str]:
    """Short human readable lines describing what was found."""
    dated = [c for c in cases if c.is_dated and c.needs_a_decision]
    plain = [c for c in cases if not c.is_dated and c.needs_a_decision]
    mismatched = sum(c.mismatched_photos for c in cases)
    if language == "de":
        lines = [
            "{n} datierte Ordner".format(n=len(dated)),
            "{n} thematische Unterordner".format(n=len(plain)),
        ]
        if mismatched:
            lines.append(
                "{n} Fotos in datierten Ordnern, deren Datum nicht passt".format(n=mismatched)
            )
        return lines
    lines = [
        "{n} dated folder(s)".format(n=len(dated)),
        "{n} topic subfolder(s)".format(n=len(plain)),
    ]
    if mismatched:
        lines.append(
            "{n} photo(s) in a dated folder whose date does not match".format(n=mismatched)
        )
    return lines
