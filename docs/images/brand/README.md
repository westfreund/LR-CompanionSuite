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
| `avatar-512.png` | the repository avatar | das Repository-Bild |
| `social-1280x640.png` | link previews | Linkvorschau |

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

## The two composed files / Die beiden zusammengesetzten Dateien

`avatar-512.png` and `social-1280x640.png` are not cuts of the mark, they are
pictures *containing* it — the mark is transparent, and a host that drops it
onto whichever colour it uses this season is not showing a mark, it is taking a
gamble. Both bring their own ground. The avatar uses the small cut, because it
lives at forty pixels in a list of repositories.

`avatar-512.png` und `social-1280x640.png` sind keine Schnitte der Marke,
sondern Bilder, die sie *enthalten* — die Marke ist transparent, und ein
Anbieter, der sie auf die gerade übliche Farbe legt, zeigt keine Marke, sondern
geht ein Wagnis ein. Beide bringen ihren eigenen Grund mit. Das Repository-Bild
nutzt den kleinen Schnitt, weil es in einer Liste von Repositorys bei vierzig
Pixeln steht.

GitLab takes the avatar through its API. GitHub has no such thing for a
repository — what it shows is the owner's avatar, and the per-repository
picture is the social preview under **Settings → General → Social preview**,
which only the web interface can set.

GitLab nimmt das Bild über seine Schnittstelle entgegen. GitHub kennt so etwas
für ein Repository nicht — gezeigt wird das Bild des Kontos, und das Bild je
Repository ist die Linkvorschau unter **Settings → General → Social preview**,
die sich nur über die Weboberfläche setzen lässt.

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
