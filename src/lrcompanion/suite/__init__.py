"""The roof over the tools: a launcher that offers each of them.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

from typing import NamedTuple


class Tool(NamedTuple):
    """One tool the suite offers, as the launcher needs to know it."""

    key: str
    name: str
    family: str  # which cut of the mark to draw
    command: str  # what to type instead, for people who prefer typing
    available: bool = True


#: The tools, in the order a newcomer meets them. A tool is added here and the
#: launcher grows a tile; there is deliberately nothing else to change.
TOOLS = [
    Tool("foldercraft", "LR-FolderCraft", "foldercraft", "lrfc gui"),
    Tool("metasearch", "LR-MetaSearch", "metasearch", "lrms gui"),
]
