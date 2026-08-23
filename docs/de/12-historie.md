# Projekthistorie

**Revision r8.0.1 · Build-Datum 2026-08-23**

Der [CHANGELOG](../../CHANGELOG.md) sagt, was sich in jeder Revision geändert
hat. Dieses Dokument sagt **warum**, und was dazwischen geschah: die getroffenen
Entscheidungen, die Tests an echten Bibliotheken und die vier Gelegenheiten, bei
denen das Werkzeug auf eine Weise falsch lag, die zählte.

Es ist für den geschrieben, der das Projekt später aufnimmt — einschließlich
einer künftigen Fassung seiner eigenen Autoren — denn die Begründung einer
Fehlerbehebung ist mehr wert als die Behebung selbst, und nichts davon lässt
sich aus dem Code zurückgewinnen.

## Wie dieses Dokument entstand, und wofür es taugt

Es wurde **am 23.08.2026 rückwirkend** geschrieben, nicht begleitend geführt.
Einträge ab diesem Datum entstehen begleitend zur Arbeit.

Dieser Unterschied zählt, deshalb genau, worauf es fußt:

| Teil | Quelle | Belastbar? |
| --- | --- | --- |
| Daten, Reihenfolge, was wann geändert wurde | Commit-Historie und Tags | Ja — maschinell festgehalten |
| Was jede Revision enthält | [CHANGELOG.md](../../CHANGELOG.md) | Ja — seinerzeit geschrieben |
| Testergebnisse und ihre Zahlen | Lauf-Ausgaben, in den Commits zitiert | Ja |
| Begründungen, Alternativen, Gelerntes | Aus dem Bestand rekonstruiert | Die Darstellung ist wahrheitsgetreu, aber im Nachhinein verfasst |

Es ist also eine Ergänzung zur Änderungshistorie, kein Ersatz. **Um eine
einzelne Änderung nachzuverfolgen**, nehmen Sie die Werkzeuge, die sie exakt
festhalten:

```bash
git log --oneline --reverse          # jeder Schritt, der Reihe nach
git show v5.0.0                      # was eine Revision war
git log -p -- src/lrfoldercraft/planner.py    # das ganze Leben einer Datei
```

Der CHANGELOG listet Releases neueste zuerst. Dieses Dokument liest sich
**vorwärts**, ältestes zuerst, weil es als Erzählung gedacht ist und nicht zum
Nachschlagen.

---

## 22.08.2026 — der Auftrag

Andreas Freund bat um ein Werkzeug, das einen Lightroom-Classic-Ordnerbaum
umsortiert — nach Aufnahmedatum, Kamera, Kalenderwoche, in frei kombinierbaren
Ebenen — **ohne die Katalogverbindung zu verlieren**. Entwicklungseinstellungen,
virtuelle Kopien und Sammlungen mussten überleben.

Zu Beginn getroffene Entscheidungen, die alle weiterhin gelten:

| Entscheidung | Warum |
| --- | --- |
| Die Katalogdatenbank direkt bearbeiten | Es gibt keine Alternative. Das Lua-SDK kann ein Foto nicht zwischen Ordnern verschieben; der Finder kann Dateien verschieben, lässt aber jedes Foto als fehlend zurück; das Ziehen im Ordner-Bedienfeld ist korrekt, aber Handarbeit. |
| Kein Kernmodul weiß von einer Oberfläche | Damit Kommandozeile, Text- und grafische Oberfläche drei dünne Aufsätze über denselben drei Aufrufen sind — und eine vierte nichts kostet. |
| Jede Feature-Erweiterung ist eine Hauptversion | Regel des Auftraggebers. Sie lässt die Revisionsnummer sagen, *wie viel sich geändert hat*, statt wie sorgfältig nummeriert wurde. |
| Doppellizenz GPL v3 und MIT | Anforderung des Auftraggebers. |
| Alles auf Englisch und Deutsch dokumentiert | Anforderung des Auftraggebers. Beide Bäume sind vollständig, nicht einer bei Bedarf übersetzt. |
| Jeden Zwischenstand committen und pushen | Anforderung des Auftraggebers — und sie zahlte sich aus: der Zähler-Defekt unten wurde durch Vergleich getaggter Revisionen diagnostiziert. |

