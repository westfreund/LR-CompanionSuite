# Prompts

**Revision r10.0.0 · Build-Datum 2026-08-23**

Dieses Dokument bewahrt die Anfrage, aus der LR-FolderCraft entstanden ist,
einen generischen Prompt zur Neuerzeugung eines vergleichbaren Werkzeugs sowie
den Kontext, der zum Fortsetzen der Entwicklung nötig ist.

---

## 1. Der ursprüngliche Prompt (wörtlich)

Aufgezeichnet exakt so, wie er am 22.08.2026 gestellt wurde.

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

### Gestellte Rückfragen und die gegebenen Antworten

| Frage | Antwort |
| --- | --- |
| Wo sollen die neuen Tagesordner angelegt werden? | **Frei konfigurierbar, beides möglich** — umgesetzt als `in-place` (Standard) und `new-tree`. |
| Welches TUI-Framework? | **Textual** — Widgets, Mausunterstützung, ein Weg zu einem Web-/GUI-Frontend. |
| Welche Python-Mindestversion? | **3.9+**, damit macOS' eigenes `/usr/bin/python3` ohne Installation genügt. |
| Wie weit beim Beispielkatalog gehen? | **Nur Analyse und Trockenlauf.** Der scharfe Lauf bleibt beim Anwender. |

---

## 2. Generischer Prompt zur Neuerzeugung

Damit lässt sich ein vergleichbares Werkzeug von Grund auf neu bauen, in einer
anderen Sprache oder mit einem anderen Technologiestapel. Er enthält die
Anforderungen und — wichtiger — die mühsam erarbeiteten Erkenntnisse, damit
dieselben Entdeckungen nicht noch einmal gemacht werden müssen.

Der Prompt ist bewusst auf Englisch gehalten, weil er sich an ein
Entwicklungswerkzeug richtet und die technischen Begriffe (Tabellen- und
Spaltennamen des Lightroom-Katalogs) ohnehin englisch sind.

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

7. **A catalog can have several root folders**, possibly on different drives.
   "The folder every selected photo sits under" only means something within one
   root, so compute one anchor per root, not one for the run. Deriving the
   anchor from a *subset* of the photos (say, only the ones being consolidated)
   looks tidier and breaks immediately: with a single such photo its own folder
   becomes the anchor and it is sorted into itself.
8. **Do not create a target directory with `mkdir(parents=True)`.** Create each
   missing level separately and record each one, or an undo cannot take the
   tree back down. And do create the target root itself -- naming a location
   that does not exist yet is the whole point of a "new tree" mode.
9. **On macOS, leave AppleDouble companions alone.** On exFAT/FAT the kernel
   moves `._X` together with `X` on rename; moving it yourself collides with
   what the system already did. On other platforms `._X` is an ordinary file a
   rename leaves behind, so there it must be carried along.
10. **Lightroom catalogs run in WAL mode.** Checkpoint after committing so the
    `.lcat` file is self-contained, and never describe `.lrcat-wal` as a stale
    file that can be deleted -- a non-empty one holds committed transactions.
    Beware that a read opened with `immutable=1` ignores the WAL entirely, so a
    verification pass using it validates a view the application will not see.

## Requirements a grown library adds

Real libraries are not one flat folder. They hold topic folders (`Urlaub`) and
folders that already carry a date (`2019-04-15 Ostern in Tirol`). What should
happen to each is a judgement call, so:

* Classify folders: a name that *begins* with a date is a dated folder; a date
  in the middle is ignored, because guessing there invents intent.
* A dated folder only counts as "already sorted" when its granularity is at
  least as fine as the structure asks for. A folder called `2019` is no answer
  to a request for day folders.
* Offer three decisions -- what to do with a topic folder, with a dated folder,
  and with a photo inside a dated folder whose own date does not match -- each
  with a default, a global switch, and a per-folder override.
* Let the operator decide per folder. The planner must not prompt: front ends
  pass a callback that receives one folder and returns an action, so the core
  stays free of any user interface. Never put the anchor folder itself up for a
  decision.
