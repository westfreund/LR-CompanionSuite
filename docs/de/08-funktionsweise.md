# Funktionsweise

**Revision r14.0.1 · Build-Datum 2026-08-23**

## Warum der Katalog direkt bearbeitet werden muss

Ein Lightroom-Classic-Katalog (`.lrcat`) ist eine SQLite-Datenbank. Einen
unterstützten programmatischen Weg, ein Foto zwischen Ordnern zu verschieben,
gibt es nicht:

| Weg | Bewertung |
| --- | --- |
| Lightroom-Lua-SDK | Kann Fotos und Metadaten lesen. Hat **keine** Schnittstelle, um ein Foto in einen anderen Ordner zu verschieben. |
| Finder / Explorer | Verschiebt die Datei, zerstört die Katalogreferenz. Alles gilt als fehlend. |
| Ziehen im Ordner-Bedienfeld | Korrekt, aber Handarbeit. Für tausende Fotos nicht praktikabel. |
| Katalog direkt bearbeiten | Der einzige automatisierbare Weg. Das tut dieses Werkzeug. |

LR-FolderCraft öffnet also die SQLite-Datei bei geschlossenem Lightroom, ändert
so wenig wie möglich und verschiebt die Dateien passend dazu.

## Was Lightroom über den Ort einer Datei speichert

Drei Tabellen beschreiben, wo ein Foto liegt.

### `AgLibraryRootFolder`

Eine Zeile je oberster Speicherstelle, aus der importiert wurde.

```
id_local      4908476
id_global     6A431BCE-A7FF-49DF-A64D-6AEE1B782A4F
absolutePath  /Volumes/Fotos/2019/raw2019/          <- mit abschließendem Schrägstrich
name          raw2019
```

### `AgLibraryFolder`

Eine Zeile je Ordner, relativ zu einem Stammordner.

```
id_local      1971944
id_global     BE11D36B-3F56-44E7-81C2-EBB52FC9B21D
parentId      NULL                 <- die Zeile des Stammordners selbst
pathFromRoot  ''                   <- leerer String für den Stammordner
rootFolder    4908476
```

`pathFromRoot` ist für den Stammordner der leere String, sonst ein POSIX-Pfad
**mit abschließendem Schrägstrich**: `2019/`, `2019/01/`, `2019/01/03/`. Jede
Zeile verweist über `parentId` auf ihren Elternordner, und ein
`UNIQUE(rootFolder, pathFromRoot)`-Index stellt sicher, dass es jeden Pfad nur
einmal gibt.

### `AgLibraryFile`

Eine Zeile je Datei auf dem Datenträger.

```
id_local        812768
baseName        IMG_5047
extension       CR2
folder          1971944            <- die einzige Spalte, die dieses Werkzeug ändert
idx_filename    IMG_5047.CR2
lc_idx_filename img_5047.cr2       <- Teil von UNIQUE(lc_idx_filename, folder)
```

Der absolute Pfad einer Datei ergibt sich daher als:

```
AgLibraryRootFolder.absolutePath + AgLibraryFolder.pathFromRoot + AgLibraryFile.idx_filename
```

## Was das Werkzeug ändert — und sonst nichts

| Änderung | Tabelle | Wann |
| --- | --- | --- |
| Ordnerzeilen einfügen | `AgLibraryFolder` | wenn ein Zielordner noch nicht existiert |
| Datei umhängen | `AgLibraryFile.folder` | für jede verschobene Datei |
| Namensspalten aktualisieren | `AgLibraryFile.baseName`, `extension`, `idx_filename`, `lc_idx_filename`, `lc_idx_filenameExtension` | nur wenn ein Konflikt eine Umbenennung erzwang |
| ID-Zähler weiterstellen | `Adobe_variablesTable` (`Adobe_entityIDCounter`) | wenn neue Zeilen entstehen |
| Stammordnerzeile einfügen | `AgLibraryRootFolder` | nur bei `--placement new-tree` |
| Leere Ordnerzeilen löschen | `AgLibraryFolder` | nur leer gewordene Ordner, nie eine Stammordnerzeile |

Alles Übrige bleibt unangetastet — nachgewiesen durch einen Hash über
`Adobe_images`, `Adobe_imageDevelopSettings`, `AgLibraryKeywordImage` und
`AgLibraryCollectionImage` vor und nach einem Lauf: identisch.

## Warum nichts verloren geht

Jede andere Tabelle verweist über `AgLibraryFile.id_local` oder
`Adobe_images.id_local` auf ein Foto, und **keiner dieser Werte ändert sich
je**:

