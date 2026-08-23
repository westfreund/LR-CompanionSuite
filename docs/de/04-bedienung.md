# Bedienung

**Revision r13.0.1 · Build-Datum 2026-08-23**

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

`-s` ist die Kurzform von `--structure` und nimmt entweder einen Vorlagennamen
oder ein eigenes Template.

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
`--yes` überspringt die Rückfrage. `--catalog-backup PFAD` benennt die
Katalogsicherung, aus der zurückgespielt wird — für den seltenen Fall, dass der
Vermerk im Journal nicht mehr stimmt; normalerweise weiß das Journal es.

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

Ohne Neustart lässt sich die Sprache auch im Fenster umschalten, im Menü
**Aktionen**. Der Eintrag zeigt immer die **andere** Sprache an, in der
deutschen Oberfläche also „English".

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

Über das Menü **Aktionen** lässt sich jederzeit zwischen Deutsch und Englisch
wechseln, und dort steht auch das Rückgängigmachen.

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
| `refile` | in die Zielstruktur einreihen, aber den **Zusatztext behalten** — auf der tiefsten Datumsebene |
| `relocate` | den Ordner **unverändert** an den neuen Ort tragen — gleicher Name, gleicher Inhalt, keine Sortierung |
| `leave` | die Fotos dieses Ordners gar nicht anfassen — sie bleiben liegen, auch wenn der Rest der Bibliothek in einen neuen Baum sortiert wird |
| `keep` | datierter Ordner: die Fotos, die er korrekt beschreibt, bleiben |

`resort` braucht ein Beispiel. Gegeben
`raw2026/2026-06-28 Makro Blume im Garten` und die Struktur
`{yyyy}-{mm}-{dd}/{folder_label}`:

| Aktion | Ergebnis |
| --- | --- |
| `consolidate` | `2026-06-28/Makro Blume im Garten` — aus `raw2026` herausgezogen |
| `sort-inside` | `raw2026/2026-06-28 Makro Blume im Garten/2026-06-28/…` — verschachtelt |
| `resort` | `raw2026/2026-06-28/Makro Blume im Garten` — aufgeteilt, an Ort und Stelle |
| `refile` | `2026-06-28 Makro Blume im Garten` in der Zielstruktur — neben einem schlichten `2026-06-28`, nicht darin aufgegangen |
| `relocate` | `<neue Wurzel>/raw2026/2026-06-28 Makro Blume im Garten` — unverändert hinübergetragen |

`relocate` ist die Aktion für Material, das mitkommen soll, ohne angefasst zu
werden: ein `_fineart`-Ordner, ein `_extern`-Eingang, ein Auftragsordner mit
eigener Ordnung. Sie erhält die gesamte Unterstruktur des Ordners und seinen
Pfad unterhalb der Quellwurzel — `_extern/2020/Fest` landet also als
`_extern/2020/Fest` unter der neuen Wurzel. Die Struktur des Laufs wird dafür
gar nicht gerendert, und der Anker wird ignoriert: den Ordner eine Ebene tiefer
zu vergraben ist nicht, was „das dorthin verschieben" heißt.

Sie bewirkt nur etwas, wenn der Lauf den Ordner überhaupt woandershin legen
kann, also mit gesetztem Zielordner. Beim Sortieren am selben Ort bleibt ein
`relocate`-Ordner genau, wo er ist — `plan` weist das als „bereits am Ziel" aus.

`refile` ist für Bibliotheken, deren Datumsordner Sessionnamen tragen. Der
Ordner wird dort eingereiht, wo die Struktur ihn hinstellt, und sein Text an die
tiefste Datumsebene angehängt — die Session behält ihren Namen im neuen Baum:

```
mobileRAW/2026-06-28 Makro Blume im Garten/   ->  2026/2026-06/2026-06-28 Makro Blume im Garten/
mobileRAW/(lose Fotos vom 28. Juni)           ->  2026/2026-06/2026-06-28/
```

