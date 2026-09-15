"""Which drive a path is on, and how to name that drive next time.

A drive's *name* is not an identity. Two external disks called "Backup" are a
matter of time, and renaming one would silently split its catalogs in the index
or merge them with another's. Every platform can do better than the name, so
this asks the platform first and only falls back to a fingerprint -- and when
it does fall back, it says so, because a weaker answer that presents itself as
a strong one is worse than no answer.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import hashlib
import os
import platform
import plistlib
import subprocess
from pathlib import Path
from typing import NamedTuple, Optional

from ..logging_setup import get_logger

log = get_logger("metasearch.volumes")

#: How the identifier was arrived at. The index stores this so a later reader
#: can tell a real volume id from a guess.
BY_UUID = "uuid"
BY_FINGERPRINT = "fingerprint"


class Volume(NamedTuple):
    """One drive, as the index knows it."""

    identity: str
    kind: str
    label: str
    mount: str
    filesystem: str
    total_bytes: int

    @property
    def is_certain(self) -> bool:
        return self.kind == BY_UUID


def mount_point(path: str | Path) -> Path:
    """The drive *path* sits on."""
    current = Path(path).expanduser().resolve()
    if not current.exists():
        current = current.parent
    while not os.path.ismount(str(current)) and current != current.parent:
        current = current.parent
    return current


def _macos_uuid(mount: Path) -> Optional[str]:
    try:
        out = subprocess.run(
            ["diskutil", "info", "-plist", str(mount)],
            capture_output=True,
            timeout=20,
        )
        if out.returncode != 0:
            return None
        info = plistlib.loads(out.stdout)
    except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException) as exc:
        log.debug("diskutil could not describe %s: %s", mount, exc)
        return None
    return info.get("VolumeUUID") or info.get("DiskUUID") or None


def _linux_uuid(mount: Path) -> Optional[str]:
    try:
        out = subprocess.run(
            ["findmnt", "-no", "UUID", "--target", str(mount)],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - platform
        log.debug("findmnt could not describe %s: %s", mount, exc)
        return None
    value = out.stdout.strip()
    return value or None


def _windows_serial(mount: Path) -> Optional[str]:  # pragma: no cover - platform
    """The volume serial number, which survives a rename.

    Not the same thing as a UUID -- it is 32 bits and is reassigned by a
    reformat -- but it is what Windows offers without extra dependencies, and
    it is bound to the volume rather than to its label.
    """
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(1024)
        serial = ctypes.c_ulong(0)
        root = str(mount)
        if not root.endswith("\\"):
            root += "\\"
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            buffer,
            ctypes.sizeof(buffer),
            ctypes.byref(serial),
            None,
            None,
            None,
            0,
        )
        if not ok:
            return None
        return "{s:08X}".format(s=serial.value)
    except Exception as exc:  # noqa: BLE001 - any failure means "fall back"
        log.debug("GetVolumeInformationW failed for %s: %s", mount, exc)
        return None


def _filesystem(mount: Path) -> str:
    system = platform.system()
    if system == "Darwin":
        try:
            out = subprocess.run(
                ["diskutil", "info", "-plist", str(mount)], capture_output=True, timeout=20
            )
            if out.returncode == 0:
                return str(plistlib.loads(out.stdout).get("FilesystemType") or "")
        except Exception:  # noqa: BLE001 - cosmetic only
            pass
    return ""


def _fingerprint(mount: Path, label: str, filesystem: str, total: int) -> str:
    """A last resort, and marked as one.

    Name plus size plus filesystem is not unique in principle. It is stable
    enough to keep one drive's catalogs together between sessions, which is all
    it is asked to do.
    """
    material = "|".join([label, filesystem, str(total)])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def describe(path: str | Path) -> Volume:
    """Identify the drive *path* is on."""
    mount = mount_point(path)
    # The boot volume mounts at "/", whose name is empty; "/" as a drive label
    # in a list of drives tells the reader nothing.
    label = mount.name or (platform.node() or str(mount))
    try:
        stat = os.statvfs(str(mount))
        total = stat.f_blocks * stat.f_frsize
    except OSError:  # pragma: no cover - a vanished mount
        total = 0
    filesystem = _filesystem(mount)

    system = platform.system()
    identity = None
    if system == "Darwin":
        identity = _macos_uuid(mount)
    elif system == "Linux":  # pragma: no cover - platform
        identity = _linux_uuid(mount)
    elif system == "Windows":  # pragma: no cover - platform
        identity = _windows_serial(mount)

    if identity:
        return Volume(identity, BY_UUID, label, str(mount), filesystem, total)
    log.info("No volume id for %s; falling back to a fingerprint", mount)
    return Volume(
        _fingerprint(mount, label, filesystem, total),
        BY_FINGERPRINT,
        label,
        str(mount),
        filesystem,
        total,
    )
