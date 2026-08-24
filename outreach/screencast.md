# Bildschirmvideo — Drehbuch

Bei einem Werkzeug, das in eine Katalogdatenbank schreibt, überzeugt Zusehen
mehr als jeder Text. Sechzig Sekunden reichen, wenn sie das Richtige zeigen.

**Die eine Botschaft:** *Es zeigt erst, was es tun würde. Dann tut es das. Und
man kann es zurücknehmen.* Alles andere ist Beiwerk.

---

## Vorbereitung

Nicht auf echten Fotos aufnehmen. Dafür gibt es eine Wegwerf-Bibliothek:

```bash
python scripts/make_demo_catalog.py ~/Desktop/lrfc-demo
```

Zwölf Fotos in zwei Jahresordnern, dazu ein thematischer Ordner
(`Portfolio/`), ein Sessionordner mit Zusatztext (`2019-03-10 Fasching/`) und
ein Foto darin, dessen Datum nicht zum Ordnernamen passt — damit die
Ausnahmen-Tabelle nicht leer ist. Hinterher den Ordner löschen.

**Aufnahme:** unter macOS ⇧⌘5 für das Fenster, oder *Kap* für ein direktes
GIF. Fürs Terminal ist *asciinema* am saubersten, weil der Text scharf bleibt
und die Datei klein.

**Einstellungen vor der Aufnahme:**

- Terminal auf mindestens 100 Spalten, Schriftgrad hochdrehen — die meisten
  sehen das auf dem Telefon.
- Hellen Hintergrund wählen. Dunkle Terminals sehen in eingebetteten Videos
  matschig aus.
- Menüleiste und Schreibtisch aufräumen; nichts Privates im Bild.
- Kein Ton. Untertitel im Schnitt sind besser: sie funktionieren stumm, und
  die meisten sehen stumm.

---

## Die sechzig Sekunden

| Zeit | Bild | Einblendung |
| --- | --- | --- |
| 0:00–0:06 | Finder: fünf riesige Jahresordner, einer aufgeklappt mit tausenden Dateien | „51.000 Fotos. Fünf Ordner." |
| 0:06–0:12 | Lightroom daneben, Ordner-Bedienfeld | „Im Finder verschieben zerreißt den Katalog." |
| 0:12–0:22 | Terminal, `lrfc plan …` tippen und laufen lassen; auf die Zusammenfassung halten | „Erst nur ansehen. Es schreibt nichts." |
| 0:22–0:30 | Auf die Zeile „Needs your answer" / Ausnahmen zoomen | „Es sagt, was es nicht selbst entscheiden will." |
| 0:30–0:40 | `lrfc apply …`, Fortschritt läuft durch | „Dateien und Katalog in einem Zug." |
| 0:40–0:48 | Finder: die neue Tagesstruktur; Lightroom öffnen, Fotos sind da, keine Fragezeichen | „Lightroom merkt nichts." |
| 0:48–0:56 | `lrfc undo …` | „Und zurück, exakt." |
| 0:56–1:00 | Standbild mit Adresse | „andy-freund.gitlab.io/LR-FolderCraft — frei und quelloffen" |

Die Sekunden 40 bis 48 sind der Kern. Wenn nur ein Ausschnitt irgendwo
weiterverbreitet wird, dann dieser.

## Zwei Fassungen

Denselben Schnitt einmal mit deutschen und einmal mit englischen
Einblendungen. Der Aufwand ist gering, die Reichweite verdoppelt sich.

## Wohin damit

- **README und Startseite:** ein GIF ganz oben, unter 5 MB. Was größer ist,
  lädt bei niemandem.
- **Foren:** die meisten mögen keine Einbettung. Ein Standbild plus Link.
- **YouTube:** nicht wegen der Zuschauer, sondern weil sich von dort
  überallhin verlinken lässt. Titel in den Worten, die gesucht werden:
  „Lightroom Ordnerstruktur ändern ohne Verknüpfung zu verlieren".

## Was nicht ins Video gehört

- Die Installation. Wer sie sehen will, liest sie.
- Die Regelsprache und die Profile. Beeindruckend, aber nicht im ersten Kontakt.
- Jede Zahl, die nicht belegt ist.