Beide bestehen **nebeneinander**. Sie zusammenzuführen würde das Einzige
wegwerfen, was die Session unterscheidbar macht — deshalb steht `refile` neben
`consolidate` und nicht an dessen Stelle.

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
| `_extern`, `raw20*`, `_in_Arbeit/*` | ein Ordnerpfad oder -name, `*` und `?` erlaubt |

Ein Muster findet seinen Ordner, **so tief er auch liegt**, und erfasst alles
**darunter** — die eine Regel `_extern` trifft also `_extern`,
`raw2019/_extern` und `raw2019/_extern/2020/Fest` gleichermaßen. Ein Schrägstrich
macht daraus einen Pfad: `_in_Arbeit/2021` trifft dieses Ordnerpaar, nicht
irgendein `2021`.

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

## Vor dem ersten Lauf: die Voraussetzungen

Bevor *Ausführen* irgendetwas startet, nennt das Fenster, was es über die
Bibliothek tatsächlich vorgefunden hat, und verlangt ein bewusstes Ja:

```
Vor diesem Lauf
  ✓  Keine Lightroom-Sperrdatei — der Katalog ist frei.
  ✓  Katalogschema 18.0.0 — eine Version, gegen die diese Revision verifiziert wurde.
  ✓  Alle 1 Wurzelordner mit Dateien existieren auf der Platte (51.049 Dateien).
  ✓  Eine frühere Sicherung dieses Katalogs von 2026-08-23 09:08 ist vorhanden.

  ☐  Ich habe das gelesen, Lightroom Classic ist geschlossen, und ich habe eine
     eigene Sicherung
```

Das Kästchen muss angekreuzt sein, bevor die Schaltfläche benutzbar wird — die
Bestätigung lässt sich also nicht aus Reflex geben. Und ein Befund, der
**blockiert** (ein Wurzelordner, den es nicht gibt), lässt sich überhaupt nicht
bestätigen. Gefragt wird einmal je Katalog und Sitzung.

Dieselbe Auskunft auf der Kommandozeile: `lrfc info KATALOG` nennt Schemaversion
und Wurzelordner, `lrfc plan` fährt die vollständige Vorabprüfung.

## Was das Werkzeug ist

Das Fenster beginnt mit der Marke, dem Namen und einem Satz, der sagt, was das
Werkzeug tut. **Aktionen → Über LR-FolderCraft** gibt die Kurzfassung in drei
Sätzen: was es
tut, das Versprechen, dass nur die Ordnerzeilen und die Ordnerspalte jeder Datei
geschrieben werden, Revision und Build-Datum, und die Lizenz. Der Zweck steht
außerdem als eine Zeile ganz oben im Fenster, sichtbar ohne einen Klick.

## Dateien, die der Katalog nicht kennt

Eine über Jahre bearbeitete Bibliothek sammelt sie an: ein nie importierter
Export, ein Photoshop-Zwischenstand, ein verwaistes `.xmp`, dessen RAW gelöscht
wurde, ein versprengtes `.png`. Lightroom sieht sie nicht, und deshalb liegt
nach dem Umsortieren immer noch Kleinkram herum.

```bash
lrfc apply KATALOG -s day --collect-orphans
```

Jede Quellwurzel bekommt dann einen Ordner — voreingestellt
`_not-in-catalog`, wählbar mit `--orphan-folder NAME` — und jede solche Datei
wandert hinein, **unter Beibehaltung ihres Herkunftspfads**, sodass nichts
kollidiert und die Herkunft sichtbar bleibt:

```
mobileRAW/raw2021/3Stufig HZ-1239 Kopie.png
  -> mobileRAW/_not-in-catalog/raw2021/3Stufig HZ-1239 Kopie.png
```

Nichts wird gelöscht, die Verschiebungen werden wie alle anderen journalisiert,
und das Zurücknehmen des Laufs holt sie wieder heraus.

**Was nie eingesammelt wird:**

