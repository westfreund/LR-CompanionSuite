# Bedienung

**Revision r1.0.2 · Build-Datum 2026-08-22**

> **Lightroom Classic vor `apply` schließen.** Das Werkzeug verweigert den
> Start, wenn es Lightrooms Sperrdatei findet — ein Katalog, den Lightroom
> *während* eines laufenden Vorgangs öffnet, kann aber dennoch Schaden nehmen.

## Der Ablauf

```
   info  ──►  plan  ──►  prüfen  ──►  apply  ──►  in Lightroom öffnen
   nur        nur        Sie          schreibt    Ergebnis kontrollieren
   lesen      lesen
```

`plan` nie überspringen. Es kostet Sekunden und zeigt die exakte Liste aller
Verschiebungen.

---

## `lrfc info KATALOG`

Liest den Katalog und gibt eine Übersicht aus: Schemaversion, Anzahl Ordner und
Dateien, virtuelle Kopien, Aufnahmezeitraum, Kameras und Dateiformate.
Schreibt nichts.

```console
$ lrfc info /Volumes/Fotos/2019/2019.lrcat --lang de
  Katalog                          : /Volumes/Fotos/2019/2019.lrcat
  Schemaversion                    : 18.0.0
  Stammordner                      : 1
  Ordner                           : 1
  Dateien                          : 9.452
  Bilder (inkl. virtueller Kopien) : 9.484
  Virtuelle Kopien                 : 32
  Ohne Aufnahmedatum               : 0
  Aufnahmezeitraum                 : 2019-01-03T17:42:29.18 .. 2019-12-29T13:39:50.98
```

## `lrfc folders KATALOG [--counts]`

Gibt den Ordnerbaum mit den Katalog-Ordner-IDs aus. Diese IDs braucht man für
`--folder` und `--anchor-folder`.

## `lrfc plan KATALOG -s STRUKTUR`

Erstellt den vollständigen Plan und gibt ihn samt Vorprüfungen aus.
**Schreibt nichts.**

```console
$ lrfc plan /Volumes/Fotos/2019/2019.lrcat -s day --lang de
  Struktur    : {yyyy}-{mm}-{dd}
  Beispiel    : 2019-01-03
  Platzierung : in-place
  Zielwurzel  : /Volumes/Fotos/2019/raw2019
  Ankerordner : (root)

Zusammenfassung:
  Zu verschieben                : 9.452
  Bereits am Ziel               : 0
  Uebersprungen                 : 0
  Neue Ordner                   : 152
  Mitgefuehrte virtuelle Kopien : 32
  Datenvolumen                  : 337.1 GiB
```

Ausgabeformate:

| Schalter | Ergebnis |
| --- | --- |
| *(keiner)* | lesbarer Bericht samt Vorprüfungen |
| `--json` | der vollständige Plan, jede Verschiebung, maschinenlesbar |
| `--csv` | eine Zeile je Datei — für die Tabellenkalkulation |
| `--out VERZ` | schreibt zusätzlich `plan-<zeitstempel>.json` und `.csv` |
| `--all` | Zielordnerliste nicht kürzen |

Einen großen Plan in der Tabellenkalkulation durchzusehen lohnt die Minute:

```bash
lrfc plan KATALOG -s day --csv > plan.csv
```

## `lrfc apply KATALOG -s STRUKTUR`

Führt aus. Gibt den Plan aus, läuft durch die Vorprüfungen, fragt nach und
arbeitet dann.

```bash
lrfc apply /Volumes/Fotos/2019/2019.lrcat -s day        # fragt nach
lrfc apply /Volumes/Fotos/2019/2019.lrcat -s day --yes  # ohne Rückfrage
```

| Schalter | Wirkung |
| --- | --- |
| `-y`, `--yes` | Sicherheitsabfrage überspringen |
| `--no-backup` | Katalog nicht sichern — **dringend abgeraten** |
| `--no-verify` | abschließende Prüfung überspringen |
| `--keep-empty-folders` | leer gewordene Ordnereinträge behalten |
| `--out VERZ` | Plandateien nach `VERZ` schreiben |

