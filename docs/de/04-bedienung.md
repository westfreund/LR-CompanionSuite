# Bedienung

**Revision r7.1.0 · Build-Datum 2026-08-23**

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
als zusätzlichen Stammordner im Katalog. Das Ziel muss noch nicht existieren --
es wird samt aller fehlenden Ebenen darüber angelegt und von einem Rollback oder
`lrfc undo` wieder entfernt:

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

**macOS-AppleDouble-Begleitdateien** (`._IMG_1234.CR2`) erfordern kein Zutun.
Auf exFAT und FAT — den üblichen Dateisystemen externer Fotoplatten — legt
macOS die erweiterten Attribute und den Resource-Fork einer Datei in einer
solchen Begleitdatei ab, und der Kernel verschiebt sie zusammen mit der Datei.
LR-FolderCraft überlässt das bewusst macOS; sie ein zweites Mal zu verschieben
würde mit dem kollidieren, was das System bereits getan hat.

Unter Linux und Windows gibt es diese Emulation nicht, dort bliebe eine früher
von einem Mac geschriebene `._X` beim Umbenennen zurück. Dort nimmt das
Werkzeug sie ausdrücklich mit, auch bei `--no-sidecars`, damit der Datenträger
seine Metadaten für den nächsten Einsatz am Mac behält.

### Ordnernamen ohne ASCII

`--ascii` reduziert Ordnernamen auf reines ASCII (`Grün` → `Grun`). Nützlich,
wenn die Bibliothek mit einem System geteilt wird, das mit Unicode Mühe hat.
Unzulässige Zeichen (`< > : " / \ | ? *`), abschließende Punkte und
Windows-Gerätenamen (`CON`, `LPT1`, …) werden ohnehin immer behandelt, auf
jeder Plattform.

## Die grafische Oberfläche

```bash
lrfc gui                                        # englisch
lrfc gui --lang de                              # deutsch
lrfc gui --lang de /Volumes/Fotos/2019/2019.lrcat   # deutsch, Katalog gleich mit
```

Ohne Neustart lässt sich die Sprache auch im Fenster umschalten: der
Menüeintrag oben zeigt immer die **andere** Sprache an, in der deutschen
Oberfläche also „English".

### Was sich das Fenster merkt

Im Fenster getroffene Einstellungen bleiben erhalten, der nächste Start setzt
also dort an, wo Sie aufgehört haben: Sprache, Katalog, Zielordner samt Modus,
Struktur, Endungsfilter, Ordneraktionen, Regelliste, Fenstergröße und
Teilerpositionen. Sie liegen in `gui-state.json` im Konfigurationsverzeichnis;
diese Datei zu löschen stellt die Vorgaben wieder her.

Zwei Dinge werden bewusst **nicht** gemerkt:

| | Warum nicht |
| --- | --- |
| Entscheidungen zu einzelnen Ordnern | Es sind Katalog-Ordner-IDs. Sie gegen einen anderen Katalog wiederherzustellen hieße, eine zu einem Ordner gegebene Antwort auf irgendeinen fremden Ordner anzuwenden, der zufällig dieselbe Nummer trägt. |
| Der Schalter „Sicherung anlegen" | Er steht immer wieder auf ein. Das Sicherheitsnetz abzuschalten sollte für den anstehenden Lauf entschieden werden, nicht von einem Lauf vor drei Wochen geerbt. |

Sie benötigt das Extra `gui`: `pip install 'lr-foldercraft[gui]'`. Fehlt es,
erklärt der Befehl die Installation, statt mit einem Traceback abzubrechen.

Ein Fenster, von oben nach unten:

