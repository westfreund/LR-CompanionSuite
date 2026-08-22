# Sicherheit und Wiederherstellung

**Revision r3.0.0 · Build-Datum 2026-08-22**

> Dieses Werkzeug bearbeitet die Lightroom-Katalogdatenbank und verschiebt Ihre
> Fotografien. Es ist sorgfältig gebaut und getestet, aber: **Halten Sie vor
> dem ersten scharfen Lauf ein unabhängiges, geprüftes Backup von Katalog und
> Bildern vor.**

## Vor dem Start

1. **Lightroom Classic beenden.** Nicht minimieren — beenden.
2. **Katalog selbst sichern**, zusätzlich zu dem, was das Werkzeug tut. In
   Lightroom: `Datei ▸ Katalog sichern…`, oder einfach die `.lrcat`-Datei
   kopieren.
3. **Fotos sichern**, oder wenigstens bestätigen, dass das vorhandene Backup
   gelaufen ist.
4. **Zuerst an einer Kopie ausprobieren.** Katalog und ein paar hundert Bilder
   an einen Testort kopieren, dort den ganzen Vorgang durchspielen und das
   Ergebnis in Lightroom öffnen.
5. **`plan` laufen lassen und lesen.** Besonders die Zielordnerliste und die
   Warnungen.

## Die sieben Ebenen

### 1. Vorprüfungen

Bevor irgendetwas geschrieben wird:

| Prüfung | Blockiert den Lauf? |
| --- | --- |
| `lightroom-closed` — keine `.lrcat.lock`-Datei | ja |
| `catalog-writable` — Datei existiert und ist beschreibbar | ja |
| `catalog-side-files` — unterbrochenes `-journal` | Warnung |
| `id-counter-type` — Katalog durch LR-FolderCraft 1.0.0–1.0.4 beschaedigt | Warnung |
| `target-writable` — der Zielort ist beschreibbar | ja |
| `free-space` — 105 % des Volume-übergreifenden Datenvolumens | ja |
| `backup-space` — Platz für das Katalog-Backup | ja |
| `work-present` — gibt es überhaupt etwas zu tun | Warnung |
| `missing-sources` — Katalogeinträge ohne Datei auf der Platte | Warnung |

### 2. Geprüftes Katalog-Backup

Der Katalog wird unter einem Zeitstempelnamen ins Backup-Verzeichnis kopiert,
und beide Kopien werden per SHA-256 verglichen. Weichen sie ab, bricht der Lauf
sofort ab.

```
~/Library/Application Support/LR-FolderCraft/backups/2019-20260822-162631.lrcat
```

Backups auf einen anderen Datenträger als den Katalog legen:

```bash
export LRFC_BACKUP_DIR=/Volumes/Backup/lrfc
```

`--no-backup` existiert, aber ein Lauf ohne Backup lässt sich nicht mit
`lrfc undo` zurücknehmen. Das ist es nicht wert.

### 3. Vorbereitete Katalogtransaktion

Jede Katalogänderung geschieht in einer Transaktion, die erst **bestätigt**
wird, wenn alle Dateien erfolgreich verschoben sind. Sie zu verwerfen kostet
nichts und lässt die Datenbankdatei bitgleich zurück.

### 4. Journalisierte Verschiebungen

