# Beiträge, Deutsch

Jeder Entwurf legt die Urheberschaft in den ersten Zeilen offen. Das bitte
stehen lassen.
Website: <https://andy-freund.gitlab.io/LR-CompanionSuite> ·
Quelltext: <https://gitlab.com/andy-freund/LR-CompanionSuite>

---

## 1. DSLR-Forum.de — Bereich Bildbearbeitung / Lightroom

*Warum dort:* das größte deutschsprachige Fotoforum, technisch interessiertes
Publikum, gute Auffindbarkeit über Suchmaschinen. Vorher die Forenregeln zur
Eigenwerbung lesen; im Zweifel einen Moderator fragen, bevor der Beitrag steht.

**Betreff:** Freies Werkzeug: Lightroom-Ordner umsortieren, ohne die Katalogverknüpfung zu verlieren

> Vorab und in eigener Sache: Ich habe das Werkzeug selbst geschrieben. Es ist
> kostenlos, quelloffen, und es gibt nichts zu kaufen. Wenn das hier fehl am
> Platz ist, bitte verschieben oder löschen.
>
> **Das Problem.** Mein Masterkatalog war in eine Handvoll riesiger
> Jahresordner hineingewachsen — 51.049 Fotos, 2,36 TB. Ich wollte
> Jahr / Monat / Tag. Jeder naheliegende Weg war versperrt:
>
> - Ordner im Finder oder Explorer verschieben zerreißt den Katalog. Lightroom
>   zeigt Fragezeichen, und Tausende Fotos von Hand neu zu verknüpfen ist kein
>   Wochenendprojekt.
> - Ordner in Lightrooms eigenem Ordner-Bedienfeld ziehen hält den Katalog
>   heil, bewegt aber immer nur einen Ordner. Bei dieser Menge sind das Tage,
>   und ein Absturz mittendrin lässt einen im Nirgendwo stehen.
> - Neu importieren verliert Entwicklungseinstellungen, Sammlungen,
>   Markierungen und Stichwörter. Kommt nicht infrage.
>
> **Was das Werkzeug tut.** LR-FolderCraft liest den Katalog, ermittelt für
> jedes Foto den Zielort nach der gewählten Struktur, verschiebt dann die
> Dateien *und* schreibt die Ordnereinträge im Katalog passend um. Lightroom
> findet anschließend alles dort, wo es es erwartet. Bei mir dauerte das
> Minuten statt Tage.
>
> **Warum ich ihm den Katalog anvertraue.** Es schreibt in die
> Katalogdatenbank, insofern verstehe ich jedes Zögern — ich hatte es bei
> meinem eigenen Code.
>
> - Der Probelauf ist der Normalfall: `plan` schreibt nirgendwo etwas, und man
>   liest den vollständigen Plan, bevor irgendetwas passiert.
> - Der Katalog wird gesichert und die Sicherung geprüft, bevor er angefasst
>   wird. Lightroom muss geschlossen sein, sonst startet es gar nicht erst.
> - Erst wandern die Dateien, jede Verschiebung sofort in ein Journal
>   geschrieben; der Katalog wird zuletzt festgeschrieben. Ein Absturz
>   mittendrin lässt den Katalog also unberührt, und `resume` stellt entweder
>   die Dateien zurück oder führt den Lauf zu Ende.
> - Jeder Lauf lässt sich exakt zurücknehmen, weil das Journal festhält, was
>   tatsächlich geschah — nicht, was geplant war.
> - Ich habe meine eigene Bibliothek viele Male umgestellt und zurückgenommen
>   und jedes Mal zehn Katalogtabellen, alle 51.049 Pfade und jede Datei auf
>   der Platte gegen einen Ausgangsstand verglichen. Jedes Mal byte-identisch.
>
> **Was es nicht kann.** Nur Lightroom **Classic** — die Cloud-Fassung hat
> keinen Ordnerbaum, den man umbauen könnte. Es braucht Python 3.9 oder neuer,
> läuft auf macOS und Windows. Und es ist das Projekt eines Einzelnen, nicht
> das einer Firma.
>
> Beipackdateien (`.xmp`), virtuelle Kopien, Stapel und RAW+JPEG-Paare werden
> mitgeführt. Ordner, die so bleiben sollen, wie sie sind, kann man als Regel
> hinterlegen; Ordner, die schon `2019-01-03 Hochzeit` heißen, lassen sich mit
> ihrem Zusatztext einreihen.
>
> Dokumentation vollständig auf Deutsch und Englisch:
> https://andy-freund.gitlab.io/LR-CompanionSuite
>
> Wenn es jemand ausprobiert: Rückmeldung, wo es unverständlich war, hilft mir
> mehr als Lob.

