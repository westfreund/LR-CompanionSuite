# Architektur

**Revision r16.0.1 · Build-Datum 2026-08-23**

## Leitregel

**Kein Kernmodul weiß etwas von einer Benutzeroberfläche.** Alles unterhalb von
`cli.py` und `tui/` ist reine Logik auf Datenobjekten. Genau das macht eine
spätere GUI zu einer Frage des zusätzlichen Frontends, nicht der zweiten
Implementierung.

```
                    ┌──────────┐   ┌──────────┐   ┌──────────┐
   Frontends        │  cli.py  │   │  tui/    │   │  gui/    │
                    └────┬─────┘   └────┬─────┘   └────┬─────┘
                         └──────────────┼──────────────┘
                                        ▼
                    ┌────────────────────────────────────────┐
   Orchestrierung   │  planner.build_plan  →  Plan           │
                    │  safety.preflight    →  PreflightResult│
                    │  executor.execute    →  RunResult      │
                    └───────────────┬────────────────────────┘
                                    ▼
                    ┌───────────────────────────┬────────────┐
   Domäne           │  rules  (Templates)       │  config    │
                    └───────────────┬───────────┴────────────┘
                                    ▼
                    ┌────────────────────────────────────────┐
   Persistenz       │  catalog/  db · model · reader · writer│
                    │  journal · logging_setup               │
                    └────────────────────────────────────────┘
```

Die Daten fließen in eine Richtung: `Settings` → `Plan` → `RunResult`. Jedes
davon ist ein einfaches Datenobjekt, das sich serialisieren, ausgeben,
speichern und vergleichen lässt.

## Verzeichnisaufbau

```
LR-FolderCraft/
├── README.md  README.de.md          Projektstartseiten, EN und DE
├── CHANGELOG.md                     Revisionshistorie
├── LICENSE  LICENSE-MIT  LICENSE-GPL-3.0
├── pyproject.toml                   Paketierung, Einstiegspunkte, ruff, pytest
├── requirements.txt requirements-dev.txt
├── .gitlab-ci.yml                   Lint, Tests auf 3.9-3.13, Build
│
├── src/lrfoldercraft/
│   ├── version.py                   Revision, Build-Datum, Banner  (einzige Quelle)
│   ├── logging_setup.py             Logdatei, --debug, nummerierte STEP-Spur
│   ├── config.py                    Settings, Validierung, JSON-Profile
│   ├── rules.py                     Platzhalter, Vorlagen, Namensbereinigung
│   ├── folders.py                   erkennt vorhandene Ordner und ihre Art
│   ├── planner.py                   Plan, PlannedMove, Anker, Konflikte
│   ├── safety.py                    Vorprüfungen
│   ├── executor.py                  Backup, Transaktion, Bewegungen, Rollback, Undo
│   ├── journal.py                   Append-only-Journal im JSON-Lines-Format
│   ├── report.py                    Text-/JSON-/CSV-Ausgabe, zweisprachig
│   ├── cli.py                       argparse-Frontend
│   ├── catalog/
│   │   ├── db.py                    Verbindungen, Validierung, ID-Vergabe
│   │   ├── model.py                 RootFolder, Folder, Photo, CatalogInfo
│   │   ├── reader.py                sämtliche Leseabfragen
│   │   └── writer.py                sämtliche Schreibanweisungen
│   ├── tui/
│   │   ├── app.py                   die Textual-Anwendung
│   │   └── app.tcss                 deren Stylesheet
│   └── gui/
│       ├── app.py                   das Qt-Hauptfenster
│       ├── workers.py               Katalog / Plan / Ausführung in Threads
│       └── i18n.py                  Oberflächentexte, EN und DE
│
├── tests/                           270 Tests, synthetischer Katalog als Fixture
├── install/                         Installationsskripte für macOS, Linux, Windows
└── docs/  en/  de/  images/         diese Dokumentation, in beiden Sprachen
```

## Zuständigkeiten der Module

### `version.py`

Die einzige Quelle für Revision, Build-Datum, Codename und die
Katalogschemaversionen, gegen die diese Revision verifiziert wurde. Jede
Oberfläche und jeder Logkopf liest von hier — nirgends steht eine Version fest
verdrahtet.