Jede Bewegung wird protokolliert, geflusht und per `fsync` gesichert, *bevor*
sie versucht wird. Siehe [funktionsweise.md](funktionsweise.md#das-journal).

### 5. Automatischer Rollback

Scheitert eine Bewegung — volle Platte, Rechte, abgezogenes Laufwerk —, dann:

1. wird die Katalogtransaktion zurückgerollt,
2. wandert jede bereits verschobene Datei an ihren Ursprungsort zurück,
3. werden die angelegten Verzeichnisse entfernt,
4. wird all das im Journal festgehalten,
5. wird berichtet, was wiederhergestellt wurde.

Abgedeckt durch einen Test, der bei Datei 4 von 6 einen Fehler einschleust und
prüft, dass Katalog und Dateisystem exakt in den Ausgangszustand zurückkehren.

### 6. Nie überschreiben

`_move_file` weigert sich, auf einen bereits existierenden Pfad zu schreiben —
selbst wenn der Planer diese Datei nicht gesehen hat. Konflikte werden durch
Umbenennen (mit nachgeführtem Katalog) oder Überspringen gelöst, nie durch
Überschreiben.

### 7. Prüfung

Nach dem Commit wird der Katalogpfad jeder verschobenen Datei mit der Realität
verglichen. Probleme werden aufgeführt und mit Rückgabewert `4` gemeldet.

## `.lrcat-wal` niemals löschen

Lightroom-Kataloge laufen im **WAL-Modus**. `<Katalog>.lrcat-wal` und
`<Katalog>.lrcat-shm` sind gewöhnliche Arbeitsdateien, keine Überbleibsel: Das
WAL enthält bestätigte Transaktionen, die noch nicht in die `.lrcat`-Datei
zurückgeschrieben wurden. Ein nicht leeres Write-Ahead-Log zu löschen
**verwirft diese Transaktionen**.

LR-FolderCraft überträgt das WAL beim Commit in den Katalog, nach einem
erfolgreichen Lauf steht die `.lrcat` also für sich. Sollten Sie doch einmal
ein nicht leeres `-wal` vorfinden, öffnen und schließen Sie den Katalog einmal
in Lightroom, statt etwas zu entfernen.

Eine Datei `<Katalog>.lrcat-journal` ist etwas anderes: Sie bedeutet, dass eine
Rollback-Journal-Transaktion unterbrochen wurde. Auch sie nicht löschen —
SQLite macht damit die unvollständige Änderung rückgängig.

## Wiederherstellung

### Der Lauf ist gescheitert und hat sich selbst zurückgerollt

Nichts zu tun. Katalog und Dateien sind wie zuvor. Log lesen, Ursache beheben,
erneut starten.

### Der Lauf war erfolgreich, soll aber rückgängig gemacht werden

```bash
lrfc undo /pfad/zu/<katalog>-<zeitstempel>.lrfc-journal.jsonl
```

Die Dateien wandern zurück, leere Verzeichnisse werden entfernt, und der
Katalog wird aus dem Backup dieses Laufs wiederhergestellt. Der Journalpfad
wird am Ende jedes Laufs ausgegeben.

### Der Lauf wurde unterbrochen (Stromausfall, erzwungenes Beenden)

Weil der Katalog zuletzt bestätigt wird, lässt eine Unterbrechung fast immer
den Katalog unverändert, während einige Dateien bereits verschoben sind.

1. **Lightroom noch nicht öffnen.**
2. Ins Journal sehen — das letzte `move-done` zeigt, wie weit es kam.
3. Fehlt eine `catalog-commit`-Zeile, ist der Katalog unverändert. Mit
   `lrfc undo JOURNAL` die Dateien zurücklegen und neu beginnen.
4. Ist `catalog-commit` vorhanden, war der Lauf im Wesentlichen abgeschlossen;
   mit `lrfc plan` den Zustand bestätigen und den Bericht prüfen.

### Lightroom zeigt Fotos als fehlend an

Dann weichen Katalog und Platte voneinander ab. Das Backup dieses Laufs
zurückspielen:

```bash
cp ~/Library/Application\ Support/LR-FolderCraft/backups/<name>-<stempel>.lrcat /pfad/zu/ihrem.lrcat
```

Danach `lrfc plan`, um den aktuellen Stand zu sehen, bevor es erneut losgeht.

Alternativ lässt sich in Lightroom neu verknüpfen: Rechtsklick auf den Ordner
im Ordner-Bedienfeld, **Fehlenden Ordner suchen…** und den neuen Ort angeben.
Das funktioniert, aber das Zurückspielen des Backups ist sauberer.

### Der Katalog ist beschädigt

Backup zurückspielen. Wurde keines angelegt: Lightrooms eigene Backups liegen
in `<Katalogordner>/Backups/`; das neueste öffnen und Lightroom die Integrität
prüfen lassen.

## Was das Werkzeug nicht tut

- Es läuft nicht, solange Lightroom den Katalog geöffnet hat.
- Es überschreibt keine vorhandene Datei.
- Es fasst weder `Adobe_images` noch irgendeine Entwicklungs-, Stichwort- oder
  Sammlungstabelle an.
- Es löscht nie ein Foto. Der einzige Codepfad, der eine Bilddatei entfernt,
  ist das Löschen der Quelle nach einer *verifizierten* Volume-übergreifenden
  Kopie.
- Es löscht keine Stammordnerzeile.
- Es schreibt bei `info`, `folders` und `plan` überhaupt nichts.

## Ein Problem melden

Beilegen:

1. die Logdatei (`~/Library/Logs/LR-FolderCraft/`), idealerweise aus einem
   `--debug`-Lauf,
2. den Plan als JSON (`lrfc plan ... --json > plan.json`),
3. das Journal, falls ein Lauf begonnen hatte,
4. `lrfc --version` und die Version von Lightroom Classic.

Den Katalog selbst bitte nicht mitschicken — er enthält die Pfade all Ihrer
Bilder.
