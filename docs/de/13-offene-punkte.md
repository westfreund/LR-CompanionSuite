# Offene Punkte und Fahrplan

**Revision r13.0.0 · Build-Datum 2026-08-23**

Eine ehrliche Aufstellung dessen, was nicht erledigt, nicht verifiziert oder
bewusst ausgelassen ist. Jeder Punkt ist ein Ansatzpunkt für die nächste
Sitzung.

## Noch nicht verifiziert

### O-1 · Die Referenzbibliothek ist migriert und von Lightroom angenommen ✔
Abgeschlossen am 22.08.2026. Der Katalog mit 9.452 Dateien / 337 GiB auf
`/Volumes/1TB-2` wurde in 152 Tagesordner umsortiert, und **Lightroom Classic
öffnet das Ergebnis, alle Bilder sind in ihrem neuen Ordner auswählbar**.

Unabhängig vom Werkzeug geprüft: alle 9.489 Dateien vorhanden mit unveränderter
Größe, `integrity_check` ok, `foreign_key_check` sauber, keine verwaisten
Ordner, keine falschen Pfadpräfixe, alle 9.452 Katalogpfade auflösbar, alle 32
virtuellen Kopien an ihrem Master, keine Speicherklassen-Drift über 272.962
Zeilen, Write-Ahead-Log auf null eingecheckpointet, und ein Hash über
`Adobe_images`, `Adobe_imageDevelopSettings`, `AgLibraryKeywordImage` und
`AgLibraryCollectionImage` identisch zur Kopie von vor dem Lauf. Ein erneuter
Plan meldet 0 zu verschieben und 9.452 bereits am Ziel.

Es brauchte drei Anläufe, und jeder Fehlschlag war mehr wert als der Erfolg:

1. Abbruch bei Datei 850 am AppleDouble-Defekt (r1.0.3). Der Rollback legte alle
   850 Dateien zurück, entfernte 152 Ordner und ließ den Katalog bitgleich — ein
   ungeplanter, aber aussagekräftiger Test des Rollback-Pfads an einer echten
   Bibliothek.
2. Durchgelaufen, aber Lightroom verweigerte das Öffnen und reparierte den
   Katalog wieder und wieder in eine byte-identische Datei. Ursache war der
   Speicherklassen-Defekt (r1.0.5): der ID-Zähler als TEXT statt REAL
   geschrieben. Alle Prüfungen des Werkzeugs waren grün, weil keine davon
   `typeof()` betrachtete.
3. Durchgelaufen und angenommen.

### O-2 · Ein migrierter Katalog wurde in Lightroom geöffnet ✔
Abgeschlossen am 22.08.2026 zusammen mit O-1. Zweimal bestätigt: zuerst an einer
korrigierten Kopie des abgelehnten Katalogs — ein Wert zurück auf REAL, sonst
nichts —, was die Diagnose bewies, und danach an der frisch migrierten
Bibliothek.

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

### O-7 · Mehrere Stammordner in einem Lauf ✔
Abgeschlossen in r3.0.0. Jeder Stammordner wird zu einem Scope mit eigenem
Anker, und alle werden in einer Transaktion und einem Journal abgearbeitet.
Über zwei physische Volumes geprüft: vier Dateien unter zwei verschiedenen
Stammordnern sortiert, alle Katalogpfade auflösbar, zweiter Lauf ohne
Arbeit.

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

## Zugesagt und zurückgestellt

Am 23.08.2026 gewünscht und bewusst bis nach dem zweiten Testlauf verschoben,
damit die Tests kein bewegliches Ziel haben. O-21, O-22 und O-24 wurden in
r5.0.0 vorgezogen, weil alle drei dem Masterkatalog-Lauf unmittelbar dienen.
Alles auf dieser Liste ist inzwischen geliefert; bei O-26 steht nur noch die
Wahl zwischen den sechs Entwürfen aus. Die ursprünglichen Anforderungen bleiben
unter jedem Punkt stehen, weil die Begründung mehr wert ist als der Haken.

### O-21 · Eine Seite zum Neuverknüpfen einer kopierten Bibliothek ✔ r5.0.0
Geliefert als [03-vorbereitung.md](03-vorbereitung.md) /
[before-you-start.md](../en/03-before-you-start.md), aus beiden Übersichten
verlinkt. Die ursprüngliche Anforderung folgt.

Ein Katalog merkt sich den **absoluten** Pfad seiner Stammordner. Kopiert man
eine Bibliothek auf ein anderes Laufwerk, benennt ein Volume um oder stellt aus
einer Sicherung wieder her, zeigt der Katalog weiterhin auf den alten Ort: Alle
Fotos gelten als fehlend, und dieses Werkzeug verweigert den Lauf (r4.0.1 nennt
die Ursache). Da vorher eine Kopie anzulegen genau das ist, was die
Sicherheitshinweise empfehlen, muss die Anleitung auch die Folge behandeln.

Gewünscht: eine eigene kurze Seite, verlinkt aus Installation, Bedienung und
Sicherheit, zweisprachig, mit dem Symptom, dem Lightroom-Weg (Rechtsklick auf
den Ordner, Fehlenden Ordner suchen) und der Alternative, das Volume wieder
umzubenennen. Dazu, wie man den vermerkten Pfad sieht (`lrfc folders KATALOG`),
damit man erkennt, was der Katalog erwartet.

### O-22 · Empfehlung, den Katalog vorher zu konvertieren ✔ r5.0.0
Geliefert als Abschnitt 2 derselben Seite. Die ursprüngliche Anforderung folgt.

