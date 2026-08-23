# Architecture

**Revision r16.0.0 · Build date 2026-08-23**

## Guiding rule

**No core module knows about a user interface.** Everything below `cli.py` and
`tui/` is pure logic operating on data objects. That is what makes a future GUI
a matter of writing another front end, not another implementation.

```
                    ┌──────────┐   ┌──────────┐   ┌──────────┐
   front ends       │  cli.py  │   │  tui/    │   │  gui/    │
                    └────┬─────┘   └────┬─────┘   └────┬─────┘
                         └──────────────┼──────────────┘
                                        ▼
                    ┌────────────────────────────────────────┐
   orchestration    │  planner.build_plan  →  Plan           │
                    │  safety.preflight    →  PreflightResult│
                    │  executor.execute    →  RunResult      │
                    └───────────────┬────────────────────────┘
                                    ▼
                    ┌───────────────────────────┬────────────┐
   domain           │  rules  (templates)       │  config    │
                    └───────────────┬───────────┴────────────┘
                                    ▼
                    ┌────────────────────────────────────────┐
   persistence      │  catalog/  db · model · reader · writer│
                    │  journal · logging_setup               │
                    └────────────────────────────────────────┘
```

Data flows one way: `Settings` → `Plan` → `RunResult`. Each is a plain data
object that can be serialised, printed, stored and diffed.

## Repository layout

```
LR-FolderCraft/
├── README.md  README.de.md          project front pages, EN and DE
├── CHANGELOG.md                     revision history
├── LICENSE  LICENSE-MIT  LICENSE-GPL-3.0
├── pyproject.toml                   packaging, entry points, ruff, pytest
├── requirements.txt requirements-dev.txt
├── .gitlab-ci.yml                   lint, tests on 3.9-3.13, build
│
├── src/lrfoldercraft/
│   ├── version.py                   revision, build date, banner  (single source)
│   ├── logging_setup.py             log file, --debug, numbered STEP trail
│   ├── config.py                    Settings, validation, JSON profiles
│   ├── rules.py                     tokens, presets, sanitising
│   ├── folders.py                   classifies the folders a library already has
│   ├── planner.py                   Plan, PlannedMove, anchors, conflicts
│   ├── safety.py                    pre-flight checks
│   ├── executor.py                  backup, transaction, moves, rollback, undo
│   ├── journal.py                   append-only JSON-Lines run journal
│   ├── report.py                    text / JSON / CSV rendering, bilingual
│   ├── cli.py                       argparse front end
│   ├── catalog/
│   │   ├── db.py                    connections, validation, id allocation
│   │   ├── model.py                 RootFolder, Folder, Photo, CatalogInfo
│   │   ├── reader.py                every read query
│   │   └── writer.py                every write statement
│   ├── tui/
│   │   ├── app.py                   the Textual application
│   │   └── app.tcss                 its stylesheet
│   └── gui/
│       ├── app.py                   the Qt main window
│       ├── workers.py               catalog / plan / apply on worker threads
│       └── i18n.py                  interface strings, EN and DE
│
├── tests/                           270 tests, synthetic catalog fixture
├── install/                         installers for macOS, Linux, Windows
└── docs/  en/  de/  images/         this documentation, in both languages
```

## Module responsibilities

### `version.py`

The single source of truth for the revision, build date, codename and the
catalog schema versions this revision was verified against. Every UI surface
and every log header reads from here — nothing hard-codes a version string.

### `logging_setup.py`

Configures a package logger with two handlers: a file handler that always gets
everything from INFO (DEBUG with `--debug`, including source locations and SQL),
and a console handler that is quiet by default. `step()` emits numbered
`STEP nnn` lines that form the audit trail of a run.

### `config.py` — `Settings`

One frozen-in-intent dataclass holding everything that determines what a run
does. `validate()` raises a `ConfigError` describing the first problem.
Profiles are plain JSON — no third-party parser on the 3.9 baseline. A profile
deliberately never stores `dry_run`, so loading one cannot start a live run.

### `rules.py`

Pure functions, no I/O. Token definitions with bilingual descriptions, twelve
presets, template validation, rendering and portable name sanitising. This is
the module to extend when adding a new grouping criterion.

### `folders.py`

Pure classification, no I/O and no policy. Recognises a date at the start of a
folder name, compares it against the granularity the structure asks for, and
carries the vocabulary of possible decisions with bilingual labels. It never
decides: that is the caller's job.

### `catalog/`

- `db.py` — opening (read-only vs read-write), schema validation, lock
  detection, id allocation from `Adobe_entityIDCounter`, the exFAT read-only
  fallback.
