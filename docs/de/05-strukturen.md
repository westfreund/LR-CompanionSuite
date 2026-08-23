# Ordnerstrukturen und Platzhalter

**Revision r14.0.1 · Build-Datum 2026-08-23**

Eine **Struktur** ist eine geordnete Liste von **Ebenen**. Jede Ebene wird zu
einem Verzeichnis, und jede Ebene ist ein **Template** aus festem Text und
Platzhaltern in geschweiften Klammern.

```
["{yyyy}", "{mm}", "{dd}"]                 ->  2019/01/03
["{camera_slug}", "{yyyy}-W{iso_week}"]    ->  canon-eos-70d/2019-W01
["{yyyy}-{mm}-{dd}"]                       ->  2019-01-03
```

Auf der Kommandozeile werden die Ebenen mit `/` getrennt:

```bash
lrfc plan KATALOG -s '{yyyy}/{mm}/{dd}'
lrfc plan KATALOG -s '{camera_slug}/{yyyy}-W{iso_week}'
```

Mehrere Gruppierungsebenen sind schlicht mehrere Einträge — die Tiefe ist nicht
begrenzt.

## Vorlagen

| Vorlage | Beispiel | Bedeutung |
| --- | --- | --- |
| `day` | `2019-01-03` | Ein Ordner je Aufnahmetag |
| `year/day` | `2019/2019-01-03` | Jahresordner mit Tagesordnern |
| `year/month/day` | `2019/01/03` | Klassischer dreistufiger Datumsbaum |
| `year/month` | `2019/01` | Jahresordner mit Monatsordnern |
| `year-month` | `2019-01` | Ein Ordner je Monat |
| `year/week` | `2019/W01` | Jahresordner mit KW-Ordnern |
| `iso-week` | `2019-W01` | Ein Ordner je ISO-Kalenderwoche |
| `year/month-name` | `2019/01 Januar` | Jahresordner mit benannten Monaten |
| `camera/day` | `canon-eos-70d/2019-01-03` | Kameraordner mit Tagesordnern |
| `day/camera` | `2019-01-03/canon-eos-70d` | Tagesordner mit Kameraordnern |
| `camera/year/month/day` | `canon-eos-70d/2019/01/03` | Kamera, danach voller Datumsbaum |
| `year/quarter/month` | `2019/Q1/01` | Jahr, Quartal, Monat |

`lrfc presets --lang de` gibt diese Tabelle mit lebenden Beispielen aus. Eine
Vorlage ist nur eine Abkürzung — alles, was eine Vorlage tut, lässt sich auch
selbst schreiben.

## Platzhalter

### Datum und Uhrzeit

