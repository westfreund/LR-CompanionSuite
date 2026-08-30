"""The front ends must not drift apart.

Every option the graphical interface can set, the text interface has to be able
to set as well, and the other way round. This is not a style rule: the text
interface once grew a full apply path while lacking the preconditions dialog
and any way to undo, which made it the surface with the greatest effect and the
smallest safety net. Nobody decided that; it accumulated one revision at a
time, and only a deliberate walk through the code found it.

The check reads the source rather than the running widgets, because a widget
that exists but is never read into the settings is not an option, and one that
is read without a widget cannot be reached.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from lrfoldercraft.config import Settings

SRC = Path(__file__).resolve().parent.parent / "src" / "lrfoldercraft"
GUI = (SRC / "gui" / "app.py").read_text(encoding="utf-8")
TUI = (SRC / "tui" / "app.py").read_text(encoding="utf-8")

#: Not an option an interface offers: the run's own bookkeeping, or a path a
#: front end has no business choosing.
NOT_AN_OPTION = {
    "dry_run",
    "language",
    "profile_name",
    "created_with",
    "log_file",
    "log_dir",
    "report_dir",
    "backup_dir",
    "folder_ids",
    "interactive_folders",
    "move_log_dir",
    "date_source",
    "extra_sidecar_extensions",
    "ignore_lock",
    "allow_unsupported_catalog",
}


def assigned_in(text: str) -> set:
    return set(re.findall(r"settings\.([a-z_]+)\s*=", text))


def options() -> list:
    return [f.name for f in dataclasses.fields(Settings) if f.name not in NOT_AN_OPTION]


@pytest.mark.parametrize("option", sorted(options()))
def test_both_interfaces_can_set_every_option(option):
    in_gui, in_tui = option in assigned_in(GUI), option in assigned_in(TUI)
    assert in_gui == in_tui, "{o}: GUI={g}, TUI={t}".format(o=option, g=in_gui, t=in_tui)


#: Capabilities that decide whether a run can be reviewed and taken back. A
#: front end that writes must offer all of them.
SAFETY_CAPABILITIES = {
    "the preconditions must be shown before applying": "preconditions",
    "a run must be reversible from here": "undo",
    "past runs must be listable": "history",
}

#: The rest of what the interfaces offer.
CAPABILITIES = {
    "profiles can be saved and loaded": "save_profile",
    "profiles can be deleted again": "delete_profile",
    "folder rules can be edited": "folder_rules",
    "what the plan could not decide is shown": "collect_findings",
}


@pytest.mark.parametrize("what,needle", sorted(SAFETY_CAPABILITIES.items()))
def test_every_writing_interface_has_the_safety_net(what, needle):
    assert needle in GUI, what
    assert needle in TUI, what


@pytest.mark.parametrize("what,needle", sorted(CAPABILITIES.items()))
def test_the_interfaces_offer_the_same_capabilities(what, needle):
    assert (needle in GUI) == (needle in TUI), what


#: Finishing an interrupted run belongs everywhere a run can be started.
@pytest.mark.parametrize("needle", ["find_interruptions", "revert_files"])
def test_every_writing_interface_can_finish_an_interrupted_run(needle):
    assert needle in GUI, needle
    assert needle in TUI, needle
