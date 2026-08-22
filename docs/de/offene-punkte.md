# Offene Punkte und Fahrplan

**Revision r1.0.1 · Build-Datum 2026-08-22**

Eine ehrliche Aufstellung dessen, was nicht erledigt, nicht verifiziert oder
bewusst ausgelassen ist. Jeder Punkt ist ein Ansatzpunkt für die nächste
Sitzung.

## Noch nicht verifiziert

### O-1 · Die echte Bibliothek wurde geplant, nie ausgeführt
Der Katalog mit 9.452 Dateien auf `/Volumes/1TB-2` hat einen sauberen Plan —
152 Tagesordner, 0 Konflikte, 0 Übersprungene, 32 mitgeführte virtuelle Kopien
—, der scharfe Lauf steht aber nach Absprache noch aus. **Nächster Schritt:**
`lrfc apply` ausführen, dann den Katalog in Lightroom Classic öffnen und das
Ordner-Bedienfeld prüfen.

### O-2 · Noch kein Ergebnis in Lightroom selbst geöffnet
Die bisherige Prüfung erfolgte auf Datenbank- und Dateisystemebene:
Integritätsprüfung, Fremdschlüsselprüfung, Gültigkeit des Ordnerbaums,
Pfadauflösung und ein unveränderter Hash über die Bild-, Entwicklungs-,
Stichwort- und Sammlungstabellen. Die visuelle Bestätigung in Lightroom ist der
verbleibende Schritt. **Nächster Schritt:** nach O-1.

### O-3 · Das Windows-Skript lief noch nie unter Windows
`install/install-windows.ps1` wurde sorgfältig geschrieben und strukturell
geprüft, es stand aber kein Windows-Rechner zur Verfügung. **Nächster
Schritt:** unter Windows 10/11 ausführen, danach dort `lrfc info` auf einen
Katalog.

### O-4 · Nur eine Katalogschemaversion getestet
Verifiziert gegen 18.0.0 (Lightroom Classic 14). 11.x–19.x werden mit Warnung
akzeptiert. **Nächster Schritt:** gegen einen älteren Katalog testen und
verifizierte Versionen in `VERIFIED_CATALOG_VERSIONS` ergänzen.

### O-5 · Cloud-synchronisierte Kataloge ungetestet
Die Synchronisationstabellen (`AgPendingOz*`) werden nicht angefasst und die
Foto-IDs ändern sich nicht — es sollte also gutgehen, ist aber unbelegt.
**Nächster Schritt:** mit Backup an einem synchronisierten Katalog testen und
das Ergebnis dokumentieren.

### O-6 · Netzlaufwerke ungetestet
SMB und NFS verhalten sich bei Sperren und atomarem Umbenennen anders.
**Nächster Schritt:** testen und eine Vorprüfungswarnung ergänzen, wenn ein
Netzpfad erkannt wird.

## Bekannte Grenzen

### O-7 · Ein Stammordner je Lauf
Umfasst eine Auswahl mehrere Stammordner, verweigert der Planer und bittet um
Eingrenzung. Mehrere Stammordner gleichzeitig bräuchten Anker je Stammordner
und ein durchdachteres Transaktionskonzept. **Behelf:** einen Lauf je
Stammordner.

### O-8 · Kein Fortsetzen nach Unterbrechung
Das Journal enthält genug Information zum Fortsetzen, implementiert ist aber
nur `undo`. Ein `lrfc resume JOURNAL`, das dort weitermacht, wo ein Lauf
stehen blieb, wäre bei sehr großen Bibliotheken nützlich. **Aufwand:** mittel;
die Daten liegen bereits vor.

### O-9 · Kein Umbenennen von Dateien als Funktion
Dateien werden nur umbenannt, um einen Konflikt aufzulösen. Umbenennen als
Ziel — etwa nach `{yyyy}-{mm}-{dd}_{camera}_{seq}` — ist eine naheliegende
Erweiterung, vervielfacht aber die Risikofläche und gehört in ein eigenes
Major-Release.

### O-10 · Kein Vergleich zweier Pläne
Zwei Pläne zu vergleichen („was hat sich seit gestern geändert?“) hülfe bei
stetig wachsenden Bibliotheken. Das Plan-JSON enthält bereits alles Nötige.

### O-11 · Grobe Fortschrittsanzeige
Konsole und TUI aktualisieren alle 25 Dateien. Für Umbenennungen genügt das,
für eine langsame Volume-übergreifende Kopie wäre Byte-Fortschritt je Datei
besser.

### O-12 · Kein paralleles Kopieren
Volume-übergreifende Übertragungen laufen sequenziell. Parallelität hülfe bei
schnellen SSDs und schadete bei Magnetplatten — sie muss also gemessen und
optional gemacht werden.