| Bereich | Inhalt |
| --- | --- |
| **Katalog** | der `.lrcat`-Pfad mit Durchsuchen-Schaltfläche und, nach dem Laden, eine Zeile mit Dateien, Bildern, virtuellen Kopien und Aufnahmezeitraum |
| **Quelle** | der zu bearbeitende Stammordner (oder alle) sowie Endungsfilter |
| **Ziel** | unterhalb des aktuellen Ordners, oder in einen neuen Ordner über den Systemdialog — dessen Schaltfläche *Neuer Ordner* legt einen an, und ein noch nicht vorhandener Pfad wird beim Lauf erzeugt |
| **Ordnerstruktur** | eine Vorlage oder ein eigenes Template, mit Live-Vorschau beim Tippen und einer Schaltfläche, die alle 25 Platzhalter auflistet |
| **Optionen** | Namenskonflikte, Fotos ohne Datum und die drei Entscheidungen zu vorhandenen Ordnern, dazu Sidecars, Katalog-Backup und ASCII-Namen |
| **Braucht Ihre Antwort** | je Ursache eine Zeile mit Dateizahl, steuernder Option und deren aktuellem Wert — eine Zeile auswählen zeigt die betroffenen Dateien |
| **Vorgefundene Ordner** | die Regelliste und darunter eine Zeile je Ordner mit Art, Fotozahl, entscheidender Regel und Auswahlfeld — eine Änderung plant sofort neu |
| **Schaltflächen** | Planen ändert nichts; Ausführen fragt vorher nach |
| **Fortschritt** | Balken und Zähler während des Laufs, danach das vollständige Ergebnis |
| **Protokoll** | was geschehen ist, samt aller Warnungen aus den Vorprüfungen |

Über die Menüleiste lässt sich jederzeit zwischen Deutsch und Englisch
wechseln.

### Die Bereiche lassen sich aufziehen — Wichtig

Zwischen den vier großen Bereichen — **Einstellungen**, **Braucht Ihre
Antwort**, **Vorgefundene Ordner** und **Protokoll** — liegt jeweils ein
**Teiler**. Er ist leicht zu übersehen: eine dünne waagerechte Linie am
**unteren Rand eines Bereichs**, früher nur ein paar graue Punkte.

```
┌─ Einstellungen ─────────────────────────┐
│  Katalog, Quelle, Ziel, Struktur …      │   ← scrollt in sich
└─────────────────────────────────────────┘
 ────────────────────────────────────────      ← Teiler: hier ziehen
┌─ Braucht Ihre Antwort ──────────────────┐
```

Der Mauszeiger wird über einem Teiler zum Doppelpfeil, und ein Tooltip sagt,
was er tut. Damit:

- **Ziehen** gibt dem Bereich darüber mehr oder weniger Platz.
- **Ganz zuziehen** blendet einen Bereich aus. Er ist nicht weg — der Teiler
  bleibt liegen, und Aufziehen holt ihn zurück. Wer das Protokoll nicht
  braucht, gewinnt so Platz für die Ordnertabelle.
- Die eingestellten Größen werden **gemerkt** und beim nächsten Start
  wiederhergestellt.

Der Bereich **Einstellungen** hat zusätzlich eine **eigene Bildlaufleiste**:
Auf einem kleinen Bildschirm sind Ziel, Ordnerstruktur und Optionen zunächst
unterhalb des sichtbaren Randes und werden durch Scrollen *innerhalb* des
Bereichs erreicht — oder eben dadurch, dass man den Teiler darunter nach unten
zieht.

Wenn also eine Tabelle abgeschnitten wirkt oder eine Einstellung zu fehlen
scheint: Der Bereich ist zu klein, nicht leer.

Das Fenster passt auf kleine Bildschirme: Es öffnet nie größer als der
verfügbare Platz, die Einstellungen scrollen, wenn sie nicht hineinpassen, und
Schaltflächen sowie Fortschrittsbalken bleiben außerhalb des Scrollbereichs
stehen. Einstellungen, Ordnertabelle und Protokoll teilen sich einen Teiler,
Sie können den Platz also dem Teil geben, mit dem Sie gerade arbeiten.

