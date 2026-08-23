# LR-FolderCraft — Überblick

**Revision r15.0.2 · Build-Datum 2026-08-23**

LR-FolderCraft sortiert die Ordnerstruktur einer Adobe-Lightroom-Classic-
Bibliothek neu. Es verschiebt die Bilddateien auf dem Datenträger und schreibt
den Katalog im selben Vorgang um, sodass jede Referenz, die Lightroom hält,
erhalten bleibt.

## Warum ein eigenes Werkzeug nötig ist

Lightroom Classic bietet keinen programmierbaren Weg dafür:

- Das **Lua-SDK** kann Fotos und Metadaten lesen, hat aber keine Schnittstelle,
  um ein Foto von einem Ordner in einen anderen zu verschieben. Plug-ins können
  das schlicht nicht.
- **Finder bzw. Explorer** können die Dateien verschieben — danach zeigt
  Lightroom jede einzelne als fehlend an und man muss Ordner von Hand neu
  verknüpfen.
- **Ziehen im Ordner-Bedienfeld** funktioniert korrekt, ist aber Handarbeit.
  Bei 152 Zielordnern und knapp zehntausend Fotos ist das keine Option.

Bleibt nur, die Katalogdatenbank direkt zu ändern, während Lightroom
geschlossen ist. Genau das tut LR-FolderCraft — eng begrenzt, transaktional und
umkehrbar. Welche Zeilen genau angefasst werden, steht in
[08-funktionsweise.md](08-funktionsweise.md).

## Was erhalten bleibt

Die Identität eines Fotos im Katalog ist seine `AgLibraryFile.id_local`, und
dieser Wert ändert sich nie. Deshalb überlebt alles, was daran hängt:

| | |
| --- | --- |
| Entwicklungseinstellungen und Verlauf | bleibt erhalten |
| Virtuelle Kopien | bleiben erhalten, sie folgen ihrem Master |
| Schnappschüsse | bleiben erhalten |
| Sammlungen und intelligente Sammlungen | bleiben erhalten |
| Stichwörter, Bewertungen, Markierungen, Farbmarkierungen | bleiben erhalten |
| Stapel | bleiben erhalten |
| Vorschauen und Smart-Vorschauen | bleiben erhalten (adressiert über die Bild-UUID, nicht über den Pfad) |
| Gesichtsbereiche, Kartendaten | bleiben erhalten |
| XMP-Sidecar-Dateien | wandern mit dem Foto mit |
| Veröffentlichungsdienste | bleiben erhalten |

## Dokumente

Nach Gewichtung nummeriert: je kleiner die Zahl, desto eher wird sie gebraucht.

**Das Werkzeug benutzen**

- [02-installation.md](02-installation.md) — Installation unter macOS, Windows, Linux
- [03-vorbereitung.md](03-vorbereitung.md) — **zuerst lesen**: Ordner verknüpfen
  und Katalog konvertieren
- [04-bedienung.md](04-bedienung.md) — alle Befehle, alle Optionen, Beispiele
- [05-strukturen.md](05-strukturen.md) — Vorlagen und die vollständige Platzhalterliste
- [06-sicherheit.md](06-sicherheit.md) — Sicherung, Rückabwicklung, Wiederherstellung
- [07-faq.md](07-faq.md) — häufige Fragen

**Es verstehen**

- [08-funktionsweise.md](08-funktionsweise.md) — die Katalog-Interna
- [09-architektur.md](09-architektur.md) — der Aufbau des Codes

**Die Arbeit fortsetzen**

- [10-entwicklung.md](10-entwicklung.md) — wie das Projekt aufgenommen wird
- [11-versionierung.md](11-versionierung.md) — das Revisionsschema
- [12-historie.md](12-historie.md) — warum das Projekt so verlief, wie es verlief
- [13-offene-punkte.md](13-offene-punkte.md) — bekannte Grenzen und Fahrplan
- [14-prompts.md](14-prompts.md) — ursprünglicher und generischer Prompt

## Die drei Befehle, die man braucht

Zuvor zwei Voraussetzungen — siehe [03-vorbereitung.md](03-vorbereitung.md): jeder
Ordner in Lightroom verknüpft, und der Katalog einmal mit dem aktuellen
Lightroom Classic geöffnet.

```bash
lrfc info  KATALOG              # was steckt im Katalog? (nur lesen)
lrfc plan  KATALOG -s day       # was würde sich ändern? (nur lesen)
lrfc apply KATALOG -s day       # ausführen
```

Oder dasselbe in einem Fenster:

```bash
lrfc gui                        # grafische Oberfläche (braucht das Extra gui)
lrfc tui                        # Textoberfläche im Terminal
lrfc gui --lang de              # beide auch auf Deutsch
```

Alles Weitere ist eine Verfeinerung dieser drei.