### `logging_setup.py`

Konfiguriert einen Paketlogger mit zwei Handlern: einem Datei-Handler, der ab
INFO immer alles bekommt (mit `--debug` ab DEBUG, inklusive Quellorten und
SQL), und einem Konsolen-Handler, der standardmäßig still ist. `step()` gibt
nummerierte `STEP nnn`-Zeilen aus, die die Prüfspur eines Laufs bilden.

### `config.py` — `Settings`

Eine Dataclass, die alles enthält, was einen Lauf bestimmt. `validate()` wirft
einen `ConfigError`, der das erste Problem beschreibt. Profile sind schlichtes
JSON — kein Fremdparser auf der 3.9-Basis. Ein Profil speichert bewusst nie
`dry_run`, sodass sein Laden keinen scharfen Lauf starten kann.

### `rules.py`

Reine Funktionen, keine Ein-/Ausgabe. Platzhalterdefinitionen mit
zweisprachigen Beschreibungen, zwölf Vorlagen, Template-Validierung, Rendering
und portable Namensbereinigung. Dieses Modul erweitert man für ein neues
Gruppierungskriterium.

### `folders.py`

Reine Klassifikation, ohne Ein-/Ausgabe und ohne Politik. Erkennt ein Datum am
Anfang eines Ordnernamens, vergleicht es mit der von der Struktur verlangten
Granularität und hält das Vokabular der möglichen Entscheidungen samt
zweisprachiger Beschriftung bereit. Entschieden wird hier nie — das ist Sache
des Aufrufers.

### `catalog/`

- `db.py` — Öffnen (lesend vs. schreibend), Schemavalidierung,
  Sperrerkennung, ID-Vergabe aus `Adobe_entityIDCounter`, der
  exFAT-Lesefallback.
- `model.py` — `RootFolder`, `Folder`, `Photo`, `CatalogInfo` und der Parser
  für Aufnahmezeiten, der Lightrooms Formatvarianten toleriert.
- `reader.py` — sämtliche Leseabfragen, mit sanftem Rückfall, wenn einem
  älteren Schema eine Tabelle fehlt.
- `writer.py` — der einzige Ort, der schreibt: `ensure_folder`, `move_row`,
  `rename_file`, `prune_empty_folders`, `ensure_root_folder`.

### `planner.py`

Das Herzstück. Aus Reader und Einstellungen entsteht ein `Plan`: ein
`PlannedMove` je Datei mit Status (`move`, `renamed`, `stay`, `skip-*`),
Zielpfad, Sidecars, Größe und der Angabe, ob eine Volume-Grenze überschritten
wird. Es löst außerdem den Anker auf, erkennt Konflikte
groß-/kleinschreibungsunabhängig und aggregiert die Statistik. Liest das
Dateisystem, schreibt nichts.

### `safety.py`

Unabhängige Prüfungen, die zweisprachige `Check`-Objekte liefern. Vom Planer
getrennt, damit ein Frontend sie schon während der Auswahl anzeigen kann.

### `executor.py`