Die Vorgabewerte der Optionen stammen aus demselben `Settings`-Objekt, das auch
die Kommandozeile verwendet — die Oberfläche kann der Dokumentation also nicht
stillschweigend widersprechen. Ein Test prüft genau das.

Lang laufende Vorgänge arbeiten in eigenen Threads, das Fenster bleibt also
bedienbar, während neuntausend Dateien verschoben werden, und das Schließen
wartet die Arbeit ab, statt sie abzuwürgen.

## Ordner, die Ihre Bibliothek schon hat

Eine über Jahre gewachsene Bibliothek ist selten ein flacher Ordner. Sie
enthält thematische Ordner — `Urlaub`, `Hochzeit Meyer` — und Ordner, die
bereits ein Datum tragen — `2019-04-15 Ostern in Tirol`. Was damit geschehen
soll, ist eine Ermessensfrage. LR-FolderCraft erkennt sie deshalb, legt offen,
was es gefunden hat, und überlässt Ihnen die Entscheidung.

### Was als datierter Ordner gilt

Ein Name, der mit einem Datum **beginnt**, wahlweise gefolgt von Text:

| Name | Erkannt als |
| --- | --- |
| `2019-04-15 Ostern in Tirol` | Tag |
| `2019_06_01 Hochzeit` | Tag |
| `20190415_Hochzeit` | Tag |
| `2019.03.10` | Tag |
| `2019-04` | Monat |
| `2019 Jahresrueckblick` | Jahr |
| `Urlaub`, `Sommer 2019`, `raw2019` | kein Datum |

Ein Datum mitten im Namen wird ignoriert — dort zu raten hieße, Absicht zu
erfinden.

Ein datierter Ordner zählt nur, wenn er **mindestens so fein** ist, wie die
Struktur es verlangt. Ein Ordner `2019` ist keine Antwort auf den Wunsch nach
Tagesordnern und wird deshalb wie ein thematischer Ordner behandelt, seine
Bilder werden ordentlich einsortiert. Umgekehrt genügt ein Tagesordner dem
Wunsch nach Jahresordnern. Enthält die Struktur überhaupt keine
Datums-Platzhalter, sagen Ordnerdaten nichts aus und werden ignoriert.

### Die vier Aktionen

| Aktion | Wirkung |
| --- | --- |
| `consolidate` | Fotos herausholen und unterhalb des Ankers einsortieren |
| `sort-inside` | Ordner behalten und die Struktur *darin* aufbauen |
| `resort` | den Ordner **an seiner Stelle** neu aufbauen, unter seinem eigenen Elternordner |
| `leave` | die Fotos dieses Ordners gar nicht anfassen |
| `keep` | datierter Ordner: die Fotos, die er korrekt beschreibt, bleiben |

`resort` braucht ein Beispiel. Gegeben
`raw2026/2026-06-28 Makro Blume im Garten` und die Struktur
`{yyyy}-{mm}-{dd}/{folder_label}`:

| Aktion | Ergebnis |
| --- | --- |
| `consolidate` | `2026-06-28/Makro Blume im Garten` — aus `raw2026` herausgezogen |
| `sort-inside` | `raw2026/2026-06-28 Makro Blume im Garten/2026-06-28/…` — verschachtelt |
| `resort` | `raw2026/2026-06-28/Makro Blume im Garten` — aufgeteilt, an Ort und Stelle |

### Die drei Vorgaben

| Situation | Schalter | Vorgabe |
| --- | --- | --- |
| Thematischer Unterordner | `--subfolder-action` | `consolidate` |
| Datierter Ordner | `--dated-folder-action` | `keep` |
| Foto in einem behaltenen oder neu aufgebauten datierten Ordner, dessen Datum nicht passt | `--mismatch-action` | `move-out` |

