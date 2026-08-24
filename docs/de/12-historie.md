# Projekthistorie

**Revision r17.0.3 · Build-Datum 2026-08-24**

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

---

## Jede Revision, der Reihe nach

Neununddreißig Revisionen an einem Tag, vom Kern bis zur Wiederaufnahme. Die
Zeiten sind die der Auslieferung; ein Name steht dort, wo eine Revision einen
trägt — nach der Projektregel ist jede Feature-Erweiterung eine Hauptversion,
und nur die bekommen einen.

Wer wissen will, *was* sich geändert hat, findet es hier in einer Zeile; wer
wissen will, *warum*, liest die Abschnitte darunter und den
[CHANGELOG](../../CHANGELOG.md).

| Revision | Zeit | Name | Worum es ging |
| --- | --- | --- | --- |
| **r1.0.0** | 16:28 | Daybreak | Der Kern: Katalogleser und -schreiber, Planer, Ausführung, Journal, Vorabprüfungen, CLI. Die Schreibfläche wird auf fünf Anweisungen gegen vier Tabellen festgelegt. |
| **r1.0.1** | 18:06 |  | AppleDouble-Begleiter `._X` werden mitverschoben. Diese Änderung verursachte den Abbruch beim ersten Echtlauf. |
| **r1.0.2** | 18:23 |  | Der exFAT-Rückfall war toter Code: `sqlite3.connect()` arbeitet verzögert, der Fehler kam erst bei der ersten Abfrage. Behoben mit einer Prüfabfrage. |
| **r1.0.3** | 18:30 |  | Nachgemessen, was der Kernel auf exFAT tut: Er verschiebt `._X` selbst. Unter macOS bleibt der Begleiter jetzt liegen, sonst wird er mitgeführt. |
| **r1.0.4** | 19:42 |  | Die Vorabprüfung nannte `.lrcat-wal` eine veraltete Nebendatei. Falsch und gefährlich: Ein nicht leeres WAL enthält festgeschriebene Transaktionen. |
| **r1.0.5** | 20:05 |  | Die Ursache, an der Lightroom den Katalog verweigerte: Der ID-Zähler wurde als TEXT statt REAL geschrieben. Speicherklasse wird jetzt gelesen, erhalten und nachgeprüft. |
| **r1.0.6** | 20:41 |  | Erkennung von Katalogen, die r1.0.0 bis r1.0.4 bereits beschädigt hatten. |
| **r2.0.0** | 22:19 | Wegweiser | Gewachsene Bibliotheken: Ordnerklassifikation datiert gegen thematisch, Granularitätsregel, und der Entscheidungs-Callback, den die Oberflächen liefern. Der Planer fragt nie selbst. |
| **r2.0.1** | 22:43 |  | Eine Zielwurzel, die es noch nicht gibt, wird angelegt — genau darum geht es bei „neuer Baum“. |
| **r3.0.0** | 23:19 | Weitwinkel | Grafische Oberfläche (PySide6/Qt) und Läufe über mehrere Wurzelordner. Über Volumes hinweg: kopieren, per SHA-256 prüfen, löschen. |
| **r3.0.1** | 00:08 |  | `lrfc` lag nach der Installation nicht im PATH. Das Skript bearbeitet nun die Startdatei der Shell. |
| **r3.0.2** | 07:02 |  | Das Fenster war höher als ein kleiner Bildschirm. Einstellungen scrollen, die Aktionszeile ist verankert. |
| **r4.0.0** | 07:29 | Pruefstand | Das Installationsskript prüft jede Komponente durch Importieren und bewirbt nur, was funktioniert. Zuvor hatte es `lrfc gui` ohne PySide6 angeboten. |
| **r4.0.1** | 07:40 |  | Ein Katalog mit nicht mehr existierendem Wurzelordner wurde als Rechteproblem gemeldet. Jetzt wird der nicht verbundene Pfad benannt. |
| **r4.0.2** | 08:08 |  | Ein wiederholter `new-tree`-Lauf war keine Nulloperation und rollte sich selbst zurück. Die Prüfung „schon am Ziel“ vergleicht jetzt nur noch Pfade. |
| **r5.0.0** | 09:26 | Regelwerk | Ordnerregeln, der Platzhalter `{folder_label}` und die Aktion `resort`. 39 Ordner werden zu fünf Zeilen. Die Simulation deckte auf, dass `resort` eine Session über Mitternacht zerriss. |
| **r6.0.0** | 10:22 | Klartext | Ausnahmen-Bericht: jede Ursache mit Dateizahl, Beispielen und der Option, die sie steuert. Dazu die Projekthistorie und reproduzierbare Screenshots. Gefunden: `--lang de` vor dem Unterbefehl wirkte nicht. |
| **r6.1.0** | 10:41 |  | Dokumente nach Gewichtung nummeriert, in beiden Sprachen mit denselben Nummern. Die Historie nennt seither ihre eigene Herkunft. |
| **r7.0.0** | 10:56 | Gedaechtnis | Das Fenster merkt sich seine Einstellungen. Nicht gemerkt werden Einzelentscheidungen (Katalog-IDs) und der Sicherungsschalter. Behoben: Der Zielordner war nicht erreichbar, weil Feld und Knopf gesperrt aussahen. |
| **r7.1.0** | 11:06 |  | Die Teiler zwischen den Bereichen waren fast unsichtbar. Dazu ein Fehler: Der Protokollbereich bekam keine eigene Größe, seit die Ausnahmen-Tabelle dazukam. |
| **r8.0.0** | 11:29 | Rueckfahrkarte | Die Aktion `relocate` trägt einen Ordner unverändert hinüber, und das Rückgängigmachen kommt in die GUI. Behoben: Ein Regelmuster traf nur Ordner direkt unter der Wurzel. |
| **r8.0.1** | 11:50 |  | Die Menüeinträge waren unter macOS unsichtbar: Qt unterstützt dort keine Aktionen direkt an der Menüleiste. Rückgängig steht jetzt zusätzlich als Schaltfläche. |
| **r9.0.0** | 13:12 | Aufgeraeumt | Katalogfremde Dateien einsammeln, Voraussetzungen bestätigen lassen, Kurzbeschreibung und Über-Dialog, sechs Logo-Entwürfe. Zwei Ausnahmen des Einsammelns fand erst der Test. |
| **r10.0.0** | 13:50 | Signet | Die Marke, in zwei Schnitten und mit gezeichneten Buchstaben. Dabei: `logo-small.svg` zeichnete nichts, weil ein doppelter Bindestrich im XML-Kommentar stand. |
| **r10.1.0** | 16:17 |  | Die Marke war unsichtbar: macOS zeigt keine Symbole in Fenstertitelleisten. Sie steht jetzt im Fenster. |
| **r11.0.0** | 16:33 | Vollstaendig | Kumulative Datumsebenen und die Aktion `refile`. Dazu ein Test, der jede Aktion, jeden Platzhalter und jeden Schalter in beiden Sprachbäumen einfordert — er fand sofort drei undokumentierte Schalter. |
| **r12.0.0** | 17:10 | Arbeitsweise | Ein Schalter für die häufigste Ordnerentscheidung, und Profile, die nur noch die Arbeitsweise tragen: kein Katalog, kein Ziel, keine Regeln, keine Notausgänge. |
| **r13.0.0** | 17:20 | Laufakte | Eine Ordnerakte je Lauf, neben dem Katalog. Verlauf, und ein Lauf lässt sich nur einmal zurücknehmen. Behoben: Zwei Läufe in derselben Sekunde teilten sich den Ordner. |
| **r13.0.1** | 17:33 |  | `leave` ließ unter `new-tree` nichts liegen — es war identisch mit `relocate`, sobald die Zielwurzel abwich. |
| **r13.0.2** | 18:31 |  | Drei der vier Tastenkürzel der TUI feuerten nie; Textual belegt `ctrl+p` mit Vorrang. Escape schloss den Bestätigungsdialog nicht. |
| **r13.0.3** | 18:42 |  | Eine bewusste Verweigerung wurde als Absturz gemeldet, mit Rückverfolgung und der Aufschrift „Unexpected error“. |
| **r13.0.4** | 19:03 |  | Die Laufakte nannte die Regeln nicht, die den Lauf geformt hatten — sie übernahm die Ausschlussliste der Profile. Für eine Aufzeichnung ist das falsch. |
| **r14.0.0** | 19:07 | Umschrift | ASCII-Namen schreiben Umlaute aus statt sie wegzuwerfen. `Straße` war zu `Strae` geworden. Der vorhandene Test hatte das falsche Ergebnis als Sollzustand festgeschrieben. |
| **r14.0.1** | 20:33 |  | Die Umschrift lief ins Leere: macOS liefert Dateinamen zerlegt, die Zeichentabelle traf nie. Betraf ebenso den Vergleich von Regelmustern. |
| **r15.0.0** | 21:26 | Gleichstand | Die Textoberfläche wird gleichwertig: sieben fehlende Einstellungen, Voraussetzungen, Verlauf, Rückgängig, Profile. Ein Gleichstands-Test verhindert das erneute Auseinanderlaufen. |
| **r15.0.1** | 21:46 |  | `refile` wiederholte einen Zusatztext, den die Struktur bereits gesetzt hatte: `2026-06-18 Voelki Voelki`. |
| **r15.0.2** | 22:00 |  | Ein überholter Plan konnte der ausgeführte werden. Der erste Behebungsversuch war schlimmer: Ein Lambda um den Slot machte die Verbindung direkt statt eingereiht, und Widgets entstanden im Arbeitsthread. |
| **r16.0.0** | 22:17 | Wiederaufnahme | Ein abgebrochener Lauf lässt sich abschließen. Die Richtung ergibt sich aus der Abbruchstelle, nicht aus einer Vermutung. Ein neuer Lauf wird verweigert, solange einer offen ist. |
| **r16.0.1** | 22:37 |  | Eine abgeschlossene Rücknahme wurde als abgebrochen gemeldet, weil ein späterer Lauf dieselben Pfade angelegt hatte. Der Fehlalarm blockierte gesunde Bibliotheken. |
| **r16.1.0** | 22:52 |  | Die Historie nennt jede ausgelieferte Revision, und ein Test hält sie dazu an. Zuvor deckte sie 18 von 39 ab. |
| **r17.0.0** | 23:—  | Beisammen | Der Sammelordner für katalogfremde Dateien liegt im Zielbaum statt in der Quelle: sonst lag das Ergebnis eines Laufs an zwei Orten. Dabei behoben: Über Laufwerksgrenzen wäre das Verschieben gescheitert. |
| **r17.0.1** | 06:30 |  | Die Liste der Läufe zeigte Platzhalter statt eines Pfads, und die Uhrzeit war auf `06:1` abgeschnitten. |
| **r17.0.2** | 07:20 |  | Ein reparierter Lauf wurde erneut als abgebrochen gemeldet — und die Dateien, die er hätte zurückstellen wollen, gehörten dem laufenden Lauf. Dazu: Das Fenster kam mit 640×480 und zwei zugeklappten Bereichen zurück. |
| **r17.0.3** | 07:50 |  | Rückgängig fand den Lauf von heute früh nicht: Ohne gemerkten Katalog meldete das Fenster, es seien keine Läufe aufgezeichnet, und öffnete einen Dateidialog in einem Ordner, in dem seit Revisionen kein Journal mehr liegt. Es nennt jetzt den wahren Grund und startet dort, wo die Journale liegen. |

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

