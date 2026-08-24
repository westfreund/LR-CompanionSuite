# The questions a careful reader asks first / Was skeptische Leser zuerst fragen

Answers to keep at hand when a post gets replies. Short, honest, no defence.
Antworten zum Bereithalten, wenn ein Beitrag Rückfragen bekommt. Kurz,
ehrlich, ohne Verteidigung.

---

## English

**"Why should I let anything write into my catalog?"**
You should not, until you have looked. That is why `plan` is the default and
writes nothing at all. Run it, read the plan, close the terminal — nothing has
happened. And run Lightroom's own backup first; the tool makes its own, but
two is not too many for something irreplaceable.

**"What happens if it crashes halfway?"**
The catalog is written last, in one transaction. If the process dies, SQLite
discards that transaction, so the catalog still describes the old state — it
is not corrupt and it is not half-changed. Only the files on disk are
half-moved, and every move was journalled as it happened, so `lrfc resume`
either puts them back or carries the run to the end. You choose which.

**"Can I undo it?"**
Yes, exactly, because the journal records what actually happened rather than
what was planned. Files go back, folders created along the way are removed if
empty, and the catalog is restored from the backup that run made.

**"Have you tested it on anything real?"**
On a 51,049-photo, 2.36 TB library — mine — migrated and reversed many times.
Each round I compared ten catalog tables, all 51,049 paths and every file on
disk against a baseline taken beforehand. Byte-identical each time. All three
front ends were run at that size, including deliberate mid-run kills that were
then repaired.

**"What does it send anywhere?"**
Nothing. No telemetry, no account, no network access at all.

**"Does it work with Lightroom CC / the cloud one?"**
No, and it never will. Cloud Lightroom has no folder tree on disk to rebuild.
This is for Lightroom **Classic**.

**"Why should I trust a one-person project?"**
You should weigh that. What I can offer: the source is open and readable, the
test suite is public and runs on five Python versions, the safety behaviour is
guarded by tests specifically so a future change cannot quietly remove it, and
the whole design is written down rather than folklore. What I cannot offer is
a support contract.

**"I already moved my folders in Finder and everything is missing."**
Then this is not your tool yet — you need to reconnect first, which Lightroom
can do: right-click the folder with the question mark, "Find Missing Folder",
and point at where it went. Do that before anything else.

---

## Deutsch

**„Warum sollte ich irgendetwas in meinen Katalog schreiben lassen?"**
Sollten Sie nicht, bevor Sie hingesehen haben. Genau deshalb ist `plan` der
Normalfall und schreibt nirgendwo etwas. Ausführen, Plan lesen, Fenster
schließen — es ist nichts passiert. Und machen Sie vorher Lightrooms eigene
Sicherung; das Werkzeug legt eine eigene an, aber bei etwas Unersetzlichem
sind zwei nicht zu viel.

**„Was passiert, wenn es mittendrin abstürzt?"**
Der Katalog wird zuletzt geschrieben, in einer einzigen Transaktion. Stirbt
der Prozess, verwirft SQLite diese Transaktion — der Katalog beschreibt also
weiterhin den alten Stand, er ist weder beschädigt noch halb geändert. Nur die
Dateien liegen halb verschoben, und jede Verschiebung wurde beim Geschehen ins
Journal geschrieben. `lrfc resume` stellt sie entweder zurück oder führt den
Lauf zu Ende. Sie entscheiden.

**„Kann ich das rückgängig machen?"**
Ja, und zwar exakt, weil das Journal festhält, was tatsächlich geschah, nicht
was geplant war. Die Dateien wandern zurück, unterwegs angelegte Ordner werden
entfernt, wenn sie leer sind, und der Katalog wird aus der Sicherung dieses
Laufs wiederhergestellt.

**„Ist das an echten Daten erprobt?"**
An einer Bibliothek mit 51.049 Fotos und 2,36 TB — meiner eigenen —, viele
Male umgestellt und zurückgenommen. Jedes Mal habe ich zehn Katalogtabellen,
alle 51.049 Pfade und jede Datei auf der Platte gegen einen vorher genommenen
Ausgangsstand verglichen. Jedes Mal byte-identisch. Alle drei Oberflächen
wurden in dieser Größe gefahren, samt absichtlicher Abbrüche mitten im Lauf,
die anschließend repariert wurden.

**„Was schickt es wohin?"**
Nichts. Keine Telemetrie, kein Konto, überhaupt kein Netzzugriff.

**„Funktioniert das mit Lightroom CC, der Cloud-Fassung?"**
Nein, und das wird es nie. Das Cloud-Lightroom hat keinen Ordnerbaum auf der
Platte, den man umbauen könnte. Dies ist für Lightroom **Classic**.

**„Warum sollte ich einem Ein-Personen-Projekt vertrauen?"**
Das sollten Sie abwägen. Was ich anbieten kann: Der Quelltext ist offen und
lesbar, die Testreihe ist öffentlich und läuft auf fünf Python-Fassungen, das
Sicherheitsverhalten ist eigens durch Tests abgesichert, damit eine spätere
Änderung es nicht stillschweigend entfernt, und der Entwurf ist aufgeschrieben
statt mündlich überliefert. Was ich nicht anbieten kann, ist ein
Wartungsvertrag.

**„Ich habe meine Ordner schon im Finder verschoben und jetzt fehlt alles."**
Dann ist dies noch nicht Ihr Werkzeug — Sie müssen zuerst wieder verknüpfen,
und das kann Lightroom selbst: Rechtsklick auf den Ordner mit dem Fragezeichen,
„Fehlenden Ordner suchen", und dorthin zeigen, wo er gelandet ist. Das zuerst,
alles andere danach.
