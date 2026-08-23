"""Single source of truth for revision information.

Versioning policy (see docs/en/11-versioning.md):
  MAJOR  -- every feature extension is a major change (project rule).
  MINOR  -- behaviour-preserving improvements, docs, refactors.
  PATCH  -- bug fixes only.

``BUILD_DATE`` is the release date of the current revision and is shown in
every UI surface (TUI header, CLI banner, log header, reports).
"""

from __future__ import annotations

__version__ = "7.0.0"
__build_date__ = "2026-08-23"
__codename__ = "Gedaechtnis"

#: Human readable revision tag, e.g. ``r1.0.0 (2026-08-22)``.
REVISION = "r{v} ({d})".format(v=__version__, d=__build_date__)

APP_NAME = "LR-FolderCraft"
APP_SLUG = "lr-foldercraft"
APP_URL = "https://gitlab.com/andy-freund/LR-FolderCraft"

#: Lightroom Classic catalog schema versions this revision was verified against.
VERIFIED_CATALOG_VERSIONS = ("18.0.0",)

#: Catalog schema versions that are accepted without an explicit warning.
SUPPORTED_CATALOG_VERSION_RANGE = (11, 19)


def banner() -> str:
    """Return the one-line identification banner used across all front ends."""
    return "{name} {rev} - {codename}".format(name=APP_NAME, rev=REVISION, codename=__codename__)


def long_banner() -> str:
    """Return a multi-line banner including licence and project URL."""
    return "\n".join(
        [
            banner(),
            "Lightroom Classic folder re-organiser / Ordner-Reorganisation",
            "SPDX-License-Identifier: MIT OR GPL-3.0-or-later",
            APP_URL,
        ]
    )