### r1.0.0 — der Kern

Katalog-Leser und -Schreiber, Planer, Ausführung, Journal, Vorabprüfungen, CLI.
Die Schreibfläche wurde auf fünf Anweisungen gegen vier Tabellen festgelegt und
ist seither nicht gewachsen; ein Test hält das fest.

---

## 22.08.2026, nachmittags — die erste echte Bibliothek

Testbibliothek: `2019.lrcat`, 9.489 Fotos, 337 GiB, auf einer externen
exFAT-Platte. Auf Initiative des Auftraggebers wurde vorher eine vollständige
Kopie angelegt.

**Der erste Echtlauf brach bei Datei 850 ab.** Ursache: AppleDouble-Begleiter
unter macOS. Auf exFAT verschiebt der Kernel `._X` beim Umbenennen zusammen mit
`X`, und das Werkzeug verschob es ein zweites Mal — auf eine Datei, die schon
dort lag.

Das ging dann **zweimal schief**:

- **r1.0.1** verschob `._X` ausdrücklich. Genau diese Änderung verursachte den
  Abbruch.
- **r1.0.3** maß nach, was der Kernel auf exFAT tatsächlich tut, und machte das
  Verhalten plattformabhängig: unter macOS den Begleiter in Ruhe lassen; sonst
  ist `._X` eine gewöhnliche Datei, die ein Umbenennen zurücklässt und die
  mitgeführt werden muss.

Die im generischen Prompt festgehaltene Lehre: *Erst messen, was die Plattform
tut, dann dafür kompensieren.*

**r1.0.2** reparierte einen Rückfallpfad, der nie gelaufen war.
`sqlite3.connect()` arbeitet verzögert — die `mode=ro`-Verbindung, die exFAT
nicht unterstützt, scheiterte erst bei der ersten Abfrage, und da war der
`immutable=1`-Rückfall längst übersprungen. Behoben mit einer Prüfabfrage.

### r1.0.4 — gefährlicher Rat, zweimal befolgt

Die Vorabprüfung nannte `.lrcat-wal` und `.lrcat-shm` „veraltete Nebendateien",
die zu entfernen seien. Das ist falsch: ein nicht leeres Write-Ahead-Log enthält
festgeschriebene Transaktionen. Das Werkzeug sagte es, und sein eigener Autor
handelte zweimal danach. Prüfung und Dokumentation wurden korrigiert, und die
FAQ sagt jetzt klar, dass ein nicht leeres WAL niemals gelöscht werden darf.

---

## 22.08.2026, abends — Lightroom verweigert den Katalog

Nach einer Migration, die Erfolg meldete und die Prüfung bestand, **öffnete
Lightroom den Katalog nicht**: „kann aufgrund eines unerwarteten Fehlers nicht
geöffnet werden."

Die Diagnose gelang durch drei Versuche des Auftraggebers:

| | Aufbau | Ergebnis |
| --- | --- | --- |
| Test A | Migrierter Katalog, auf APFS kopiert | Lightroom versucht zu reparieren, öffnet nicht |
| Test B | Originalkatalog auf exFAT | Öffnet, findet aber keine Bilder |
| Test C | Migrierter Katalog, ein Wert zurück nach REAL gecastet | **Öffnet, alle Bilder selektierbar** |

Test C benannte die Ursache exakt. `Adobe_variablesTable.Adobe_entityIDCounter`
war als **TEXT** statt als **REAL** geschrieben worden. SQLite speichert eine
Zahl in einer Spalte ohne strengen Typ bereitwillig als Text; Lightroom nicht.
Ein Wert in einer Zeile, in einer Tabelle, die mit Ordnern nichts zu tun hat,
machte den ganzen Katalog unöffenbar.

**r1.0.5** liest den gespeicherten Typ vor dem Schreiben, schreibt in derselben
Speicherklasse zurück und prüft danach, dass sie sich nicht geändert hat — und
bricht ab, wenn doch. Zwei Tests bewachen das: einer den Zähler, einer die
Zusicherung, dass ein ganzer Lauf nirgends die Speicherklasse einer bestehenden
Zeile ändert.

