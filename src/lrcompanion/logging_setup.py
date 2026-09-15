"""Logging configuration for the LR-CompanionSuite.

Requirements this module implements:

* Every executed script step is written to a log file.
* A ``--debug`` mode raises verbosity to DEBUG and adds source locations.
* The log file header always records revision and build date, so a log can be
  attributed to an exact tool revision later on.
* A dedicated :func:`step` helper produces uniformly numbered, greppable
  ``STEP nnn`` lines that form the audit trail of a run.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .version import REVISION, __build_date__, __version__, banner

LOGGER_NAME = "lrcompanion"

#: Format used for the on-disk log -- deliberately verbose and machine
#: parseable (ISO timestamp | level | logger | message).
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s"
FILE_FORMAT_DEBUG = (
    "%(asctime)s | %(levelname)-8s | %(name)-28s | "
    "%(filename)s:%(lineno)d:%(funcName)s | %(message)s"
)
CONSOLE_FORMAT = "%(levelname)-8s %(message)s"

_step_counter = 0


def default_log_dir() -> Path:
    """Return the platform specific directory for log files."""
    env = os.environ.get("LRFC_LOG_DIR")
    if env:
        return Path(env).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "LR-CompanionSuite" / "logs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "LR-CompanionSuite"
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "lr-companion-suite" / "logs"


def build_log_path(log_dir: Optional[Path] = None, tag: str = "run") -> Path:
    """Return a timestamped log file path inside *log_dir*."""
    directory = Path(log_dir) if log_dir else default_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return directory / "lrfc-{tag}-{stamp}.log".format(tag=tag, stamp=stamp)


class _NotFileOnly(logging.Filter):
    """Keeps records marked ``file_only`` off the console."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not getattr(record, "file_only", False)


def setup_logging(
    debug: bool = False,
    log_file: Optional[Path] = None,
    log_dir: Optional[Path] = None,
    quiet: bool = False,
    verbose: bool = False,
    tag: str = "run",
) -> Path:
    """Configure the package logger and return the active log file path.

    The log *file* always receives everything from INFO (DEBUG with *debug*).
    The console is intentionally quiet -- WARNING and above -- so that command
    output stays readable; ``verbose`` or ``debug`` open it up.

    Args:
        debug: enable DEBUG level everywhere and add source locations.
        log_file: explicit log file path; overrides *log_dir*.
        log_dir: directory for an auto-named log file.
        quiet: console output only for errors.
        verbose: also show INFO level progress on the console.
        tag: short label embedded in the auto-generated file name.
    """
    global _step_counter
    _step_counter = 0

    path = Path(log_file) if log_file else build_log_path(log_dir, tag=tag)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT_DEBUG if debug else FILE_FORMAT))
    logger.addHandler(file_handler)

    console = logging.StreamHandler(stream=sys.stderr)
    if debug:
        console.setLevel(logging.DEBUG)
    elif quiet:
        console.setLevel(logging.ERROR)
    elif verbose:
        console.setLevel(logging.INFO)
    else:
        console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    console.addFilter(_NotFileOnly())
    logger.addHandler(console)

    _write_header(logger, path, debug)
    return path


def _write_header(logger: logging.Logger, path: Path, debug: bool) -> None:
    only = {"file_only": True}
    logger.info("=" * 78, extra=only)
    logger.info(banner(), extra=only)
    logger.info(
        "Revision %s | version %s | build date %s",
        REVISION,
        __version__,
        __build_date__,
        extra=only,
    )
    logger.info("Log file      : %s", path, extra=only)
    logger.info("Debug mode    : %s", "ON" if debug else "off", extra=only)
    logger.info("Python        : %s (%s)", platform.python_version(), sys.executable, extra=only)
    logger.info(
        "Platform      : %s %s (%s)",
        platform.system(),
        platform.release(),
        platform.machine(),
        extra=only,
    )
    logger.info("Working dir   : %s", Path.cwd(), extra=only)
    logger.info("Command line  : %s", " ".join(sys.argv), extra=only)
    logger.info("=" * 78, extra=only)


def get_logger(name: str = "") -> logging.Logger:
    """Return a child logger below the package root logger."""
    if not name:
        return logging.getLogger(LOGGER_NAME)
    return logging.getLogger("{root}.{name}".format(root=LOGGER_NAME, name=name))


def step(message: str, *args: object) -> None:
    """Log a numbered high-level script step.

    Every meaningful action taken by the tool goes through this helper, which
    yields a contiguous ``STEP 001 ...`` trail in the log file.
    """
    global _step_counter
    _step_counter += 1
    logging.getLogger(LOGGER_NAME).info(
        "STEP %03d | %s", _step_counter, message % args if args else message
    )


def current_step() -> int:
    """Return the number of steps logged so far in this run."""
    return _step_counter
