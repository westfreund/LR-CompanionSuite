# Prompts

**Revision r1.0.5 · Build date 2026-08-22**

This document preserves the request that created LR-FolderCraft, a generic
prompt for regenerating a comparable tool from scratch, and the context needed
to resume development.

---

## 1. The original prompt (verbatim, German)

Recorded exactly as given on 2026-08-22.

```text
LR-FolderCraft
22.8.26

Problemstellung:
ich nutze lightroom classic auf diesem Rechner. Unterschiedliche Bibliotheken
kommen zum Einsatz.
Eine private HAuptbibliothek ist mittlerweile sehr angewachsen.
Es gibt nur nach Jahren aufgeteilte Verzeichnisse. Darin liegen dann einige
tausende Bilder.
Nun würde ich gerne die Bilder eines Jahres in einzelne separate Tagesordner
umsortieren und die entsprechenden Fotos dorthin verschieben lassen.

Ziel:
Da das Problem sicher häufiger besteht, würde ich gerne ein Tool mit dir
entwickeln, dass diese Aufgabe übernimmt.
Wichtig ist dabei, dass Die Verbindung zur Lightroom-Bibliothek nicht verloren
geht, da es ja mehrere Bearbeitungen, virtuelle Kopien, etc, geben kann.

Umsetzung:
Das Tool sollte also über eine API von Lightroom eine Datei anhand ihres
Aufnahmedatums in einen ggf. zu erstellenden Ordner verschieben können.
Die Ordnerstruktur soll angepasst werden können.
Mögliche kombinierbare Kriterien wären:
- Kameramodell
- Datum Jahr, Monat, Tag oder Kalenderwoche

Es sollen mehrere Gruppierungsebenen möglich sein.

Das Tool hätte ich gerne in Python erstellt, sodass es auf allen Plattformen
zum Einsatz kommen kann.
Die lokale Instanz wird im aktuell geöffneten VS Code Fenster im entsprechenden
Ordner liegen. Bitte hierzu alle notwendigen Verbindungen, Einstellungen, etc.
vornehmen.
Der Projektordner ist unter home /Projekte/LR-FolderCraft. So möchte ich auch
das Repository nennen.

Das Tool soll öffentlich unter meinen GITLAB Account veröffentlicht werden.

Eine umfassende Dokumentation ist anzufertigen.
Darunter den ursprünglichen Prompt.
Dann einen generischen Prompt der ein späteres neues generieren ermöglicht.
Außerdem alle Daten die notwendig sind, um die Weiterentwicklung an der
unterbrochenen Stelle fortzusetzen.
Als Sprachen sind immer Englisch und Deutsch zu verwenden (doppelte
Dokumentenhaltung).
Eine Strukturbeschreibung ist ebenfalls wichtig.
Eine umfassende Installationsanleitung und Installationsscripts für Windows und
MacOS erstellen.

Offene Punkte und eine FAQ sind ebenfalls vorzubereiten, damit wir
Anknüpfungspunkte haben.

Die Dokumentation bitte in einer geeigneten Weise strukturieren.

Alle Zwischenstände sind automatisch zu comitten und zu pushen.
Das Tool soll über eine TUI verfügen, die später um eine GUI erweitert werden
kann.
Ein Debug-Modus soll tieferen Einblick in die Prozesse geben, damit man
Fehlersuche betreiben kann.
Ein Logfile ist zu erstellen, in dem jeder durchgeführte Script-Schritt
dokumentiert wird.

Eine eindeutige Revisionierung ist notwendig. Jede Feature-Erweiterung ist eine
große Änderung.

Das Tool soll immer die Revision und das Erstellungsdatum anzeigen.

Lizenz ist GPL v3 sowie MIT.

Fragen bitte eindeutig formulieren. Für Struktur- und Ablaufideen bin ich offen
und dankbar.

Für einen Versuch liegt auf einem externen Datenträger eine Kopie einer
Lightroom-Bibliothek.
/Volumes/1TB-2/Lightroom/2019/2019.lrcat
```

### Clarifying questions asked, and the answers given

| Question | Answer |
| --- | --- |
| Where should the new day folders be created? | **Freely configurable, both possible** — implemented as `in-place` (default) and `new-tree`. |
| Which TUI framework? | **Textual** — widgets, mouse support, a path to a web/GUI front end. |
| Minimum Python version? | **3.9+**, so macOS's own `/usr/bin/python3` works with no installation. |
| How far to go with the sample catalog? | **Analysis and dry-run only.** The live run stays with the user. |

---

## 2. Generic prompt for regenerating the tool

