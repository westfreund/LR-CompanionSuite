"""The mark: two cuts, single colour, and both of them actually renderable."""

from __future__ import annotations

import xml.dom.minidom
from pathlib import Path

import pytest

from lrfoldercraft.resources import LOGO, LOGO_SMALL, logo_for

BRAND = Path(__file__).resolve().parent.parent / "docs" / "images" / "brand"


@pytest.mark.parametrize("source", [LOGO, LOGO_SMALL])
def test_the_mark_is_well_formed_xml(source):
    """A double hyphen inside an XML comment yields an empty image, silently.

    It raises nothing the renderer reports; the file simply draws nothing. This
    happened once and cost a full round of rendering to notice.
    """
    xml.dom.minidom.parse(str(source))


@pytest.mark.parametrize("source", [LOGO, LOGO_SMALL])
def test_the_mark_is_single_colour(source):
    """It has to take the surrounding text colour, on any ground."""
    text = source.read_text(encoding="utf-8")
    assert "currentColor" in text
    for literal in ("#", "rgb(", 'fill="black"', 'fill="white"'):
        assert literal not in text.replace("currentColor", ""), literal


@pytest.mark.parametrize("source", [LOGO, LOGO_SMALL])
def test_the_mark_carries_a_name_for_screen_readers(source):
    text = source.read_text(encoding="utf-8")
    assert "<title>" in text
    assert 'role="img"' in text


def test_the_small_cut_is_used_where_the_full_one_cannot_read():
    assert logo_for(16) == LOGO_SMALL
    assert logo_for(24) == LOGO_SMALL
    assert logo_for(32) == LOGO
    assert logo_for(512) == LOGO


def test_the_package_ships_the_mark():
    """It is loaded at runtime for the window icon, so it must be installed."""
    assert LOGO.is_file() and LOGO_SMALL.is_file()


def test_the_exported_sizes_exist_and_are_not_blank():
    """The blank-image failure mode is invisible unless something looks."""
    png = pytest.importorskip("PySide6.QtGui", reason="needs the gui extra")
    from PySide6.QtGui import QImage

    del png
    missing = []
    for size in (16, 24, 32, 64, 128, 256, 512):
        for way in ("dark", "light"):
            path = BRAND / "logo-{s}-{w}.png".format(s=size, w=way)
            if not path.is_file():
                missing.append(path.name)
                continue
            image = QImage(str(path))
            assert not image.isNull(), path.name
            assert image.width() == size, path.name
            opaque = any(
                image.pixelColor(x, y).alpha() > 0
                for x in range(0, size, max(1, size // 16))
                for y in range(0, size, max(1, size // 16))
            )
            assert opaque, "{p} is a blank image".format(p=path.name)
    assert not missing, missing
