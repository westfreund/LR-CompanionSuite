"""Everything about a plan that deserves an answer before it is run.

A plan is not just a count of files to move. It also contains the cases the
tool could not decide on its own: photos with no usable capture date, names
that would collide, files the catalog names but the disk does not have. Each of
those is governed by a setting, and each is a question to the operator.

Reporting them as a single "skipped: 43" is the same as not reporting them. So
this module turns a plan and its pre-flight result into a list of findings that
each name the cause, the number of files affected, examples, and -- crucially --
**the setting that decides what happens to them**, so the answer is one option
away rather than a search through the documentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple

from .planner import (
    RENAMED,
    SKIP_CONFLICT,
    SKIP_FILTERED,
    SKIP_MISSING_SOURCE,
    SKIP_NO_DATE,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .planner import Plan
    from .safety import PreflightResult

#: Stops the run outright.
ERROR = "error"
#: Will not stop the run, but changes what it does.
WARNING = "warning"
#: A decision the tool made for you, which a setting can change.
EXCEPTION = "exception"
#: Worth knowing, nothing to answer.
NOTE = "note"

#: Sort order for display: the things that block come first.
_ORDER = {ERROR: 0, WARNING: 1, EXCEPTION: 2, NOTE: 3}

#: How many example paths to keep per finding. Enough to recognise a pattern,
#: few enough that a dialog stays readable.
SAMPLE_LIMIT = 5


@dataclass
class Finding:
    """One thing about the plan that an operator may want to answer."""

    level: str
    category: str
    count: int
    text_en: str
    text_de: str
    #: The command line option that governs this, e.g. ``--on-missing-date``.
    setting: Optional[str] = None
    #: What the setting is currently doing, in the run's language.
    current_en: str = ""
    current_de: str = ""
    samples: List[str] = field(default_factory=list)

    def text(self, language: str = "en") -> str:
        return self.text_de if language == "de" else self.text_en

    def current(self, language: str = "en") -> str:
        return self.current_de if language == "de" else self.current_en

    @property
    def blocks(self) -> bool:
        return self.level == ERROR


def collect_findings(plan: Plan, checks: Optional[PreflightResult] = None) -> List[Finding]:
    """Everything worth an answer, most serious first."""
    findings: List[Finding] = []
    findings += _from_preflight(checks)
    findings += _from_moves(plan)
    findings += _from_folders(plan)
    findings += _from_warnings(plan)
    findings.sort(key=lambda f: (_ORDER.get(f.level, 9), -f.count))
    return findings


def _from_preflight(checks: Optional[PreflightResult]) -> List[Finding]:
    if checks is None:
        return []
    found = []
    for check in checks.checks:
        if check.level == "ok":
            continue
        found.append(
            Finding(
                level=ERROR if check.level == "error" else WARNING,
                category="preflight:" + check.name,
                count=0,
                text_en=check.message_en,
                text_de=check.message("de"),
            )
        )
    return found


def _from_moves(plan: Plan) -> List[Finding]:
    """The per-file exceptions, each with the setting that governs it."""
    settings = plan.settings
    buckets: List[Tuple[str, str, str, str, str, str, str]] = [
        (
            SKIP_MISSING_SOURCE,
            ERROR,
            "missing-source",
            "file(s) the catalog names but the disk does not have",
            "Datei(en), die der Katalog nennt, die auf der Platte aber fehlen",
            "",
            "",
        ),
        (
            SKIP_NO_DATE,
            EXCEPTION,
            "no-date",
            "file(s) with no usable capture date",
            "Datei(en) ohne brauchbares Aufnahmedatum",
            "--on-missing-date",
            settings.on_missing_date,
        ),
        (
            SKIP_CONFLICT,
            EXCEPTION,
            "conflict",
            "file(s) whose target name is already taken",
            "Datei(en), deren Zielname schon belegt ist",
            "--conflict",
            settings.conflict,
        ),
        (
            SKIP_FILTERED,
            EXCEPTION,
            "filtered",
            "file(s) excluded by the extension filter",
            "Datei(en), die der Endungsfilter ausschliesst",
            "--include-ext / --exclude-ext",
            "",
        ),
        (
            RENAMED,
            NOTE,
            "renamed",
            "file(s) that will be renamed to avoid a collision",
            "Datei(en), die zur Vermeidung einer Kollision umbenannt werden",
            "--conflict",
            settings.conflict,
        ),
    ]
    found = []
    for status, level, category, text_en, text_de, setting, current in buckets:
        affected = [m for m in plan.moves if m.status == status]
        if not affected:
            continue
        found.append(
            Finding(
                level=level,
                category=category,
                count=len(affected),
                text_en=text_en,
                text_de=text_de,
                setting=setting or None,
                current_en=current,
                current_de=current,
                samples=[m.source_path for m in affected[:SAMPLE_LIMIT]],
            )
        )
    return found


def _from_folders(plan: Plan) -> List[Finding]:
    """Folder-level questions: stray dates, and folders nothing spoke about."""
    found = []
    settings = plan.settings

    mismatched = [c for c in plan.folder_cases if c.mismatched_photos]
    if mismatched:
        total = sum(c.mismatched_photos for c in mismatched)
        found.append(
            Finding(
                level=EXCEPTION,
                category="date-mismatch",
                count=total,
                text_en=(
                    "photo(s) in {n} dated folder(s) whose own date differs from "
                    "the folder name -- often a shoot that ran past midnight"
                ).format(n=len(mismatched)),
                text_de=(
                    "Foto(s) in {n} datierten Ordner(n), deren eigenes Datum vom "
                    "Ordnernamen abweicht -- oft eine Session über Mitternacht"
                ).format(n=len(mismatched)),
                setting="--mismatch-action",
                current_en=settings.mismatch_action,
                current_de=settings.mismatch_action,
                samples=[
                    "{p} ({n})".format(p=c.path_from_root or ".", n=c.mismatched_photos)
                    for c in mismatched[:SAMPLE_LIMIT]
                ],
            )
        )

    undecided = [
        c
        for c in plan.folder_cases
        if c.photo_count and not c.is_anchor and c.action_source == "default"
    ]
    if undecided:
        found.append(
            Finding(
                level=NOTE,
                category="folders-on-default",
                count=len(undecided),
                text_en=("folder(s) fell through to the default because no rule spoke about them"),
                text_de=(
                    "Ordner sind auf die Voreinstellung gefallen, weil keine Regel über sie spricht"
                ),
                setting="--rule",
                current_en="{n} rule(s) set".format(n=len(settings.folder_rules)),
                current_de="{n} Regel(n) gesetzt".format(n=len(settings.folder_rules)),
                samples=[c.path_from_root or "." for c in undecided[:SAMPLE_LIMIT]],
            )
        )
    return found


def _from_warnings(plan: Plan) -> List[Finding]:
    return [
        Finding(
            level=WARNING,
            category="plan-warning",
            count=0,
            text_en=warning,
            text_de=warning,
        )
        for warning in plan.warnings
    ]


def render_findings(findings: Sequence[Finding], language: str = "en") -> List[str]:
    """Plain text lines, for the command line and the log."""
    if not findings:
        return ["Nothing needs an answer." if language != "de" else "Nichts zu beantworten."]
    lines = []
    for finding in findings:
        head = "[{lvl}]".format(lvl=finding.level.upper())
        if finding.count:
            head += " {n:,}".format(n=finding.count)
        lines.append("{h} {t}".format(h=head, t=finding.text(language)))
        if finding.setting:
            lines.append(
                "        {s}{c}".format(
                    s=finding.setting,
                    c=" = {v}".format(v=finding.current(language))
                    if finding.current(language)
                    else "",
                )
            )
        for sample in finding.samples:
            lines.append("        - {s}".format(s=sample))
    return lines
