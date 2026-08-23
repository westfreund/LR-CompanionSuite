# The mark / Die Marke

One mark, two cuts. Both are single-colour SVG using `currentColor`, so they
take the surrounding text colour rather than shipping a light and a dark copy.

Eine Marke, zwei Schnitte. Beide sind einfarbige SVG mit `currentColor`, nehmen
also die umgebende Textfarbe an, statt je eine helle und eine dunkle Fassung
mitzuführen.

| File | Use | Verwendung |
| --- | --- | --- |
| `logo.svg` | 32 px and above | ab 32 px |
| `logo-small.svg` | 24 px and below | bis 24 px |

The small cut exists because the full mark has four elements and none of them
survive sixteen pixels. That is not a compromise — every mark that works as a
favicon has a cut drawn for that size.

Der kleine Schnitt existiert, weil die volle Marke vier Elemente hat und keines
davon sechzehn Pixel überlebt. Das ist kein Notbehelf: Jede Marke, die als
Favicon funktioniert, hat einen eigens dafür gezeichneten Schnitt.

The letters are drawn as strokes, not set as type — a logo that depends on a
font installed on the viewer's machine is not a logo.

Die Buchstaben sind als Striche gezeichnet, nicht gesetzt — ein Logo, das von
einer installierten Schrift abhängt, ist keines.

## Regenerating the PNGs / PNG neu erzeugen

```bash
python scripts/make_brand.py
```

Renders 16, 24, 32, 64, 128, 256 and 512 px in a dark and a light ink from the
two SVG sources. Never edit a PNG: change the SVG and run the script.

Erzeugt 16, 24, 32, 64, 128, 256 und 512 px in dunkler und heller Tinte aus den
beiden SVG-Quellen. Niemals ein PNG bearbeiten: das SVG ändern und das Skript
laufen lassen.

## A warning worth repeating / Eine Warnung, die es wert ist

A double hyphen is illegal inside an XML comment. It raises nothing the
renderer reports — the file simply draws an empty image. `tests/test_brand.py`
parses both files so this cannot ship again.

Ein doppelter Bindestrich ist innerhalb eines XML-Kommentars unzulässig. Der
Renderer meldet nichts — die Datei zeichnet einfach ein leeres Bild.
`tests/test_brand.py` parst beide Dateien, damit das nicht erneut ausgeliefert
wird.

## The proposals / Die Entwürfe

The six that were put up for choice, and the three variants of the chosen one,
are kept in [`../logos/`](../logos/) for the record.

Die sechs zur Wahl gestellten Entwürfe und die drei Varianten des gewählten
liegen zur Dokumentation in [`../logos/`](../logos/).
