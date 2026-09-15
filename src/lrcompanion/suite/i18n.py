"""The launcher's strings, in both languages.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

TEXT = {
    "title": ("LR-CompanionSuite", "LR-CompanionSuite"),
    "purpose": (
        "Tools that sit beside Adobe Lightroom Classic rather than replacing it.",
        "Werkzeuge, die neben Adobe Lightroom Classic stehen, statt es zu ersetzen.",
    ),
    "foldercraft_what": (
        "Reorganise the folder tree — files and catalog together, so nothing is "
        "lost and every run can be taken back.",
        "Den Ordnerbaum umsortieren — Dateien und Katalog in einem Zug, sodass "
        "nichts verloren geht und jeder Lauf zurücknehmbar ist.",
    ),
    "metasearch_what": (
        "Search across every library you own, find what is held twice, and build "
        "catalogs out of a selection. Reads only.",
        "Über alle Bibliotheken suchen, Doppeltes finden und aus einer Auswahl "
        "Kataloge bauen. Liest nur.",
    ),
    "open": ("Open", "Öffnen"),
    "or_type": ("or type: {c}", "oder tippen: {c}"),
    "more": ("More to come", "Weitere folgen"),
    "more_what": (
        "A tile appears here for every tool the suite grows.",
        "Für jedes weitere Werkzeug der Suite erscheint hier eine Kachel.",
    ),
    "language": ("Deutsch / English", "Deutsch / English"),
    "menu_actions": ("Actions", "Aktionen"),
    "about": ("About", "Über"),
    "needs_gui": (
        "This tool needs the graphical extra: pip install 'lr-companion-suite[gui]'",
        "Dieses Werkzeug braucht das grafische Extra: pip install 'lr-companion-suite[gui]'",
    ),
}


def tr(key: str, language: str = "en") -> str:
    english, german = TEXT[key]
    return german if language == "de" else english
