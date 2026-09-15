# Vorbereitung

**Revision r20.0.0 · Build-Datum 2026-09-15**

Zwei Dinge müssen für Ihre Bibliothek zutreffen, bevor LR-FolderCraft etwas
anfasst. Keines davon ist schwierig, beide werden leicht übersehen, und beide
sind bei den Tests dieses Werkzeugs auf die harte Tour aufgefallen.

---

## 1. Jeder Ordner muss in Lightroom verknüpft sein

Ein Lightroom-Katalog speichert nicht, wo Ihre Fotos heute liegen. Er speichert,
wo sie beim Import lagen: einen absoluten Wurzelpfad wie

```
/Volumes/LR_Master/mobileRAW/
```

und darunter je Ordner einen relativen Pfad. Ist das Laufwerk inzwischen unter
einem anderen Namen eingebunden — weil es umbenannt, geklont, aus einer
Sicherung zurückgespielt oder an einen anderen Rechner gesteckt wurde — nennt
der Katalog weiterhin den alten Pfad. Lightroom zeigt diese Ordner mit einem
**Fragezeichen**.

**LR-FolderCraft kann mit einer Bibliothek in diesem Zustand nicht arbeiten.**
Es löst jedes Foto zu einem absoluten Pfad auf und verschiebt die echte Datei.
Existiert der Pfad aus dem Katalog nicht, gibt es keine Datei zu verschieben,
und die Vorabprüfung bricht ab, statt zu raten, wo die Fotos liegen könnten.

### Woran Sie es erkennen

`lrfc info` auf den Katalog angewendet listet jeden Wurzelordner mit der Zahl
der auf der Platte gefundenen Dateien:

```
Wurzelordner
  /Volumes/LR_Master/mobileRAW/     51.049 Dateien    0 gefunden     <- kaputt
  /Volumes/Photos/2019/              9.489 Dateien    9.489 gefunden <- in Ordnung
```

`0 gefunden` bei einer Wurzel mit Tausenden Dateien heißt: der Pfad ist veraltet
— nicht, dass die Fotos weg sind.

### Wie Sie es beheben

Das machen Sie **in Lightroom, nicht im Werkzeug**. Lightrooms eigenes
Verknüpfen ist der einzige Mechanismus, der den Katalog so aktualisiert, wie
Lightroom es erwartet.

1. Katalog in Lightroom Classic öffnen.
2. Im Bedienfeld **Ordner** den obersten Ordner mit Fragezeichen suchen. Das
   Verknüpfen eines übergeordneten Ordners verknüpft alles darunter mit — also
   immer oben im Baum anfangen.
3. Rechtsklick → **Fehlenden Ordner suchen…**
4. Im Dialog auf den Ort zeigen, an dem der Ordner heute tatsächlich liegt.
5. Für verbleibende Fragezeichen wiederholen, danach Lightroom beenden.

`lrfc info` erneut ausführen. Jede Wurzel sollte ihre Dateien nun als gefunden
melden.

### Warum das Werkzeug das nicht selbst tut

Es könnte — die Änderung ist ein einziges `UPDATE` auf
`AgLibraryRootFolder.absolutePath` — und es tut es bewusst nicht. Zu raten,
welches Verzeichnis auf welchem Laufwerk die neue Heimat eines Wurzelordners
sein soll, ist genau die Art Entscheidung, die billig falsch und teuer
rückgängig zu machen ist. Lightroom bittet Sie, auf den Ordner zu zeigen; alles,
was seinen Katalog bearbeitet, sollte das auch.

---

## 2. Der Katalog sollte auf der aktuellen Lightroom-Version sein

Lightroom Classic hebt das Schema eines Katalogs an, sobald eine neue Version
ihn zum ersten Mal öffnet. Bis dahin liegt die Datei im alten Format vor.

LR-FolderCraft liest die Schemaversion und verweigert Versionen, gegen die es
nicht verifiziert wurde — ein unbekanntes Schema kann eine Tabelle enthalten,
von der das Werkzeug nicht weiß, dass es sie konsistent halten muss. An einem
alten Katalog zu arbeiten und das Ergebnis danach von einem neuen Lightroom
anheben zu lassen, bedeutet zwei aufeinandergestapelte Migrationen, von denen
nur die zweite durch eine bewusst angelegte Sicherung gedeckt ist.

**Erst konvertieren, dann umsortieren.** In Lightroom Classic: **Datei →
Katalog öffnen…**, die `.lrcat` wählen und die Aktualisierung bestätigen.
Lightroom schreibt eine neue Datei — typischerweise `MeinKatalog-v14.lrcat` —
und lässt das Original unangetastet. LR-FolderCraft dann auf die angehobene
Datei zeigen lassen.

`lrfc info` gibt die gefundene Schemaversion aus und ob sie verifiziert ist:

```
Katalogversion     18.0.0  (verifiziert)
```

Steht dort `nicht verifiziert`, fährt `--allow-unsupported-catalog` trotzdem
fort. Tun Sie das nur an einer Kopie.

---

## Die kurze Checkliste

| | |
| --- | --- |
| Katalog einmal mit dem aktuellen Lightroom Classic geöffnet | damit das Schema aktuell ist |
| Keine Fragezeichen im Bedienfeld Ordner | damit jede Datei gefunden wird |
| `lrfc info` meldet für jede Wurzel gefundene Dateien | dasselbe, maschinell geprüft |
| Lightroom Classic **geschlossen** | der Katalog darf beim Umschreiben nicht offen sein |
| Eine selbst angelegte Sicherung auf einem anderen Laufwerk | das Werkzeug legt auch eine an, aber Ihre liegt woanders |

Das Werkzeug prüft all das in der Vorabprüfung und verweigert den Lauf, wenn
etwas fehlt. Die Liste steht hier, damit die Verweigerung keine Überraschung
ist.

---

## Siehe auch

- [04-bedienung.md](04-bedienung.md) — die Befehle und Optionen
- [06-sicherheit.md](06-sicherheit.md) — was die Sicherung abdeckt und wie ein Lauf
  rückgängig gemacht wird
- [07-faq.md](07-faq.md) — unter anderem, was zu tun ist, wenn Lightroom einen
  Katalog danach nicht öffnen will
