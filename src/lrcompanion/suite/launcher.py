"""The launcher window: one tile per tool.

Deliberately plain. Its whole job is to say what the suite contains and get out
of the way -- and to have somewhere obvious to put the next tool, which is the
reason it exists at all rather than two separate commands.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..logging_setup import get_logger, setup_logging
from ..resources import logo_for
from ..version import REVISION, SUITE_NAME, __build_date__
from . import TOOLS
from .i18n import tr

log = get_logger("suite.launcher")

#: How many tiles fit across before wrapping. Two reads comfortably at the
#: window's opening size and leaves the grid room to grow downwards.
COLUMNS = 2


def tinted(family: str, size: int, colour: QColor) -> QPixmap:
    """A cut of the mark in *colour*, so it reads in either theme."""
    from PySide6.QtCore import QByteArray, QRectF
    from PySide6.QtSvg import QSvgRenderer

    text = logo_for(size, family).read_text(encoding="utf-8")
    text = text.replace("currentColor", colour.name(QColor.HexRgb))
    renderer = QSvgRenderer(QByteArray(text.encode("utf-8")))
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return QPixmap.fromImage(image)


class Tile(QFrame):
    """One tool, offered."""

    def __init__(self, tool, language: str, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.language = language
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumSize(300, 190)

        column = QVBoxLayout(self)
        head = QHBoxLayout()
        self.mark = QLabel()
        self.mark.setPixmap(tinted(tool.family, 48, self.palette().windowText().color()))
        head.addWidget(self.mark)
        self.name = QLabel("<b>{n}</b>".format(n=tool.name))
        self.name.setTextFormat(Qt.RichText)
        head.addWidget(self.name, 1)
        column.addLayout(head)

        self.what = QLabel()
        self.what.setWordWrap(True)
        column.addWidget(self.what, 1)

        self.hint = QLabel()
        self.hint.setEnabled(False)
        column.addWidget(self.hint)

        self.open_button = QPushButton()
        column.addWidget(self.open_button, 0, Qt.AlignLeft)
        self.retranslate(language)

    def retranslate(self, language: str) -> None:
        self.language = language
        self.what.setText(tr("{k}_what".format(k=self.tool.key), language))
        self.hint.setText(tr("or_type", language).format(c=self.tool.command))
        self.open_button.setText(tr("open", language))


class ComingTile(QFrame):
    """The empty place, which is a promise rather than a gap."""

    def __init__(self, language: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumSize(300, 190)
        self.setEnabled(False)
        column = QVBoxLayout(self)
        self.name = QLabel()
        self.what = QLabel()
        self.what.setWordWrap(True)
        column.addWidget(self.name)
        column.addWidget(self.what, 1)
        self.retranslate(language)

    def retranslate(self, language: str) -> None:
        self.name.setText("<b>{t}</b>".format(t=tr("more", language)))
        self.name.setTextFormat(Qt.RichText)
        self.what.setText(tr("more_what", language))


class Launcher(QMainWindow):
    """What the suite is, and a way into each part of it."""

    def __init__(self, language: str = "en"):
        super().__init__()
        self.language = language
        self.windows: list = []
        self.tiles: list = []
        self._build()
        self._retranslate()
        self.resize(720, 520)
        self.setWindowIcon(self._icon())

    def _icon(self) -> QIcon:
        icon = QIcon()
        colour = self.palette().windowText().color()
        for size in (16, 24, 32, 64, 128, 256):
            icon.addPixmap(tinted("suite", size, colour))
        return icon

    def _build(self) -> None:
        central = QWidget()
        outer = QVBoxLayout(central)

        head = QHBoxLayout()
        self.mark = QLabel()
        self.mark.setPixmap(tinted("suite", 52, self.palette().windowText().color()))
        head.addWidget(self.mark)
        column = QVBoxLayout()
        self.title = QLabel("<b>{n}</b>".format(n=SUITE_NAME))
        self.title.setTextFormat(Qt.RichText)
        self.purpose = QLabel()
        self.purpose.setWordWrap(True)
        column.addWidget(self.title)
        column.addWidget(self.purpose)
        head.addLayout(column, 1)
        outer.addLayout(head)

        grid = QGridLayout()
        grid.setSpacing(14)
        for position, tool in enumerate(TOOLS):
            tile = Tile(tool, self.language)
            tile.open_button.clicked.connect(self._opener(tool))
            self.tiles.append(tile)
            grid.addWidget(tile, position // COLUMNS, position % COLUMNS)
        self.coming = ComingTile(self.language)
        grid.addWidget(self.coming, len(TOOLS) // COLUMNS, len(TOOLS) % COLUMNS)
        outer.addLayout(grid, 1)

        self.setCentralWidget(central)
        self.statusBar().showMessage(
            "{n} {r} - build {d}".format(n=SUITE_NAME, r=REVISION, d=__build_date__)
        )
        self.actions_menu = self.menuBar().addMenu("")
        self.language_action = QAction(self)
        self.language_action.triggered.connect(self.toggle_language)
        self.about_action = QAction(self)
        self.about_action.triggered.connect(self.show_about)
        self.actions_menu.addAction(self.language_action)
        self.actions_menu.addAction(self.about_action)

    def _opener(self, tool):
        """A bound callable per tool, so the tile knows what it opens.

        A lambda capturing the loop variable would give every tile the last
        tool -- the classic late-binding trap, and one nobody notices until
        there are three tiles.
        """

        def open_it() -> None:
            self.open_tool(tool.key)

        return open_it

    def open_tool(self, key: str) -> None:
        """Open a tool's window, keeping a reference so it is not collected."""
        try:
            if key == "foldercraft":
                from ..gui.app import MainWindow

                window = MainWindow(language=self.language)
            elif key == "metasearch":
                from ..metasearch.gui.app import MetaSearchWindow

                window = MetaSearchWindow(language=self.language)
            else:  # pragma: no cover - TOOLS is the only source of keys
                return
        except ImportError as exc:
            log.warning("Cannot open %s: %s", key, exc)
            QMessageBox.warning(self, SUITE_NAME, tr("needs_gui", self.language))
            return
        # Without this the window is garbage collected the moment this method
        # returns, and it vanishes as soon as it appears.
        self.windows.append(window)
        window.show()
        window.raise_()

    def _retranslate(self) -> None:
        language = self.language
        self.setWindowTitle(SUITE_NAME)
        self.purpose.setText(tr("purpose", language))
        for tile in self.tiles:
            tile.retranslate(language)
        self.coming.retranslate(language)
        self.actions_menu.setTitle(tr("menu_actions", language))
        self.language_action.setText(tr("language", language))
        self.about_action.setText(tr("about", language))

    def toggle_language(self) -> None:
        self.language = "de" if self.language == "en" else "en"
        self._retranslate()

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            SUITE_NAME,
            "{n} {r}\nbuild {d}\n\n{p}".format(
                n=SUITE_NAME, r=REVISION, d=__build_date__, p=tr("purpose", self.language)
            ),
        )


def run(argv: Optional[list] = None) -> int:
    setup_logging(tag="lrcs")
    arguments = list(argv if argv is not None else sys.argv)
    application = QApplication.instance() or QApplication(arguments)
    language = "de" if any(a in ("--lang=de", "de") for a in arguments) else "en"
    window = Launcher(language=language)
    window.show()
    if QGuiApplication.instance() is application:
        return application.exec()
    return 0  # pragma: no cover - already inside another event loop
