"""Run configuration and reusable profiles.

Profiles are plain JSON so that no third party parser is required on the
Python 3.9 baseline. They live in a per-user config directory and can be
listed, saved and loaded from both the CLI and the TUI.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .folders import (
    CONSOLIDATE,
    DATED_FOLDER_ACTIONS,
    KEEP,
    MISMATCH_ACTIONS,
    MOVE_OUT,
    SUBFOLDER_ACTIONS,
    FolderRule,
    FolderRuleError,
    parse_rules,
)
from .logging_setup import get_logger
from .rules import RuleError, make_cumulative, parse_structure, validate_structure
from .version import __version__

log = get_logger("config")

#: How a photo without a usable capture date is handled.
MISSING_DATE_MODES = ("unsorted", "skip", "abort")

#: How a name collision in the target folder is handled.
CONFLICT_MODES = ("rename", "skip", "abort")

#: Where the new folders are created.
PLACEMENT_MODES = ("in-place", "new-tree")

#: Which timestamp drives the date tokens, tried in the given order.
DATE_SOURCES = ("capture", "exif-fields", "file-mtime")


class ConfigError(ValueError):
    """Raised for an invalid configuration."""


#: What the directory was called before the tools became a suite. A person's
#: profiles, their remembered window and their library index all live in it, so
#: the rename moves them rather than starting again somewhere else.
FORMER_DIRECTORY_NAMES = {
    "win32": "LR-FolderCraft",
    "darwin": "LR-FolderCraft",
    "linux": "lr-foldercraft",
}


def _config_home() -> tuple[Path, str, str]:
    """Where per-user files live, and what this directory is called here."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base, "LR-CompanionSuite", FORMER_DIRECTORY_NAMES["win32"]
    if sys.platform == "darwin":
        return (
            Path.home() / "Library" / "Application Support",
            "LR-CompanionSuite",
            FORMER_DIRECTORY_NAMES["darwin"],
        )
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base, "lr-companion-suite", FORMER_DIRECTORY_NAMES["linux"]


def config_dir() -> Path:
    """Return the per-user configuration directory.

    If the suite's directory does not exist yet but the folder tool's older one
    does, it is moved across. Losing somebody's profiles and their library index
    to a rename would be a poor way to introduce a new name, and leaving them
    behind silently would be worse than losing them loudly.
    """
    env = os.environ.get("LRFC_CONFIG_DIR")
    if env:
        return Path(env).expanduser()
    base, name, former = _config_home()
    directory = base / name
    if not directory.exists():
        previous = base / former
        if previous.is_dir():
            try:
                previous.rename(directory)
                log.info("Moved the configuration from %s to %s", previous, directory)
            except OSError as error:  # pragma: no cover - depends on the filesystem
                log.warning("Could not move %s to %s: %s", previous, directory, error)
                return previous
    return directory


#: Settings that describe one particular library rather than a way of working.
#: A profile leaves them out so it can be applied to the next library unchanged.
PER_LIBRARY_FIELDS = frozenset(
    {
        "catalog",
        "target_root",
        "root_folder_id",
        "anchor_folder_id",
        "folder_ids",
        "folder_actions",
        "folder_rules",
    }
)

#: Escape hatches for one awkward run. Carrying "ignore the lock" or "skip the
#: backup" into the next library, months later and unnoticed, is exactly the
#: kind of thing a profile must not do.
NEVER_IN_A_PROFILE = frozenset(
    {"ignore_lock", "allow_unsupported_catalog", "backup_catalog", "dry_run"}
)


def profiles_dir() -> Path:
    return config_dir() / "profiles"


def default_backup_dir() -> Path:
    env = os.environ.get("LRFC_BACKUP_DIR")
    if env:
        return Path(env).expanduser()
    return config_dir() / "backups"


def default_report_dir() -> Path:
    env = os.environ.get("LRFC_REPORT_DIR")
    if env:
        return Path(env).expanduser()
    return config_dir() / "reports"


