"""Textual based interactive front end.

Kept in its own subpackage with a lazy import so the CLI stays usable when
Textual is not installed. A later GUI can reuse everything below
:mod:`lrcompanion.planner` unchanged -- no core module knows about any UI.
"""

from __future__ import annotations

__all__ = ["run_tui"]


def run_tui(catalog: str = "", language: str = "en", debug: bool = False) -> int:
    """Start the interactive interface. Imported lazily on purpose."""
    from .app import run_tui as _run

    return _run(catalog=catalog, language=language, debug=debug)