**r1.0.6** ergänzte die Erkennung bereits durch r1.0.0–r1.0.4 beschädigter
Kataloge, damit eine betroffene Bibliothek benannt wird statt nur zu scheitern.

Zwei weitere Funde aus derselben Episode:

- **Die Prüfung war blind.** Sie las mit `immutable=1`, was das Write-Ahead-Log
  ignoriert — sie bestätigte also eine Sicht, die Lightroom nie zu sehen bekommt.
- **Die Tests schrieben in das echte Konfigurationsverzeichnis des Benutzers.**
  Eine autouse-Fixture lenkt jetzt jeden Benutzerpfad um.

### Die Migration, wiederholt und geprüft

Mit r1.0.5 stellte der Auftraggeber aus der Kopie ein frisches Original her, und
der Lauf wurde wiederholt. Danach wurde unabhängig geprüft: Integritätsprüfung,
Fremdschlüssel, Ordnerbaum, jeder Pfad, Speicherklassen-Drift über 272.962
Zeilen, ein Hash über die Entwicklungs-, Stichwort- und Sammlungstabellen, und
das WAL ausgecheckpointet.

**Lightroom öffnete ihn, und die Bilder waren in ihren neuen Ordnern
selektierbar.**

---

## 22.08.2026, nachts — wie eine gewachsene Bibliothek wirklich aussieht

Die nächste Anforderung: echte Bibliotheken haben Unterordner, und ein Ordner,
der bereits ein Datum trägt, darf weder verschoben noch umbenannt werden. Auf
die Frage, ob das globale Schalter sein sollten, lautete die Antwort:
**fallweise Rücksprache mit dem Operator**.

**r2.0.0** brachte die Ordnerklassifikation — datiert gegen thematisch, mit
einer Granularitätsregel, sodass ein Ordner namens `2019` keine Antwort auf die
Bitte um Tagesordner ist — und den Entscheidungs-Callback, den die Oberflächen
liefern. Der Planer selbst fragt nie.

**r3.0.0** brachte die grafische Oberfläche (PySide6/Qt, vom Auftraggeber
gegenüber den Alternativen gewählt) und Läufe über mehrere Wurzelordner hinweg,
nachdem gefragt worden war, ob das Werkzeug über alle erreichbaren Laufwerke
arbeitet und ob Verschieben auch Umkopieren einschließt. Es tut beides: auf
demselben Volume ein atomares Umbenennen, über Volumes hinweg Kopie,
SHA-256-Prüfung, Löschen.

---

## 23.08.2026, morgens — die Installation, aus Anwendersicht

Drei vom Auftraggeber aus einer echten Installation gemeldete Mängel, von denen
kein Test einen hätte finden können:

- **r3.0.1** — `lrfc` lag nach der Installation nicht im `PATH`. Das
  Installationsskript bearbeitet nun die Startdatei der Shell. (Meine erste
  Überprüfung der Behebung war falsch: `zsh -l -c` liest `.zshrc` nicht.)
- **r3.0.2** — das Fenster war höher als ein kleiner Bildschirm. Die
  Einstellungen scrollen jetzt, die Aktionszeile ist verankert.
- **r4.0.0** — das Installationsskript bewarb `lrfc gui`, ohne PySide6
  installiert zu haben. Es prüft nun jede Komponente durch Importieren und
  bewirbt nur, was tatsächlich funktioniert. Eine `components`-Datei hält fest,
  was gewollt war, damit `--check` „nie installiert" von „defekt" unterscheiden
  kann.

**r4.0.1** — die Vorabprüfung schob Rechteprobleme vor, wenn der Wurzelordner
eines Katalogs nicht mehr existiert. Sie benennt jetzt den nicht verbundenen
Pfad, also das eigentliche Problem.

**r4.0.2** — ein wiederholter `new-tree`-Lauf war keine Nulloperation: ob ein
Foto schon am Ziel lag, wurde durch Pfadvergleich *und* die Forderung nach
In-Place-Platzierung entschieden. Dieselbe Migration zweimal zu fahren plante
daher jede Datei als Verschiebung auf sich selbst und rollte den ganzen Lauf
zurück.

### Der zweite echte Test

