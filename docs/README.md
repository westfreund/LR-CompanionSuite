# LR-FolderCraft documentation / Dokumentation

Every document exists in both languages. The two trees are kept in sync:
a change to one must be mirrored in the other.

Jedes Dokument existiert in beiden Sprachen. Die beiden Bäume werden synchron
gehalten: Eine Änderung auf einer Seite ist auf der anderen nachzuziehen.

The number is the weight, not a chapter: the lower it is, the sooner a reader is
likely to need the document. Both languages carry the same numbers, so
`04-usage.md` and `04-bedienung.md` are the same document.

Die Zahl ist die Gewichtung, kein Kapitel: je kleiner sie ist, desto eher wird
das Dokument gebraucht. Beide Sprachen tragen dieselben Nummern, `04-usage.md`
und `04-bedienung.md` sind also dasselbe Dokument.

| # | Topic / Thema | 🇬🇧 English | 🇩🇪 Deutsch |
| --- | --- | --- | --- |
| 01 | Overview / Überblick | [en/01-index.md](en/01-index.md) | [de/01-index.md](de/01-index.md) |
| 02 | Installation | [en/02-installation.md](en/02-installation.md) | [de/02-installation.md](de/02-installation.md) |
| 03 | Before you start / Vorbereitung | [en/03-before-you-start.md](en/03-before-you-start.md) | [de/03-vorbereitung.md](de/03-vorbereitung.md) |
| 04 | Usage / Bedienung | [en/04-usage.md](en/04-usage.md) | [de/04-bedienung.md](de/04-bedienung.md) |
| 05 | Structures / Strukturen | [en/05-structures.md](en/05-structures.md) | [de/05-strukturen.md](de/05-strukturen.md) |
| 06 | Safety / Sicherheit | [en/06-safety.md](en/06-safety.md) | [de/06-sicherheit.md](de/06-sicherheit.md) |
| 07 | FAQ | [en/07-faq.md](en/07-faq.md) | [de/07-faq.md](de/07-faq.md) |
| 08 | How it works / Funktionsweise | [en/08-how-it-works.md](en/08-how-it-works.md) | [de/08-funktionsweise.md](de/08-funktionsweise.md) |
| 09 | Architecture / Architektur | [en/09-architecture.md](en/09-architecture.md) | [de/09-architektur.md](de/09-architektur.md) |
| 10 | Development / Weiterentwicklung | [en/10-development.md](en/10-development.md) | [de/10-entwicklung.md](de/10-entwicklung.md) |
| 11 | Versioning / Versionierung | [en/11-versioning.md](en/11-versioning.md) | [de/11-versionierung.md](de/11-versionierung.md) |
| 12 | History / Historie | [en/12-history.md](en/12-history.md) | [de/12-historie.md](de/12-historie.md) |
| 13 | Open issues / Offene Punkte | [en/13-open-issues.md](en/13-open-issues.md) | [de/13-offene-punkte.md](de/13-offene-punkte.md) |
| 14 | Prompts | [en/14-prompts.md](en/14-prompts.md) | [de/14-prompts.md](de/14-prompts.md) |

`images/` holds the interface screenshots referenced from the READMEs. They are
regenerated with `python scripts/make_screenshots.py`.

`images/` enthält die Oberflächen-Screenshots, auf die die READMEs verweisen.
Sie werden mit `python scripts/make_screenshots.py` neu erzeugt.

## Adding a document / Ein Dokument ergänzen

Give it the next free number if it belongs at the end, or renumber from its
position onward if it belongs in the middle — the number states where it sits in
the reading order, so keeping it truthful is worth a rename. Add it to this
table, to both `01-index.md` files, and write it in **both** languages.

Die nächste freie Nummer vergeben, wenn es ans Ende gehört, sonst ab seiner
Position neu durchnummerieren — die Nummer sagt, wo das Dokument in der
Lesereihenfolge steht, und das wahr zu halten ist eine Umbenennung wert. In
diese Tabelle und in beide `01-index.md` eintragen, und in **beiden** Sprachen
schreiben.