Use this to have a comparable tool built from scratch, in another language or
with another stack. It captures the requirements and, importantly, the hard-won
findings — so the same discoveries do not have to be made again.

````text
Build a cross-platform command line tool with a text user interface that
reorganises the folder structure of an Adobe Lightroom Classic library, without
breaking the catalog's connection to the image files.

## Problem

A Lightroom Classic library has grown into a few year folders, each holding
thousands of images. The user wants them re-sorted into subfolders by capture
date, camera model or ISO calendar week, with several grouping levels freely
combinable. Develop settings, virtual copies, collections, keywords and history
must all survive.

## Essential technical background (do not re-derive this)

* Lightroom Classic has NO API for moving photos between folders. The Lua SDK
  can read photos and metadata but cannot move them. The only automatable route
  is editing the catalog's SQLite database directly, with Lightroom closed.
* The catalog `.lrcat` is SQLite. The relevant tables:
  - `AgLibraryRootFolder(id_local, id_global, absolutePath, name,
    relativePathFromCatalog)` — `absolutePath` has a TRAILING SLASH.
  - `AgLibraryFolder(id_local, id_global, parentId, pathFromRoot, rootFolder,
    visibility)` — `pathFromRoot` is '' for the root folder itself, otherwise a
    POSIX relative path WITH a trailing slash ('2019/01/03/'). UNIQUE index on
    (rootFolder, pathFromRoot). `parentId` chains folders together.
  - `AgLibraryFile(id_local, id_global, baseName, extension, folder,
    idx_filename, lc_idx_filename, lc_idx_filenameExtension, originalFilename,
    sidecarExtensions)` — UNIQUE index on (lc_idx_filename, folder).
  - `Adobe_images(id_local, captureTime, fileFormat, masterImage, rootFile,
    copyName, ...)` — `rootFile` points at `AgLibraryFile.id_local`;
    `masterImage` non-NULL marks a virtual copy.
  - `AgHarvestedExifMetadata(image, cameraModelRef, cameraSNRef, lensRef,
    dateYear, dateMonth, dateDay)` joined to `AgInternedExifCameraModel`,
    `AgInternedExifCameraSN`, `AgInternedExifLens` by id.
  - `Adobe_variablesTable` holds `Adobe_entityIDCounter` — the catalog-wide
    counter Lightroom allocates every `id_local` from. New rows MUST take their
    ids from it and advance it; anything else eventually collides.
* A file's absolute path is
  `AgLibraryRootFolder.absolutePath + AgLibraryFolder.pathFromRoot + AgLibraryFile.idx_filename`.
* `captureTime` is a local, timezone-less ISO string with a variable number of
  fractional digits: '2019-01-03T17:42:29.18'. Parse tolerantly.
* `id_global` values are uppercase, dashed UUIDs (36 characters).
* Changing ONLY `AgLibraryFolder` rows and `AgLibraryFile.folder` preserves
  everything, because every other table refers to the unchanged
  `AgLibraryFile.id_local` / `Adobe_images.id_local`. Virtual copies share their
  master's file row and therefore follow automatically. Previews are keyed by
  image UUID, not by path.
* Lightroom holds `<Catalog>.lrcat.lock` while a catalog is open. Refuse to run.
* On filesystems without POSIX advisory locking — exFAT and FAT, i.e. most
  external photo drives — SQLite's `mode=ro` fails with "unable to open database
  file". Fall back to `immutable=1`, which is safe once you know no one else is
  writing.

## Pitfalls that WILL bite you

1. On case-insensitive filesystems (macOS, Windows, exFAT), probing both
   `name.xmp` and `name.XMP` finds the SAME file twice and you will try to move
   it twice. Match against a real directory listing instead.
2. Re-running on an already sorted library nests the structure inside itself if
   the anchor is computed as the common parent folder — that parent IS a target
   folder after the first run. Detect an anchor whose tail equals what the
   structure renders and step back. Runs must be idempotent.
3. Re-parenting a file and then renaming it as two statements violates the
   UNIQUE index on (lc_idx_filename, folder) in between. Change folder and name
   in ONE statement, defer rows that still collide, and break genuine rename
   cycles with temporary names.
4. Do not use the file modification time as a default date source. It is
   usually the copy date, and it misfiles photos silently.
5. ISO weeks: pair `{iso_week}` with `{iso_year}`, never with the calendar
   year. 30 December 2019 is week 1 of 2020.