Der Auftraggeber schickte die 2019er-Bibliothek erneut durch, diesmal über die
GUI nach `Kamera/Jahr/Monat/Tag`. Lightroom öffnete das Ergebnis anstandslos.
Danach bearbeitete er ein Foto, um zu bestätigen, dass die Bibliothek wirklich
arbeitsfähig ist — die Entwicklungshistorie von 2022 war intakt.

---

## 23.08.2026, mittags — der Masterkatalog

Eine zweite Bibliothek, `Masterkatalog.Neu.lrcat`, 51.049 Fotos, auf einem
anderen Laufwerk, mit wirklich komplexer Struktur: 16 thematische Ordner
(`_extern`, `_fineart`, `_in_Arbeit/2020…2026`, `raw2020…raw2026`) und 23
datierte Ordner mit Zusatztext unter `raw2026`.

Zwei Dinge standen fest, bevor irgendetwas lief:

- **Der Katalog ist nicht verbunden.** Er verzeichnet
  `/Volumes/LR_Master/mobileRAW/`, während das Laufwerk als
  `/Volumes/Extreme Pro` eingebunden ist; 0 von 51.049 Pfaden lösen auf. Die
  Kopie selbst wurde als vollständig nachgewiesen — alle 51.049 Dateien unter
  dem ersetzten Pfad vorhanden, eine Stichprobe von 300 Dateien durchweg nicht
  leer. Vor jedem Lauf muss in Lightroom neu verknüpft werden.
- **Fünf der sechs Wurzelordner enthalten überhaupt keine Dateien** —
  Importreste.

Auf die Frage, was mit der Struktur geschehen soll, benannte die Antwort vier
verschiedene Absichten über 39 Ordner. Das vorhandene Vokabular konnte sie nicht
ausdrücken — daraus wurde **r5.0.0**:

- `resort`, eine Aktion, die einen Ordner *an seiner Stelle* neu aufbaut, unter
  seinem eigenen Elternordner — weder `consolidate` noch `sort-inside` konnten
  das sagen;
- `{folder_label}`, der Zusatztext hinter dem Datum eines Ordnernamens, mit
  wegfallenden leeren Ebenen, damit der Platzhalter als eigene Ebene taugt;
- eine geordnete Regelliste, erste passende gewinnt, sodass 39 Ordner fünf
  Zeilen sind;
- das Verschiebeprotokoll neben der Bibliothek (O-24) und die Vorbereitungsseite
  (O-21, O-22).

### Ein Fehler, den die Simulation fing

Die Simulation der neuen Regeln gegen eine Arbeitskopie des Masterkatalogs —
bevor ein einziges Byte geschrieben wurde — zeigte, dass `resort` jedes Foto
nach seinem eigenen Datum einsortierte und damit
`2026-06-27 Test 150mm Spiegelobjektiv` zerriss, weil zwölf Aufnahmen vom
Vorabend stammten. Genau das, was der Auftraggeber ausgeschlossen hatte.

`--mismatch-action leave` regiert jetzt auch `resort`. Vorher 1 von 23 Sessions
aufgesplittet, danach 0. **Der Fehler ist in den Zahlen unsichtbar und tritt in
keinem synthetischen Katalog auf** — nur eine echte Bibliothek hat eine Session
über Mitternacht.

### Und einer, der beim Lesen der Ausgabe auffiel

Beim Prüfen dieses Berichts auf Deutsch zeigte sich, dass
`lrfc --lang de plan X` auf Englisch lief. Jeder Unterbefehl deklariert die
globalen Schalter erneut, und die Vorgabe eines Unterbefehls überschreibt, was
die oberste Ebene bereits geparst hatte. Auch `--debug` vor dem Unterbefehl
wurde stillschweigend ignoriert — seit r1.0.0.

---

## 23.08.2026, nachmittags — Klartext

Zwei Fragen des Auftraggebers, die je eine Lücke trafen.

**„Wird nach dem Plandurchlauf ausgewiesen, welche Ausnahmen gefunden wurden,
damit man darauf seine Präferenzen hinterlegen kann?"** — Nur unzureichend.
Warnungen standen in derselben Zeile wie die Zahlen, und die Ausnahmen waren
*eine* Zahl „Übersprungen". Das ist so gut wie keine Auskunft. **r6.0.0** gibt
jeder Ursache einen eigenen Eintrag mit Dateizahl, Beispielen und der Option,
die sie steuert — in der GUI eine eigene Tabelle, in der CLI eine eigene
Rubrik.