* Provide five actions, not three. Beyond "pull the photos up" (consolidate),
  "build the structure inside this folder" (sort-inside), "do not touch"
  (leave) and "honour the date in the name" (keep), a grown library needs
  **rebuild this folder where it stands**: the structure replaces the folder
  below its own parent, so `raw2026/2026-06-28 Makro Blume im Garten` becomes
  `raw2026/2026-06-28/Makro Blume im Garten`. Neither consolidate (which drags
  the photos out of `raw2026`) nor sort-inside (which nests the structure below
  the folder) can express that, and it is the single most-asked-for shape.
* Offer a token for the descriptive text after a folder name's date prefix.
  Without it the text is simply lost when a dated folder is rebuilt. And make a
  level whose tokens all render empty **collapse** rather than become a folder
  called `unnamed`, or the token is unusable as a level of its own.
* **Rules, not one answer per folder.** Asking about thirty-nine folders when
  the operator has four intentions is a failure of interface design. Provide an
  ordered `PATTERN=ACTION` list, first match wins, where a pattern is a path
  glob (covering everything below the folder it names) or a keyword selecting
  by kind: every folder, dated, dated-with-text, dated-without-text, undated.
  Precedence: per-folder override, then rule, then the interactive question,
  then the kind default -- and a rule must *silence* the question it already
  answers. Record on each folder which rule decided it, and show that, or a
  rule set cannot be checked before it is run.
* **Offer an action that moves a folder across unchanged.** Not every folder
  wants sorting: a curated selection, an external drop box, a job folder with
  an order of its own should arrive at the new location with its name, its
  contents and its sub-structure intact. Render no structure for it, keep its
  path relative to the source root, and ignore the run's anchor -- burying the
  folder one level deeper is not what "move this there" means. Sorting in place
  then leaves such a folder where it is, which is the honest outcome.
* **Match a rule pattern at any depth.** A bare name that only matches folders
  sitting directly below the root is not how anyone reads `_extern=leave`; test
  the pattern against the folder path, its name, and every partial path ending
  at it, and let it cover the subtree below.
* **A "leave mismatched photos alone" setting must govern the rebuild action
  too.** This is easy to miss and was missed: a shoot running past midnight
  leaves photos whose own date disagrees with the folder naming the session.
  Rebuilding by each photo's own date tears the session in two. Under that
  setting a stray photo must follow its *folder's* date instead of its own.
  Test it against real data -- a synthetic catalog will not have the case, and
  the fault is invisible in the counts.

## Front ends

Build the core so that a command line, a text interface and a graphical one all
reach it through the same three calls and nothing else: build a plan, run the
pre-flight checks, execute with a progress callback. Then:

* Take every interface default from the same settings object the command line
  uses. Reading the first entry of each dropdown instead lets the graphical
  front end quietly disagree with the documentation, per option, invisibly.
  Write a test that compares them.
* Run long work on threads and *wait* for them when the window closes.
  Destroying a running thread aborts the process -- which is exactly what a
  user closing the window mid-run does.
* Use the operating system's own folder chooser: it already has a "new folder"
  button, and re-implementing one is wasted work.
* Give the rule list a small editable table above the folder table, with the
  folder table gaining a column naming the rule that decided each row. Order is
  meaning, so provide move-up and move-down. Changing a rule must clear the
  manual decisions it might have made and replan, or the display stops matching
  what would run.
* **Offer to collect what the catalog does not know.** A library worked in for
  years accumulates files the application cannot see, and they are why a
  reorganised tree still has odds and ends in it. Sweeping them into one named
  folder, keeping the path each came from, is worth having -- but define the
  exclusions before the inclusions, and test each: a file referenced from any
  root, a sidecar of a catalogued photo, the application's own working data,
  the filesystem's scribbles, the collection folder itself, and any tree the
  run is sorting into. Recognise a sidecar from the catalogued file beside it
  rather than from the move, or a second run sweeps up what the first one
  sorted -- a photo already in the right place makes no move. Default it off:
  it moves files nobody asked about.
