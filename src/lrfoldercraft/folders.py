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
from fnmatch import fnmatchcase
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
#: Rebuild the folder in place of itself, below its own parent. This is what
#: turns "2026-06-28 Makro Blume im Garten" into "2026-06-28/Makro Blume im
#: Garten" without dragging the photos out of the year folder they sit in.
RESORT = "resort"
#: Carry the folder to the new location exactly as it is: same name, same
#: contents, same sub-structure, no sorting applied. Only meaningful when the
#: run has somewhere else to put it -- sorting in place leaves it where it is.
RELOCATE = "relocate"

SUBFOLDER_ACTIONS = (SORT_INSIDE, CONSOLIDATE, RESORT, RELOCATE, LEAVE)
DATED_FOLDER_ACTIONS = (KEEP, RESORT, CONSOLIDATE, SORT_INSIDE, RELOCATE, LEAVE)

#: What to do with a photo inside a kept dated folder whose date does not match.
MOVE_OUT = "move-out"
MISMATCH_ACTIONS = (MOVE_OUT, LEAVE)

#: Everything a folder rule may ask for, in the order they are offered.
ALL_ACTIONS = (KEEP, RESORT, SORT_INSIDE, CONSOLIDATE, RELOCATE, LEAVE)

ACTION_LABELS = {
    SORT_INSIDE: (
        "sort by date inside this folder",
        "innerhalb dieses Ordners nach Datum sortieren",
    ),
    CONSOLIDATE: (
        "move the photos up and merge them",
        "Fotos herausholen und zusammenführen",
    ),
    LEAVE: ("leave the photos untouched", "Fotos unangetastet lassen"),
    KEEP: (
        "keep the folder and its matching photos",
        "Ordner mit seinen passenden Fotos behalten",
    ),
    RESORT: (
        "rebuild this folder where it stands",
        "diesen Ordner an seiner Stelle neu aufbauen",
    ),
    RELOCATE: (
        "move the folder unchanged to the new location",
        "den Ordner unverändert an den neuen Ort verschieben",
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


#: Separators that may sit between a date prefix and the text after it.
_LABEL_SEPARATORS = re.compile(r"^[\s_.\-]+")


def folder_label(name: str) -> str:
    """The descriptive text after a folder name's date prefix.

    ``2026-06-28 Makro Blume im Garten`` yields ``Makro Blume im Garten``;
    ``raw2020`` and a bare ``2026-06-28`` yield the empty string. This is what
    lets a structure put the date and the description on separate levels
    instead of losing one of them.
    """
    found = parse_folder_date(name)
    if found is None:
        return ""
    return _LABEL_SEPARATORS.sub("", name[len(found.matched_text) :]).strip()


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
    #: Descriptive text after a date prefix in :attr:`name`; empty when the
    #: name carries no date. Derived from the raw name, so it survives a
    #: folder being demoted to PLAIN for being too coarse.
    label: str = ""
    photo_count: int = 0
    folder_date: Optional[FolderDate] = None
    matching_photos: int = 0
    mismatched_photos: int = 0
    action: str = CONSOLIDATE
    action_source: str = "default"
    #: Human readable pattern of the rule that decided this folder, if any.
    matched_rule: str = ""
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
        label=folder_label(name),
        folder_date=folder_date,
    )


class FolderRuleError(ValueError):
    """A folder rule could not be understood."""


#: Patterns that select folders by kind rather than by path.
RULE_KEYWORDS = ("*", "dated", "dated+label", "dated-only", "plain")

RULE_KEYWORD_HELP = {
    "*": ("every folder not matched earlier", "jeder noch nicht getroffene Ordner"),
    "dated": (
        "folders whose name starts with a date",
        "Ordner, deren Name mit einem Datum beginnt",
    ),
    "dated+label": (
        "dated folders that also carry descriptive text",
        "datierte Ordner, die zusätzlich Text tragen",
    ),
    "dated-only": (
        "dated folders with nothing but the date",
        "datierte Ordner mit nichts als dem Datum",
    ),
    "plain": ("folders without a date in the name", "Ordner ohne Datum im Namen"),
}


@dataclass(frozen=True)
class FolderRule:
    """One line of the ordered rule list: which folders, and what to do."""

    pattern: str
    action: str

    def describe(self, language: str = "en") -> str:
        what = RULE_KEYWORD_HELP.get(self.pattern)
        subject = what[1 if language == "de" else 0] if what else self.pattern
        return "{s} -> {a}".format(s=subject, a=label(self.action, language))


def parse_rule(text: str) -> FolderRule:
    """Read one ``PATTERN=ACTION`` rule, as typed on the command line."""
    if "=" not in text:
        raise FolderRuleError(
            "rule {t!r} needs the form PATTERN=ACTION, for example '_extern=leave'".format(t=text)
        )
    pattern, _, action = text.rpartition("=")
    pattern, action = pattern.strip(), action.strip().lower()
    if not pattern:
        raise FolderRuleError("rule {t!r} has an empty pattern".format(t=text))
    if action not in ALL_ACTIONS:
        raise FolderRuleError(
            "rule {t!r} names an unknown action {a!r} -- known actions: {k}".format(
                t=text, a=action, k=", ".join(ALL_ACTIONS)
            )
        )
    return FolderRule(pattern=pattern, action=action)


def parse_rules(texts: Sequence[str]) -> Tuple[FolderRule, ...]:
    """Read a whole ordered rule list."""
    return tuple(parse_rule(text) for text in texts)


def rule_matches(rule: FolderRule, case: FolderCase) -> bool:
    """True when *rule* speaks about *case*.

    A keyword selects by kind. Anything else is a shell glob matched against the
    folder's path below its root, against its bare name, and against every
    partial path ending at the folder -- so ``_extern`` finds ``_extern`` no
    matter how deep it sits. A pattern also covers everything **below** the
    folder it names, so the one rule reaches ``raw2019/_extern/2020/Fest`` too.
    """
    pattern = rule.pattern
    if pattern in ("*", "any"):
        return True
    if pattern == "dated":
        return case.is_dated
    if pattern == "dated+label":
        return case.is_dated and bool(case.label)
    if pattern == "dated-only":
        return case.is_dated and not case.label
    if pattern == "plain":
        return not case.is_dated
    glob = pattern.strip("/").lower()
    return any(
        fnmatchcase(candidate, glob) or fnmatchcase(candidate, glob + "/*")
        for candidate in _match_candidates(case)
    )


def _match_candidates(case: FolderCase) -> List[str]:
    """Every path a pattern may reasonably be understood to mean.

    For ``raw2019/_extern/2020`` these are that path and each shorter one
    ending at the same folder: ``_extern/2020`` and ``2020``. Without them a
    rule would only ever reach folders sitting directly below the root, which
    is not how anyone reads ``_extern=leave``.
    """
    segments = [segment.lower() for segment in case.path_from_root.strip("/").split("/") if segment]
    if not segments:
        return [case.name.lower()]
    return ["/".join(segments[start:]) for start in range(len(segments))]


def first_matching_rule(
    case: FolderCase, rules: Sequence[FolderRule]
) -> Optional[Tuple[int, FolderRule]]:
    """The first rule that speaks about *case*, with its 1-based position."""
    for position, rule in enumerate(rules, start=1):
        if rule_matches(rule, case):
            return position, rule
    return None


def usable_action(action: str, case: FolderCase) -> str:
    """Soften an action that cannot mean anything for this folder.

    ``keep`` is about honouring the date in a folder's name. Asked of a folder
    that has no date, the honest reading is to leave it alone rather than to
    fail.
    """
    if action == KEEP and not case.is_dated:
        return LEAVE
    return action


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