### O-13 · Leere Verzeichnisse werden nur für Quellordner entfernt
Verzeichnisse, die schon vor dem Lauf leer waren, bleiben unangetastet. Das ist
Absicht — Verzeichnisse zu löschen, die das Werkzeug nicht angelegt hat, ist
nicht seine Aufgabe —, kann aber einen leicht unaufgeräumten Baum
hinterlassen.

### O-14 · `--ignore-lock` ist eine geladene Waffe
Es existiert, um einen gesperrten Katalog zu untersuchen. Nichts hindert daran,
es an `apply` zu übergeben. Man könnte es auf lesende Befehle beschränken.

## Ideen, keine Zusagen

### O-15 · GUI
Die Schnittstelle ist vorbereitet, siehe
[entwicklung.md](entwicklung.md#die-gui-schnittstelle). Empfohlener erster
Schritt: `textual serve`, um die bestehende TUI im Browser
weiterzuverwenden, bevor man sich auf Qt festlegt.

### O-16 · Weitere Gruppierungskriterien
Kandidaten: ISO-Bereiche, Brennweitenbereiche, GPS-Ort (Stadt per Reverse
Geocoding — braucht eine Datenquelle), Stichwort, Farbmarkierung, Bewertung,
Importsitzung, Teilmuster von `{orig_folder}`.

### O-17 · Undo-Historie / mehrere Journale
Ein `lrfc history`, das vergangene Läufe mit ihren Journalen auflistet, damit
sich auch der vorletzte Lauf zurücknehmen lässt.

### O-18 · Katalog-Gesundheitsbericht
`lrfc doctor`: fehlende Dateien, doppelte Namen, Ordner ohne Zeilen, Fotos
außerhalb jedes Stammordners, Aufnahmezeiten weit in der Zukunft.

### O-19 · Vorlagen teilen
Profile sind bereits JSON. Eine kleine Sammlung gemeinschaftlicher Strukturen
wäre leicht umsetzbar.

### O-20 · Weitere Sprachen über EN/DE hinaus
`rules.py` hält Monats- und Wochentagsnamen in einem nach Sprache
geschlüsselten Dictionary, und `Check`/`TokenSpec` tragen beide Texte inline.
Eine dritte Sprache hieße, diese Strukturen zu erweitern — die Architektur ist
bereit, die Texte liegen aber noch nicht in `.po`-Dateien, was dann nötig
würde.

## Beantwortete Fragen

Festgehalten, damit die Begründung nicht verloren geht.

| Frage | Entscheidung |
| --- | --- |
| Wo entstehen die neuen Ordner? | Beide Modi implementiert; `in-place` ist Standard. |
| Welches TUI-Framework? | Textual — Widgets, Maus und ein Weg zu Textual Web. |
| Python-Basis? | 3.9, damit macOS' eigenes Python ohne Installation genügt. |
| Wie weit beim Beispielkatalog gehen? | Nur Analyse und Trockenlauf; der scharfe Lauf bleibt beim Anwender. |
| Umbenennen oder überspringen bei Konflikt? | Standardmäßig umbenennen, mit nachgeführtem Katalog, damit nichts verloren geht. Jede Umbenennung steht im Plan, im Bericht und im Journal. |
| Ist `file-mtime` eine gute Standardquelle? | Nein. Es ist meist das Kopierdatum und würde Fotos stillschweigend falsch einsortieren. Nur bewusst zuschaltbar. |

## Offene Fragen

**F-1 · Soll `apply` `--ignore-lock` verweigern?** Sicherer, nimmt aber den
Notausgang bei einer verwaisten Sperrdatei nach einem Lightroom-Absturz.
Vielleicht ein zusätzliches `--i-know-what-i-am-doing` verlangen.

**F-2 · Soll der `_unsorted`-Ordner innerhalb oder neben dem Anker liegen?**
Derzeit innerhalb, neben den Tagesordnern. Daneben hielte den sortierten Baum
sauberer.

**F-3 · Soll `apply` standardmäßig eine Ergebnisdatei schreiben?** Derzeit
wird der Plan ins Berichtsverzeichnis geschrieben. Eine maschinenlesbare
*Ergebnis*-Datei könnte für Automatisierung nützlich sein.

**F-4 · Wie soll ein Resume „unterbrochen“ von „fertig“ unterscheiden?** Das
Journal hat `run-end`, aber ein harter Stromausfall hinterlässt keines. Das
Fehlen von `run-end` bei vorhandenem `catalog-commit` ist für genau einen
Augenblick mehrdeutig.
