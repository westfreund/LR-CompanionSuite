"""Command line front end.

    lrfc info      CATALOG                 summarise a catalog
    lrfc folders   CATALOG                 list the folder tree
    lrfc plan      CATALOG --structure ... show what would happen (read only)
    lrfc apply     CATALOG --structure ... actually do it
    lrfc undo      JOURNAL                 reverse a completed run
    lrfc profiles / tokens / presets       help surfaces
    lrfc tui       [CATALOG]               start the interactive interface

Every command accepts ``--debug`` and ``--lang {en,de}``. Nothing is ever
written unless the command is ``apply`` (or ``undo``).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Sequence

from .catalog.db import CatalogError, open_catalog
from .catalog.reader import CatalogReader
from .config import (
    CONFLICT_MODES,
    DATE_SOURCES,
    MISSING_DATE_MODES,
    PLACEMENT_MODES,
    ConfigError,
    Settings,
    default_report_dir,
    list_profiles,
    profiles_dir,
)
from .executor import ExecutionError, execute, undo
from .folders import (
    DATED_FOLDER_ACTIONS,
    MISMATCH_ACTIONS,
    SUBFOLDER_ACTIONS,
    FolderCase,
)
from .folders import (
    label as action_label,
)
from .journal import JOURNAL_SUFFIX
from .logging_setup import get_logger, setup_logging, step
from .planner import PlanError, build_plan
from .report import (
    render_info,
    render_plan,
    render_plan_csv,
    render_plan_json,
    render_preflight,
    render_presets,
    render_result,
    render_tokens,
    write_plan_files,
)
from .rules import RuleError, parse_structure
from .safety import preflight
from .version import REVISION, long_banner

log = get_logger("cli")

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_PREFLIGHT = 3
EXIT_VERIFY = 4
EXIT_ABORTED = 5


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lrfc",
        description="LR-FolderCraft {r} -- reorganise Lightroom Classic folders "
        "without losing the catalog connection.".format(r=REVISION),
        epilog="Run 'lrfc presets' and 'lrfc tokens' to see the available "
        "structures and template placeholders.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=long_banner())
    _add_global_flags(parser)

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_info = sub.add_parser("info", help="summarise a catalog (read only)")
    p_info.add_argument("catalog", help="path to the .lrcat file")
    _add_global_flags(p_info)
    _add_catalog_flags(p_info)

    p_folders = sub.add_parser("folders", help="list the catalog folder tree")
    p_folders.add_argument("catalog")
    p_folders.add_argument(
        "--counts", action="store_true", help="include the file count per folder"
    )
    _add_global_flags(p_folders)
    _add_catalog_flags(p_folders)

    p_plan = sub.add_parser("plan", help="show what a run would do (read only)")
    p_plan.add_argument("catalog")
    _add_plan_flags(p_plan)
    _add_global_flags(p_plan)
    _add_catalog_flags(p_plan)
    p_plan.add_argument("--json", action="store_true", help="print the plan as JSON")
    p_plan.add_argument("--csv", action="store_true", help="print the plan as CSV")
    p_plan.add_argument("--out", metavar="DIR", help="also write plan.json and plan.csv into DIR")
    p_plan.add_argument("--all", action="store_true", help="do not truncate the folder listing")

    p_apply = sub.add_parser("apply", help="move the files and update the catalog")
    p_apply.add_argument("catalog")
    _add_plan_flags(p_apply)
    _add_global_flags(p_apply)
    _add_catalog_flags(p_apply)
    p_apply.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    p_apply.add_argument(
        "--no-backup",
        action="store_true",
        help="skip the catalog backup (strongly discouraged)",
    )
    p_apply.add_argument("--no-verify", action="store_true", help="skip the post-run verification")
    p_apply.add_argument(
        "--keep-empty-folders",
        action="store_true",
        help="keep folder entries that fall empty",
    )
    p_apply.add_argument("--out", metavar="DIR", help="write the plan and result into DIR")

    p_undo = sub.add_parser("undo", help="reverse a run using its journal")
    p_undo.add_argument("journal", help="path to a *{s} file".format(s=JOURNAL_SUFFIX))
    p_undo.add_argument("--catalog-backup", help="explicit catalog backup to restore")
    p_undo.add_argument("-y", "--yes", action="store_true")
    _add_global_flags(p_undo)

    p_profiles = sub.add_parser("profiles", help="list saved profiles")
    _add_global_flags(p_profiles)

    p_tokens = sub.add_parser("tokens", help="list template placeholders")
    _add_global_flags(p_tokens)

    p_presets = sub.add_parser("presets", help="list ready made structures")
    _add_global_flags(p_presets)

    p_tui = sub.add_parser("tui", help="start the interactive interface")
    p_tui.add_argument("catalog", nargs="?", help="optional catalog to preload")
    _add_global_flags(p_tui)

    p_gui = sub.add_parser("gui", help="start the graphical interface")
    p_gui.add_argument("catalog", nargs="?", help="optional catalog to preload")
    _add_global_flags(p_gui)

    return parser


def _add_global_flags(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("general")
    group.add_argument("--debug", action="store_true", help="verbose logging with source locations")
    group.add_argument(
        "--verbose", action="store_true", help="show progress messages on the console"
    )
    group.add_argument("--quiet", action="store_true", help="console output only for errors")
    group.add_argument("--lang", choices=("en", "de"), default=None, help="output language")
    group.add_argument("--log-file", metavar="PATH", help="explicit log file path")
    group.add_argument("--log-dir", metavar="DIR", help="directory for the auto-named log file")


def _add_catalog_flags(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("catalog access")
    group.add_argument(
        "--allow-unsupported-catalog",
        action="store_true",
        help="accept a catalog schema version outside the tested range",
    )
    group.add_argument(
        "--ignore-lock",
        action="store_true",
        help="proceed even though Lightroom seems to have the catalog open",
    )


def _add_plan_flags(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("structure")
    group.add_argument(
        "-s",
        "--structure",
        help="preset name (see 'lrfc presets') or a template such as "
        "'{camera_slug}/{yyyy}-{mm}-{dd}'",
    )
    group.add_argument("--profile", help="load a saved profile as the basis")
    group.add_argument("--config", help="load settings from a JSON file")
    group.add_argument("--save-profile", metavar="NAME", help="store these settings as a profile")
    group.add_argument(
        "--placement",
        choices=PLACEMENT_MODES,
        help="in-place: create folders below the current folder (default); "
        "new-tree: build a fresh tree at --target-root",
    )
    group.add_argument("--target-root", metavar="DIR", help="target tree for --placement new-tree")
    group.add_argument(
        "--anchor-folder", type=int, metavar="ID", help="explicit catalog folder id to build below"
    )

    selection = parser.add_argument_group("selection")
    selection.add_argument("--root-folder", type=int, metavar="ID", help="limit to one root folder")
    selection.add_argument(
        "--folder",
        type=int,
        action="append",
        metavar="ID",
        help="limit to a catalog folder id (repeatable)",
    )
    selection.add_argument(
        "--include-ext", action="append", metavar="EXT", help="only these extensions (repeatable)"
    )
    selection.add_argument(
        "--exclude-ext", action="append", metavar="EXT", help="skip these extensions (repeatable)"
    )

    existing = parser.add_argument_group("existing folder structure")
    existing.add_argument(
        "--subfolder-action",
        choices=SUBFOLDER_ACTIONS,
        help="what to do with a subfolder that has no date in its name, e.g. "
        "'Urlaub' (default: consolidate)",
    )
    existing.add_argument(
        "--dated-folder-action",
        choices=DATED_FOLDER_ACTIONS,
        help="what to do with a folder whose name starts with a date, e.g. "
        "'2019-04-15 Ostern in Tirol' (default: keep)",
    )
    existing.add_argument(
        "--mismatch-action",
        choices=MISMATCH_ACTIONS,
        help="what to do with a photo in a kept dated folder whose capture date "
        "does not match the folder name (default: move-out)",
    )
    existing.add_argument(
        "--folder-action",
        action="append",
        metavar="ID=ACTION",
        help="decide one catalog folder explicitly, repeatable, e.g. "
        "--folder-action 4711=sort-inside. Beats the defaults above.",
    )
    existing.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="ask about every folder that could reasonably go either way",
    )

    behaviour = parser.add_argument_group("behaviour")
    behaviour.add_argument(
        "--date-source",
        action="append",
        choices=DATE_SOURCES,
        help="timestamp priority, repeatable (default: capture, "
        "exif-fields). Add file-mtime only if you accept "
        "the file date as a stand-in for the capture date.",
    )
    behaviour.add_argument(
        "--on-missing-date",
        choices=MISSING_DATE_MODES,
        help="what to do without a capture date (default: unsorted)",
    )
    behaviour.add_argument(
        "--unsorted-folder",
        metavar="NAME",
        help="folder name for undated files (default: _unsorted)",
    )
    behaviour.add_argument(
        "--conflict", choices=CONFLICT_MODES, help="name collision handling (default: rename)"
    )
    behaviour.add_argument(
        "--no-sidecars", action="store_true", help="do not move XMP and other sidecar files"
    )
    behaviour.add_argument("--ascii", action="store_true", help="fold folder names to plain ASCII")


# ---------------------------------------------------------------------------
# Settings assembly
# ---------------------------------------------------------------------------


def settings_from_args(args: argparse.Namespace) -> Settings:
    """Build a :class:`Settings` from profile, config file and flags."""
    if getattr(args, "config", None):
        settings = Settings.load_file(args.config)
    elif getattr(args, "profile", None):
        settings = Settings.load_profile(args.profile)
    else:
        settings = Settings()

    settings.catalog = str(Path(args.catalog).expanduser())
    if getattr(args, "structure", None):
        settings.structure = parse_structure(args.structure)
    if getattr(args, "placement", None):
        settings.placement = args.placement
    if getattr(args, "target_root", None):
        settings.target_root = str(Path(args.target_root).expanduser())
        if not getattr(args, "placement", None):
            settings.placement = "new-tree"
    if getattr(args, "anchor_folder", None) is not None:
        settings.anchor_folder_id = args.anchor_folder
    if getattr(args, "root_folder", None) is not None:
        settings.root_folder_id = args.root_folder
    if getattr(args, "folder", None):
        settings.folder_ids = tuple(args.folder)
    if getattr(args, "include_ext", None):
        settings.include_extensions = tuple(args.include_ext)
    if getattr(args, "exclude_ext", None):
        settings.exclude_extensions = tuple(args.exclude_ext)
    if getattr(args, "date_source", None):
        settings.date_source = tuple(args.date_source)
    if getattr(args, "on_missing_date", None):
        settings.on_missing_date = args.on_missing_date
    if getattr(args, "unsorted_folder", None):
        settings.unsorted_folder = args.unsorted_folder
    if getattr(args, "conflict", None):
        settings.conflict = args.conflict
    if getattr(args, "subfolder_action", None):
        settings.subfolder_action = args.subfolder_action
    if getattr(args, "dated_folder_action", None):
        settings.dated_folder_action = args.dated_folder_action
    if getattr(args, "mismatch_action", None):
        settings.mismatch_action = args.mismatch_action
    if getattr(args, "folder_action", None):
        for entry in args.folder_action:
            folder_id, _, action = entry.partition("=")
            if not action:
                raise ConfigError("--folder-action expects ID=ACTION, got {e!r}".format(e=entry))
            try:
                settings.folder_actions[int(folder_id)] = action
            except ValueError:
                raise ConfigError(
                    "--folder-action folder id must be a number, got {f!r}".format(f=folder_id)
                ) from None
    if getattr(args, "interactive", False):
        settings.interactive_folders = True
    if getattr(args, "no_sidecars", False):
        settings.move_sidecars = False
    if getattr(args, "ascii", False):
        settings.ascii_only = True
    if getattr(args, "lang", None):
        settings.language = args.lang
    if getattr(args, "no_backup", False):
        settings.backup_catalog = False
    if getattr(args, "no_verify", False):
        settings.verify_after = False
    if getattr(args, "keep_empty_folders", False):
        settings.prune_empty_folders = False
    settings.allow_unsupported_catalog = bool(getattr(args, "allow_unsupported_catalog", False))
    settings.ignore_lock = bool(getattr(args, "ignore_lock", False))
    settings.__post_init__()
    return settings


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_info(args: argparse.Namespace) -> int:
    language = args.lang or "en"
    with open_catalog(
        args.catalog,
        allow_unsupported=args.allow_unsupported_catalog,
        ignore_lock=args.ignore_lock,
    ) as conn:
        print(render_info(CatalogReader(conn).info(), language))
    return EXIT_OK


def cmd_folders(args: argparse.Namespace) -> int:
    with open_catalog(
        args.catalog,
        allow_unsupported=args.allow_unsupported_catalog,
        ignore_lock=args.ignore_lock,
    ) as conn:
        reader = CatalogReader(conn)
        counts = reader.folder_file_counts() if args.counts else {}
        for root in reader.root_folders():
            print("[{i}] {p}".format(i=root.id_local, p=root.absolute_path))
            for folder in reader.folders(root.id_local):
                indent = "    " * (folder.depth + 1)
                label = folder.name or "."
                suffix = (
                    "  ({n:,} files)".format(n=counts.get(folder.id_local, 0))
                    if args.counts
                    else ""
                )
                print("{i}[{d}] {l}{s}".format(i=indent, d=folder.id_local, l=label, s=suffix))
    return EXIT_OK


def cmd_plan(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    settings.dry_run = True
    language = settings.language
    decide = _folder_prompt(language) if settings.interactive_folders else None
    with open_catalog(
        settings.catalog,
        allow_unsupported=settings.allow_unsupported_catalog,
        ignore_lock=settings.ignore_lock,
    ) as conn:
        plan = build_plan(CatalogReader(conn), settings, decide=decide)

    if args.json:
        print(render_plan_json(plan))
    elif args.csv:
        print(render_plan_csv(plan))
    else:
        print(render_plan(plan, language, show_all=args.all))
        print()
        print(render_preflight(preflight(plan), language))

    if args.out:
        paths = write_plan_files(plan, Path(args.out).expanduser(), _stamp("plan"))
        print("\nWritten: " + ", ".join(str(p) for p in paths))
    if args.save_profile:
        print("Profile saved: " + str(settings.save_profile(args.save_profile)))
    return EXIT_OK


def cmd_apply(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    settings.dry_run = False
    language = settings.language

    decide = _folder_prompt(language) if settings.interactive_folders else None
    with open_catalog(
        settings.catalog,
        allow_unsupported=settings.allow_unsupported_catalog,
        ignore_lock=settings.ignore_lock,
    ) as conn:
        plan = build_plan(CatalogReader(conn), settings, decide=decide)

    print(render_plan(plan, language))
    checks = preflight(plan)
    print()
    print(render_preflight(checks, language))
    if not checks.ok:
        print("\nPre-flight failed -- nothing was changed.", file=sys.stderr)
        return EXIT_PREFLIGHT
    if not plan.has_work:
        print("\nNothing to do.")
        return EXIT_OK

    out_dir = Path(args.out).expanduser() if args.out else default_report_dir()
    write_plan_files(plan, out_dir, _stamp("plan"))

    if not args.yes and not _confirm(plan, language):
        print("Aborted.")
        return EXIT_ABORTED

    try:
        result = execute(plan, settings, progress=_console_progress, skip_preflight=True)
    except ExecutionError as exc:
        print("\nFAILED: {e}".format(e=exc), file=sys.stderr)
        return EXIT_ERROR
    print()
    print(render_result(result, language))
    if args.save_profile:
        print("Profile saved: " + str(settings.save_profile(args.save_profile)))
    return EXIT_VERIFY if result.verification else EXIT_OK


def cmd_undo(args: argparse.Namespace) -> int:
    language = args.lang or "en"
    if not args.yes:
        answer = (
            input("Reverse the run recorded in {j}? [y/N] ".format(j=args.journal)).strip().lower()
        )
        if answer not in ("y", "yes", "j", "ja"):
            print("Aborted.")
            return EXIT_ABORTED
    result = undo(args.journal, args.catalog_backup)
    print(render_result(result, language))
    return EXIT_OK if result.success else EXIT_ERROR


def cmd_profiles(args: argparse.Namespace) -> int:
    names = list_profiles()
    if not names:
        print("No profiles saved yet. Use --save-profile NAME with 'plan' or 'apply'.")
        print("Profile directory: {d}".format(d=profiles_dir()))
        return EXIT_OK
    print("Profiles in {d}:".format(d=profiles_dir()))
    for name in names:
        settings = Settings.load_profile(name)
        print("  {n:<24} {s}".format(n=name, s="/".join(settings.structure)))
    return EXIT_OK


def cmd_tokens(args: argparse.Namespace) -> int:
    print(render_tokens(args.lang or "en"))
    return EXIT_OK


def cmd_presets(args: argparse.Namespace) -> int:
    print(render_presets(args.lang or "en"))
    return EXIT_OK


def cmd_tui(args: argparse.Namespace) -> int:
    try:
        from .tui.app import run_tui
    except ImportError as exc:
        print(
            "The TUI needs Textual. Install it with:\n"
            "    python3 -m pip install 'lr-foldercraft[tui]'\n"
            "or\n"
            "    python3 -m pip install textual\n"
            "({e})".format(e=exc),
            file=sys.stderr,
        )
        return EXIT_ERROR
    return run_tui(catalog=args.catalog, language=args.lang or "en", debug=args.debug)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _folder_prompt(language: str) -> Callable[[FolderCase], Optional[str]]:
    """Build the per-folder question the planner calls back into.

    The planner never prompts on its own -- it hands each folder that could
    reasonably go either way to this callback and takes the answer. Returning
    ``None`` accepts the configured default, so pressing Enter is always safe.

    Everything is written to stderr: the prompt is interface, not output, and
    ``plan --json --interactive`` has to stay machine readable.
    """

    def say(text: str = "") -> None:
        print(text, file=sys.stderr)

    def ask(case: FolderCase) -> Optional[str]:
        choices = DATED_FOLDER_ACTIONS if case.is_dated else SUBFOLDER_ACTIONS
        say()
        say("-" * 78)
        say(case.describe(language))
        if case.is_dated and case.mismatched_photos:
            say(
                (
                    "  davon {n} mit abweichendem Aufnahmedatum"
                    if language == "de"
                    else "  of which {n} have a different capture date"
                ).format(n=case.mismatched_photos)
            )
        for number, action in enumerate(choices, start=1):
            marker = " *" if action == case.action else "  "
            say(
                "  {m}{n}) {a:<14} {d}".format(
                    m=marker, n=number, a=action, d=action_label(action, language)
                )
            )
        question = (
            "  Auswahl [Enter = {d}]: " if language == "de" else "  Choice [Enter = {d}]: "
        ).format(d=case.action)
        while True:
            sys.stderr.write(question)
            sys.stderr.flush()
            try:
                answer = input().strip()
            except (EOFError, KeyboardInterrupt):
                say()
                return None
            if not answer:
                return None
            if answer in choices:
                return answer
            if answer.isdigit() and 1 <= int(answer) <= len(choices):
                return choices[int(answer) - 1]
            say("  ?")

    return ask


def _stamp(prefix: str) -> str:
    return "{p}-{s}".format(p=prefix, s=datetime.now().strftime("%Y%m%d-%H%M%S"))


def _confirm(plan, language: str) -> bool:
    question = (
        "\n{n:,} Datei(en) verschieben und den Katalog aendern? [y/N] "
        if language == "de"
        else "\nMove {n:,} file(s) and modify the catalog? [y/N] "
    ).format(n=plan.stats.touched)
    try:
        answer = input(question).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes", "j", "ja")


def _console_progress(done: int, total: int, message: str) -> None:
    percent = 100.0 * done / total if total else 100.0
    sys.stderr.write(
        "\r  {d:,}/{t:,} ({p:5.1f}%) {m:<50}".format(
            d=done, t=total, p=percent, m=Path(message).name[:50]
        )
    )
    sys.stderr.flush()
    if done >= total:
        sys.stderr.write("\n")


def cmd_gui(args: argparse.Namespace) -> int:
    try:
        from .gui.app import run_gui
    except ImportError as exc:
        print(
            "The graphical interface needs PySide6. Install it with:\n"
            "    python3 -m pip install 'lr-foldercraft[gui]'\n"
            "or\n"
            "    python3 -m pip install PySide6-Essentials\n"
            "({e})".format(e=exc),
            file=sys.stderr,
        )
        return EXIT_ERROR
    return run_gui(catalog=args.catalog or "", language=args.lang or "en", debug=args.debug)


DISPATCH = {
    "info": cmd_info,
    "folders": cmd_folders,
    "plan": cmd_plan,
    "apply": cmd_apply,
    "undo": cmd_undo,
    "profiles": cmd_profiles,
    "tokens": cmd_tokens,
    "presets": cmd_presets,
    "tui": cmd_tui,
    "gui": cmd_gui,
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return EXIT_USAGE

    setup_logging(
        debug=args.debug,
        log_file=Path(args.log_file) if args.log_file else None,
        log_dir=Path(args.log_dir) if args.log_dir else None,
        quiet=args.quiet,
        verbose=args.verbose,
        tag=args.command,
    )
    step("Command: %s", args.command)

    try:
        return DISPATCH[args.command](args)
    except (CatalogError, ConfigError, PlanError, RuleError) as exc:
        log.error("%s", exc)
        print("Error: {e}".format(e=exc), file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        print("\nInterrupted.", file=sys.stderr)
        return EXIT_ABORTED
    except Exception as exc:  # noqa: BLE001 - top level guard
        log.exception("Unhandled error: %s", exc)
        print("Unexpected error: {e}".format(e=exc), file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
