# FAQ

**Revision r10.0.0 · Build-Datum 2026-08-23**

## Sicherheit und Daten

### Gehen meine Entwicklungseinstellungen verloren?

Nein. Bearbeitungen hängen an der Zeilen-ID des Fotos, und die ändert sich nie.
Geändert wird nur, auf welchen Ordner eine Datei zeigt. Ein Test belegt das: Er
bildet vor und nach einem Lauf einen Hash über `Adobe_images`,
`Adobe_imageDevelopSettings`, `AgLibraryKeywordImage` und
`AgLibraryCollectionImage` und verlangt, dass er identisch ist.

### Was passiert mit meinen virtuellen Kopien?

Sie folgen automatisch. Eine virtuelle Kopie ist eine eigene
`Adobe_images`-Zeile, die auf *dieselbe* Dateizeile zeigt — verschiebt man die
Datei, kommen alle Kopien mit. Der Plan meldet, wie viele betroffen sind.

### Und Sammlungen, Stichwörter, Bewertungen, Markierungen, Stapel?

Bleiben alle erhalten, aus demselben Grund. Ebenso Vorschauen und
Smart-Vorschauen, die über die Bild-UUID statt über den Pfad adressiert werden.

### Brauche ich ein Backup, wenn das Werkzeug eines anlegt?

Ja. Das Backup des Werkzeugs umfasst den Katalog, nicht Ihre Fotografien, und
es ist nur so gut wie das Laufwerk, auf dem es liegt. Ein eigenes Backup
vorhalten.

### Kann ich einen Lauf rückgängig machen?

Ja: `lrfc undo <Journal>`. Die Dateien wandern zurück und der Katalog wird aus
dem Backup dieses Laufs wiederhergestellt. Der Journalpfad wird am Ende jedes
Laufs ausgegeben.

### Was, wenn mitten im Lauf der Strom ausfällt?

