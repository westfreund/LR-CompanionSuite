"""Render the PNG sizes of the mark from its two SVG sources.

The mark lives in exactly two files, both single-colour and both taking
``currentColor``. Everything raster is produced from them by this script, so a
change to the drawing never has to be repeated by hand across six sizes and two
colour ways.

    python scripts/make_brand.py

Needs the gui extra: it rasterises through Qt rather than an extra dependency.
"""

from __future__ import annotations

import os
import sys
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "docs" / "images" / "brand"

#: Below this the full mark is unreadable, which is what the small cut is for.
SMALL_CUT_UP_TO = 24

SIZES = (16, 24, 32, 64, 128, 256, 512)

#: One file per colour way. The SVG is single-colour by design; these are the
#: two grounds the mark actually has to sit on.
COLOURS = {"dark": "#17191d", "light": "#f2f2f3"}


def check_well_formed(path: Path) -> None:
    """Parse before rendering.

    A double hyphen inside an XML comment makes a file that renders as an empty
    image with no error anywhere, which cost an afternoon once.
    """
    xml.dom.minidom.parse(str(path))


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QByteArray, QRectF, Qt
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    full, small = BRAND / "logo.svg", BRAND / "logo-small.svg"
    for source in (full, small):
        check_well_formed(source)

    QGuiApplication.instance() or QGuiApplication([])
    written = 0
    for size in SIZES:
        source = small if size <= SMALL_CUT_UP_TO else full
        for way, colour in COLOURS.items():
            text = source.read_text(encoding="utf-8").replace("currentColor", colour)
            renderer = QSvgRenderer(QByteArray(text.encode("utf-8")))
            if not renderer.isValid():
                print("cannot render {s}".format(s=source), file=sys.stderr)
                return 1
            image = QImage(size, size, QImage.Format_ARGB32)
            image.fill(Qt.transparent)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing, True)
            renderer.render(painter, QRectF(0, 0, size, size))
            painter.end()
            target = BRAND / "logo-{s}-{w}.png".format(s=size, w=way)
            image.save(str(target))
            written += 1
            print("  {p}  ({src})".format(p=target.relative_to(ROOT), src=source.name))
    print("{n} file(s) written".format(n=written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
