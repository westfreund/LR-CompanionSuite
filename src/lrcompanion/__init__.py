"""LR-FolderCraft -- reorganise Adobe Lightroom Classic folder trees safely.

The package is deliberately split so that no core module depends on a user
interface:

    catalog/   read + write access to the ``.lrcat`` SQLite database
    rules      token based folder-name templates and grouping criteria
    planner    turns a catalog + a structure definition into a Plan
    executor   applies a Plan (backup, file moves, catalog rewrite, journal)
    report     renders a Plan or a Result in text / JSON / CSV
    cli        argparse front end
    tui/       Textual front end (optional dependency)
"""

from __future__ import annotations

from .version import (
    APP_NAME,
    APP_SLUG,
    APP_URL,
    REVISION,
    __build_date__,
    __codename__,
    __version__,
    banner,
    long_banner,
)

__all__ = [
    "APP_NAME",
    "APP_SLUG",
    "APP_URL",
    "REVISION",
    "__build_date__",
    "__codename__",
    "__version__",
    "banner",
    "long_banner",
]