@dataclass
class Settings:
    """Everything that determines what a run does.

    Only :attr:`catalog` and :attr:`structure` are really mandatory; every
    other field has a conservative default. ``dry_run`` defaults to ``True`` --
    the tool never writes unless the caller says so explicitly.
    """

    # -- what to work on ------------------------------------------------
    catalog: str = ""
    root_folder_id: Optional[int] = None
    folder_ids: Tuple[int, ...] = ()
    include_extensions: Tuple[str, ...] = ()
    exclude_extensions: Tuple[str, ...] = ()

    # -- how to group ---------------------------------------------------
    structure: Tuple[str, ...] = ("{yyyy}-{mm}-{dd}",)
    placement: str = "in-place"
    target_root: Optional[str] = None
    anchor_folder_id: Optional[int] = None
    language: str = "en"
    ascii_only: bool = False

    # -- existing folder structure --------------------------------------
    #: What to do with a subfolder whose name carries no date ("Urlaub").
    subfolder_action: str = CONSOLIDATE
    #: What to do with a folder whose name starts with a date
    #: ("2019-04-15 Ostern in Tirol").
    dated_folder_action: str = KEEP
    #: What to do with a photo inside a kept dated folder whose capture date
    #: does not match the folder's name.
    mismatch_action: str = MOVE_OUT
    #: Ordered ``"PATTERN=ACTION"`` rules, first match wins. A rule speaks
    #: about a whole class of folders at once and beats the three settings
    #: above, so a grown library needs a handful of lines instead of one
    #: answer per folder. See :mod:`lrcompanion.folders` for the patterns.
    folder_rules: Tuple[str, ...] = ()
    #: Per-folder overrides, ``{catalog folder id: action}``. Beats the rules
    #: and the three settings above, and is what an operator's case-by-case
    #: answers become.
    folder_actions: Dict[int, str] = field(default_factory=dict)
    #: Ask the operator about every folder that could reasonably go either way.
    interactive_folders: bool = False

    #: Repeat the coarser date parts in every date level, so ``{yyyy}/{mm}``
    #: reads ``2019/2019-01`` rather than ``2019/01``. Every folder name is
    #: then complete on its own.
    cumulative_dates: bool = False

    #: Sweep files that are on disk but not in the catalog into one folder.
    #: Off by default: it moves files nobody asked the tool about.
    collect_orphans: bool = False
    #: Where they go, below each source root.
    orphan_folder: str = "_not-in-catalog"

    #: Write a human readable record of the run beside the library. It is
    #: named after the tool, the date and the catalog, so it is found by
    #: whoever wonders months later where a photo went.
    move_log: bool = True
    #: Where that record goes. ``None`` means beside the ``.lrcat`` file.
    move_log_dir: Optional[str] = None

    # -- edge cases -----------------------------------------------------
    date_source: Tuple[str, ...] = ("capture", "exif-fields")
    on_missing_date: str = "unsorted"
    unsorted_folder: str = "_unsorted"
    conflict: str = "rename"
    move_sidecars: bool = True
    extra_sidecar_extensions: Tuple[str, ...] = ("xmp",)

    # -- execution ------------------------------------------------------
    dry_run: bool = True
    backup_catalog: bool = True
    backup_dir: Optional[str] = None
    prune_empty_folders: bool = True
    verify_after: bool = True
    allow_unsupported_catalog: bool = False
    ignore_lock: bool = False

    # -- bookkeeping ----------------------------------------------------
    profile_name: Optional[str] = None
    created_with: str = __version__

    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        self.structure = tuple(self.structure)
        self.folder_ids = tuple(self.folder_ids)
        self.include_extensions = tuple(e.lower().lstrip(".") for e in self.include_extensions)
        self.exclude_extensions = tuple(e.lower().lstrip(".") for e in self.exclude_extensions)
        self.extra_sidecar_extensions = tuple(
            e.lower().lstrip(".") for e in self.extra_sidecar_extensions
        )
        self.date_source = tuple(self.date_source)
        self.folder_rules = tuple(str(r).strip() for r in self.folder_rules if str(r).strip())
        self.folder_actions = {int(k): str(v) for k, v in dict(self.folder_actions).items()}

    def validate(self) -> None:
        """Raise :class:`ConfigError` describing the first problem found."""
        if not self.catalog:
            raise ConfigError("no catalog given")
        try:
            validate_structure(self.structure)
        except RuleError as exc:
            raise ConfigError(str(exc)) from exc
        if self.placement not in PLACEMENT_MODES:
            raise ConfigError("placement must be one of {m}".format(m=", ".join(PLACEMENT_MODES)))
        if self.placement == "new-tree" and not self.target_root:
            raise ConfigError("placement 'new-tree' requires --target-root")
        if self.on_missing_date not in MISSING_DATE_MODES:
            raise ConfigError(
                "on-missing-date must be one of {m}".format(m=", ".join(MISSING_DATE_MODES))
            )
        if self.conflict not in CONFLICT_MODES:
            raise ConfigError("conflict must be one of {m}".format(m=", ".join(CONFLICT_MODES)))
        for source in self.date_source:
            if source not in DATE_SOURCES:
                raise ConfigError(
                    "unknown date source {s!r}; known: {k}".format(
                        s=source, k=", ".join(DATE_SOURCES)
                    )
                )
        if not self.date_source:
            raise ConfigError("date-source list must not be empty")
        if self.language not in ("en", "de"):
            raise ConfigError("language must be 'en' or 'de'")
        if self.include_extensions and self.exclude_extensions:
            overlap = set(self.include_extensions) & set(self.exclude_extensions)
            if overlap:
                raise ConfigError(
                    "extension(s) both included and excluded: " + ", ".join(sorted(overlap))
                )
        if not self.unsorted_folder.strip():
            raise ConfigError("unsorted-folder name must not be empty")
        if self.collect_orphans and not self.orphan_folder.strip():
            raise ConfigError("orphan-folder name must not be empty")
        if "/" in self.orphan_folder or "\\" in self.orphan_folder:
            raise ConfigError("orphan-folder must be a single folder name, not a path")
        if self.subfolder_action not in SUBFOLDER_ACTIONS:
            raise ConfigError(
                "subfolder-action must be one of {m}".format(m=", ".join(SUBFOLDER_ACTIONS))
            )
        if self.dated_folder_action not in DATED_FOLDER_ACTIONS:
            raise ConfigError(
                "dated-folder-action must be one of {m}".format(m=", ".join(DATED_FOLDER_ACTIONS))
            )
        if self.mismatch_action not in MISMATCH_ACTIONS:
            raise ConfigError(
                "mismatch-action must be one of {m}".format(m=", ".join(MISMATCH_ACTIONS))
            )
        for folder_id, action in self.folder_actions.items():
            if action not in set(SUBFOLDER_ACTIONS) | set(DATED_FOLDER_ACTIONS):
                raise ConfigError(
                    "unknown action {a!r} for folder {f}".format(a=action, f=folder_id)
                )
        try:
            parse_rules(self.folder_rules)
        except FolderRuleError as error:
            raise ConfigError(str(error)) from error

    @property
    def effective_structure(self) -> Tuple[str, ...]:
        """The structure as it will actually be rendered.

        :attr:`structure` stays as the operator wrote it, so turning
        ``cumulative_dates`` off restores exactly what they typed.
        """
        if not self.cumulative_dates:
            return tuple(self.structure)
        return make_cumulative(self.structure)

    @property
    def parsed_folder_rules(self) -> Tuple[FolderRule, ...]:
        """The rule list as objects the planner can match against."""
        return parse_rules(self.folder_rules)

    # -- serialisation ---------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, tuple):
                data[key] = list(value)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Settings:
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            log.warning("Ignoring unknown setting(s) in profile: %s", ", ".join(sorted(unknown)))
        return cls(**{k: v for k, v in data.items() if k in known})

    def save_profile(self, name: str, directory: Optional[Path] = None) -> Path:
        """Persist these settings as a named profile and return its path.

        A profile carries the **options** and nothing that belongs to one
        library: not the catalog, not the target folder, not the rule list, and
        certainly not the per-folder decisions, which are catalog row ids and
        would apply one library's answer to whatever folder happens to share a
        number in the next. That is what makes a profile worth having when the
        same way of sorting is wanted across several collections.
        """
        target_dir = Path(directory) if directory else profiles_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / "{n}.json".format(n=_safe_profile_name(name))
        payload = self.to_dict()
        payload["profile_name"] = name
        # A profile describes *how* to sort, not one specific run.
        payload.pop("dry_run", None)
        for field_name in PER_LIBRARY_FIELDS | NEVER_IN_A_PROFILE:
            payload.pop(field_name, None)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        log.info("Saved profile %r to %s", name, path)
        return path

    @classmethod
    def load_profile(cls, name: str, directory: Optional[Path] = None) -> Settings:
        source_dir = Path(directory) if directory else profiles_dir()
        path = source_dir / "{n}.json".format(n=_safe_profile_name(name))
        if not path.exists():
            raise ConfigError("profile not found: {p}".format(p=path))
        data = json.loads(path.read_text(encoding="utf-8"))
        settings = cls.from_dict(data)
        log.info("Loaded profile %r from %s", name, path)
        return settings

    @classmethod
    def load_file(cls, path: str | Path) -> Settings:
        source = Path(path).expanduser()
        if not source.exists():
            raise ConfigError("config file not found: {p}".format(p=source))
        return cls.from_dict(json.loads(source.read_text(encoding="utf-8")))

    # -- convenience ------------------------------------------------------

    def resolved_backup_dir(self) -> Path:
        return Path(self.backup_dir).expanduser() if self.backup_dir else default_backup_dir()

    def with_structure(self, spec: str) -> Settings:
        """Return a copy whose structure comes from a preset name or template."""
        clone = Settings.from_dict(self.to_dict())
        clone.structure = parse_structure(spec)
        return clone

    def accepts_extension(self, extension: str) -> bool:
        ext = (extension or "").lower().lstrip(".")
        if self.include_extensions and ext not in self.include_extensions:
            return False
        if ext in self.exclude_extensions:
            return False
        return True


def _safe_profile_name(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-")
    if not cleaned:
        raise ConfigError("invalid profile name: {n!r}".format(n=name))
    return cleaned


def list_profiles(directory: Optional[Path] = None) -> List[str]:
    """Return the names of all saved profiles."""
    source_dir = Path(directory) if directory else profiles_dir()
    if not source_dir.exists():
        return []
    return sorted(p.stem for p in source_dir.glob("*.json"))


def profile_exists(name: str, directory: Optional[Path] = None) -> bool:
    source_dir = Path(directory) if directory else profiles_dir()
    return (source_dir / "{n}.json".format(n=_safe_profile_name(name))).is_file()


def delete_profile(name: str, directory: Optional[Path] = None) -> Path:
    """Remove a saved profile and return the path that is gone.

    An interface that can make profiles but not unmake them turns the profile
    folder into a place where mistakes accumulate for ever.
    """
    source_dir = Path(directory) if directory else profiles_dir()
    path = source_dir / "{n}.json".format(n=_safe_profile_name(name))
    if not path.is_file():
        raise ConfigError("profile not found: {p}".format(p=path))
    path.unlink()
    log.info("Deleted profile %r at %s", name, path)
    return path