## 23.08.2026, Nachmittag bis Nacht — was das Benutzen zutage fördert

Von r7 bis r16 kam kaum eine Revision aus einer Planung. Fast jede entstand,
weil der Auftraggeber das Werkzeug benutzte und etwas nicht stimmte.

**Was die Oberfläche nicht hergab.** Der Zielordner war nicht erreichbar, weil
Feld und Schaltfläche gesperrt *aussahen* (r7.0.0). Die Teiler zwischen den
Bereichen waren praktisch unsichtbar (r7.1.0). Die Menüeinträge fehlten unter
macOS ganz, weil Qt dort keine Aktionen direkt an der Menüleiste unterstützt
— damit war das eben erst eingebaute Rückgängigmachen unerreichbar (r8.0.1).
Und die frisch gewählte Marke war nirgends zu sehen, weil macOS keine Symbole
in Fenstertitelleisten zeigt (r10.1.0). Vier Mal dasselbe Muster: gebaut,
vorhanden, unbenutzbar.

**Was erst echte Daten zeigten.** Ein Regelmuster traf nur Ordner direkt unter
der Wurzel (r8.0.0). `leave` ließ unter `new-tree` nichts liegen, weil es
identisch mit `relocate` war (r13.0.1). Die Laufakte nannte die Regeln nicht,
die den Lauf geformt hatten — das Ergebnis war aus der Aufzeichnung nicht
erklärbar (r13.0.4). Aus `Straße` wurde `Strae`, das ß verschwand ersatzlos
(r14.0.0). Und die Behebung dafür lief ins Leere, weil macOS Dateinamen zerlegt
liefert und die Zeichentabelle nie traf (r14.0.1).

