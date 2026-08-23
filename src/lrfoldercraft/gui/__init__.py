"""Qt based graphical front end.

Kept in its own subpackage behind a lazy import, exactly like the TUI, so that
neither the command line nor the core needs PySide6 installed. A missing
dependency produces a helpful message instead of a traceback.
"""

from __future__ import annotations

from typing import Optional

__all__ = ["run_gui"]


def run_gui(catalog: str = "", language: Optional[str] = None, debug: bool = False) -> int:
    """Start the graphical interface. Imported lazily on purpose."""
    from .app import run_gui as _run

    return _run(catalog=catalog, language=language, debug=debug)