Der Katalog wird *zuletzt* bestätigt. Eine Unterbrechung lässt die Datenbank
also fast immer unberührt, während einige Dateien schon verschoben sind. Das
Journal zeigt genau, wie weit es kam, und `lrfc undo` legt die Dateien zurück.
Siehe [06-sicherheit.md](06-sicherheit.md#der-lauf-wurde-unterbrochen-stromausfall-erzwungenes-beenden).

### Kann es eines meiner Fotos überschreiben?

Nein. Jede Bewegung prüft zuvor das Ziel und weigert sich, über eine vorhandene
Datei zu schreiben — auch über eine, die erst nach der Planung entstanden ist.

## Anwendung

### Muss Lightroom geschlossen sein?

Ja. Das Werkzeug verweigert den Start, solange Lightrooms
`.lrcat.lock`-Datei existiert. Lightroom Classic beenden, nicht nur
minimieren.

### Wie lange dauert das?

Auf einem Volume: Sekunden. Eine Datei innerhalb eines Dateisystems zu
verschieben ist ein Umbenennen, es werden keine Daten kopiert. Eine Bibliothek
mit 9.452 Dateien und 337 GiB wird in rund zwei Sekunden geplant und fast
ebenso schnell verschoben.

Über Volume-Grenzen hinweg ist es eine echte Kopie mit Prüfsumme und läuft mit
Laufwerksgeschwindigkeit.

### Kann ich es mit einer anderen Struktur erneut laufen lassen?

Ja, beliebig oft; jeder Lauf sortiert vom aktuellen Stand aus neu. Dieselbe
Struktur zweimal anzuwenden bewirkt nichts — der zweite Lauf meldet alles als
bereits am Ziel.

### Was ist mit Fotos ohne Aufnahmedatum?

Standardmäßig kommen sie in einen Ordner `_unsorted` neben die Tagesordner. Mit
`--on-missing-date skip` bleiben sie liegen, mit `abort` wird die Planung
verweigert. Der Ordnername lässt sich mit `--unsorted-folder` ändern.

### Kann ich nur einen Teil des Katalogs sortieren?

Ja: `--root-folder ID`, `--folder ID` (wiederholbar), `--include-ext`,
`--exclude-ext`. Die IDs liefert `lrfc folders KATALOG`.

### Kann ich je Kamera *und* je Tag einen Ordner haben?

Ja, genau dafür sind mehrere Ebenen da:

```bash
lrfc apply KATALOG -s '{camera_slug}/{yyyy}-{mm}-{dd}'   # Kamera, dann Tag
lrfc apply KATALOG -s '{yyyy}-{mm}-{dd}/{camera_slug}'   # Tag, dann Kamera
```

### Kommen XMP-Sidecars mit?

Ja, sowohl `IMG_1234.xmp` als auch `IMG_1234.CR2.xmp`. Erzwingt ein Konflikt
eine Umbenennung des Fotos, wird die Sidecar-Datei passend mit umbenannt.
Abschaltbar mit `--no-sidecars`.

### Funktioniert es mit einem Katalog, der mit Lightroom (Cloud) synchronisiert?

Die Synchronisationsdaten liegen in eigenen Tabellen, die dieses Werkzeug nicht
anfasst, und die Foto-IDs ändern sich nicht — ein synchronisierter Katalog
sollte also unproblematisch sein. Getestet wurde das **nicht**. Backup anlegen
und den Synchronisationsstand danach prüfen.

### Mehrere Stammordner oder Laufwerke?

Jeder Lauf arbeitet auf einem Stammordner. Umfasst die Auswahl mehrere, weist
der Planer darauf hin und bittet um Eingrenzung mit `--root-folder`. Also einen
Lauf je Stammordner.

### In der GUI ist eine Tabelle abgeschnitten oder eine Einstellung fehlt

Der Bereich ist zu klein, nicht leer. Zwischen den vier großen Bereichen —
Einstellungen, „Braucht Ihre Antwort", „Vorgefundene Ordner" und Protokoll —
liegt am **unteren Rand** jeweils ein **Teiler**, eine dünne waagerechte Linie.
Ziehen gibt dem Bereich darüber mehr Platz; ganz zuziehen blendet ihn aus, und
Aufziehen holt ihn zurück. Der Mauszeiger wird dort zum Doppelpfeil.

Der Bereich Einstellungen scrollt zusätzlich in sich selbst — auf einem kleinen
Bildschirm liegen Ziel, Ordnerstruktur und Optionen zunächst unterhalb des
sichtbaren Randes. Die eingestellten Größen werden für den nächsten Start
gemerkt. Siehe [04-bedienung.md](04-bedienung.md).

### Ich kann in der GUI keinen Zielordner angeben

Bis r6.1.0 war das Feld gesperrt, solange oben nicht „In einen neuen Ordner"
gewählt war — ein graues Feld neben einer grauen Schaltfläche, ohne Hinweis,
welcher Knopf gemeint ist. Ab r7.0.0 sind beide immer bedienbar, und einen
Ordner zu benennen wählt den Modus gleich mit.

### Kann ich Fotos auf ein ganz anderes Laufwerk verschieben?

Ja, mit `--placement new-tree --target-root /Volumes/Anderes/Sortiert`. Die
Dateien werden kopiert, per Prüfsumme verifiziert und erst dann an der Quelle
entfernt; das Ziel wird als zusätzlicher Stammordner im Katalog registriert.

## Strukturen

### Warum liegt mein Dezemberfoto in einem Wochenordner des Folgejahres?

Weil ISO 8601 es so vorsieht: Eine Woche gehört zu dem Jahr, in dem ihr
Donnerstag liegt, der 30. Dezember 2019 ist also Woche 1 von 2020.
`{iso_week}` deshalb immer mit `{iso_year}` kombinieren, nie mit `{yyyy}`.
Siehe [05-strukturen.md](05-strukturen.md#iso-kalenderwochen).

### Bekomme ich deutsche Monatsnamen?

Mit `--lang de`, in der TUI mit `F1`. `{month_name}` liefert dann `Januar`.

### Welches Datum wird verwendet — Dateidatum oder EXIF-Datum?

Lightrooms Aufnahmezeit, also das EXIF-Datum, sofern Sie es nicht im
Metadaten-Bedienfeld korrigiert haben — dann gewinnt Ihre Korrektur. Das
Änderungsdatum der Datei wird standardmäßig **nicht** verwendet: Es ist meist
das Kopierdatum und würde Fotos stillschweigend falsch einsortieren. Bewusst
zuschaltbar mit `--date-source capture --date-source file-mtime`.

### Wo entstehen die neuen Ordner?

Standardmäßig innerhalb des Ordners, in dem die Fotos jetzt liegen. Aus
`raw2019/` wird `raw2019/2019-01-03/`, `raw2019/2019-01-06/` und so fort. Für
einen anderen Elternordner `--anchor-folder ID`, für einen eigenen Baum
`--placement new-tree`.

## Technisches

### Warum geht das nicht als Lightroom-Plug-in?

Das Lightroom-Lua-SDK kann Fotos und Metadaten lesen, bietet aber keine
Schnittstelle, um ein Foto in einen anderen Ordner zu verschieben. Kein
Plug-in kann das. Den Katalog bei geschlossenem Lightroom direkt zu bearbeiten
ist der einzige automatisierbare Weg.

### Ist das Bearbeiten des Katalogs von Adobe unterstützt?

Nein. Das Katalogformat ist nicht dokumentiert. Dieses Werkzeug beschränkt sich
auf vier seit langem stabile Tabellen, nutzt Lightrooms eigenen ID-Zähler und
folgt dessen Pfadkonventionen — es bleibt aber Reverse Engineering, und genau
deshalb gibt es die Sicherheitsmechanik. Nach dem ersten Lauf das Ergebnis in
Lightroom prüfen.

### Welche Katalogversionen funktionieren?

Verifiziert gegen Schema 18.0.0 (Lightroom Classic 14). Die Schemata 11.x–19.x
werden akzeptiert, mit Warnung, sofern nicht ausdrücklich verifiziert. Ältere
brauchen `--allow-unsupported-catalog`.

### Warum Python 3.9 und nicht etwas Neueres?

Damit es mit dem Python läuft, das macOS ohnehin mitbringt. Für die meisten
Anwender entfällt damit ein Installationsschritt.

### Brauche ich die TUI?

Nein. `pip install lr-foldercraft` ohne Extras hat überhaupt keine
Abhängigkeiten; die CLI kann alles. Textual wird nur für `lrfc tui` gebraucht.

### Installiert, aber das Terminal sagt `lrfc: command not found`

Der Starter liegt in `~/.local/bin`, und macOS nimmt dieses Verzeichnis nicht
von selbst in den PATH auf. Seit r3.0.1 erledigt das Installationsskript das —
aber **ein bereits geöffnetes Terminalfenster behält den PATH, mit dem es
gestartet ist**. Neues Fenster öffnen, oder `source ~/.zshrc` ausführen.

So prüfen Sie es nach:

```bash
ls -l ~/.local/bin/lrfc          # ist der Starter da?
~/.local/bin/lrfc --version      # funktioniert er über den vollen Pfad?
echo $PATH | tr ':' '\n'         # ist ~/.local/bin aufgeführt?
```

Funktioniert er über den vollen Pfad, aber nicht über den Namen, fehlt nur der
PATH. Diese Zeile in `~/.zshrc` eintragen und ein neues Fenster öffnen:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### `lrfc gui` meldet, PySide6 fehle

Die grafische Oberfläche ist ein optionales Extra von rund 100 MB, das
Installationsskript nimmt sie deshalb nur auf Wunsch mit. Seit r4.0.0 fragt es
danach, wenn es in einem Terminal läuft; davor musste man `--with-gui` kennen,
und die Liste der nächsten Schritte bewarb `lrfc gui` unabhängig davon, ob es
installiert war.

Zu einer bestehenden Installation hinzufügen — die Umgebung wird
weiterverwendet, das dauert Sekunden:

```bash
./install/install-macos.sh --with-gui
```

Oder die gesamte Installation prüfen und reparieren:

```bash
./install/install-macos.sh --check
```

### Wo liegen Logdateien, Profile und Backups?

Siehe [02-installation.md](02-installation.md#wo-was-abgelegt-wird). Überschreibbar
mit `LRFC_CONFIG_DIR`, `LRFC_LOG_DIR`, `LRFC_BACKUP_DIR`, `LRFC_REPORT_DIR`.

### Was sind `.lrcat-wal` und `.lrcat-shm`? Soll ich die löschen?

**Nein — ein nicht leeres `.lrcat-wal` niemals löschen.** Lightroom-Kataloge
laufen im WAL-Modus, und diese Datei enthält bestätigte Transaktionen, die noch
nicht in die `.lrcat` zurückgeschrieben wurden. Sie zu löschen verwirft diese
Änderungen. LR-FolderCraft überträgt das WAL beim Commit, nach einem
erfolgreichen Lauf steht der Katalog also für sich. Ein `.lrcat-journal`
bedeutet eine unterbrochene Transaktion; auch das nicht löschen — Katalog in
Lightroom öffnen und schließen und SQLite die Wiederherstellung überlassen.

### Es meldet „unable to open database file“ — die Datei ist aber da.

Das war ein reales Symptom auf exFAT-Laufwerken, die das Sperren nicht
unterstützen, das SQLite für den Lesezugriff benötigt. Das Werkzeug erkennt das
und versucht es mit `immutable=1` erneut. Tritt es weiterhin auf, ist die Datei
tatsächlich nicht lesbar — Rechte prüfen und ob das Laufwerk schreibgeschützt
eingebunden ist.

### Lässt es sich skripten?

Ja. Jeder Befehl hat definierte Rückgabewerte, `plan --json` liefert den
kompletten Plan, und `apply --yes` überspringt die Rückfrage. Profile halten
lange Optionslisten aus den Skripten heraus.