- `model.py` — `RootFolder`, `Folder`, `Photo`, `CatalogInfo` and the capture
  time parser that tolerates Lightroom's format variants.
- `reader.py` — every read query, degrading gracefully when an older schema
  lacks a table.
- `writer.py` — the only place that writes: `ensure_folder`, `move_row`,
  `rename_file`, `prune_empty_folders`, `ensure_root_folder`.

### `planner.py`

The heart. Given a reader and settings it produces a `Plan`: one `PlannedMove`
per file with its status (`move`, `renamed`, `stay`, `skip-*`), the target
path, sidecars, size and whether it crosses a volume boundary. It also resolves
the anchor, detects collisions case-insensitively and aggregates statistics.
Reads the filesystem, writes nothing.

### `safety.py`

Independent checks returning bilingual `Check` objects. Separate from the
planner so a front end can show them live while the user is still choosing.

### `executor.py`

The only module that changes anything. Owns the ordering described in
[08-how-it-works.md](08-how-it-works.md#the-execution-order), the rollback, the
cross-volume verified copy and `undo`.

### `report.py`

All rendering, no dependencies. Text (EN/DE), JSON and CSV.

## Key data objects

```python
Settings      # what to do        -> config.py
Plan          # what would happen -> planner.py
  .moves      #   List[PlannedMove]
  .stats      #   PlanStats
  .warnings   #   List[str]
RunResult     # what happened     -> executor.py
PreflightResult
CatalogInfo
```

## Design decisions worth knowing

| Decision | Reason |
| --- | --- |
| No dependency for the CLI | works on a stock Python; the TUI is an extra |
| Python 3.9 baseline | macOS ships 3.9; `from __future__ import annotations` covers the syntax gap |
| `str.format()` over f-strings in messages | keeps log calls lazy and the 3.9 target honest |
| Plan and execution split | the plan is reviewable, exportable and testable without side effects |
| Journal before action | a crash leaves a usable record |
| Commit the catalog last | the database is never ahead of the disk |
| Ids from `Adobe_entityIDCounter` | anything else eventually collides with Lightroom's own allocation |
| Case-insensitive path keys | macOS, Windows and exFAT are case insensitive |
| Bilingual at the data level | `Check` and `TokenSpec` carry both languages, so no translation layer is needed |

## Adding a new grouping criterion

1. Add a `TokenSpec` to `TOKEN_SPECS` in `rules.py`, with both descriptions.
2. Produce the value in `TokenContext.values()`.
3. If it needs new catalog data, extend `Photo` and the query in `reader.py`.
4. Optionally add a preset to `PRESETS` and `PRESET_DESCRIPTIONS`.
5. Add a case to `tests/test_rules.py::test_tokens_render`.
6. Bump the **major** version — see [11-versioning.md](11-versioning.md).

Nothing else needs to change: the CLI, the TUI, the docs tables and the help
output are all generated from `TOKEN_SPECS`.

## The three front ends

`cli.py`, `tui/` and `gui/` all reach the core through the same three calls and
nothing else:

```python
with open_catalog(path) as conn:
    plan = build_plan(CatalogReader(conn), settings, decide=ask_about_folder)
checks = preflight(plan)
result = execute(plan, settings, progress=callback)
```

`decide` is optional and is how a front end asks the operator about a folder
without the planner knowing a user interface exists. It receives a `FolderCase`
and returns an action or `None` for "use the default". `progress` is called as
`progress(done, total, message)` while files move.

### `gui/`

PySide6, an optional extra, imported lazily by `cli.cmd_gui` so a missing
dependency produces an explanation rather than a traceback.

- `app.py` builds one window and collects a `Settings` from its widgets. The
  option defaults are read from a fresh `Settings()` rather than from the first
  entry of each list, so the interface cannot drift away from the documented
  defaults -- a test asserts it.
- `workers.py` runs catalog reading, planning and execution on `QThread`s and
  reports back through signals. It also owns the rule that a thread must be
  waited for, not abandoned: destroying a running `QThread` aborts the process,
  which is what happens when a window is closed mid-run.
- `i18n.py` holds every interface string in both languages.

## Root folders and scopes

A catalog may hold several root folders, possibly on different drives. Each
becomes a `RootScope` with its own anchor, because "the folder every selected
photo sits under" only means anything within one root. Every `PlannedMove`
carries the index of its scope, and the executor creates folder rows and
directories per scope -- all inside the one transaction and the one journal.

With `new-tree` placement every source root shares a single scope: everything
is consolidated into the new tree regardless of where it came from.
