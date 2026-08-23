"""The documentation has to keep up with the code, in both languages.

Two complete language trees are a project requirement, and the failure mode is
never a missing file -- it is a feature that quietly exists in only one of
them, or in neither. These checks are cheap and they are the reason a reader
can trust the German tree as much as the English one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lrfoldercraft.cli import build_parser
from lrfoldercraft.folders import ALL_ACTIONS, MISMATCH_ACTIONS
from lrfoldercraft.rules import PRESETS, TOKEN_NAMES

DOCS = Path(__file__).resolve().parent.parent / "docs"
LANGUAGES = ("en", "de")

#: `--help` is argparse's own and needs no prose.
UNDOCUMENTED_BY_DESIGN = {"--help"}


def tree(language: str) -> str:
    return " ".join(p.read_text(encoding="utf-8") for p in sorted((DOCS / language).glob("*.md")))


@pytest.fixture(scope="module")
def trees():
    return {language: tree(language) for language in LANGUAGES}


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("action", sorted(set(ALL_ACTIONS) | set(MISMATCH_ACTIONS)))
def test_every_folder_action_is_documented(trees, language, action):
    assert action in trees[language]


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("token", sorted(TOKEN_NAMES))
def test_every_token_is_documented(trees, language, token):
    assert "{{{t}}}".format(t=token) in trees[language]


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_every_preset_is_documented(trees, language, preset):
    assert preset in trees[language]


def _long_flags() -> list:
    text = build_parser().format_help()
    for action in build_parser()._subparsers._group_actions:  # noqa: SLF001
        for sub in action.choices.values():
            text += sub.format_help()
    return sorted(set(re.findall(r"--[a-z][a-z-]+", text)) - UNDOCUMENTED_BY_DESIGN)


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_command_line_flag_is_documented(trees, language):
    missing = [flag for flag in _long_flags() if flag not in trees[language]]
    assert not missing, missing


@pytest.mark.parametrize("language", LANGUAGES)
def test_both_trees_hold_the_same_documents(language):
    numbers = sorted(p.name.split("-")[0] for p in (DOCS / language).glob("*.md"))
    other = sorted(
        p.name.split("-")[0] for p in (DOCS / ("de" if language == "en" else "en")).glob("*.md")
    )
    assert numbers == other


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_document_carries_the_current_revision(language):
    from lrfoldercraft.version import __version__

    stale = [
        p.name
        for p in (DOCS / language).glob("*.md")
        if "r{v}".format(v=__version__) not in p.read_text(encoding="utf-8")
    ]
    assert not stale, stale
