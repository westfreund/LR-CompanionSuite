"""Build a place to experiment, out of disk images that behave like drives.

Three faults reached Lightroom before anyone caught them, and every one of them
was invisible to the test suite: a synthetic catalog is a plausible imitation of
a real one, and plausible is exactly what fails here. So the experiments need
real catalogs -- and real catalogs need Lightroom, which is the one thing this
script cannot do.

What it *can* do is everything around them. A disk image mounts at
``/Volumes/<name>``, carries a genuine VolumeUUID, and can be detached or
renamed -- which is a drive being unplugged, or replaced, without anybody
having to own five external disks.

    python scripts/make_playground.py prepare   ~/Desktop/LRCS-Spielwiese
    #   ... make catalogs in Lightroom, then:
    python scripts/make_playground.py scenarios ~/Desktop/LRCS-Spielwiese
    python scripts/make_playground.py teardown  ~/Desktop/LRCS-Spielwiese

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

#: The drives the playground pretends to have. A source, a backup target, and
#: the name the source is later renamed to -- the three states every one of
#: these problems lives in.
SOURCE = "LRCS_Quelle"
BACKUP = "LRCS_Sicherung"
RENAMED = "LRCS_Quelle_neu"

#: Small enough to make and throw away without thinking about it.
IMAGE_MB = 200
PHOTOS = 12


def run(*command: str) -> str:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit("{c} failed: {e}".format(c=" ".join(command), e=result.stderr.strip()))
    return result.stdout


def is_mounted(name: str) -> bool:
    return Path("/Volumes", name).is_dir()


def detach(name: str) -> None:
    if is_mounted(name):
        subprocess.run(
            ["hdiutil", "detach", str(Path("/Volumes", name)), "-quiet"], capture_output=True
        )


def make_image(directory: Path, name: str) -> Path:
    image = directory / "{n}.dmg".format(n=name)
    if image.exists():
        return image
    run(
        "hdiutil",
        "create",
        "-size",
        "{m}m".format(m=IMAGE_MB),
        "-fs",
        "APFS",
        "-volname",
        name,
        "-quiet",
        str(image),
    )
    return image


def attach(image: Path) -> None:
    run("hdiutil", "attach", str(image), "-quiet")


def write_photographs(target: Path, count: int = PHOTOS) -> None:
    """Small JPEGs, so Lightroom has something real to import.

    Drawn rather than copied from anywhere: a playground should not contain
    somebody's photographs, and Lightroom does not care what is in them.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

    QGuiApplication.instance() or QGuiApplication([])
    target.mkdir(parents=True, exist_ok=True)
    for number in range(1, count + 1):
        image = QImage(1200, 800, QImage.Format_RGB32)
        hue = (number * 29) % 360
        image.fill(QColor.fromHsv(hue, 120, 200))
        painter = QPainter(image)
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setPixelSize(160)
        painter.setFont(font)
        painter.drawText(image.rect(), 0x84, "{n:02d}".format(n=number))
        painter.end()
        image.save(str(target / "LRCS_{n:04d}.jpg".format(n=number)), "JPG", 88)


def cmd_prepare(directory: Path) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    for name in (SOURCE, BACKUP):
        attach(make_image(directory, name))
    photographs = Path("/Volumes", SOURCE, "Bilder")
    write_photographs(photographs)

    print("Ready.\n")
    print("Two drives are mounted:")
    print("  /Volumes/{s}   with {n} photographs in Bilder/".format(s=SOURCE, n=PHOTOS))
    print("  /Volumes/{b}   empty, for the backup".format(b=BACKUP))
    print()
    print("Now, in Lightroom Classic -- this is the part no script can do:")
    print("  1. File > New Catalog, save it as /Volumes/{s}/Kurs.lrcat".format(s=SOURCE))
    print("  2. Import the photographs from /Volumes/{s}/Bilder (Add, not Copy)".format(s=SOURCE))
    print("  3. Edit two or three of them, add a keyword or two,")
    print("     make one virtual copy and stack two photographs")
    print("  4. Quit Lightroom, so the catalog is closed and complete")
    print()
    print("Then run:  python scripts/make_playground.py scenarios {d}".format(d=directory))
    return 0


def cmd_scenarios(directory: Path) -> int:
    source = Path("/Volumes", SOURCE)
    backup = Path("/Volumes", BACKUP)
    if not source.is_dir():
        raise SystemExit("{s} is not mounted -- run prepare first".format(s=source))
    catalogs = [p for p in source.rglob("*.lrcat") if not p.name.startswith("._")]
    if not catalogs:
        raise SystemExit(
            "no catalog on {s}. Make one in Lightroom first; prepare explains how.".format(s=source)
        )

    print("Found {n} catalog(s):".format(n=len(catalogs)))
    for catalog in catalogs:
        print("  {c}".format(c=catalog))

    # 1. A backup: the whole library copied, catalog and all. Its paths point at
    #    the source drive, which is correct and must not be "repaired".
    target = backup / "Sicherung von {s}".format(s=SOURCE)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(str(source), str(target), ignore=shutil.ignore_patterns("._*"))
    print("\n  backup made at {t}".format(t=target))

    # 2. A library moved sideways on its own drive: the catalog still names the
    #    old folder, which is gone.
    moved = source / "Umgezogen"
    if not moved.exists():
        shutil.copytree(
            str(catalogs[0].parent),
            str(moved),
            ignore=shutil.ignore_patterns("._*"),
        )
        print("  a copy moved to {m} (its paths now lead nowhere)".format(m=moved))

    print("\nThe drives can now be put into any of these states by hand:")
    print("  detach the source        hdiutil detach /Volumes/{s}".format(s=SOURCE))
    print("  rename it                diskutil rename /Volumes/{s} {r}".format(s=SOURCE, r=RENAMED))
    print("  put it back              diskutil rename /Volumes/{r} {s}".format(r=RENAMED, s=SOURCE))
    print("\nWhich covers every case O-34 has to tell apart.")
    return 0


def cmd_teardown(directory: Path) -> int:
    for name in (SOURCE, BACKUP, RENAMED):
        detach(name)
    print("Detached. The disk images are still in {d}; delete them when done.".format(d=directory))
    return 0


COMMANDS = {"prepare": cmd_prepare, "scenarios": cmd_scenarios, "teardown": cmd_teardown}


def main(argv) -> int:
    if len(argv) != 3 or argv[1] not in COMMANDS:
        print(__doc__)
        return 2
    return COMMANDS[argv[1]](Path(argv[2]).expanduser())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