Rückgabewerte: `0` Erfolg · `1` Fehler · `2` Aufrufsfehler · `3` Vorprüfung
fehlgeschlagen · `4` fertig, aber Prüfung fand Probleme · `5` abgebrochen.

## `lrfc undo JOURNAL`

Macht einen abgeschlossenen Lauf rückgängig: Die Dateien wandern zurück, und
der Katalog wird aus dem Backup dieses Laufs wiederhergestellt.

```bash
lrfc undo ~/Library/Application\ Support/LR-FolderCraft/backups/2019-20260822-162631.lrfc-journal.jsonl
```

Der Journalpfad wird am Ende jedes Laufs ausgegeben und im Log vermerkt.

## `lrfc tui`

Die interaktive Oberfläche: Katalog wählen, Struktur festlegen und die
Live-Vorschau beobachten, planen, die Zielordner in einer Tabelle prüfen und
hinter einem Bestätigungsdialog ausführen.

| Taste | Aktion |
| --- | --- |
| `Strg+L` | Katalog laden |
| `Strg+P` | planen |
| `Strg+R` | ausführen |
| `F1` | zwischen Englisch und Deutsch wechseln |
| `Strg+Q` | beenden |

## `lrfc presets` / `lrfc tokens` / `lrfc profiles`

Hilfsausgaben. `presets` listet die fertigen Strukturen mit Beispielpfad,
`tokens` alle Platzhalter, `profiles` die gespeicherten Einstellungen. Alle
verstehen `--lang de`.

---

## Auswahl der zu bearbeitenden Dateien

Standardmäßig wird jede Datei im Katalog betrachtet.

```bash
lrfc plan KATALOG -s day --root-folder 4908476   # ein Stammordner
lrfc plan KATALOG -s day --folder 1971944        # ein Katalogordner
lrfc plan KATALOG -s day --folder 12 --folder 13 # mehrere, wiederholbar
lrfc plan KATALOG -s day --include-ext cr2 --include-ext dng
lrfc plan KATALOG -s day --exclude-ext jpg
```

## Platzierung: wo die neuen Ordner entstehen

**`in-place`** (Standard) baut die Struktur unterhalb des Ordners auf, in dem
die Auswahl derzeit liegt:

```
raw2019/                 raw2019/
  IMG_0001.CR2     ──►     2019-01-03/
  IMG_0002.CR2               IMG_0001.CR2
  ...                        IMG_0002.CR2
                           2019-01-06/
```

Der Anker ist der tiefste Ordner, der allen ausgewählten Fotos gemeinsam ist.
Liegen die Fotos bereits in Tagesordnern, erkennt das Werkzeug, dass der Anker
selbst eine gerenderte Ebene ist, und tritt einen Schritt zurück — ein zweiter
Lauf ändert dann nichts.

Mit `--anchor-folder ID` lässt sich der Anker vorgeben (siehe `lrfc folders`).

**`new-tree`** baut einen frischen Baum an anderer Stelle und registriert ihn
als zusätzlichen Stammordner im Katalog:

```bash
lrfc plan KATALOG -s year/month/day --target-root /Volumes/Fotos/sortiert
```

`--target-root` schaltet automatisch auf `new-tree`. Liegt das Ziel auf einem
anderen Volume, werden die Dateien kopiert, per Prüfsumme verifiziert und erst
dann an der Quelle entfernt — deutlich langsamer, und die Vorprüfung besteht
auf ausreichend freiem Speicher.

## Sonderfälle

### Fotos ohne Aufnahmedatum

| `--on-missing-date` | Verhalten |
| --- | --- |
| `unsorted` (Standard) | in einen Ordner `_unsorted`; umbenennbar mit `--unsorted-folder` |
| `skip` | bleiben liegen, werden gezählt und gemeldet |
| `abort` | Planung wird verweigert |

Welcher Zeitstempel zählt, steuert `--date-source`, wiederholbar und in der
angegebenen Reihenfolge. Standard ist `capture`, dann `exif-fields`:

- `capture` — Lightrooms eigene Aufnahmezeit, also der Wert, den man im
  Metadaten-Bedienfeld sieht und korrigieren kann. Eine Korrektur gewinnt, und
  genau das ist gewollt.