| | |
| --- | --- |
| Alles, worauf der Katalog verweist | aus jeder Wurzel, auch Dateien, die dieser Lauf gerade bewegt |
| Sidecars katalogisierter Fotos | sie gehören zu ihrem Foto und reisen mit — erkannt am Foto daneben, nicht an der Bewegung, damit ein zweiter Lauf nicht einsammelt, was der erste sortiert hat |
| Lightrooms eigene Dateien | der Katalog, seine Nebendateien, `*.lrdata`-Vorschauen, `*.lrcat-data` |
| Das Gekritzel des Dateisystems | `.DS_Store`, `Thumbs.db`, AppleDouble-Begleiter `._X` |
| Der Sammelordner selbst | und ein Zielbaum, in den dieser Lauf gerade sortiert |

Das Einsammeln ist **standardmäßig aus**: Es bewegt Dateien, nach denen niemand
das Werkzeug gefragt hat. Ist es an, meldet `plan` die gefundene Zahl mit
Beispielen — eine Überraschung soll es nie sein.

### Vorhandene Tagesordner übernehmen

Eine Bibliothek, deren Datumsordner Sessionnamen tragen, will keine Regel je
Ordner. Das Ankreuzfeld **„Vorhandene Tagesordner in die neue Struktur
übernehmen, Zusatztext behalten"** über der Regelliste gibt jedem datierten
Ordner auf einen Schlag die Aktion `refile`:

```bash
lrfc plan KATALOG -s year/month/day --cumulative-dates --dated-folder-action refile
```

`2026-06-28 Makro Blume im Garten` behält damit seinen Titel im neuen Baum und
steht neben dem schlichten `2026-06-28` mit den übrigen Fotos des Tages. Das
Ankreuzfeld und das Feld *Datierter Ordner* in den Optionen sind dieselbe
Einstellung und stimmen deshalb immer überein.

Regeln stechen weiterhin, wo sie gesetzt sind — das Ankreuzfeld ist die
Voreinstellung darunter, kein Gegenspieler.

## Was ein Lauf hinterlässt

Alles, was ein Lauf erzeugt, landet in einem Ordner **neben dem Katalog, den er
verändert hat**:

```
Masterkatalog.Neu/
    Masterkatalog.Neu.lrcat
    LR-FolderCraft/
        2026-08-23_165247/
            run.json        was getan wurde, wie viel, und ob es zurückgenommen ist
            settings.json   jede genutzte Option, in der Form eines Profils
            journal.jsonl   die maschinenlesbare Aufzeichnung, aus der Undo arbeitet
            moves.log       dasselbe in Prosa, für Menschen
```

Das zählt genau dort, wo es am leichtesten schiefgeht: auf einem externen
Laufwerk mit mehreren Bibliotheken. Deren Journale lagen bisher gemeinsam in
einem Konfigurationsverzeichnis unter ähnlichen Namen, und das falsche
zurückzunehmen versetzt eine Bibliothek in einen Zustand, in dem sie nie war.
Jetzt liegen die Läufe jedes Katalogs unter diesem Katalog.

Die **Katalogsicherung liegt bewusst nicht dort.** Eine 700-MB-Kopie neben dem
Original, auf demselben Laufwerk, übersteht einen Fehler, aber nicht das
Laufwerk. Sie geht weiterhin ins Konfigurationsverzeichnis, und `run.json`
vermerkt wohin. Wer Portabilität höher gewichtet als die Unabhängigkeit vom
Laufwerk, richtet `--backup-dir` auf den Katalogordner.

Ist das Volume schreibgeschützt oder voll, läuft der Lauf trotzdem: Die
Aufzeichnungen fallen auf das Konfigurationsverzeichnis zurück, und das Ergebnis
sagt es.

### `lrfc history KATALOG`

Führt auf, was mit diesem Katalog geschehen ist, neueste zuerst, mit dem Befehl
zum Zurücknehmen jedes noch stehenden Laufs:

```console
$ lrfc history /Volumes/Extreme\ Pro/.../Masterkatalog.Neu.lrcat
2 Lauf/Läufe, neueste zuerst:
  2026-08-23 16:52  51.049 Datei(en)  {yyyy}/{yyyy}-{mm}/{yyyy}-{mm}-{dd}  [kann zurückgenommen werden]
    .../LR-FolderCraft/2026-08-23_165247
    rückgängig: lrfc undo .../LR-FolderCraft/2026-08-23_165247/journal.jsonl
  2026-08-23 11:40  51.049 Datei(en)  {yyyy}/{mm}/{dd}  [zurückgenommen 2026-08-23 12:45]
    .../LR-FolderCraft/2026-08-23_114055
```