**„Wir haben keine Historie-Datei."** — Stimmte. Dieses Dokument ist die
Antwort darauf.

Beim Prüfen der neuen Ausgabe fielen zwei Altlasten auf: `lrfc --lang de plan X`
lief auf Englisch, weil jeder Unterbefehl die globalen Schalter neu deklariert
und deren Vorgaben überschreiben, was die oberste Ebene bereits geparst hatte
(seit r1.0.0, `--debug` ebenso). Und die deutschen Meldungen benutzten „ue/oe/ae"
statt Umlauten, während die GUI-Texte echte verwendeten — auf dem Bildschirm
standen beide nebeneinander.

**r6.1.0** nummerierte die Dokumente nach Gewichtung, auf Wunsch des
Auftraggebers, in beiden Sprachen mit denselben Nummern.

---

## 23.08.2026, später Nachmittag — die Rückfahrkarte

Zwei weitere Wünsche, und der zweite war der gewichtige.

**„Kann man einen thematischen Ordner unverändert an den neuen Ort
verschieben?"** — Konnte man nicht; jede Aktion sortierte entweder den Inhalt
oder ließ ihn liegen. Die Aktion `relocate` füllt die Lücke, für Material, das
mitkommen soll, ohne angefasst zu werden.

**„Könnten wir eine Roll-Back-Funktion machen?"** — Es gab sie seit r1.0.0, und
erreichbar war sie nur über die Kommandozeile. Eine Rückabwicklung, die der
Anwender aus dem Fenster, das er tatsächlich benutzt, nicht erreicht, ist eine,
die er im Ernstfall nicht hat — also kam **Lauf rückgängig machen…** in die
Menüleiste. Zurücknehmen heißt Dateien und Katalog gemeinsam: die
Verschiebungen in umgekehrter Reihenfolge, die angelegten Ordner entfernt,
sofern leer, und der Katalog aus der Sicherung genau dieses Laufs.

Den ersten `relocate`-Test gegen einen verschachtelten Ordner zu schreiben legte
einen älteren Fehler offen: Ein Regelmuster traf immer nur Ordner direkt
unterhalb der Wurzel, `_extern` also `_extern`, aber nicht `raw2019/_extern`.
Kein Lauf hatte das gezeigt, weil der Masterkatalog `_extern` zufällig ganz oben
führt.

---

## Was die echten Tests gezeigt haben

| Datum | Bibliothek | Fotos | Ergebnis |
| --- | --- | --- | --- |
| 22.08.2026 | `2019.lrcat` | 9.489 | Abbruch bei Datei 850 — AppleDouble-Kollision |
| 22.08.2026 | `2019.lrcat` | 9.489 | Gelaufen, geprüft, **Lightroom verweigerte den Katalog** — Zähler als TEXT geschrieben |
| 22.08.2026 | `2019.lrcat` | 9.489 | Gelaufen, geprüft, **Lightroom öffnete ihn**, Bilder selektierbar |
| 23.08.2026 | `2019.lrcat` | 9.489 | `Kamera/Jahr/Monat/Tag` über die GUI, **geöffnet, danach Foto bearbeitet** |
| offen | `Masterkatalog.Neu.lrcat` | 51.049 | Nur simuliert; muss vorher verknüpft werden |

Drei der vier Mängel, die zählten, wurden durch Läufe gegen eine echte
Bibliothek gefunden, keiner durch die Testsuite. Die Aufgabe der Suite ist es,
sie behoben zu halten.

---

## Siehe auch

- [CHANGELOG.md](../../CHANGELOG.md) — was sich je Revision geändert hat
- [13-offene-punkte.md](13-offene-punkte.md) — was bekanntermaßen fehlt
- [14-prompts.md](14-prompts.md) — der ursprüngliche Auftrag und der generische Prompt
- [10-entwicklung.md](10-entwicklung.md) — wie die Arbeit fortgesetzt wird
