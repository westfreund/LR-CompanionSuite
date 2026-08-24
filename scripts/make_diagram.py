"""Draw the before-and-after diagram used on the website and in the READMEs.

A reader decides in about two seconds whether a tool is for them, and no
paragraph wins that race against a picture of their own folder tree. Generated
rather than drawn so the two languages cannot drift apart and so a change to
the wording is a change to one file.

    python scripts/make_diagram.py

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "docs" / "images"

TEXT = {
    "en": {
        "before": "Before — five folders, everything in them",
        "after": "After — one folder per day",
        "command": "lrfc apply Photos.lrcat --structure day",
        "files": "files",
        "footer": "51,049 photos · every catalog link intact · every run reversible",
        "root": "Photos/",
    },
    "de": {
        "before": "Vorher — fünf Ordner, alles darin",
        "after": "Nachher — ein Ordner je Tag",
        "command": "lrfc apply Fotos.lrcat --structure day",
        "files": "Dateien",
        "footer": "51.049 Fotos · jede Katalogverknüpfung erhalten · jeder Lauf rücknehmbar",
        "root": "Fotos/",
    },
}

#: Thousands separators differ, so the counts are per language too.
COUNTS = {
    "en": ["12,481", "10,905", "9,630", "8,744", "9,289"],
    "de": ["12.481", "10.905", "9.630", "8.744", "9.289"],
}

YEARS = ["2019", "2020", "2021", "2022", "2023"]

#: Drawn out rather than computed. A tree is three lines of arithmetic and an
#: hour of getting the elbows wrong; this way the picture is the source.
AFTER = [
    ("└── 2019/", ""),
    ("    ├── 2019-01/", ""),
    ("    │   ├── 2019-01-03/", "128"),
    ("    │   └── 2019-01-19/", "94"),
    ("    └── 2019-02/", ""),
    ("        ├── 2019-02-11/", "211"),
    ("        └── 2019-02-24/", "176"),
]

#: Two fixed palettes rather than CSS variables. A variable is resolved by the
#: browser, and an SVG travels through renderers that have none -- it came back
#: as a black rectangle the first time. The READMEs pick between the two with
#: <picture>, exactly as they already do for the logo.
PALETTES = {
    "light": {
        "ink": "#1b1f24",
        "dim": "#57606a",
        "line": "#d0d7de",
        "card": "#ffffff",
        "page": "#f6f8fa",
        "accent": "#1f6feb",
        "good": "#1a7f37",
    },
    "dark": {
        "ink": "#e6edf3",
        "dim": "#9198a1",
        "line": "#30363d",
        "card": "#161b22",
        "page": "#0d1117",
        "accent": "#58a6ff",
        "good": "#3fb950",
    },
}

MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "system-ui, -apple-system, Segoe UI, Helvetica, Arial, sans-serif"

WIDTH, HEIGHT = 940, 400
COL = 430
LEFT_X, RIGHT_X = 20, WIDTH - COL - 20


def rows_before(language: str):
    """The tree as it was: a root and five year folders."""
    text = TEXT[language]
    yield 0, text["root"], ""
    last = len(YEARS) - 1
    for index, (year, count) in enumerate(zip(YEARS, COUNTS[language])):
        stem = "└── " if index == last else "├── "
        yield 1, stem + year + "/", "{c} {f}".format(c=count, f=text["files"])


def rows_after(language: str):
    """The tree as it became: year, year-month, year-month-day."""
    text = TEXT[language]
    yield 0, text["root"], ""
    for label, count in AFTER:
        yield 1, label, "{c} {f}".format(c=count, f=text["files"]) if count else ""


def panel(x: int, title: str, rows, colour) -> str:
    """One card with a heading and a folder tree in it."""
    out = [
        '<rect x="{x}" y="56" width="{w}" height="250" rx="8" fill="{c}" stroke="{s}"/>'.format(
            x=x, w=COL, c=colour["card"], s=colour["line"]
        ),
        '<text x="{x}" y="42" font-family="{f}" font-size="15" font-weight="600" '
        'fill="{c}">{t}</text>'.format(x=x + 4, f=SANS, c=colour["ink"], t=title),
    ]
    for index, (_depth, label, note) in enumerate(rows):
        y = 86 + index * 26
        out.append(
            '<text x="{x}" y="{y}" font-family="{f}" font-size="14" fill="{c}" '
            'xml:space="preserve">{l}</text>'.format(
                x=x + 18, y=y, f=MONO, c=colour["ink"], l=label
            )
        )
        if note:
            out.append(
                '<text x="{x}" y="{y}" font-family="{f}" font-size="14" fill="{c}" '
                'text-anchor="end">{n}</text>'.format(
                    x=x + COL - 18, y=y, f=MONO, c=colour["dim"], n=note
                )
            )
    return "\n  ".join(out)


def diagram(language: str, scheme: str) -> str:
    text = TEXT[language]
    colour = PALETTES[scheme]
    middle = LEFT_X + COL
    body = [
        '<rect x="0" y="0" width="{w}" height="{h}" rx="10" fill="{c}"/>'.format(
            w=WIDTH, h=HEIGHT, c=colour["page"]
        ),
        panel(LEFT_X, text["before"], rows_before(language), colour),
        panel(RIGHT_X, text["after"], rows_after(language), colour),
        '<path d="M {a} 180 L {b} 180" stroke="{c}" stroke-width="2" fill="none"/>'.format(
            a=middle + 6, b=RIGHT_X - 6, c=colour["accent"]
        ),
        '<path d="M {b} 180 l -9 -6 m 9 6 l -9 6" stroke="{c}" stroke-width="2" '
        'fill="none"/>'.format(b=RIGHT_X - 6, c=colour["accent"]),
        '<text x="{x}" y="340" text-anchor="middle" font-family="{f}" font-size="13" '
        'fill="{c}">{t}</text>'.format(x=WIDTH // 2, f=MONO, c=colour["accent"], t=text["command"]),
        '<text x="{x}" y="372" text-anchor="middle" font-family="{f}" font-size="14" '
        'fill="{c}">{t}</text>'.format(x=WIDTH // 2, f=SANS, c=colour["good"], t=text["footer"]),
    ]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        'width="{w}" height="{h}" role="img" aria-label="{a}">\n  {b}\n</svg>\n'
    ).format(w=WIDTH, h=HEIGHT, a=text["before"] + " / " + text["after"], b="\n  ".join(body))


def main() -> int:
    for language in TEXT:
        for scheme in PALETTES:
            target = IMAGES / "before-after-{l}-{s}.svg".format(l=language, s=scheme)
            target.write_text(diagram(language, scheme), encoding="utf-8")
            print("wrote {t}".format(t=target.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
