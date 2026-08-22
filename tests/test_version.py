"""The revision must be stated in exactly one place and never drift."""

from __future__ import annotations

import re
from pathlib import Path

from lrfoldercraft import version as version_module

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_matches_version_module():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml has no version field"
    assert match.group(1) == version_module.__version__


def test_revision_string_is_derived():
    assert version_module.__version__ in version_module.REVISION
    assert version_module.__build_date__ in version_module.REVISION


def test_build_date_is_an_iso_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", version_module.__build_date__)


def test_banner_carries_revision_and_licence():
    long_banner = version_module.long_banner()
    assert version_module.REVISION in long_banner
    assert "MIT OR GPL-3.0-or-later" in long_banner


def test_changelog_documents_this_version():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[{v}]".format(v=version_module.__version__) in changelog


def test_readmes_show_the_current_revision():
    for name in ("README.md", "README.de.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "revision-r{v}".format(v=version_module.__version__) in text, name


def test_documents_state_the_revision():
    """Every document carries the revision line, in both languages."""
    stamp = "**Revision r{v} · Build".format(v=version_module.__version__)
    stamp_de = "**Revision r{v} · Build".format(v=version_module.__version__)
    missing = []
    for folder in ("en", "de"):
        for path in sorted((ROOT / "docs" / folder).glob("*.md")):
            text = path.read_text(encoding="utf-8")
            if stamp not in text and stamp_de not in text:
                missing.append(str(path.relative_to(ROOT)))
    assert not missing, "documents without a revision line: " + ", ".join(missing)