Das einzige Modul, das etwas verändert. Verantwortlich für die in
[08-funktionsweise.md](08-funktionsweise.md#die-ausführungsreihenfolge) beschriebene
Reihenfolge, den Rollback, die verifizierte Volume-übergreifende Kopie und
`undo`.

### `report.py`

Sämtliche Ausgabe, ohne Abhängigkeiten. Text (EN/DE), JSON und CSV.

## Zentrale Datenobjekte

```python
Settings      # was zu tun ist       -> config.py
Plan          # was geschehen würde  -> planner.py
  .moves      #   List[PlannedMove]
  .stats      #   PlanStats
  .warnings   #   List[str]
RunResult     # was geschehen ist    -> executor.py
PreflightResult
CatalogInfo
```

## Erwähnenswerte Entwurfsentscheidungen

| Entscheidung | Begründung |
| --- | --- |
| Keine Abhängigkeit für die CLI | läuft auf einem nackten Python; die TUI ist ein Extra |
| Python-3.9-Basis | macOS liefert 3.9 mit; `from __future__ import annotations` schließt die Syntaxlücke |
| `str.format()` statt f-Strings in Meldungen | hält Logaufrufe lazy und das 3.9-Ziel ehrlich |
| Trennung von Plan und Ausführung | der Plan ist prüfbar, exportierbar und testbar, ohne Nebenwirkungen |
| Journal vor der Aktion | ein Absturz hinterlässt eine brauchbare Aufzeichnung |
| Katalog zuletzt bestätigen | die Datenbank ist der Platte nie voraus |
| IDs aus `Adobe_entityIDCounter` | alles andere kollidiert irgendwann mit Lightrooms eigener Vergabe |
| Pfadschlüssel ohne Groß-/Kleinschreibung | macOS, Windows und exFAT unterscheiden sie nicht |
| Zweisprachigkeit auf Datenebene | `Check` und `TokenSpec` tragen beide Sprachen, eine Übersetzungsschicht entfällt |

## Ein neues Gruppierungskriterium ergänzen

1. `TokenSpec` in `TOKEN_SPECS` in `rules.py` ergänzen, mit beiden
   Beschreibungen.
2. Den Wert in `TokenContext.values()` erzeugen.
3. Werden neue Katalogdaten gebraucht: `Photo` und die Abfrage in `reader.py`
   erweitern.
4. Optional eine Vorlage in `PRESETS` und `PRESET_DESCRIPTIONS` ergänzen.
5. Einen Fall in `tests/test_rules.py::test_tokens_render` ergänzen.
6. Die **Hauptversion** erhöhen — siehe [11-versionierung.md](11-versionierung.md).

Mehr ist nicht nötig: CLI, TUI, die Tabellen in der Dokumentation und die
Hilfeausgabe werden alle aus `TOKEN_SPECS` erzeugt.

## Die drei Frontends

`cli.py`, `tui/` und `gui/` erreichen den Kern über dieselben drei Aufrufe und
sonst nichts:

```python
with open_catalog(pfad) as conn:
    plan = build_plan(CatalogReader(conn), settings, decide=frage_zu_ordner)
checks = preflight(plan)
result = execute(plan, settings, progress=callback)
```

`decide` ist optional und der Weg, auf dem ein Frontend den Operator zu einem
Ordner befragt, ohne dass der Planer von einer Oberfläche wüsste. Es bekommt
einen `FolderCase` und liefert eine Aktion oder `None` für „Vorgabe". `progress`
wird als `progress(done, total, message)` während des Verschiebens aufgerufen.

### `gui/`

PySide6, ein optionales Extra, von `cli.cmd_gui` verzögert importiert — eine
fehlende Abhängigkeit erzeugt also eine Erklärung statt eines Tracebacks.

- `app.py` baut ein Fenster und sammelt daraus ein `Settings`. Die Vorgabewerte
  der Optionen stammen aus einem frischen `Settings()` statt aus dem ersten
  Listeneintrag, damit die Oberfläche nicht von den dokumentierten Vorgaben
  abdriften kann — ein Test prüft das.
- `workers.py` führt Katalog lesen, Planen und Ausführen in `QThread`s aus und
  meldet über Signale zurück. Dort steht auch die Regel, dass ein Thread
  abgewartet und nicht fallen gelassen wird: Ein laufender `QThread`, der
  zerstört wird, bricht den Prozess ab — genau das passiert beim Schließen des
  Fensters während eines Laufs.
- `i18n.py` hält alle Oberflächentexte in beiden Sprachen.

## Stammordner und Scopes

Ein Katalog kann mehrere Stammordner enthalten, auch auf verschiedenen
Laufwerken. Jeder wird zu einem `RootScope` mit eigenem Anker, denn „der
Ordner, unter dem alle ausgewählten Fotos liegen" ergibt nur innerhalb eines
Stammordners einen Sinn. Jede `PlannedMove` trägt den Index ihres Scopes, und
der Executor legt Ordnerzeilen und Verzeichnisse je Scope an — alles in
derselben Transaktion und demselben Journal.

Bei `new-tree` teilen sich alle Quell-Stammordner einen einzigen Scope: Es wird
alles in den neuen Baum zusammengeführt, unabhängig von der Herkunft.