```
AgLibraryFile.id_local  ◄── Adobe_images.rootFile
                                 ▲
                                 ├── Adobe_imageDevelopSettings.image
                                 ├── AgLibraryKeywordImage.image
                                 ├── AgLibraryCollectionImage.image
                                 ├── Adobe_images.masterImage   (virtuelle Kopien)
                                 └── ...
```

Nur die Spalte `folder` von `AgLibraryFile` wandert. Eine virtuelle Kopie ist
eine eigene `Adobe_images`-Zeile, deren `rootFile` auf *dieselbe*
`AgLibraryFile`-Zeile zeigt — sie folgt ihrem Master also automatisch und kann
nicht verwaisen.

Vorschauen liegen in `<Katalog> Previews.lrdata` und werden über die Bild-UUID
adressiert, nicht über den Pfad. Auch sie überstehen den Vorgang.

## Zeilen-IDs stammen aus Lightrooms eigenem Zähler

Lightroom vergibt jede `id_local` aus einem katalogweiten Zähler in
`Adobe_variablesTable` unter `Adobe_entityIDCounter`. Neue Ordnerzeilen holen
ihre IDs aus genau diesem Zähler, und der Zähler wird um exakt die Zahl der
angelegten Zeilen erhöht. IDs selbst zu erfinden — etwa `MAX(id_local) + 1` —
würde früher oder später mit einer ID kollidieren, die Lightroom später selbst
vergibt.

Der Zähler muss außerdem in derselben **SQLite-Speicherklasse** zurückgeschrieben
werden. `Adobe_variablesTable.value` ist ohne Typ deklariert, hat also
BLOB-Affinität und behält genau das, was man ihm gibt. Lightroom speichert den
Zähler als REAL; schreibt man stattdessen die Zeichenkette `'4914941.0'` statt
der Zahl `4914941.0`, entsteht ein Wert, der sich gleich liest,
`integrity_check` besteht und bei einem Zeilenvergleich nicht auffällt — aber
Lightroom weigert sich dann, den Katalog zu öffnen, und seine eigene Reparatur
kopiert den Wert unverändert mit, repariert also endlos in eine byte-identische
Datei. `allocate_ids()` liest nach dem Schreiben `typeof()` erneut und bricht
den Lauf ab, wenn sich die Speicherklasse geändert hat.

## Die Ausführungsreihenfolge

Die Reihenfolge ist so gewählt, dass der Schritt, der sich *am billigsten
zurücknehmen lässt*, zuletzt kommt.

```
1  Vorprüfung   Lightroom zu? Rechte? Speicher?                ── Abbruch kostet hier nichts
2  Backup       Katalog kopieren, per SHA-256 verifizieren
3  Katalog      schreibend öffnen, BEGIN, Ordnerzeilen anlegen,
                Dateien umhängen                               ── noch nicht bestätigt
4  Dateisystem  Verzeichnisse anlegen, jede Datei verschieben,
                jede vorher ins Journal schreiben
5  Commit       erst jetzt wird die Katalogtransaktion bestätigt
6  Aufräumen    leer gewordene Ordnerzeilen und Verzeichnisse entfernen
7  Prüfung      Katalog erneut lesen, jeden Pfad gegen die Platte prüfen
```

Scheitert Schritt 4 bei Datei 3.000 von 9.452:

- die Katalogtransaktion wird **zurückgerollt** — die Datenbank auf der Platte
  ist bitgleich mit dem Zustand vor dem Lauf;
- die 2.999 bereits verschobenen Dateien werden anhand des Journals
  zurückgelegt;
- das Journal hält Fehler und Wiederherstellung fest.

Weil der Katalog erst nach dem Eintreffen aller Dateien bestätigt wird, gibt es
kein Zeitfenster, in dem die Datenbank eine Struktur beschreibt, die auf der
Platte nicht existiert.

## Dateien verschieben

Innerhalb eines Volumes ist eine Verschiebung ein `os.replace()` — ein atomares
Umbenennen, selbst bei 300 GB augenblicklich, weil keine Daten kopiert werden.

Über Volume-Grenzen hinweg wird die Datei kopiert, beide Kopien werden per
SHA-256 verglichen, und erst dann wird die Quelle entfernt. Das ist langsam,
aber sicher, und die Vorprüfung verweigert den Start ohne 105 % des benötigten
freien Speichers.

