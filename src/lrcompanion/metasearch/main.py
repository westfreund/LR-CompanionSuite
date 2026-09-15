"""``lrms`` -- LR-MetaSearch, the searching half of the suite.

A command of its own rather than a subcommand of the folder tool. The two
answer different questions and a reader looking for one should not have to know
about the other.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from ..cli import GLOBAL_FLAG_DEFAULTS, _add_global_flags
from ..logging_setup import setup_logging
from ..version import METASEARCH_NAME, REVISION, __build_date__
from .cli import add_subcommands, cmd_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lrms",
        description=(
            "{n} {r} -- search across every Lightroom Classic library you own, "
            "find what is held twice, and build catalogs out of a selection. "
            "Reads only.".format(n=METASEARCH_NAME, r=REVISION)
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="{n} {r} - build {d}".format(n=METASEARCH_NAME, r=REVISION, d=__build_date__),
    )
    _add_global_flags(parser)
    inner = parser.add_subparsers(dest="index_command", metavar="COMMAND")
    add_subcommands(inner, _add_global_flags)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    for flag, value in GLOBAL_FLAG_DEFAULTS.items():
        if not hasattr(args, flag):
            setattr(args, flag, value)
    if not getattr(args, "index_command", None):
        parser.print_help()
        return 2
    setup_logging(
        debug=args.debug,
        verbose=args.verbose,
        quiet=args.quiet,
        log_file=args.log_file,
        log_dir=args.log_dir,
        tag="lrms",
    )
    return cmd_index(args)


if __name__ == "__main__":  # pragma: no cover - module entry point
    sys.exit(main())
