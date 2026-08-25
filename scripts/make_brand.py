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

#: The avatar a repository host shows beside the project name. It needs a
#: ground of its own: the mark is transparent, and an avatar dropped onto
#: whichever colour the host happens to use that season is not a mark, it is a
#: gamble. Square, because both hosts crop to a square and round it themselves.
AVATAR_SIZE = 512

#: A card for the link preview -- what a chat window or a social site shows
#: when the address is pasted. Neither host generates one from the README.
SOCIAL_SIZE = (1280, 640)
SOCIAL_TEXT = {
    "title": "LR-FolderCraft",
    "line": "Reorganise Lightroom Classic folders without losing the catalog",
    "line_de": "Lightroom-Ordner umsortieren, ohne den Katalog zu verlieren",
}


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
    written += write_avatar(small, QByteArray, QRectF, Qt, QImage, QPainter, QSvgRenderer)
    written += write_social(full, QByteArray, QRectF, Qt, QImage, QPainter, QSvgRenderer)
    print("{n} file(s) written".format(n=written))
    return 0


def _render(source_text, QByteArray, QSvgRenderer):
    renderer = QSvgRenderer(QByteArray(source_text.encode("utf-8")))
    if not renderer.isValid():  # pragma: no cover - a malformed source
        raise SystemExit("cannot render the mark")
    return renderer


def write_avatar(source, QByteArray, QRectF, Qt, QImage, QPainter, QSvgRenderer) -> int:
    """The square tile the hosts show beside the project name.

    Drawn from the small cut, not the full mark: an avatar lives at forty
    pixels in a list of repositories, and four elements do not survive that any
    better there than they do in a favicon.
    """
    from PySide6.QtGui import QColor

    text = source.read_text(encoding="utf-8").replace("currentColor", COLOURS["light"])
    renderer = _render(text, QByteArray, QSvgRenderer)
    size = AVATAR_SIZE
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(QColor(COLOURS["dark"]))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    inset = size * 0.16
    renderer.render(painter, QRectF(inset, inset, size - 2 * inset, size - 2 * inset))
    painter.end()
    target = BRAND / "avatar-{s}.png".format(s=size)
    image.save(str(target))
    print("  {p}  (logo-small.svg on a ground)".format(p=target.relative_to(ROOT)))
    return 1


def write_social(source, QByteArray, QRectF, Qt, QImage, QPainter, QSvgRenderer) -> int:
    """The wide card a link preview shows. Mark on the left, words on the right.

    Sizes in pixels, not points: a point is a physical measure that Qt resolves
    against whatever the machine claims its screen is, and the first cut ran off
    the right-hand edge on this one. A card is pixels wide, so say pixels.
    """
    from PySide6.QtGui import QColor, QFont

    text = source.read_text(encoding="utf-8").replace("currentColor", COLOURS["light"])
    renderer = _render(text, QByteArray, QSvgRenderer)
    width, height = SOCIAL_SIZE
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(QColor(COLOURS["dark"]))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)

    mark = 320
    renderer.render(painter, QRectF(88, (height - mark) / 2, mark, mark))

    left = 88 + mark + 64
    column = width - left - 88
    wrap = int(Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap)

    title = QFont()
    title.setPixelSize(78)
    title.setWeight(QFont.Bold)
    painter.setFont(title)
    painter.setPen(QColor(COLOURS["light"]))
    painter.drawText(QRectF(left, 176, column, 96), wrap, SOCIAL_TEXT["title"])

    body = QFont()
    body.setPixelSize(34)
    painter.setFont(body)
    painter.setPen(QColor("#c3c7cf"))
    painter.drawText(QRectF(left, 292, column, 110), wrap, SOCIAL_TEXT["line"])

    body.setPixelSize(30)
    painter.setFont(body)
    painter.setPen(QColor("#8c9199"))
    painter.drawText(QRectF(left, 396, column, 110), wrap, SOCIAL_TEXT["line_de"])
    painter.end()
    target = BRAND / "social-{w}x{h}.png".format(w=width, h=height)
    image.save(str(target))
    print("  {p}".format(p=target.relative_to(ROOT)))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