Mit den Vorgaben behält `2019-04-15 Ostern in Tirol` Namen und Bilder, während
ein Foto darin, das an einem anderen Tag entstand, in seinen eigenen
Datumsordner wandert. Thematische Ordner gehen in der gemeinsamen
Datumsstruktur auf.

`--mismatch-action leave` wiegt schwerer, als es aussieht. Eine Session, die
über Mitternacht läuft, hinterlässt Fotos, deren eigenes Datum dem Ordnernamen
widerspricht. Unter `keep` bleiben diese Fotos einfach liegen. Unter `resort`
folgen sie dem Datum **des Ordners** statt ihrem eigenen, sodass die Session
ganz neu aufgebaut wird, statt über zwei Tagesordner zerrissen zu werden.

### Regeln: ganze Ordnerklassen auf einmal entscheiden

Ordner einzeln zu beantworten skaliert nicht. Eine gewachsene Bibliothek hat
Dutzende Ordner und vielleicht vier verschiedene Absichten. `--rule` drückt die
Absichten aus:

```bash
lrfc plan KATALOG -s '{yyyy}-{mm}-{dd}/{folder_label}' \
    --rule '_extern=leave' \
    --rule '_fineart=leave' \
    --rule 'dated+label=resort' \
    --rule 'dated=keep' \
    --rule '*=sort-inside' \
    --mismatch-action leave
```

Regeln sind **geordnet**, und die **erste passende gewinnt** — die speziellen
also nach vorn. Ein Muster ist entweder ein Pfad-Glob oder eines von fünf
Schlüsselwörtern:

| Muster | Trifft |
| --- | --- |
| `*` | jeden Ordner, den keine frühere Regel getroffen hat |
| `dated` | Ordner, deren Name mit einem Datum beginnt |
| `dated+label` | datierte Ordner, die zusätzlich Text tragen |
| `dated-only` | datierte Ordner mit nichts als dem Datum |
| `plain` | Ordner ohne Datum im Namen |
| `_extern`, `raw20*`, `_in_Arbeit/*` | ein Pfad unterhalb der Wurzel, `*` und `?` erlaubt |

Ein Pfadmuster erfasst auch alles **unterhalb** des benannten Ordners, sodass
`_extern` ohne zweite Regel bis `_extern/2019` reicht.

`keep` auf einen Ordner ohne Datum im Namen angewandt wird zu `leave`
abgemildert — die ehrliche Lesart von „das Datum im Namen achten", wenn es
keines gibt.

### Vorrang

Von stark nach schwach:

1. `--folder-action ID=AKTION` — ein namentlich benannter Katalogordner
2. die erste passende `--rule`
3. Ihre Antwort unter `--interactive`
4. die Vorgabe `--subfolder-action` / `--dated-folder-action` für die Ordnerart

Eine Regel **unterdrückt die Frage, die sie bereits beantwortet** — genau darum
geht es: Mit fünf Regeln fragt `--interactive` nur noch nach Ordnern, über die
keine Regel spricht.

`plan` listet jeden Ordner mit der Regel, die ihn entschieden hat, sodass sich
ein Regelsatz vor dem Lauf prüfen lässt.

### Einzelne Ordner abweichend entscheiden

```bash
lrfc folders KATALOG                      # Ordner-IDs ermitteln
lrfc plan KATALOG -s day --folder-action 4711=sort-inside
```

`--folder-action ID=AKTION` ist wiederholbar und sticht sowohl die Regeln als
auch die globalen Vorgaben.

### Gefragt werden

```bash
lrfc plan KATALOG -s day --interactive
```

Jeder Ordner, der vernünftigerweise so oder so behandelt werden kann, wird
Ihnen vorgelegt — mit dem Befund, der Zahl der Fotos, wie viele davon ein
abweichendes Datum tragen, und welche Option die Vorgabe ist. Enter übernimmt
die Vorgabe, es passiert also nichts versehentlich. Der Ankerordner wird nie
vorgelegt: Er ist das Behältnis, in das sortiert wird, kein Unterordner, dessen
Schicksal zur Debatte steht.

