"""Read and write access to Adobe Lightroom Classic ``.lrcat`` catalogs."""

from __future__ import annotations

from .db import CatalogConnection, CatalogError, CatalogLockedError, open_catalog
from .model import CatalogInfo, Folder, Photo, RootFolder
from .reader import CatalogReader
from .writer import CatalogWriter

__all__ = [
    "CatalogConnection",
    "CatalogError",
    "CatalogInfo",
    "CatalogLockedError",
    "CatalogReader",
    "CatalogWriter",
    "Folder",
    "Photo",
    "RootFolder",
    "open_catalog",
]
