"""``lrcs`` -- open the suite's launcher.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from ..version import REVISION, SUITE_NAME, __build_date__
from . import TOOLS


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lrcs",
        description="{n} {r} -- open the launcher, which offers every tool in the suite.".format(
            n=SUITE_NAME, r=REVISION
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="{n} {r} - build {d}".format(n=SUITE_NAME, r=REVISION, d=__build_date__),
    )
    parser.add_argument("--lang", choices=["en", "de"], default=None)
    parser.add_argument(
        "--list", action="store_true", help="name the tools instead of opening the window"
    )
    args = parser.parse_args(argv)

    if args.list:
        for tool in TOOLS:
            print("  {n:<20} {c}".format(n=tool.name, c=tool.command))
        return 0

    try:
        from .launcher import run
    except ImportError:
        print(
            "The launcher needs the graphical extra:\n"
            "  pip install 'lr-companion-suite[gui]'\n\n"
            "Without it the tools are still there on the command line:"
        )
        for tool in TOOLS:
            print("  {n:<20} {c}".format(n=tool.name, c=tool.command))
        return 1

    return run(["lrcs"] + (["--lang=de"] if args.lang == "de" else []))


if __name__ == "__main__":  # pragma: no cover - module entry point
    sys.exit(main())