- `exif-fields` — die abgeleiteten Spalten `dateYear/dateMonth/dateDay`.
- `file-mtime` — das Änderungsdatum der Datei. **Kein Standard**: es ist meist
  das Kopierdatum, nicht das Aufnahmedatum, und würde Fotos stillschweigend
  unter dem falschen Tag ablegen. Nur bewusst zuschalten:

```bash
lrfc plan KATALOG -s day --date-source capture --date-source file-mtime
```

### Namenskonflikte

Zwei gleichnamige Dateien können nur zusammentreffen, wenn mehrere
Quellordner in einen Zielordner zusammengeführt werden.

| `--conflict` | Verhalten |
| --- | --- |
| `rename` (Standard) | die zweite Datei wird `NAME_1.ext`; der Katalog wird nachgeführt, sodass Lightroom folgt |
| `skip` | bleibt liegen und wird gemeldet |
| `abort` | Planung wird verweigert |

Eine vorhandene Datei am Ziel wird in **keinem** Modus überschrieben.

### Sidecar-Dateien

`IMG_1234.xmp` und `IMG_1234.CR2.xmp` werden beide erkannt und mit dem Foto
verschoben. Wird das Foto umbenannt, wird die Sidecar-Datei mit umbenannt.
Abschaltbar mit `--no-sidecars`.

**macOS-AppleDouble-Begleitdateien** (`._IMG_1234.CR2`) sind ein eigener Fall.
Auf exFAT und FAT — den üblichen Dateisystemen externer Fotoplatten — legt
macOS die erweiterten Attribute und den Resource-Fork einer Datei in einer
solchen Begleitdatei ab. Sie ist die andere Hälfte der Datei, kein Dokument
daneben, und wandert deshalb immer mit dem Foto mit, auch bei `--no-sidecars`.
Sie zurückzulassen würde der verschobenen Datei ihre Attribute nehmen und einen
4-KiB-Rest als Waise hinterlassen.

### Ordnernamen ohne ASCII

`--ascii` reduziert Ordnernamen auf reines ASCII (`Grün` → `Grun`). Nützlich,
wenn die Bibliothek mit einem System geteilt wird, das mit Unicode Mühe hat.
Unzulässige Zeichen (`< > : " / \ | ? *`), abschließende Punkte und
Windows-Gerätenamen (`CON`, `LPT1`, …) werden ohnehin immer behandelt, auf
jeder Plattform.

## Profile

Eine Konfiguration einmal speichern und wiederverwenden:

```bash
lrfc plan KATALOG -s '{camera_slug}/{yyyy}-{mm}-{dd}' --save-profile nach-kamera
lrfc apply ANDERER_KATALOG --profile nach-kamera
lrfc profiles
```

Ein Profil speichert, *wie* sortiert wird, niemals `dry_run` — das Laden eines
Profils kann also nie versehentlich einen scharfen Lauf starten. `--config
DATEI.json` lädt Einstellungen aus einer bestimmten Datei.

## Protokollierung und Fehlersuche

Jeder Lauf schreibt eine Logdatei mit nummerierter `STEP`-Spur:

```
2026-08-22 16:26:31,412 | INFO | lrfoldercraft | STEP 004 | Anchor resolved: ...
2026-08-22 16:26:31,502 | INFO | lrfoldercraft | STEP 007 | Moved 40 file(s) and 1 sidecar(s)
```

| Schalter | Wirkung |
| --- | --- |
| `--debug` | DEBUG-Stufe mit Datei, Zeile und Funktion; jede SQL-Anweisung |
| `--verbose` | Fortschritt auch auf der Konsole |
| `--quiet` | Konsole zeigt nur Fehler |
| `--log-file PFAD` | Log an eine bestimmte Stelle schreiben |
| `--log-dir VERZ` | Verzeichnis für die automatisch benannte Logdatei |

Die Logdatei hält immer Revision, Build-Datum, Python-Version, Plattform und
die vollständige Befehlszeile fest, sodass sich ein Log später eindeutig einer
Werkzeugrevision zuordnen lässt.

Bei einer Fehlermeldung bitte das Log **und** den Plan als JSON beilegen.
