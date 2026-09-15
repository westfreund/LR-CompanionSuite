"""Files shipped with the package rather than generated at runtime.

Currently the two cuts of the mark. They are single-colour SVG taking
``currentColor``, so a front end tints them to whatever it needs rather than
carrying a light and a dark copy.
"""

from __future__ import annotations

from pathlib import Path

RESOURCES = Path(__file__).resolve().parent

#: The full mark: use it at 32 px and above.
LOGO = RESOURCES / "logo.svg"
#: The small cut: use it at 24 px and below, where the full mark cannot read.
LOGO_SMALL = RESOURCES / "logo-small.svg"

#: One family per tool, plus the suite's own. Each has two cuts for the same
#: reason the first one did: four elements do not survive sixteen pixels.
FAMILIES = {
    "foldercraft": ("logo.svg", "logo-small.svg"),
    "metasearch": ("metasearch.svg", "metasearch-small.svg"),
    "suite": ("suite.svg", "suite-small.svg"),
}

#: Below this the full cut is unreadable, which is what the small one is for.
SMALL_CUT_UP_TO = 24


def logo_for(size: int, family: str = "foldercraft") -> Path:
    """The cut of *family* that is legible at *size* pixels."""
    full, small = FAMILIES.get(family, FAMILIES["foldercraft"])
    return RESOURCES / (small if size <= SMALL_CUT_UP_TO else full)
