# LR-FolderCraft — Überblick

**Revision r2.0.0 · Build-Datum 2026-08-22**

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
[funktionsweise.md](funktionsweise.md).

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

- [installation.md](installation.md) — Installation unter macOS, Windows, Linux
- [bedienung.md](bedienung.md) — alle Befehle, alle Optionen, Beispiele
- [strukturen.md](strukturen.md) — Vorlagen und die vollständige Platzhalterliste
- [funktionsweise.md](funktionsweise.md) — die Katalog-Interna
- [sicherheit.md](sicherheit.md) — Backups, Rollback, Undo, Wiederherstellung
- [architektur.md](architektur.md) — der Aufbau des Codes
- [entwicklung.md](entwicklung.md) — wie die Arbeit fortgesetzt wird
- [versionierung.md](versionierung.md) — das Revisionsschema
- [faq.md](faq.md) — häufige Fragen
- [offene-punkte.md](offene-punkte.md) — bekannte Grenzen und Fahrplan
- [prompts.md](prompts.md) — ursprünglicher und generischer Prompt

## Die drei Befehle, die man braucht

```bash
lrfc info  KATALOG              # was steckt im Katalog? (nur lesen)
lrfc plan  KATALOG -s day       # was würde sich ändern? (nur lesen)
lrfc apply KATALOG -s day       # ausführen
```

Alles Weitere ist eine Verfeinerung dieser drei.
