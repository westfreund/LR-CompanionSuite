"""Run configuration and reusable profiles.

Profiles are plain JSON so that no third party parser is required on the
Python 3.9 baseline. They live in a per-user config directory and can be
listed, saved and loaded from both the CLI and the TUI.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .logging_setup import get_logger
from .rules import RuleError, parse_structure, validate_structure
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


def config_dir() -> Path:
    """Return the per-user configuration directory."""
    env = os.environ.get("LRFC_CONFIG_DIR")
    if env:
        return Path(env).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "LR-FolderCraft"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "LR-FolderCraft"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "lr-foldercraft"


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
        """Persist these settings as a named profile and return its path."""
        target_dir = Path(directory) if directory else profiles_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / "{n}.json".format(n=_safe_profile_name(name))
        payload = self.to_dict()
        payload["profile_name"] = name
        # A profile describes *how* to sort, not one specific run.
        payload.pop("dry_run", None)
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