Die Werte stammen aus der Aufnahmezeit des Fotos (wie sie ermittelt wird, steht
in [04-bedienung.md](04-bedienung.md#fotos-ohne-aufnahmedatum)).

| Platzhalter | Beispiel | Bedeutung |
| --- | --- | --- |
| `{yyyy}` | `2019` | Vierstellige Jahreszahl |
| `{yy}` | `19` | Zweistellige Jahreszahl |
| `{mm}` | `01` | Monat, zweistellig |
| `{m}` | `1` | Monat, ohne fuehrende Null |
| `{dd}` | `03` | Tag, zweistellig |
| `{d}` | `3` | Tag, ohne fuehrende Null |
| `{hh}` | `17` | Stunde, 24h zweistellig |
| `{mi}` | `42` | Minute, zweistellig |
| `{month_name}` | `January` | Ausgeschriebener Monatsname |
| `{month_short}` | `Jan` | Abgekuerzter Monatsname |
| `{quarter}` | `Q1` | Kalenderquartal |
| `{iso_week}` | `01` | ISO-8601-Kalenderwoche, zweistellig |
| `{iso_year}` | `2019` | ISO-8601-Wochenjahr |
| `{weekday}` | `Thursday` | Ausgeschriebener Wochentag |
| `{weekday_short}` | `Thu` | Abgekuerzter Wochentag |
| `{doy}` | `003` | Tag des Jahres, dreistellig |

### Kamera und Objektiv

| Platzhalter | Beispiel | Bedeutung |
| --- | --- | --- |
| `{camera}` | `Canon EOS 70D` | Kameramodell laut Lightroom |
| `{camera_slug}` | `canon-eos-70d` | Kameramodell, klein und mit Bindestrichen |
| `{camera_sn}` | `053022010127` | Seriennummer der Kamera |
| `{lens}` | `EF-S18-55mm f/3.5-5.6 IS STM` | Objektiv laut Lightroom |
| `{lens_slug}` | `ef-s18-55mm-f-3-5-5-6-is-stm` | Objektiv, klein und mit Bindestrichen |

### Datei

| Platzhalter | Beispiel | Bedeutung |
| --- | --- | --- |
| `{format}` | `RAW` | Lightroom-Dateiformatklasse |
| `{ext}` | `CR2` | Dateiendung, gross |
| `{ext_lower}` | `cr2` | Dateiendung, klein |
| `{orig_folder}` | `raw2019` | Name des heutigen Ordners |
| `{folder_label}` | `Makro Blume im Garten` | Text hinter dem Datum in diesem Ordnernamen, sonst leer |

`lrfc tokens --lang de` gibt dieselbe Referenz aus.

## Sprache

`{month_name}`, `{month_short}`, `{weekday}` und `{weekday_short}` richten sich
nach `--lang`:

```bash
lrfc plan KATALOG -s '{yyyy}/{mm} {month_name}'              # 2019/01 January
lrfc plan KATALOG -s '{yyyy}/{mm} {month_name}' --lang de    # 2019/01 Januar
```

Die Namen sind eingebaut, es muss also kein System-Locale installiert sein.

## ISO-Kalenderwochen

`{iso_week}` und `{iso_year}` folgen ISO 8601: Eine Woche gehört zu dem Jahr,
in dem ihr Donnerstag liegt. Um den Jahreswechsel herum ist das relevant:

| Datum | `{yyyy}` | `{iso_year}` | `{iso_week}` |
| --- | --- | --- | --- |
| 2019-12-29 | 2019 | 2019 | 52 |
| 2019-12-30 | 2019 | **2020** | **01** |
| 2020-01-01 | 2020 | 2020 | 01 |

`{iso_week}` deshalb immer mit `{iso_year}` kombinieren, nie mit `{yyyy}` —
sonst landen Fotos vom 30. Dezember 2019 in einem Ordner `2019-W01`, direkt
neben Fotos von Anfang Januar 2019.

```bash
lrfc plan KATALOG -s '{iso_year}-W{iso_week}'      # richtig
lrfc plan KATALOG -s '{yyyy}-W{iso_week}'          # überrascht zum Jahresende
```

## Namensbereinigung

Gerenderte Namen werden für alle unterstützten Plattformen nutzbar gemacht, in
dieser Reihenfolge:

1. optionale ASCII-Reduktion (`--ascii`): `Grün` → `Grun`
2. Zeichen, die auf mindestens einem Betriebssystem unzulässig sind
   (`< > : " / \ | ? *` sowie Steuerzeichen) werden zu `-`
3. Folgen von Leerraum werden zu einem Leerzeichen, das Ergebnis wird getrimmt
4. abschließende Punkte und Leerzeichen entfallen — Windows verwirft sie
   stillschweigend
5. Windows-Gerätenamen bekommen einen Unterstrich: `CON` → `_CON`
6. Namen über 100 Zeichen werden gekürzt
7. ein leeres Ergebnis wird zu `unnamed`

Das gilt auch unter macOS und Linux, damit eine Bibliothek portabel bleibt.

## Fehlende Metadaten

Ein Platzhalter mit unbekanntem Wert erzeugt keinen leeren Ordnernamen:

| Platzhalter | Ersatzwert |
| --- | --- |
| `{camera}` | `Unknown Camera` |
| `{camera_slug}` | `unknown-camera` |
| `{camera_sn}` | `unknown-sn` |
| `{lens}` | `Unknown Lens` |
| Datums-Platzhalter | das Foto kommt nach `_unsorted`, siehe `--on-missing-date` |

## Beispiele

```bash
# ein Ordner je Tag, innerhalb des vorhandenen Jahresordners
lrfc apply KATALOG -s day

# klassischer dreistufiger Baum
lrfc apply KATALOG -s year/month/day

# deutsche Monatsnamen, Tag mit Wochentag
lrfc apply KATALOG -s '{yyyy}/{mm} {month_name}/{dd} {weekday_short}' --lang de

# erst nach Kameragehäuse trennen, dann nach Tag
lrfc apply KATALOG -s '{camera_slug}/{yyyy}-{mm}-{dd}'

# nach Seriennummer -- nützlich bei zwei baugleichen Gehäusen
lrfc apply KATALOG -s '{camera}-{camera_sn}/{yyyy}-{mm}-{dd}'

# Kalenderwochen, korrekt
lrfc apply KATALOG -s '{iso_year}/W{iso_week}'

# Raw und JPEG trennen
lrfc apply KATALOG -s '{yyyy}-{mm}-{dd}/{format}'

# Quartale für ein geschäftliches Archiv
lrfc apply KATALOG -s '{yyyy}/{quarter}/{mm}'
```

Immer zuerst `plan` laufen lassen und die Zielordnerliste lesen.



### ASCII-Namen

`--ascii` (das Feld *ASCII-Namen* im Fenster) beschränkt Ordnernamen auf reines
ASCII — für ein Laufwerk oder ein Sicherungsziel, das nichts anderes trägt.

Buchstaben, die ein Akzent nicht abbilden kann, werden **ausgeschrieben** statt
weggeworfen:

| | |
| --- | --- |
| `Völki` | `Voelki` |
| `Tabaksmühle` | `Tabaksmuehle` |
| `Straße` | `Strasse` |
| `MÜNCHEN` | `MUENCHEN` — ein durchgehend großgeschriebenes Wort bleibt es |
| `Ærø` | `Aeroe` |
| `Café`, `Señor` | `Cafe`, `Senor` — hier *ist* das Weglassen die Umschrift |

Abgedeckt: ä ö ü ß æ ø œ å þ ð đ ł ı und die Großbuchstaben dazu. Alles andere
behält seinen Grundbuchstaben, was für französische, spanische, polnische
Akzente und die übrigen richtig ist.

## Datumsebenen, die das ganze Datum nennen

Voreingestellt baut `{yyyy}/{mm}/{dd}` den Pfad `2019/01/03`: Jede Ebene nennt
nur ihren eigenen Teil. Mit **kumulativen Datumsangaben** wird daraus

```
2019/2019-01/2019-01-03
```

Jeder Ordnername ist dann für sich vollständig — ein Ordner sagt also auch
dann noch, welcher Tag er ist, wenn er in einem Suchergebnis, einem Dateidialog
oder aus seinem Baum herausgezogen auftaucht.

```bash
lrfc plan KATALOG -s year/month/day --cumulative-dates
```

Im Fenster ist es das Ankreuzfeld **„Jede Datumsebene nennt das ganze Datum"**,
und die Live-Vorschau zeigt die kumulative Form, sobald es gesetzt ist.

Nur Datumsebenen nehmen teil. Aus `{camera_slug}/{yyyy}/{mm}` wird
`{camera_slug}/{yyyy}/{yyyy}-{mm}` — die Kamera ist kein Datum und wird nicht
wiederholt. Eine Ebene, die das Datum bereits vollständig schreibt, gewinnt
nichts hinzu, denn jede Ebene erbt nur von den Datumsebenen **über** ihr.

Die von Ihnen getippte Struktur bleibt, wie Sie sie getippt haben: Die Option
abzuschalten gibt exakt `{yyyy}/{mm}/{dd}` zurück. Zwei Vorlagen haben es
eingebaut, falls Sie den Schalter nicht verwenden möchten:

| Vorlage | Ergebnis |
| --- | --- |
| `year/year-month/full-day` | `2019/2019-01/2019-01-03` |
| `year/full-day` | `2019/2019-01-03` |

## Ebenen, die leer bleiben

Eine Ebene, deren Platzhalter sämtlich leer ausfallen, wird **weggelassen** und
nicht zu einem Ordner namens `unnamed`. Erst das macht `{folder_label}` als
eigene Ebene brauchbar:

| Ordner, in dem das Foto liegt | `{yyyy}-{mm}-{dd}/{folder_label}` ergibt |
| --- | --- |
| `2026-06-28 Makro Blume im Garten` | `2026-06-28/Makro Blume im Garten` |
| `2026-06-28` | `2026-06-28` |
| `raw2020` | `2020-01-03` |

Dasselbe gilt an jeder Stelle der Struktur: `{yyyy}/{folder_label}/{mm}-{dd}`
fällt zu `2026/06-28` zusammen, wenn kein Text zu setzen ist.

Eine Struktur, deren Ebenen *alle* leer ausfallen, legt das Foto direkt in den
Anker. `{folder_label}` allein ist damit eine Struktur, die alles ohne
Ordnertext in ein einziges Verzeichnis legt — zulässig, selten gemeint.