**Zwei Tests, die das Falsche festhielten.** Der ASCII-Test behauptete
`"Grun Strae"` als Sollzustand — er hat den Fehler nicht gefunden, sondern
festgeschrieben. Und der Test zur Umschrift war mit einem Quelltext-Literal
geschrieben, das die zerlegte Form gar nicht erzeugen kann.

**Und Behebungen, die schlimmer waren als der Fehler.** Um einen überholten
Plan abzuweisen, reichte ich eine Kennung per Lambda um den Slot — damit verlor
die Verbindung ihren QObject-Empfänger, Qt machte sie direkt statt eingereiht,
und Widgets entstanden im Arbeitsthread. Die Ordnerentscheidungen funktionierten
danach stumm nicht mehr (r15.0.2). Und der erste Erkenner für abgebrochene Läufe
las den Zustand aus Pfaden; ein späterer Lauf ins selbe Ziel machte daraus einen
Fehlalarm, der gesunde Bibliotheken blockierte (r16.0.1).

**Wächter statt Vorsätze.** Dreimal war die Antwort nicht eine Behebung, sondern
eine Prüfung, die den Rückfall unmöglich macht: dass jede Aktion, jeder
Platzhalter und jeder Schalter in beiden Sprachbäumen steht (r11.0.0); dass
beide Oberflächen dieselben Einstellungen setzen können und jede schreibende
Oberfläche Voraussetzungen, Verlauf und Rückgängig anbietet (r15.0.0); und dass
diese Historie jede ausgelieferte Revision nennt.

