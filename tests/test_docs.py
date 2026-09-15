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
    """Revision *and* build date.

    Checking only the revision let every banner sit on a build date a week old
    through two releases: the bump script replaces the version string, and the
    date beside it was nobody's business.
    """
    from lrfoldercraft.version import __build_date__, __version__

    wanted = ("r{v}".format(v=__version__), __build_date__)
    stale = [
        "{n}: {w}".format(n=p.name, w=w)
        for p in (DOCS / language).glob("*.md")
        for w in wanted
        if w not in p.read_text(encoding="utf-8")
    ]
    assert not stale, stale


# -- the history must not fall behind again ----------------------------------


def released_revisions() -> list:
    """Every version the changelog records as released."""
    changelog = (DOCS.parent / "CHANGELOG.md").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.M)))


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_history_names_every_released_revision(language):
    """It had drifted to covering eighteen of thirty-nine before anyone looked.

    The changelog says what changed and was kept current because releasing
    touches it; the history says why and was not, because nothing forced it.
    This is what forces it.
    """
    name = "12-history.md" if language == "en" else "12-historie.md"
    text = (DOCS / language / name).read_text(encoding="utf-8")
    missing = [v for v in released_revisions() if "r{v}".format(v=v) not in text]
    assert not missing, missing


def test_the_changelog_names_every_tagged_revision():
    """A release without a changelog entry is a release nobody can read about.

    Skipped where git is not there to ask. A slim container has no git binary,
    and the check then failed for a reason that had nothing to do with the
    documentation -- so CI ran red for two revisions while the thing being
    guarded was fine. The `docs` job runs this for real.
    """
    import shutil
    import subprocess

    if shutil.which("git") is None:  # pragma: no cover - depends on the machine
        pytest.skip("no git to ask for the tags")
    tags = subprocess.run(
        ["git", "tag"], capture_output=True, text=True, cwd=str(DOCS.parent)
    ).stdout.split()
    if not tags:  # pragma: no cover - a source checkout without tags
        pytest.skip("no tags in this checkout")
    released = set(released_revisions())
    missing = [t for t in tags if t.lstrip("v") not in released]
    assert not missing, missing


#: Links into the repository, as opposed to the web.
LOCAL_LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
ROOT = DOCS.parent


def _linking_files():
    yield from sorted(DOCS.rglob("*.md"))
    for name in ("README.md", "README.de.md", "CHANGELOG.md"):
        yield ROOT / name


def test_no_document_points_at_a_file_that_is_not_there():
    """Link rot is invisible until a reader hits it, and then it is embarrassing.

    Renaming a document is the usual cause -- the two language trees are moved
    together but the links between them are not.
    """
    broken = []
    for path in _linking_files():
        for target in LOCAL_LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (path.parent / target).resolve().exists():
                broken.append("{p} -> {t}".format(p=path.relative_to(ROOT), t=target))
    assert not broken


def test_the_site_offers_every_document():
    """A document missing from the navigation exists but cannot be found.

    Read with a regular expression rather than a YAML parser: the site is built
    by CI, and the test suite should not need the documentation extra to run.
    """
    nav = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    listed = set(re.findall(r"((?:en|de)/[0-9a-z-]+\.md)", nav))
    present = {
        "{d}/{n}".format(d=language, n=path.name)
        for language in LANGUAGES
        for path in (DOCS / language).glob("*.md")
    }
    assert present - listed == set()