6. **Preserve SQLite storage classes.** `Adobe_variablesTable.value` is declared
   without a type, so it has BLOB affinity and keeps exactly what you give it.
   Lightroom stores `Adobe_entityIDCounter` as a REAL; writing it back as a
   string (`repr(float)`, `str(...)`, an f-string) produces a value that reads
   identically, passes `integrity_check`, shows no difference in a row-value
   comparison — and makes Lightroom refuse to open the catalog. Lightroom's own
   repair copies the value through unchanged, so it repairs the catalog into a
   byte-identical file over and over. Bind numbers as numbers, and verify with
   `typeof()` after writing. Test for type drift explicitly: it is invisible to
   every other check.

## Functional requirements

* Folder structures as an ordered list of levels; each level a template of
  literal text plus placeholders. Unlimited levels, freely combinable.
* Placeholders for year, 2-digit year, month, day, hour, minute, month name,
  short month, quarter, ISO week, ISO year, weekday, day of year, camera model,
  camera slug, camera serial, lens, file format, extension, original folder.
* Ready made presets (day, year/month/day, year/week, camera/day, ...).
* Two placement modes: build the structure below the current folder, or build a
  new tree elsewhere and register it as an additional root folder.
* Selection by root folder, catalog folder, file extension.
* Handle photos with no capture date (unsorted folder / skip / abort).
* Handle name collisions (rename with catalog update / skip / abort). Never
  overwrite an existing file.
* Move XMP sidecars with their photo, both naming conventions
  (`IMG.xmp` and `IMG.CR2.xmp`), renaming them alongside.
* Sanitise folder names for Windows, macOS and Linux: illegal characters,
  trailing dots, reserved device names (CON, LPT1, ...), length limit, optional
  ASCII folding.
* Reusable configuration profiles.

## Non-functional requirements

* Python, cross-platform, minimum version = the one the target OS ships.
* A dry run that writes absolutely nothing and shows the complete plan; export
  as JSON and CSV.
* Safety, in this order: pre-flight checks → verified catalog backup → staged
  catalog transaction → journalled file moves → commit LAST → verification.
  Automatic rollback of both database and filesystem on any failure. A separate
  undo command driven by the journal.
* Same-volume moves via atomic rename; cross-volume via copy, checksum compare,
  then delete, with a free-space pre-check.
* A log file recording every executed step, numbered, plus a debug mode with
  source locations and SQL.
* A TUI, structured so a GUI can be added later: no core module may know about
  a user interface.
* Unique revisioning where every feature extension is a MAJOR bump. Revision
  and build date shown in every interface and every log header, from a single
  source of truth.
* Documentation in English and German, kept in parallel: overview, installation,
  usage, structures, how it works, safety, architecture, development
  continuation, versioning, FAQ, open issues, prompts.
* Installation scripts for macOS, Linux and Windows creating an isolated
  virtual environment.
* Tests against a synthetic catalog so no Lightroom installation is required.
* Dual licence MIT OR GPL-3.0-or-later.

## Working method

Ask clear questions where two readings would lead to materially different work.
Verify against a real catalog read-only first. Never run a live migration on the
user's library without explicit consent. Commit and push at every milestone.
````

---

## 3. Resuming development

The context needed to continue is kept in
[development.md](development.md) — current state, what is *not* done, the test
strategy, where to make which change, and the prepared GUI seam.
[open-issues.md](open-issues.md) holds the prioritised backlog, the decisions
already taken and the questions still open.

### The short version

```bash
git clone https://gitlab.com/andy-freund/LR-FolderCraft.git
cd LR-FolderCraft && python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[dev]' && pytest        # expect 181 passing
```

Then read, in this order:

1. `docs/en/development.md` — where things stand
2. `docs/en/open-issues.md` — what to do next (start at O-1)
3. `docs/en/how-it-works.md` — the catalog internals
4. `src/lrfoldercraft/planner.py` — the heart of the tool

### Prompt for resuming with an AI assistant

```text
Continue work on LR-FolderCraft, a Python tool that reorganises Adobe Lightroom
Classic folder trees by rewriting the .lrcat SQLite catalog while moving the
files. The repository is at https://gitlab.com/andy-freund/LR-FolderCraft.

Read these first: docs/en/development.md (current state and what is NOT done),
docs/en/open-issues.md (the backlog, with items numbered O-1 onwards) and
docs/en/how-it-works.md (the catalog internals and the execution order).

Conventions: Python 3.9 baseline with `from __future__ import annotations`;
no core module may import from cli or tui; every state change goes through
logging_setup.step(); every feature extension is a MAJOR version bump; all
documentation exists in English and German and both must be updated together;
commit and push at every milestone.

Before changing the executor, make sure
tests/test_executor.py::test_rollback_restores_everything_when_a_move_fails
still passes — it is the most important test in the suite.

<state what you want done>
```