* **State the preconditions and make the operator tick, not click.** Before the
  first destructive run, report what was actually found -- the schema version
  read, whether every root resolves and with how many files, when the last
  backup was made. A dialog that recites three rules gets dismissed by reflex;
  one that says "51,049 of 51,049 files found" is read. Put the refusal of a
  blocking finding in the rule rather than in whether the control is clickable:
  a disabled checkbox can still be ticked from code.
* **Put undo in every front end, not only on the command line.** A rollback
  that exists but cannot be reached from the window the operator actually uses
  is a rollback they will not have when they need it. Reverse the file moves in
  the order they were journalled, remove the directories the run created if
  they are empty, and restore the catalog from that run's backup -- the
  database and the filesystem have to move back together or neither has moved
  back. Say so in the confirmation, and require the application to be closed.
* Write a human-readable record of each run **beside the library**, named after
  the tool, the date and the catalog. The machine-readable journal lives in the
  backup directory and exists for undo; this is the one a person finds months
  later. Write it in the run's `finally` so a failed run is recorded too, make
  it switchable and relocatable, and make it strictly non-fatal: by the time it
  is written the photos are already moved and verified, so a full disk must
  leave a note on the result, never fail the run.

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
* A text interface and a graphical one, both structured so that no core module
  knows a user interface exists.
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

## 3. Entwicklung fortsetzen

Der zum Weiterarbeiten nötige Kontext steht in
[10-entwicklung.md](10-entwicklung.md) — aktueller Stand, was *nicht* erledigt ist,
Teststrategie, wo welche Änderung hingehört und die vorbereitete
GUI-Schnittstelle. [13-offene-punkte.md](13-offene-punkte.md) enthält den
priorisierten Rückstand, die bereits getroffenen Entscheidungen und die noch
offenen Fragen.

### Die Kurzfassung

```bash
git clone https://gitlab.com/andy-freund/LR-FolderCraft.git
cd LR-FolderCraft && python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[dev]' && pytest        # 270 Tests sollten grün sein
```

Danach in dieser Reihenfolge lesen:

1. `docs/de/10-entwicklung.md` — wo die Dinge stehen
2. `docs/de/13-offene-punkte.md` — was als Nächstes ansteht (beginnend bei O-1)
3. `docs/de/08-funktionsweise.md` — die Katalog-Interna
4. `src/lrfoldercraft/planner.py` — das Herzstück des Werkzeugs
5. `src/lrfoldercraft/folders.py` — wie vorhandene Ordner eingeordnet werden
6. `src/lrfoldercraft/gui/app.py` — das Qt-Frontend, falls die Oberfläche dran ist

### Prompt zum Fortsetzen mit einem KI-Assistenten

```text
Setze die Arbeit an LR-FolderCraft fort, einem Python-Werkzeug, das
Ordnerstrukturen von Adobe Lightroom Classic neu sortiert, indem es den
SQLite-Katalog (.lrcat) umschreibt und dabei die Dateien verschiebt. Das
Repository liegt unter https://gitlab.com/andy-freund/LR-FolderCraft.

Lies zuerst: docs/de/10-entwicklung.md (aktueller Stand und was NICHT erledigt
ist), docs/de/13-offene-punkte.md (der Rückstand, Punkte ab O-1 nummeriert) und
docs/de/08-funktionsweise.md (Katalog-Interna und Ausführungsreihenfolge).

Konventionen: Python-3.9-Basis mit `from __future__ import annotations`; kein
Kernmodul darf aus cli oder tui importieren; jede Zustandsänderung läuft über
logging_setup.step(); jede Feature-Erweiterung erhöht die Hauptversion; die
gesamte Dokumentation existiert auf Englisch und Deutsch und beide Fassungen
sind gemeinsam zu pflegen; zu jedem Meilenstein committen und pushen.

Bevor du den Executor änderst, stelle sicher, dass
tests/test_executor.py::test_rollback_restores_everything_when_a_move_fails
weiterhin grün ist — es ist der wichtigste Test der Suite.

<hier beschreiben, was zu tun ist>
```