Im Fenster ist dieselbe Liste **Aktionen → Verlauf der Läufe…**, und
*Rückgängig* öffnet sie statt eines Dateidialogs — der zurückgenommene Lauf ist
also immer einer von *diesem* Katalog.

### Ein Lauf wird einmal zurückgenommen

Ihn zweimal zurückzunehmen würde verschieben, was inzwischen an jenen Pfaden
liegt. Ein als zurückgenommen vermerkter Lauf wird deshalb verweigert;
`--force` übergeht das und ist fast nie richtig.

Das Journal wird **behalten**, nicht gelöscht. Nach einem teilweise
gescheiterten Undo ist es die einzige Auskunft darüber, was tatsächlich bewegt
wurde — es genau dann wegzuwerfen, wenn es gebraucht wird, wäre die falsche Art
von Ordnung. Was das erneute Anbieten verhindert, ist der Vermerk am Lauf.


## Profile


Eine Arbeitsweise einmal speichern und über Bibliotheken hinweg anwenden:

```bash
lrfc plan KATALOG -s '{camera_slug}/{yyyy}-{mm}-{dd}' --save-profile nach-kamera
lrfc apply ANDERER_KATALOG --profile nach-kamera
lrfc profiles
```

Im Fenster steht dafür ganz oben eine Zeile **Profil** mit Namensfeld sowie
*Laden* und *Speichern*.

### Was ein Profil enthält — und was nicht

Ein Profil hält die **Optionen**: Struktur, kumulative Datumsangaben, die drei
Ordnervorgaben, Konfliktbehandlung, Endungsfilter, Sidecars, ASCII-Namen, das
Einsammeln katalogfremder Dateien und dessen Ordnername, Verschiebeprotokoll,
Datumsquellen, Sprache.

Bewusst **nicht** enthalten:

| | Warum nicht |
| --- | --- |
| Katalog, Zielordner, Stammordner | Sie gehören zu einer Bibliothek, nicht zu einer Arbeitsweise |
| Die Regelliste | Regeln benennen Ordner, die es genau in einer Bibliothek gibt |
| Entscheidungen zu einzelnen Ordnern | Es sind Katalog-Ordner-IDs; in der nächsten Bibliothek träfen sie fremde Ordner |
| `--ignore-lock`, `--allow-unsupported-catalog`, „keine Sicherung" | Notausgänge für einen einzelnen Lauf. Sie Monate später unbemerkt in die nächste Bibliothek zu tragen, ist genau das, was ein Profil nicht tun darf |

Genau deshalb lässt sich dasselbe Profil auf mehrere Sammlungen anwenden. Ein
Profil speichert außerdem niemals `dry_run` — das Laden kann also nie
versehentlich einen scharfen Lauf starten. `--config DATEI.json` lädt
Einstellungen aus einer bestimmten Datei.

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

### Einen Lauf aus dem Fenster zurücknehmen

Die Schaltfläche **Rückgängig…** neben *Ausführen* — und derselbe Eintrag im
Menü **Aktionen** — dreht einen abgeschlossenen Lauf um. Er fragt nach dessen Journal — der neueste wird zuerst angeboten, weil fast
immer er gemeint ist —, sagt unmissverständlich, was geschieht, und stellt dann
jede verschobene Datei an ihren Platz zurück, entfernt die vom Lauf angelegten
Ordner, sofern sie leer sind, und spielt den Katalog aus der Sicherung dieses
Laufs zurück.

Lightroom Classic muss dafür geschlossen sein, genau wie für den Lauf selbst.

Läufe werden vom neuesten her zurückgenommen. Einen älteren Lauf zurückzunehmen,
während ein neuerer noch steht, spielte einen Katalog ein, der nicht mehr
beschreibt, was auf der Platte liegt; wer weiter zurück muss, nimmt die Läufe
der Reihe nach zurück. `lrfc undo JOURNAL` tut auf der Kommandozeile dasselbe.

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