**Zuletzt der Abbruch.** Beim automatisierten Steuern der Oberfläche beendete
ich selbst einen Prozess mitten in einer Rücknahme: 27.660 Dateien zurück,
23.050 noch am neuen Ort. Reparabel, weil der Katalog zuletzt zurückgespielt
wird — aber nichts im Werkzeug sagte es oder half. Daraus wurde r16.0.0.


---

## Was die echten Tests gezeigt haben

Alle Läufe gegen `Masterkatalog.Neu.lrcat`, 51.049 Fotos, 2,36 TB, sofern nicht
anders vermerkt.

| Datum | Bibliothek | Was gefahren wurde | Ergebnis |
| --- | --- | --- | --- |
| 22.08. | `2019.lrcat`, 9.489 | erster Echtlauf | Abbruch bei Datei 850 — AppleDouble-Kollision |
| 22.08. | `2019.lrcat` | Wiederholung | gelaufen und geprüft, **Lightroom verweigerte den Katalog** |
| 22.08. | `2019.lrcat` | nach r1.0.5 | gelaufen, **Lightroom öffnete**, Bilder selektierbar |
| 23.08. | `2019.lrcat` | `Kamera/Jahr/Monat/Tag` über die GUI | geöffnet, danach Foto bearbeitet |
| 23.08. 11:40 | Masterkatalog | `{yyyy}/{mm}/{dd}`, CLI | 51.049 verschoben, Lightroom öffnete, zurückgenommen |
| 23.08. 16:52 | Masterkatalog | kumulative Datumsebenen | geprüft, zurückgenommen |
| 23.08. 17:34 | Masterkatalog | alle vier Ordneraktionen zugleich, Waisen | geprüft, zurückgenommen |
| 23.08. 18:50 | Masterkatalog | GUI mit Einzelentscheidungen | geprüft, zurückgenommen |
| 23.08. 20:25 | Masterkatalog | GUI, ASCII-Namen | zeigte, dass die Umschrift nicht griff |
| 23.08. 21:05 | Masterkatalog | GUI nach r14.0.1 | `Voelki` korrekt, zurückgenommen |
| 23.08. 21:35 | Masterkatalog | **TUI**, schreibend | 50.709 verschoben, über `Strg+Z` zurückgenommen |
| 23.08. 21:40 | Masterkatalog | **CLI**, `{folder_label}` + `refile` | deckte die Verdopplung auf |
| 23.08. 22:24 | Masterkatalog | **GUI** nach r15.0.2 | geprüft, zurückgenommen |
| 23.08. 22:31 | Masterkatalog | CLI, **nach 35 s abgeschossen** | 13.605 bewegt, `resume` stellte alles zurück |
| 23.08. 22:41 | Masterkatalog | **TUI** nach r16.0.1 | geprüft, über `Strg+Z` zurückgenommen |
| 23.08. 22:46 | Masterkatalog | TUI, **nach 45 s abgeschossen** | über `Strg+E` aus der TUI wiederaufgenommen |

Jeder Zyklus endete bitidentisch am Ausgangszustand: zehn Katalogtabellen, alle
Pfade und alle 51.063 Dateien auf der Platte.

**Die meisten Fehler, die zählten, fanden echte Läufe, nicht die Testsuite.**
Deren Aufgabe ist es, sie behoben zu halten — inzwischen mit 555 Tests.

## Siehe auch

- [CHANGELOG.md](../../CHANGELOG.md) — was sich je Revision geändert hat
- [13-offene-punkte.md](13-offene-punkte.md) — was bekanntermaßen fehlt
- [14-prompts.md](14-prompts.md) — der ursprüngliche Auftrag und der generische Prompt
- [10-entwicklung.md](10-entwicklung.md) — wie die Arbeit fortgesetzt wird
