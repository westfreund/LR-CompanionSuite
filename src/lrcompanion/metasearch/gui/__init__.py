"""The LR-MetaSearch window.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

__all__ = ["main"]


def main(argv=None) -> int:
    """Open the window. Imported lazily so the extra stays optional."""
    from .app import run

    return run(argv)