In der TUI trifft man dieselbe Wahl mit Enter auf einer Zeile der Ordnertabelle
— das wechselt die Entscheidung dieses Ordners und plant sofort neu.

In der grafischen Oberfläche ist die Regelliste eine kleine Tabelle über der
Ordnertabelle: dort Regeln hinzufügen, entfernen und umsortieren — die
Ordnertabelle darunter zeigt, welche Regel jeden Ordner entschieden hat. Eine
dort von Hand getroffene Entscheidung sticht weiterhin jede Regel und wird als
Ihre ausgewiesen.

Wie auch immer Sie wählen: `plan` führt jeden gefundenen Ordner auf, welcher
Art er ist, was entschieden wurde und ob das aus einer Vorgabe, einer Regel,
einem ausdrücklichen `--folder-action` oder Ihrer eigenen Antwort stammt. Der
JSON-Export enthält dasselbe unter `folders`.

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

### Was der Plan nicht allein entscheiden konnte

Sowohl `plan` als auch die grafische Oberfläche führen getrennt von den Zahlen
jeden Fall auf, den das Werkzeug für Sie entschieden hat:

```
Braucht Ihre Antwort:
  [EXCEPTION] 12 Foto(s) in 1 datierten Ordner(n), deren eigenes Datum vom
              Ordnernamen abweicht -- oft eine Session über Mitternacht
          --mismatch-action = leave
          - raw2026/2026-06-27 Test 150mm Spiegelobjektiv/ (12)
```

Jeder Eintrag nennt die steuernde Option und was sie gerade tut — eine andere
Entscheidung ist also einen Schalter entfernt.

| Stufe | Bedeutung |
| --- | --- |
| `BLOCKIERT` | der Lauf startet nicht: eine fehlgeschlagene Vorabprüfung, oder eine Datei, die der Katalog nennt und die Platte nicht hat |
| `Warnung` | der Lauf startet, aber etwas ist nicht wie erwartet |
| `Ausnahme` | eine Entscheidung, die das Werkzeug für Sie getroffen hat und die eine Einstellung ändern kann |
| `Hinweis` | wissenswert, nichts zu beantworten |

In der grafischen Oberfläche ist das eine eigene Tabelle zwischen den
Einstellungen und der Ordnertabelle. Eine Zeile auswählen zeigt die betroffenen
Dateien.

### Das Verschiebeprotokoll, neben der Bibliothek

Ein `apply`-Lauf hinterlässt neben der `.lrcat`-Datei einen Klartext-Bericht:

```
Lightroom.Kataloge/Masterkatalog.Neu/
    Masterkatalog.Neu.lrcat
    LR-FolderCraft_2026-08-23_143012_Masterkatalog.Neu.log
```

Das ist nicht das Debug-Log. Das Debug-Log dient der Fehlersuche am Werkzeug;
dies dient der Person, die sich Monate später fragt, wo ein Foto geblieben ist.
Es führt jeden Quell- und Zielpfad auf, die verwendeten Regeln, wo
Katalogsicherung und Journal liegen, und eine Zusammenfassung.

| Schalter | Wirkung |
| --- | --- |
| `--no-move-log` | nicht schreiben |
| `--move-log-dir VERZ` | hierhin schreiben statt neben den Katalog |

Das Schreiben kann einen Lauf nie zum Scheitern bringen. Ist das Verzeichnis
nicht beschreibbar — schreibgeschütztes Volume, volle Platte — gelingt der Lauf
trotzdem, und das Ergebnis trägt einen Hinweis, dass der Bericht nicht
geschrieben werden konnte. Zum Zeitpunkt des Schreibens sind die Fotos längst
verschoben und geprüft.

Trockenläufe schreiben kein Verschiebeprotokoll: es wurde nichts verschoben.