Eine vorhandene Datei am Ziel wird nie überschrieben. Der Executor prüft
unmittelbar vor jeder Verschiebung erneut, sodass selbst eine erst nach der
Planung aufgetauchte Datei sicher ist.

Zu einer Datei können Begleiter gehören, die mitwandern müssen. XMP-Sidecars
werden als Teil der Verschiebung des Fotos geplant und erscheinen im Journal
unter derselben `file_id`.

Die macOS-AppleDouble-Datei `._<name>`, die auf exFAT/FAT die erweiterten
Attribute und den Resource-Fork enthält, ist ein Sonderfall: Unter macOS
verschiebt der Kernel sie zusammen mit der Datei, das Werkzeug darf sie also
*nicht* zusätzlich verschieben — das kollidiert mit dem, was das System bereits
getan hat. Auf anderen Plattformen ist sie eine gewöhnliche Datei und wird
ausdrücklich mitgenommen.

## Das Journal

Jeder Lauf schreibt ein JSON-Lines-Journal; jede Zeile wird geflusht und per
`fsync` gesichert, *bevor* die beschriebene Aktion versucht wird:

```json
{"ts": "...", "event": "run-start",  "tool_version": "1.0.0", "catalog": "...", "plan": {...}}
{"ts": "...", "event": "backup",     "source": "...", "target": "..."}
{"ts": "...", "event": "mkdir",      "path": "..."}
{"ts": "...", "event": "move-begin", "file_id": 812768, "source": "...", "target": "..."}
{"ts": "...", "event": "move-done",  "file_id": 812768}
{"ts": "...", "event": "catalog-commit", "folders": 152, "files": 9452}
{"ts": "...", "event": "run-end",    "status": "success", "moved": 9452}
```

Selbst ein Stromausfall hinterlässt eine brauchbare Aufzeichnung: Eine
abgeschnittene letzte Zeile wird ignoriert, allem davor wird vertraut.
`lrfc undo` spielt das Journal rückwärts ab.

## Den Katalog sicher lesen

Lesezugriffe nutzen SQLites URI-Modus `mode=ro`, sodass der Treiber selbst
jeden Schreibversuch verweigert.

Eine Eigenheit ist erwähnenswert: Auf Dateisystemen ohne POSIX-Advisory-Locking
— insbesondere exFAT und FAT, also das, was auf den meisten externen
Fotoplatten liegt — scheitert `mode=ro` mit *„unable to open database file“*,
weil SQLite seine gemeinsame Sperre nicht setzen kann. Das Werkzeug erkennt das
und versucht es erneut mit `immutable=1`, was das Sperren komplett übergeht.
Das ist nur sicher, solange niemand sonst in den Katalog schreibt — und genau
das hat die Prüfung auf die Sperrdatei bereits festgestellt.

## Sperren

Lightroom legt `<Katalog>.lrcat.lock` an, solange ein Katalog geöffnet ist.
Existiert diese Datei, verweigert das Werkzeug den Dienst. `--ignore-lock` ist
für die forensische Untersuchung eines gesperrten Katalogs gedacht; für `apply`
sollte es nicht verwendet werden.

Übrig gebliebene `.lrcat-wal`- und `.lrcat-shm`-Dateien werden als Warnung
gemeldet. Sie sind für sich harmlos; den Katalog einmal in Lightroom zu öffnen
und zu schließen lässt sie ordentlich leeren.

## Idempotenz

Dieselbe Struktur zweimal anzuwenden muss folgenlos bleiben — und ist es. Beim
zweiten Lauf liegt jedes Foto bereits in seinem Zielordner und wird als
`bereits am Ziel` gemeldet.

Der knifflige Teil ist der Anker. Im Modus `in-place` wird die Struktur
unterhalb des tiefsten Ordners aufgebaut, der allen ausgewählten Fotos
gemeinsam ist. Nach einem ersten Lauf in Tagesordner *ist* dieser gemeinsame
Ordner unter Umständen selbst ein Tagesordner — ein naiver zweiter Lauf würde
also `2019-01-03/2019-01-03/` anlegen. Der Planer erkennt, dass der Anker
bereits auf das endet, was die Struktur rendert, und tritt entsprechend zurück.

## Prüfung

Nach dem Commit wird der Katalog erneut gelesen und für jede verschobene Datei
geprüft, ob der nun im Katalog beschriebene Pfad genau dem geplanten Ziel
entspricht und die Datei dort liegt. Probleme werden im Ergebnis aufgeführt und
mit Rückgabewert `4` gemeldet. Mit `--no-verify` abschaltbar, wozu es aber
selten einen Grund gibt.