Ein von einer älteren Lightroom-Classic-Fassung geschriebener Katalog lässt
sich in einer neueren erst nach Konvertierung öffnen. Mit einem nicht
konvertierten Katalog zu arbeiten hieße, in ein Schema zu schreiben, das das
installierte Lightroom noch gar nicht angenommen hat. In der Praxis beobachtet:
Eine wiederhergestellte Bibliothek hatte Schema 17.0.0 und wurde 18.0.0, sobald
Lightroom sie öffnete.

Gewünscht: die ausdrückliche Empfehlung, den Katalog einmal im installierten
Lightroom Classic zu öffnen — das verknüpft und konvertiert in einem Zug —,
bevor LR-FolderCraft läuft. Gehört neben O-21.

### O-23 · Beide Oberflächen sollen die Voraussetzungen nennen ✔ r9.0.0
Geliefert als `safety.preconditions()` samt Dialog, der angekreuzt und nicht
weggeklickt werden muss. Die ursprüngliche Anforderung folgt.

Gewünscht: Vor dem ersten Lauf einer Sitzung sollen TUI und GUI die drei
Voraussetzungen nennen — Lightroom geschlossen, Katalog einmal im installierten
Lightroom geöffnet, Sicherung vorhanden — und eine ausdrückliche Bestätigung
verlangen. Kein Dialog, den man reflexhaft wegklickt: Er soll zeigen, was
tatsächlich vorgefunden wurde (Schemaversion, ob alle Pfade auflösen, ob im
Backup-Verzeichnis eine frische Kopie liegt), damit die Bestätigung etwas
bedeutet.

Die Kommandozeile hat dafür den Vorprüfungsbericht; die beiden Oberflächen
zeigen ihn erst nach dem Planen.

### O-24 · Ein Verschiebeprotokoll neben der Bibliothek ✔ r5.0.0
Geliefert in `movelog.py`, gesteuert über `--no-move-log` und
`--move-log-dir`. Im `finally` des Laufs geschrieben, sodass auch ein
gescheiterter oder zurückgerollter Lauf festgehalten wird, und strikt
nicht-fatal. Die ursprüngliche Anforderung folgt.

Gewünscht: eine lesbare Aufzeichnung dessen, was ein Lauf getan hat, im Ordner
der Bibliothek selbst statt nur in `~/Library/Logs` — damit sie mitwandert,
wenn die Bibliothek umzieht oder archiviert wird, und damit man sie Monate
später findet, ohne zu wissen, wo das Werkzeug seine Logs ablegt.

Entwurf: `LR-FolderCraft_<Katalog>_<jjjj-mm-tt_HHMM>.log` neben der `.lrcat`,
mit Revision und Build-Datum, den Einstellungen, den Ordnerentscheidungen, je
einer Zeile pro verschobener Datei (von, nach, umbenannt), den Zählungen und
dem Ergebnis samt Backup- und Journalpfad. Das JSON-Lines-Journal bleibt, was
es ist — die maschinenlesbare Grundlage für das Rückgängigmachen; dies hier ist
das, was ein Mensch liest. Ort konfigurierbar und abschaltbar machen, denn ein
schreibgeschütztes oder volles Volume darf keinen Lauf scheitern lassen.

### O-25 · Eine Kurzbeschreibung in der grafischen Oberfläche ✔ r9.0.0
Geliefert als Zweckzeile oben im Fenster und Aktionen → Über. Die ursprüngliche
Anforderung folgt.

Das Fenster sagt nur über seine Titelzeile, was es ist. Wer es öffnet, ohne die
Dokumentation gelesen zu haben, findet keine Aussage darüber, was das Werkzeug
tut, was es anfasst und was nicht, und wo sein Sicherheitsnetz liegt.

Gewünscht: ein kompaktes „Über" aus dem Menü heraus — was LR-FolderCraft in
drei Sätzen tut, die Zusage, dass nur Ordnerzeilen und die Ordnerspalte der
Datei geschrieben werden, Revision und Build-Datum, die Lizenz und ein Verweis
auf das Repository. Dazu eine einzeilige Beschreibung im Fenster selbst, über
dem Katalogfeld, damit der Zweck sichtbar ist, ohne etwas zu öffnen.
Zweisprachig, aus der vorhandenen Tabelle in `gui/i18n.py`.

### O-26 · Ein Logo ✔ r10.0.0
Sechs Entwürfe, dann drei Varianten des gewählten; 6c wurde genommen. Die Marke
liegt als zwei Schnitte in `docs/images/brand/`, die Buchstaben gezeichnet statt
gesetzt, und erscheint im Fenstersymbol, im Über-Dialog und in beiden READMEs.
Die Entwürfe bleiben zur Dokumentation in `docs/images/logos/`. Die
ursprüngliche Anforderung folgt.

Das Projekt hat kein eigenes Zeichen: weder im Fenster noch in den READMEs,
noch als GitLab-Projektbild, noch als Favicon der Dokumentation.

Gewünscht: eine Handvoll unterschiedlicher Entwürfe zur Auswahl, als SVG, damit
sie skalieren und umfärbbar sind. Zu beachten: Es muss bei 16 px als Favicon
und Fenstersymbol ebenso lesbar sein wie groß; es muss auf hellem und dunklem
Grund funktionieren; und es sollte *Fotos in Ordner einsortieren* andeuten
statt eine beliebige Kamera zu zeigen. Nach der Auswahl: die Größen erzeugen,
die Fenstersymbol, GitLab-Profilbild und Dokumentation brauchen, und aus beiden
READMEs darauf verweisen.

## Ideen, keine Zusagen

### O-15 · GUI ✔
Abgeschlossen in r3.0.0: ein Qt-Frontend mit allen Einstellungen,
Entscheidungen je Ordner, nativer Zielordnerauswahl und Fortschrittsbalken.
`textual serve` bliebe ein günstiger Weg, die Textoberfläche aus der Ferne zu
bedienen, falls das je gewünscht ist.

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
