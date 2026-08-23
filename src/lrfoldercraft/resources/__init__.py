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


def logo_for(size: int) -> Path:
    """The cut that is legible at *size* pixels."""
    return LOGO_SMALL if size <= 24 else LOGO
