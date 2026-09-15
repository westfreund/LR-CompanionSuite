"""An index across every known library.

This package is deliberately separate from the folder reorganisation. It only
ever *reads* catalogs, it has its own store, and nothing in ``planner.py``,
``executor.py`` or ``folders.py`` may import it -- a test enforces that, so a
fault here cannot reach the part of the tool that moves photographs.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

__all__ = ["INDEX_FILE", "default_index_path"]

from pathlib import Path

from ..config import config_dir

#: The index is one SQLite file. It is not a catalog and never pretends to be.
INDEX_FILE = "library-index.db"


def default_index_path() -> Path:
    """Where the index lives unless the operator names somewhere else.

    Beside the profiles rather than beside any one catalog: the whole point is
    that it spans libraries and drives, so it cannot belong to one of them.
    """
    return config_dir() / INDEX_FILE