---

## 2. fotocommunity.de — Forum, Bereich Bildbearbeitung

*Warum dort:* weniger technisch, dafür sehr viele Menschen mit gewachsenen
Bibliotheken. Der Text sollte kürzer und weniger technisch sein als oben.

> In eigener Sache, und kostenlos: Ich hatte 51.000 Fotos in fünf riesigen
> Jahresordnern und wollte endlich eine Struktur nach Jahr, Monat und Tag.
>
> Wer das schon versucht hat, kennt die Falle: Verschiebt man die Ordner im
> Finder oder Explorer, findet Lightroom die Fotos nicht mehr. Zieht man sie
> in Lightrooms Ordner-Bedienfeld, bleibt zwar alles verknüpft, aber bei
> dieser Menge sitzt man Tage daran.
>
> Ich habe mir dafür ein Werkzeug geschrieben und stelle es frei zur
> Verfügung: **LR-FolderCraft**. Es verschiebt die Dateien und schreibt
> gleichzeitig den Katalog um, sodass die Verknüpfung erhalten bleibt.
>
> Das Wichtigste ist für mich nicht, was es kann, sondern was es nicht
> kaputtmacht: Es zeigt zuerst einen vollständigen Plan und fasst dabei nichts
> an. Es sichert den Katalog und prüft die Sicherung. Es schreibt den Katalog
> zuletzt, damit ein Stromausfall mittendrin ihn unberührt lässt. Und jeder
> Lauf lässt sich vollständig rückgängig machen.
>
> Nur für Lightroom **Classic**, nicht für die Cloud-Fassung. Für macOS und
> Windows, mit deutscher Oberfläche und deutscher Anleitung.
>
> https://andy-freund.gitlab.io/LR-CompanionSuite

---

## 3. Kommentar unter bestehenden Fragen

Wirkt fast immer besser als ein eigener Beitrag. Auslöser sind Fragen wie
„Lightroom findet Fotos nicht mehr", „Ordnerstruktur nachträglich ändern",
„Fotos nach Datum sortieren". Kurz halten:

> Der übliche Rat gilt weiter: Ordner niemals im Finder oder Explorer
> verschieben, sondern in Lightrooms Ordner-Bedienfeld ziehen — dann bleibt
> die Verknüpfung erhalten. Bei ein paar tausend Fotos ist das der sichere
> Weg.
>
> Bei Zehntausenden wird das unzumutbar. Dafür habe ich mir ein freies
> Werkzeug geschrieben, LR-FolderCraft, das Dateien und Katalog gemeinsam
> umstellt — mit Probelauf, Katalogsicherung und vollständiger Rücknahme.
> Offenlegung: ist von mir, kostenlos, quelloffen.
> https://andy-freund.gitlab.io/LR-CompanionSuite
>
> Egal womit: vorher Lightroom schließen und den Katalog selbst zusätzlich
> sichern.

---

## 4. Weitere deutschsprachige Anlaufstellen

- **DOCMA** (docma.info) — Magazin und Blog für Photoshop und Lightroom; eher
  über die Redaktion als über ein Forum, siehe [letters.md](letters.md).
- **c't Fotografie** — Leserzuschrift oder Themenvorschlag an die Redaktion.
- **Traumflieger.de** — Forum und Redaktion.
- **Mac & i / heise Foto** — falls das Werkzeug auf macOS besonders punktet.
- **Lokale Fotoclubs und VHS-Kurse** — unterschätzt: dort sitzen genau die
  Menschen mit einer über zwanzig Jahre gewachsenen Bibliothek und ohne
  jemanden, der ihnen dabei hilft. Ein Vortragsangebot wirkt stärker als
  jeder Forenbeitrag.
