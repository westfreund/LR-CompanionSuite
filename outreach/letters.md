# Anschreiben an Redaktionen und Autoren

Wenige Adressaten, größte Hebelwirkung. Ein Mensch, der über Lightroom
schreibt, erreicht in einem Artikel mehr Betroffene als zwanzig Forenbeiträge.

**Regeln für alle drei:** kurz. Keine Anhänge im Erstkontakt. Nichts
verlangen — anbieten. Und niemals denselben Text an mehrere gleichzeitig, mit
sichtbarem Verteiler schon gar nicht.

---

## 1. fotoespresso (Jürgen Gulbins / Steffen Körber)

*Warum:* kostenloses deutschsprachiges PDF-Magazin, technisch fundiert,
regelmäßig Workflow- und Lightroom-Themen. Nimmt Fachbeiträge von Lesern.
Aktuelle Kontaktadresse auf fotoespresso.de nachsehen.

**Betreff:** Themenvorschlag: Ordnerstruktur einer gewachsenen
Lightroom-Bibliothek nachträglich umbauen

> Sehr geehrte Redaktion,
>
> ich lese fotoespresso seit Jahren und möchte Ihnen einen Beitrag anbieten.
>
> Mein Lightroom-Classic-Masterkatalog war über die Jahre in eine Handvoll
> riesiger Jahresordner hineingewachsen: 51.049 Fotos, 2,36 TB. Der Wunsch
> nach einer Struktur nach Jahr, Monat und Tag scheitert in dieser Größe an
> allen drei üblichen Wegen — Verschieben im Finder zerreißt den Katalog,
> Ziehen im Ordner-Bedienfeld dauert Tage, Neuimport verliert die
> Entwicklungsarbeit.
>
> Ich habe mir daraufhin ein Werkzeug geschrieben, das beides in einem Zug
> macht: Dateien verschieben und die Ordnereinträge im Katalog umschreiben.
> Es ist frei und quelloffen (LR-FolderCraft), aber das ist nicht der
> eigentliche Stoff für einen Artikel. Interessanter fände ich:
>
> - **wie eine Lightroom-Classic-Katalogdatei aufgebaut ist** und warum das
>   Verschieben von Ordnern sie zerreißt — mit einem Blick in die Tabellen;
> - **welche Ordnerstruktur überhaupt sinnvoll ist** und warum die Antwort
>   davon abhängt, ob man über Datum, Kamera oder Thema sucht;
> - **wie man einen solchen Umbau sicher macht**: Probelauf, Sicherung,
>   Reihenfolge der Schritte, Wiederanlauf nach Abbruch, Rücknahme.
>
> Das Werkzeug wäre dabei ein Beispiel, nicht das Thema. Wenn Ihnen eine
> andere Zuschneidung lieber ist, richte ich mich gern danach.
>
> Umfang nach Ihrem Wunsch, Bildmaterial und Bildschirmfotos kann ich
> beisteuern. Ich schreibe das ohne kommerzielles Interesse; das Werkzeug ist
> kostenlos und bleibt es.
>
> https://andy-freund.gitlab.io/LR-CompanionSuite
>
> Mit freundlichen Grüßen
> Andreas Freund

---

## 2. Victoria Bampton — „The Lightroom Queen"

*Warum:* schreibt das Standardwerk zu Lightroom Classic und betreibt das
Forum, in dem dieses Problem am häufigsten auftaucht. **Zuerst im Forum
auftreten und dort mitarbeiten, erst danach schreiben** — eine Mail von einem
unbekannten Namen ist Werbung, eine von jemandem, der seit Wochen dort
sinnvoll antwortet, ist ein Hinweis.

**Subject:** A free tool for the "reorganise my folders" question, if it is of use to you

> Dear Victoria,
>
> I have been reading your forum while sorting out my own catalog, and the
> question that brought me there comes up regularly: how to reorganise a large
> folder tree without breaking the catalog. The honest answer — drag them in
> the Folders panel — stops being practical somewhere in the tens of
> thousands.
>
> That was my situation at 51,049 photos, so I wrote a tool that moves the
> files and rewrites the catalog's folder records in one operation. It is free
> and open source, and I have nothing to sell.
>
> I am not asking you to endorse it, and I would not expect you to recommend
> anything that writes into a catalog without looking at it yourself. What I
> would value is your judgement: whether the safety design is sound enough to
> mention when the question next comes up.
>
> The design in one paragraph: the dry run is the default and writes nothing;
> the catalog is backed up and verified first; files move before the catalog
> is committed, each move journalled, so an interruption leaves the catalog
> intact and a resume can go either way; every run is exactly reversible from
> its journal. I migrated my own library and reversed it many times, comparing
> ten catalog tables, all 51,049 paths and every file on disk against a
> baseline. Byte-identical each round.
>
> Documentation is complete in English and German:
> https://andy-freund.gitlab.io/LR-CompanionSuite
>
> If it is not something you want to point people at, that is entirely fair —
> I will not ask twice.
>
> With thanks for the forum,
> Andreas Freund

---

## 3. DOCMA / c't Fotografie — Kurzanschrift

*Warum:* deutschsprachige Fachredaktionen mit Lightroom-Leserschaft. Kurz
halten; Redaktionen lesen die ersten drei Zeilen.

**Betreff:** Freies Werkzeug für ein häufiges Lightroom-Problem — Hinweis für die Redaktion

> Sehr geehrte Redaktion,
>
> ein Hinweis ohne kommerzielles Interesse: Für das verbreitete Problem, die
> Ordnerstruktur einer gewachsenen Lightroom-Classic-Bibliothek nachträglich
> umzubauen, ohne die Katalogverknüpfung zu verlieren, gibt es seit kurzem ein
> freies, quelloffenes Werkzeug — LR-FolderCraft. Ich habe es geschrieben,
> weil ich das Problem selbst hatte: 51.049 Fotos in fünf Jahresordnern.
>
> Es verschiebt die Dateien und schreibt die Ordnereinträge im Katalog in
> einem Zug um, mit Probelauf, geprüfter Katalogsicherung, Journal,
> Wiederanlauf nach Abbruch und vollständiger Rücknahme. Deutsche Oberfläche
> und deutsche Dokumentation, macOS und Windows, kostenlos.
>
> https://andy-freund.gitlab.io/LR-CompanionSuite
>
> Für Rückfragen, eine Vorführung oder einen Fachbeitrag stehe ich gern zur
> Verfügung.
>
> Mit freundlichen Grüßen
> Andreas Freund
