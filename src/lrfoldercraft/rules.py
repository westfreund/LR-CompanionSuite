"""Folder-name templates and the grouping criteria they expose.

A *structure* is an ordered list of level templates. Each level becomes one
directory below the anchor folder, so multiple grouping levels are simply
multiple entries::

    ["{yyyy}", "{mm}", "{dd}"]          ->  2019/01/03
    ["{camera_slug}", "{yyyy}-W{iso_week}"] -> canon-eos-70d/2019-W01
    ["{yyyy}-{mm}-{dd}"]                ->  2019-01-03

Templates are rendered per photo, then sanitised so the result is a legal
directory name on Windows, macOS and Linux alike.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from .logging_setup import get_logger

log = get_logger("rules")

# --------------------------------------------------------------------------
# Localised month / weekday names -- the project is bilingual by requirement,
# and we do not want to depend on the machine's locale being installed.
# --------------------------------------------------------------------------

MONTH_NAMES: Dict[str, Tuple[str, ...]] = {
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "de": (
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ),
}

MONTH_SHORT: Dict[str, Tuple[str, ...]] = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "de": ("Jan", "Feb", "Mrz", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"),
}

WEEKDAY_NAMES: Dict[str, Tuple[str, ...]] = {
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
    "de": ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"),
}

WEEKDAY_SHORT: Dict[str, Tuple[str, ...]] = {
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    "de": ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"),
}


@dataclass(frozen=True)
class TokenSpec:
    """Describes one template token for help output and the TUI."""

    name: str
    example: str
    description_en: str
    description_de: str
    category: str  # "date" | "camera" | "file"


TOKEN_SPECS: Tuple[TokenSpec, ...] = (
    TokenSpec("yyyy", "2019", "Four digit year", "Vierstellige Jahreszahl", "date"),
    TokenSpec("yy", "19", "Two digit year", "Zweistellige Jahreszahl", "date"),
    TokenSpec("mm", "01", "Month, zero padded", "Monat, zweistellig", "date"),
    TokenSpec("m", "1", "Month, no padding", "Monat, ohne führende Null", "date"),
    TokenSpec("dd", "03", "Day, zero padded", "Tag, zweistellig", "date"),
    TokenSpec("d", "3", "Day, no padding", "Tag, ohne führende Null", "date"),
    TokenSpec("hh", "17", "Hour, 24h zero padded", "Stunde, 24h zweistellig", "date"),
    TokenSpec("mi", "42", "Minute, zero padded", "Minute, zweistellig", "date"),
    TokenSpec("month_name", "January", "Full month name", "Ausgeschriebener Monatsname", "date"),
    TokenSpec("month_short", "Jan", "Abbreviated month name", "Abgekürzter Monatsname", "date"),
    TokenSpec("quarter", "Q1", "Calendar quarter", "Kalenderquartal", "date"),
    TokenSpec(
        "iso_week",
        "01",
        "ISO-8601 calendar week, zero padded",
        "ISO-8601-Kalenderwoche, zweistellig",
        "date",
    ),
    TokenSpec("iso_year", "2019", "ISO-8601 week-numbering year", "ISO-8601-Wochenjahr", "date"),
    TokenSpec("weekday", "Thursday", "Full weekday name", "Ausgeschriebener Wochentag", "date"),
    TokenSpec("weekday_short", "Thu", "Abbreviated weekday name", "Abgekürzter Wochentag", "date"),
    TokenSpec("doy", "003", "Day of year, zero padded", "Tag des Jahres, dreistellig", "date"),
    TokenSpec(
        "camera",
        "Canon EOS 70D",
        "Camera model as stored by Lightroom",
        "Kameramodell laut Lightroom",
        "camera",
    ),
    TokenSpec(
        "camera_slug",
        "canon-eos-70d",
        "Camera model, lower case and hyphenated",
        "Kameramodell, klein und mit Bindestrichen",
        "camera",
    ),
    TokenSpec(
        "camera_sn", "053022010127", "Camera serial number", "Seriennummer der Kamera", "camera"
    ),
    TokenSpec(
        "lens",
        "EF-S18-55mm f/3.5-5.6 IS STM",
        "Lens as stored by Lightroom",
        "Objektiv laut Lightroom",
        "camera",
    ),
    TokenSpec(
        "lens_slug",
        "ef-s18-55mm-f-3-5-5-6-is-stm",
        "Lens, lower case and hyphenated",
        "Objektiv, klein und mit Bindestrichen",
        "camera",
    ),
    TokenSpec(
        "format", "RAW", "Lightroom file format class", "Lightroom-Dateiformatklasse", "file"
    ),
    TokenSpec("ext", "CR2", "File extension, upper case", "Dateiendung, groß", "file"),
    TokenSpec("ext_lower", "cr2", "File extension, lower case", "Dateiendung, klein", "file"),
    TokenSpec(
        "orig_folder",
        "raw2019",
        "Name of the folder the file is in today",
        "Name des heutigen Ordners",
        "file",
    ),
    TokenSpec(
        "folder_label",
        "Makro Blume im Garten",
        "Text after the date in the current folder name, empty if there is none",
        "Text hinter dem Datum im heutigen Ordnernamen, leer wenn keiner da ist",
        "file",
    ),
)

TOKEN_NAMES = tuple(spec.name for spec in TOKEN_SPECS)

#: Ready made structures offered by the CLI and the TUI.
PRESETS: Dict[str, Tuple[str, ...]] = {
    "day": ("{yyyy}-{mm}-{dd}",),
    "year/day": ("{yyyy}", "{yyyy}-{mm}-{dd}"),
    "year/month/day": ("{yyyy}", "{mm}", "{dd}"),
    "year/month": ("{yyyy}", "{mm}"),
    "year-month": ("{yyyy}-{mm}",),
    "year/week": ("{yyyy}", "W{iso_week}"),
    "iso-week": ("{iso_year}-W{iso_week}",),
    "year/month-name": ("{yyyy}", "{mm} {month_name}"),
    "camera/day": ("{camera_slug}", "{yyyy}-{mm}-{dd}"),
    "day/camera": ("{yyyy}-{mm}-{dd}", "{camera_slug}"),
    "camera/year/month/day": ("{camera_slug}", "{yyyy}", "{mm}", "{dd}"),
    "year/quarter/month": ("{yyyy}", "{quarter}", "{mm}"),
    # Cumulative: every level says the whole date, not just its own part.
    "year/year-month/full-day": ("{yyyy}", "{yyyy}-{mm}", "{yyyy}-{mm}-{dd}"),
    "year/full-day": ("{yyyy}", "{yyyy}-{mm}-{dd}"),
}

PRESET_DESCRIPTIONS: Dict[str, Tuple[str, str]] = {
    "day": ("One folder per capture day", "Ein Ordner je Aufnahmetag"),
    "year/day": ("Year folder, day folders inside", "Jahresordner mit Tagesordnern"),
    "year/month/day": ("Classic three level date tree", "Klassischer dreistufiger Datumsbaum"),
    "year/month": ("Year folder, month folders inside", "Jahresordner mit Monatsordnern"),
    "year-month": ("One folder per month", "Ein Ordner je Monat"),
    "year/week": ("Year folder, ISO week folders inside", "Jahresordner mit KW-Ordnern"),
    "iso-week": ("One folder per ISO calendar week", "Ein Ordner je ISO-Kalenderwoche"),
    "year/month-name": ("Year folder, numbered month names", "Jahresordner mit benannten Monaten"),
    "camera/day": ("Camera folder, day folders inside", "Kameraordner mit Tagesordnern"),
    "day/camera": ("Day folder, camera folders inside", "Tagesordner mit Kameraordnern"),
    "camera/year/month/day": ("Camera, then full date tree", "Kamera, danach voller Datumsbaum"),
    "year/quarter/month": ("Year, quarter, month", "Jahr, Quartal, Monat"),
    "year/year-month/full-day": (
        "Date tree where every level names the whole date",
        "Datumsbaum, in dem jede Ebene das ganze Datum nennt",
    ),
    "year/full-day": (
        "Year folder, full dates inside",
        "Jahresordner mit vollständigen Datumsangaben",
    ),
}


# --------------------------------------------------------------------------
# Sanitising
# --------------------------------------------------------------------------

#: Characters that are illegal in a path segment on at least one supported OS.
ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

#: Windows device names that may not be used as a directory name.
RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *("COM{n}".format(n=i) for i in range(1, 10)),
    *("LPT{n}".format(n=i) for i in range(1, 10)),
}

MAX_SEGMENT_LENGTH = 100


class RuleError(ValueError):
    """Raised for malformed templates."""


def sanitise_segment(text: str, replacement: str = "-", ascii_only: bool = False) -> str:
    """Turn arbitrary text into a portable directory name.

    Applies, in order: optional ASCII folding, illegal-character replacement,
    whitespace collapsing, Windows reserved-name escaping, trailing dot/space
    removal and length limiting.
    """
    value = text
    if ascii_only:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = ILLEGAL_CHARS.sub(replacement, value)
    value = re.sub(r"\s+", " ", value).strip()
    value = value.rstrip(". ")
    if not value:
        value = "unnamed"
    if value.upper() in RESERVED_NAMES or value.split(".")[0].upper() in RESERVED_NAMES:
        value = "_" + value
    if len(value) > MAX_SEGMENT_LENGTH:
        value = value[:MAX_SEGMENT_LENGTH].rstrip(". ")
    return value


def slugify(text: str) -> str:
    """Lower-case, hyphen separated, ASCII only version of *text*."""
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "unknown"


# --------------------------------------------------------------------------
# Token context
# --------------------------------------------------------------------------


@dataclass
class TokenContext:
    """Everything a template may refer to for one photo."""

    when: Optional[datetime]
    camera: Optional[str]
    camera_serial: Optional[str]
    lens: Optional[str]
    file_format: Optional[str]
    extension: Optional[str]
    original_folder: Optional[str]
    #: Descriptive text after the date prefix of the current folder's name.
    original_folder_label: str = ""
    language: str = "en"
    unknown_camera: str = "Unknown Camera"
    unknown_lens: str = "Unknown Lens"

    def values(self) -> Dict[str, str]:
        """Materialise every token as a string."""
        lang = self.language if self.language in MONTH_NAMES else "en"
        camera = self.camera or self.unknown_camera
        lens = self.lens or self.unknown_lens
        out: Dict[str, str] = {
            "camera": camera,
            "camera_slug": slugify(camera),
            "camera_sn": self.camera_serial or "unknown-sn",
            "lens": lens,
            "lens_slug": slugify(lens),
            "format": (self.file_format or "unknown").upper(),
            "ext": (self.extension or "").upper() or "noext",
            "ext_lower": (self.extension or "").lower() or "noext",
            "orig_folder": self.original_folder or "",
            "folder_label": self.original_folder_label or "",
        }
        when = self.when
        if when is None:
            for spec in TOKEN_SPECS:
                if spec.category == "date":
                    out[spec.name] = ""
            return out
        iso_year, iso_week, iso_weekday = when.isocalendar()
        out.update(
            {
                "yyyy": "{:04d}".format(when.year),
                "yy": "{:02d}".format(when.year % 100),
                "mm": "{:02d}".format(when.month),
                "m": str(when.month),
                "dd": "{:02d}".format(when.day),
                "d": str(when.day),
                "hh": "{:02d}".format(when.hour),
                "mi": "{:02d}".format(when.minute),
                "month_name": MONTH_NAMES[lang][when.month - 1],
                "month_short": MONTH_SHORT[lang][when.month - 1],
                "quarter": "Q{q}".format(q=(when.month - 1) // 3 + 1),
                "iso_week": "{:02d}".format(iso_week),
                "iso_year": "{:04d}".format(iso_year),
                "weekday": WEEKDAY_NAMES[lang][iso_weekday - 1],
                "weekday_short": WEEKDAY_SHORT[lang][iso_weekday - 1],
                "doy": "{:03d}".format(when.timetuple().tm_yday),
            }
        )
        return out

    @property
    def has_date(self) -> bool:
        return self.when is not None


_TOKEN_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def template_tokens(template: str) -> List[str]:
    """Return the token names referenced by *template*."""
    return _TOKEN_RE.findall(template)


def validate_template(template: str) -> None:
    """Raise :class:`RuleError` if *template* is unusable."""
    if not template or not template.strip():
        raise RuleError("empty level template")
    if "/" in template or "\\" in template:
        raise RuleError(
            "a level template must not contain a path separator: {t!r} "
            "(use one list entry per level)".format(t=template)
        )
    unknown = [name for name in template_tokens(template) if name not in TOKEN_NAMES]
    if unknown:
        raise RuleError(
            "unknown token(s) {u} in {t!r} -- known tokens: {k}".format(
                u=", ".join(sorted(set(unknown))), t=template, k=", ".join(TOKEN_NAMES)
            )
        )


def validate_structure(structure: Sequence[str]) -> None:
    """Validate every level of a structure and require at least one."""
    if not structure:
        raise RuleError("structure must have at least one level")
    for template in structure:
        validate_template(template)


#: Which date tokens pin a value down to which granularity.
TOKEN_GRANULARITY = {
    "yyyy": "year",
    "yy": "year",
    "iso_year": "year",
    "quarter": "month",
    "mm": "month",
    "m": "month",
    "month_name": "month",
    "month_short": "month",
    "iso_week": "week",
    "dd": "day",
    "d": "day",
    "doy": "day",
    "weekday": "day",
    "weekday_short": "day",
    "hh": "day",
    "mi": "day",
}

#: Ordering of :data:`TOKEN_GRANULARITY` values, coarsest first.
GRANULARITY_ORDER = ("year", "month", "week", "day")


#: What a cumulative date level joins its inherited parts with.
CUMULATIVE_SEPARATOR = "-"


def is_date_level(template: str) -> bool:
    """True when this level of the structure is named after a date."""
    return any(token in TOKEN_GRANULARITY for token in template_tokens(template))


def make_cumulative(structure: Sequence[str]) -> Tuple[str, ...]:
    """Rewrite date levels so each one repeats the ones above it.

    ``{yyyy}/{mm}/{dd}`` becomes ``{yyyy}/{yyyy}-{mm}/{yyyy}-{mm}-{dd}``, which
    is what most photographers mean by a date tree: every folder name is
    complete on its own, so a folder dragged out of the tree, shown in a search
    result, or read in a file dialog still says which day it is.

    Only date levels take part. ``{camera_slug}/{yyyy}/{mm}`` becomes
    ``{camera_slug}/{yyyy}/{yyyy}-{mm}`` -- the camera is not a date and is not
    repeated. A level that is already cumulative gains nothing, because it
    inherits only from the date levels *above* it.
    """
    inherited: List[str] = []
    result: List[str] = []
    for template in structure:
        if not is_date_level(template):
            result.append(template)
            continue
        result.append(CUMULATIVE_SEPARATOR.join(inherited + [template]))
        inherited.append(template)
    return tuple(result)


def structure_date_granularity(structure: Sequence[str]) -> Optional[str]:
    """Finest date granularity the structure pins down, or ``None``.

    ``{yyyy}/{mm}/{dd}`` asks for day resolution, ``{yyyy}`` only for a year.
    A structure without date tokens returns ``None``: an existing dated folder
    then says nothing about whether the structure is satisfied.
    """
    finest: Optional[str] = None
    for template in structure:
        for token in template_tokens(template):
            granularity = TOKEN_GRANULARITY.get(token)
            if granularity is None:
                continue
            if finest is None or GRANULARITY_ORDER.index(granularity) > GRANULARITY_ORDER.index(
                finest
            ):
                finest = granularity
    return finest


def structure_requires_date(structure: Sequence[str]) -> bool:
    """True when any level uses a date token."""
    date_tokens = {spec.name for spec in TOKEN_SPECS if spec.category == "date"}
    return any(
        token in date_tokens for template in structure for token in template_tokens(template)
    )


def render_level(template: str, context: TokenContext, ascii_only: bool = False) -> str:
    """Render one level template into a sanitised path segment."""
    values = context.values()

    def substitute(match: re.Match[str]) -> str:
        return values.get(match.group(1), "")

    return sanitise_segment(_TOKEN_RE.sub(substitute, template), ascii_only=ascii_only)


def render_structure(
    structure: Sequence[str], context: TokenContext, ascii_only: bool = False
) -> Tuple[str, ...]:
    """Render every level into a tuple of sanitised path segments.

    A level whose tokens all render empty is dropped rather than turned into a
    folder called ``unnamed``: ``{yyyy}-{mm}-{dd}/{folder_label}`` has to give a
    plain day folder for a photo whose folder carries no descriptive text.
    """
    segments = []
    for template in structure:
        if _renders_empty(template, context):
            continue
        segments.append(render_level(template, context, ascii_only))
    return tuple(segments)


def _renders_empty(template: str, context: TokenContext) -> bool:
    """True when substituting the tokens leaves nothing but separators."""
    values = context.values()

    def substitute(match: re.Match[str]) -> str:
        return values.get(match.group(1), "")

    return not _TOKEN_RE.sub(substitute, template).strip(" ._-")


def parse_structure(spec: str) -> Tuple[str, ...]:
    """Parse a user supplied structure.

    Accepts either a preset name (``year/month/day``) or an explicit template
    list where levels are separated by ``/``, e.g.
    ``{camera_slug}/{yyyy}-{mm}-{dd}``.
    """
    text = spec.strip()
    if not text:
        raise RuleError("empty structure specification")
    if text in PRESETS:
        return PRESETS[text]
    levels = tuple(part for part in text.split("/") if part.strip())
    validate_structure(levels)
    return levels


def describe_structure(structure: Sequence[str], language: str = "en") -> str:
    """Render an example path for *structure* using a fixed sample photo."""
    sample = TokenContext(
        when=datetime(2019, 1, 3, 17, 42),
        camera="Canon EOS 70D",
        camera_serial="053022010127",
        lens="EF-S18-55mm f/3.5-5.6 IS STM",
        file_format="RAW",
        extension="CR2",
        original_folder="raw2019",
        original_folder_label="",
        language=language,
    )
    return "/".join(render_structure(structure, sample))


def token_help(language: str = "en") -> List[Tuple[str, str, str]]:
    """Return ``(token, example, description)`` triples for help screens."""
    return [
        (
            "{" + spec.name + "}",
            spec.example,
            spec.description_de if language == "de" else spec.description_en,
        )
        for spec in TOKEN_SPECS
    ]
