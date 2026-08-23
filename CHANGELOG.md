# Changelog

All notable changes to LR-FolderCraft are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows the project rule that **every feature extension is a major
change** — see [docs/en/versioning.md](docs/en/versioning.md).

For **why** each change was made, and what happened between the releases, see
[docs/en/history.md](docs/en/history.md) /
[docs/de/historie.md](docs/de/historie.md).

Alle wesentlichen Änderungen an LR-FolderCraft sind hier dokumentiert. Die
Versionierung folgt der Projektregel, dass **jede Feature-Erweiterung eine
große Änderung** ist — siehe [docs/de/versionierung.md](docs/de/versionierung.md).

---

## [6.0.0] — 2026-08-23 — "Klartext"

Saying what the plan could not decide on its own.

### Added

- **A findings report** (`exceptions_report.py`). A plan is not just a count of
  files to move; it also holds the cases the tool decided for you. Reporting
  them as a single "skipped: 43" is the same as not reporting them. Each cause
  now gets its own entry naming the number of files, examples, and — the point —
  **the option that governs it**, so the answer is one setting away rather than
  a search through the documentation.

  Levels: BLOCKS (a file the catalog names but the disk does not have, a failed
  pre-flight check), Warning, Exception (no usable date, a name collision, the
  extension filter, a stray date inside a dated folder), Note (renames, folders
  no rule spoke about).

- **The graphical interface shows them in a table** between the settings and
  the folder table: level colour-coded, the governing option and its current
  value in their own columns, and the affected files listed when a row is
  selected. The counts line above it is now only counts — warnings used to be
  crammed onto it. The command line plan report gained the same list.

- **A project history** in both languages,
  [docs/en/history.md](docs/en/history.md) /
  [docs/de/historie.md](docs/de/historie.md), reconstructed retroactively. The
  changelog says what changed; this says why, and what happened in between —
  the decisions and their reasoning, the tests against real libraries, and the
  four occasions on which the tool was wrong in a way that mattered. None of it
  is recoverable from the code.

- **`scripts/make_screenshots.py`.** The images in the READMEs had gone stale
  within one revision because there was no way to remake them. The script
  builds a demonstration catalog, drives both interfaces against it and writes
  all four files.

### Fixed

- **Global command line flags were ignored before the subcommand.** Every
  sub-parser redeclares `--lang`, `--debug`, `--verbose`, `--quiet`,
  `--log-file` and `--log-dir`, and a sub-parser's default overwrites what the
  top level already parsed. `lrfc --lang de plan X` therefore ran in English and
  `lrfc --debug plan X` ran without debug logging — since r1.0.0. Found by
  reading the German output of the new findings report and noticing it was
  English. There is now a test per flag and position.

- **German messages used ASCII substitutes for umlauts** — "ueber Mitternacht",
  "zusammenfuehren", "Uebersprungen" — while the graphical interface's own text
  used real ones, so the two disagreed on screen. All of it now uses proper
  umlauts.

---

## [5.0.0] — 2026-08-23 — "Regelwerk"

Expressing what a grown library actually needs. Prompted by a master catalog
whose 39 folders held four distinct intentions and could not be described with
the vocabulary the tool had.

### Added

- **`resort`, a fifth folder action.** Rebuilds a folder *where it stands*,
  below its own parent: `raw2026/2026-06-28 Makro Blume im Garten` becomes
  `raw2026/2026-06-28/Makro Blume im Garten`. Neither `consolidate` (which
  drags the photos out of `raw2026`) nor `sort-inside` (which nests the
  structure below the folder itself) could express this.

- **The `{folder_label}` token** — the descriptive text after a folder name's
  date prefix, empty when there is none. Together with `resort` this is what
  splits a dated folder into a date level and a description level instead of
  losing the description.

- **Levels that render empty now collapse** instead of becoming a folder called
  `unnamed`, which is what makes `{folder_label}` usable as a level of its own:
  `{yyyy}-{mm}-{dd}/{folder_label}` gives a plain day folder for a photo whose
  folder carries no text.

- **An ordered rule list**, `PATTERN=ACTION`, first match wins, via `--rule`
  and the `folder_rules` setting. Patterns are path globs — covering everything
  below the folder they name — or the keywords `dated`, `dated+label`,
  `dated-only`, `plain` and `*`. Precedence: per-folder override, then rule,
  then the interactive question, then the kind default. A rule silences the
  question it already answers, and each folder records which rule decided it.

  The master catalog's 39 folders are now five lines rather than 39 dropdowns.

- **A rule table in the graphical interface**, above the folder table, with
  add, remove and reorder. The folder table gains a "Decided by" column naming
  the rule that settled each row, or marking the decision as the user's own.
  Changing a rule clears the manual decisions it might have made and replans.

- **A move log beside the library** (O-24). A plain text record named after the
  tool, the date and the catalog, written next to the `.lrcat` file: every
  source and target path, the rules used, the backup and journal locations, and
  a summary. The JSON-Lines journal remains what it was — a machine-readable
  record for undo; this is the one a person reads months later. Written in the
  run's `finally`, so a failed run is recorded too, and strictly non-fatal: an
  unwritable directory leaves a note on the result and nothing else.
  `--no-move-log` and `--move-log-dir` control it.

- **A preparation page** in both languages (O-21, O-22):
  [before-you-start.md](docs/en/before-you-start.md) /
  [vorbereitung.md](docs/de/vorbereitung.md) — reconnecting a library whose
  drive was renamed or restored, and converting the catalog to the installed
  Lightroom Classic first. Linked from both indexes.

### Fixed

- **`resort` tore sessions in two.** A shoot that runs past midnight leaves
  photos whose own date disagrees with the folder naming the session. Rebuilding
  such a folder filed each photo by its own date, which is precisely what
  `--mismatch-action leave` says must not happen. That setting now governs
  `resort` as well, so a stray photo follows its folder's date and the session
  stays whole.

  Found by simulating the new rules against the real master catalog before
  writing a line of it to disk: 1 of 23 sessions split, the twelve frames of
  `2026-06-27 Test 150mm Spiegelobjektiv` that were shot the evening before.
  The fault is invisible in the counts and does not occur in any synthetic
  catalog.

---

## [4.0.2] — 2026-08-23

### Fixed

- **A repeated `new-tree` run was not a no-op.** Whether a photo already sits
  where it belongs was decided by comparing paths *and* requiring in-place
  placement. Running the same `new-tree` migration twice therefore planned
  every file as a move onto itself, which then tripped the "never overwrite an
  existing file" guard and rolled the whole run back. The check is now purely
  about the paths, as it should always have been.

  Found by verifying a real run: after 9,452 files had been sorted into a new
  tree, planning the identical run again still offered to move all of them.

### Added

- **A guard that only four tables may ever be written.** The promise that
  develop settings, virtual copies, collections and keywords survive rests on
  the tool touching nothing but `AgLibraryFolder`, `AgLibraryFile`,
  `AgLibraryRootFolder` and `Adobe_variablesTable`. A test now hashes every
  table before and after a run and fails if anything else differs.

  Motivated by that same verification: six further tables had changed in the
  live catalog, and the only way to answer "was that us?" was to grep the
  source for SQL statements. It was not — the user had edited a photo in
  Lightroom to check that access worked. But that should be a property the
  suite enforces, not an argument made after the fact.

### Verified against

- The reference library reorganised through the graphical interface with
  `{camera_slug}/{yyyy}/{mm}/{dd}` and `new-tree` placement: 9,452 files into a
  second root folder in ten seconds, every file present at an unchanged size,
  `integrity_check` ok, `foreign_key_check` clean, 210 folder rows with no
  orphans and no bad prefixes, all 9,452 catalog paths resolving, the id
  counter still REAL, and the write-ahead log checkpointed away.

- **And then actually used.** Editing a photo in Lightroom afterwards shows the
  whole chain intact: the file is found at its new path, its develop history
  from 2022 is still there, a new step ("convert to black and white") is added
  on top, and the result is written back. A migrated library is not merely
  readable, it is fully workable.

## [4.0.1] — 2026-08-23

### Fixed

- **A catalog that has lost track of its photos is now named as such.** When
  the drive is mounted under a different name than the catalog records — which
  happens whenever a volume is renamed or a library is restored elsewhere — the
  pre-flight reported "No write permission for /Volumes", because the search
  for an existing parent directory had walked all the way up. That sends the
  operator looking for a permission problem that is not there.

  With in-place placement the target *is* the catalog's own root folder, so a
  missing one now says exactly that, names the path, and points at Lightroom's
  Find Missing Folder.

- **Every file missing is an error, not a warning.** A few strays in a large
  library are normal and must not block a run. All of them missing means the
  catalog is disconnected from its photos, and sorting it would be meaningless.
  The warning also states the total now ("3 of 9,452"), so the scale is visible
  at a glance.

  Found while preparing a test: a restored 2019 library recorded its root as
  `/Volumes/LR_Archiv/...` while the drive was mounted as `/Volumes/1TB-2`.

## [4.0.0] — 2026-08-23 — "Prüfstand"

The installer now verifies what it installed, repairs what is missing, updates
what has aged, and only advertises interfaces that actually work.

### Added

- **Verification.** Each optional interface is one importable module and one
  pip requirement, and the installer imports it after installing. Nothing is
  reported as ready that cannot be imported.

- **`--check` / `-Check`** verifies an existing installation and reinstalls
  whatever is missing, without touching what works. It also reports when a
  newer version of a component is available.

- **The installation remembers its components.** A `components` file in the
  install prefix records which interfaces were asked for, so a repair can tell
  "never asked for" from "installed and broken" — the two are indistinguishable
  by import alone.

- **Updating.** Re-running the installer upgrades anything already present that
  has gone out of date, instead of leaving an old version in place.

- **The environment is reused** rather than deleted and rebuilt, which makes
  adding the graphical interface later a matter of seconds. `--recreate` /
  `-Recreate` forces a clean build.

- **It asks about the graphical interface** when run in a terminal and nobody
  said either way. `--with-gui` / `--no-gui` (and `-WithGui` / `-NoGui`) skip
  the question for scripted installs; a non-interactive run never prompts.

### Fixed

- **The installer advertised `lrfc gui` even when it had not installed it.**
  Reported from use: a run without `--with-gui` finished with `lrfc gui` in its
  list of next steps, and the command then said PySide6 was missing. The final
  report now lists only the interfaces that were installed and verified, and
  prints the exact command to add anything that is not there.

- A component that fails to install is named explicitly, with the reason and
  the command to try by hand, rather than being passed over in a run that
  reports success.

## [3.0.2] — 2026-08-23

### Fixed

- **The window did not fit a small screen.** It opened at a fixed 1024x860,
  which is taller than the usable area of a 13-inch laptop once the menu bar
  and the dock are taken off, leaving the Plan and Apply buttons below the
  bottom edge with no way to reach them.

  The settings now live in a scroll area, and the action row with the progress
  bar sits outside it so it can never be the thing that scrolls away. The
  window opens at the smaller of a comfortable size and the space the screen
  actually offers, and its minimum is 720x420. Settings, folder table and log
  share one splitter, so the space can be given to whichever part is in use.

  Five regression tests: the window never opens larger than the screen, the
  minimum fits a small laptop, the action row stays inside the window at five
  heights down to 420, the settings scroll when they do not fit, and shrinking
  below the minimum is refused.

## [3.0.1] — 2026-08-23

### Fixed

- **The installer left an un-runnable command.** It wrote the launcher into
  `~/.local/bin` and then only *printed* a note that the directory is not on
  the PATH — which macOS never puts there by itself. Reported from a real
  installation: the script finished, said it had verified itself, and the
  terminal answered `lrfc: command not found`.

  The installer now appends the PATH line to the startup file the user's shell
  actually reads (`~/.zshrc`, `~/.bash_profile`/`~/.bashrc`,
  `~/.config/fish/config.fish`, else `~/.profile`), skips it when the directory
  is already listed, and takes exactly that line back out on `--uninstall`,
  leaving the rest of the file untouched. `--no-path` keeps the old
  print-only behaviour.

  On Windows the entry was already added; the uninstaller now removes it again,
  and the message says plainly that an open terminal keeps its old PATH.

- The installation guides and both FAQs explain the "command not found" case,
  including how to tell a PATH problem from a broken installation.

## [3.0.0] — 2026-08-22 — "Weitwinkel"

Two large additions: a graphical interface, and runs that span several root
folders.

### Added

- **A Qt graphical interface**, `lrfc gui`, as the optional `gui` extra.
  One window holds the catalog with a file chooser and a summary, the source
  root folder and extension filters, the target (in place, or a new folder
  picked with the system dialog — its *New Folder* button creates one, and a
  path that does not exist yet is created during the run), the structure with a
  live preview and a placeholder reference, every option, the folders that were
  found with a dropdown each for their decision, a progress bar with a counter,
  and a log. English and German, switchable at any time.

  Catalog reading, planning and execution run on worker threads, so the window
  stays responsive; closing it waits for the work rather than killing it.

- **A run can span several root folders.** Each becomes a `RootScope` with its
  own anchor, and all of them are handled in one transaction and one journal.
  With `new-tree` placement they share a single scope and everything is
  consolidated into the new tree. Verified across two physical volumes.
  Closes O-7.

- Pre-flight now checks every scope: each target must be writable or creatable,
  and free space is summed **per target volume**, so two scopes copying onto
  the same drive cannot both pass while together they do not fit.

- The plan lists every root folder with its anchor when there is more than one,
  in the text report and under `scopes` in the JSON export.

- Installers grew `--with-gui` (macOS/Linux) and `-WithGui` (Windows), and CI
  gained a headless Qt job.

### Fixed

- **The graphical interface used the first entry of each dropdown as its
  default** instead of the documented one, so `subfolder_action` silently
  started at `sort-inside` rather than `consolidate`. Every option default is
  now read from a fresh `Settings()`, and a test compares the two.

- **Closing the window while a worker was running aborted the process.**
  Destroying a running `QThread` does that. Threads are now awaited on close
  and dropped from the list when they finish.

### Changed

- `Plan.root_folder`, `.anchor_segments` and `.target_root_path` are now
  convenience properties for the first scope; `Plan.scopes` is the real model
  and `PlannedMove.scope` says which one a move belongs to.

## [2.0.1] — 2026-08-22

### Fixed

- **A target root that does not exist yet is now created.** Naming a new
  location is the whole point of `--placement new-tree`, but the run aborted
  with `FileNotFoundError` because only the folders *below* the root were
  created. Every missing level is now made, and journalled individually, so a
  rollback or `lrfc undo` takes the whole tree back down again.

- The `target-writable` pre-flight check said "target location is writable" for
  a path that did not exist, because it walked up to the nearest existing
  parent. It now says plainly that the target will be created, and where.

## [2.0.0] — 2026-08-22 — "Wegweiser"

A grown library is not one flat folder. It has topic folders and folders that
already carry a date, and what should happen to them is a judgement call. This
release makes the tool **recognise** those folders and lets the operator decide
— per folder if they want to.

### Added

- **Folder classification.** Every source folder is examined. A name that
  *begins* with a date is a dated folder: `2019-04-15 Ostern in Tirol`,
  `2019_06_01 Hochzeit`, `20190415_Hochzeit`, `2019.03.10`, `2019-04`, `2019`.
  Anything else is a topic folder. A date in the middle of a name is ignored —
  guessing there would invent intent.

- **A dated folder only counts when it is fine enough.** A folder called `2019`
  is no answer to a request for day folders, so it is treated as a topic folder
  and its photos are sorted properly. A day folder does satisfy a request for
  year folders. With a structure that has no date tokens at all, folder dates
  are irrelevant and ignored.

- **Three decisions, each with a default, a global switch and a per-folder
  override:**

  | setting | flag | choices | default |
  | --- | --- | --- | --- |
  | `subfolder_action` | `--subfolder-action` | `consolidate`, `sort-inside`, `leave` | `consolidate` |
  | `dated_folder_action` | `--dated-folder-action` | `keep`, `consolidate`, `sort-inside`, `leave` | `keep` |
  | `mismatch_action` | `--mismatch-action` | `move-out`, `leave` | `move-out` |

  `--folder-action ID=ACTION` decides one catalog folder explicitly and beats
  the defaults. Decisions live in `Settings.folder_actions`, so a profile can
  carry them.

- **Asking the operator.** `lrfc plan|apply --interactive` puts every folder
  that could reasonably go either way to the operator, showing what was found,
  how many photos are affected, how many carry a different date, and which
  option is the default. Enter accepts the default. The planner itself never
  prompts: front ends pass a `decide` callback, so the core stays free of any
  user interface. In the TUI the same choice is made by pressing Enter on a row
  of the folder table, which cycles the decision and re-plans.

- **The plan shows its findings**: which folders exist, what kind each is, how
  many photos, what was decided and whether that came from a default, an
  explicit override or the operator. Also in the JSON export, under `folders`.

### Changed

- **A dated folder's photos now stay put by default.** Previously
  `2019-04-15 Ostern in Tirol` was dissolved into a bare `2019-04-15`, losing
  the description. Photos inside it whose capture date does *not* match still
  move out to their own date folder — a photo filed in the wrong place gets
  corrected. Set `--dated-folder-action consolidate` for the old behaviour, or
  `--mismatch-action leave` to make a dated folder entirely off limits.

- The anchor folder is never offered as a decision and always sorts its own
  photos: "leave subfolders alone" must not silently mean "do nothing at all".

[2.0.0]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v2.0.0

## [1.0.6] — 2026-08-22

### Added

- **Pre-flight now detects a catalog damaged by 1.0.0–1.0.4.** If
  `Adobe_entityIDCounter` has storage class `text` instead of a number, the
  check reports it, names the revisions responsible, and prints the one
  statement that repairs it. Such a catalog cannot be opened by Lightroom at
  all, so reusing it silently would only deepen the confusion.

### Confirmed

The r1.0.5 diagnosis is verified against the reference library: a copy of the
rejected catalog with `Adobe_entityIDCounter` cast back to REAL — and nothing
else changed — opens in Lightroom Classic, with all 9,452 photos selectable in
their new day folders. One value of the wrong SQLite storage class was the
entire fault; the folder reorganisation itself had been correct from the start.

[1.0.6]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.6

## [1.0.5] — 2026-08-22

**Root cause of the failure reported in 1.0.4.** Lightroom Classic could not
open the reorganised catalog because the id counter had changed SQLite storage
class.

### Fixed

- **`Adobe_entityIDCounter` was written back as TEXT instead of REAL.**
  `allocate_ids()` stored the new value with `repr(float)`, producing the string
  `'4914941.0'` where Lightroom keeps the number `4914941.0`.
  `Adobe_variablesTable.value` is declared without a type, so it has BLOB
  affinity and stores exactly what it is handed — the value *reads* the same and
  nothing flags it:

  * `PRAGMA integrity_check` and `foreign_key_check` pass;
  * the schema is unchanged;
  * comparing row values finds no difference, because both sides print
    `4914941.0`;
  * **Lightroom's own catalog repair copies the value through unchanged**, so it
    produced a byte-identical file and failed again — repairing in a loop that
    could never converge.

  The counter is now written back in whatever storage class it already had, and
  `allocate_ids()` re-reads `typeof()` afterwards and aborts the run if it
  changed. Recovering an affected catalog needs one statement:

  ```sql
  UPDATE Adobe_variablesTable
     SET value = CAST(value AS REAL)
   WHERE name = 'Adobe_entityIDCounter';
  ```

### Added

- Three regression tests: the counter keeps REAL, a catalog that genuinely uses
  TEXT is not converted either, and a broad guard that compares the SQLite
  storage class of every column of every row that exists before *and* after a
  run. Type drift is invisible to both value comparison and `integrity_check`,
  so it needs a check of its own.

### How it was found

Two controlled tests separated content from environment: the migrated catalog
on an internal APFS disk still failed to open, while the untouched original on
the same exFAT volume opened fine. That ruled out the filesystem and pointed at
the data — after which comparing `typeof()` against the *original* (rather than
against Lightroom's repair, where both sides were already TEXT) showed the one
differing value.

[1.0.5]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.5

## [1.0.4] — 2026-08-22

Lightroom Classic refused to open the reorganised reference catalog with an
"unexpected error" and quarantined it. Its own repair then produced a catalog
whose **135 tables are byte-for-byte identical in content** to what this tool
had written — every folder row, every file-to-folder mapping, every variable.
The reorganisation was correct; what Lightroom objected to was the state of the
*file*, and the investigation exposed three genuine defects.

### Fixed

- **The catalog is left self-contained after a run.** Lightroom catalogs run in
  WAL mode. A plain commit leaves new data in `<catalog>.lrcat-wal` until
  something checkpoints it, so the `.lrcat` file alone did not describe the
  finished state. `commit()` now runs `PRAGMA wal_checkpoint(TRUNCATE)` and logs
  the outcome, including when the checkpoint reports busy.

- **Verification no longer looks through a blind view.** On filesystems without
  POSIX locking — exFAT, i.e. the drive this library lives on — reads fall back
  to `immutable=1`, and *that mode ignores the write-ahead log entirely*. The
  post-run verification therefore validated the main database file rather than
  what Lightroom would see, and reported "passed" regardless. Connections now
  record whether they ignore the WAL, and verification fails with an explicit
  problem if it had to read past a non-empty one.

- **The pre-flight check no longer gives dangerous advice.** It called
  `.lrcat-wal` and `.lrcat-shm` "stale side files" and suggested clearing them.
  For a WAL-mode catalog they are ordinary working files, and deleting a
  non-empty write-ahead log throws away committed transactions. The check now
  reports how much the catalog depends on its WAL and says never to delete it,
  and warns separately about a `-journal`, which really does indicate an
  interrupted transaction.

- **The test suite no longer writes into the user's directories.** Tests that
  exercised `apply` deposited catalog backups, journals and reports in the
  caller's real LR-FolderCraft configuration directory. An autouse fixture now
  redirects all four location variables into the pytest temp tree.

### Still unexplained

The precise trigger for Lightroom's error could not be determined from outside
the application: the file passed `integrity_check` and `foreign_key_check`, its
schema was identical to the original, and its contents matched Lightroom's own
repair exactly. The defects above are real and were worth fixing on their own
merits, but none of them is *proven* to be the cause.

[1.0.4]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.4

## [1.0.3] — 2026-08-22

### Fixed

- **macOS already moves AppleDouble companions; 1.0.1 moved them a second
  time.** The premise of the previous release was wrong. Measured on an exFAT
  volume: writing an extended attribute to `X.dat` creates `._X.dat`, and after
  `os.replace("X.dat", "sub/X.dat")` the companion has moved to `sub/` on its
  own, with the attributes still readable on the moved file. The kernel's
  AppleDouble emulation handles it transparently.

  The explicit move therefore collided with the file macOS had already placed
  at the target, and aborted the first live run against the reference library
  at file 850 of 9,452. The rollback did its job: 850 files were restored, 152
  directories removed, the catalog transaction discarded, and the library came
  back byte-identical — catalog SHA-256 unchanged, all 9,489 files present with
  identical sizes.

  Companion handling is now platform-aware. On macOS the kernel is left to it.
  On other platforms `._X` is an ordinary file that a rename leaves behind, so
  it is still carried along explicitly to preserve the metadata of a drive that
  will go back to a Mac. Both branches are covered by tests.

[1.0.3]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.3

## [1.0.2] — 2026-08-22

### Fixed

- **The read-only fallback for lock-less filesystems never actually ran.**
  `sqlite3.connect()` is lazy: it opens nothing, so a volume that cannot
  provide SQLite's shared lock — exFAT and FAT, i.e. most external photo
  drives — raises on the first *statement*, not on connecting. The `try` only
  wrapped the connect call, so the `immutable=1` fallback was dead code and the
  failure surfaced as an unhandled `unable to open database file` deep inside
  the caller.

  The fallback is now driven by a probe query. Two regression tests cover it: a
  connection that connects and then refuses every statement must fall back, and
  a genuinely unreadable file must still raise rather than be masked.

  This hid itself for a long time: a stray `.lrcat-shm` file left behind by an
  earlier read-write connection happened to make `mode=ro` succeed. Removing
  that file exposed the defect.

[1.0.2]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.2

## [1.0.1] — 2026-08-22

### Fixed

- **macOS AppleDouble companions are moved with their photo.** On filesystems
  that cannot store extended attributes and resource forks natively — exFAT and
  FAT, which is what most external photo drives use — macOS keeps them in a
  `._<filename>` companion. A plain rename does not carry it, so the companion
  was orphaned in the source folder and the moved file lost its attributes.
  Found on the reference library, where 37 of 9,452 files had one.

  Companions move unconditionally, including with `--no-sidecars`: `._X` is the
  other half of `X`, not an independent document like an XMP sidecar. A renamed
  photo takes its companion under the new name.

[1.0.1]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.1

## [1.0.0] — 2026-08-22 — “Daybreak”

First release. Reorganises a Lightroom Classic folder tree by moving the files
and rewriting the catalog in one reversible operation.

### Added

**Core**
- Direct, narrowly scoped access to the `.lrcat` SQLite database. Only
  `AgLibraryFolder` rows and `AgLibraryFile.folder` (plus the name columns on a
  forced rename) are ever changed. Row ids come from Lightroom's own
  `Adobe_entityIDCounter`.
- Token based folder templates with 25 placeholders across date, camera and
  file categories, and 12 presets. Unlimited grouping levels.
- Bilingual month and weekday names (EN/DE) without a system locale.
- Portable name sanitising for Windows, macOS and Linux, including reserved
  device names, trailing dots and an optional ASCII fold.
- Two placement modes: `in-place` (structure below the current folder) and
  `new-tree` (a fresh tree registered as an additional root folder).
- Selection by root folder, catalog folder and file extension.
- Configurable capture-date resolution (`capture`, `exif-fields`,
  `file-mtime`), collision handling (`rename`, `skip`, `abort`) and
  missing-date handling (`unsorted`, `skip`, `abort`).
- XMP sidecar detection for both naming conventions, moved with their photo and
  renamed alongside it.
- Reusable JSON profiles.

**Safety**
- Eight pre-flight checks before anything is written.
- SHA-256 verified catalog backup.
- Staged catalog transaction committed only after every file has moved.
- Append-only, fsynced JSON-Lines journal.
- Automatic rollback of both the catalog and the filesystem on any failure.
- `lrfc undo` to reverse a completed run.
- Post-run verification of every catalog path against the filesystem.
- Existing files are never overwritten.
- Cross-volume transfers are copy-verify-delete, with a free-space check.

**Interfaces**
- CLI: `info`, `folders`, `plan`, `apply`, `undo`, `profiles`, `tokens`,
  `presets`, `tui`. Plans export as JSON and CSV.
- Textual TUI with a live folder-name preview, target folder table, progress
  bar, log pane, confirmation dialog and EN/DE switching.
- Debug mode and a per-run log file carrying a numbered `STEP` audit trail.

**Project**
- 270 tests, 87 % coverage, built on a synthetic catalog fixture so no
  Lightroom installation is needed.
- GitLab CI: lint, tests on Python 3.9–3.13, a dedicated safety job, build.
- Installers for macOS, Linux and Windows.
- Complete documentation in English and German.
- Dual licensed MIT OR GPL-3.0-or-later.

### Fixed during development

Defects the test suite and the end-to-end runs exposed before release, recorded
because the same traps await anyone working on this kind of tool:

- Sidecars were discovered twice on case-insensitive filesystems, because
  `name.xmp` and `name.XMP` resolve to the same file. Replaced per-name probing
  with a cached, case-insensitive directory index.
- Re-running on an already sorted library nested the structure inside itself.
  The anchor now drops any trailing segments that match a *prefix* of what the
  structure renders — a partial overlap, not just a full one, since a common
  parent folder may cover only the first levels of a multi-level structure.
- Re-parenting a file and renaming it as two statements briefly violated the
  UNIQUE index on `(lc_idx_filename, folder)`. Folder and name now change in one
  statement, with a deferral loop and a temporary-name pass for rename cycles.
- `mkdir(parents=True)` created several directory levels but journalled only the
  leaf, so `undo` left empty intermediates behind. Every created level is now
  journalled.
- `file-mtime` was a default date source. It is usually the copy date, not the
  capture date, and silently misfiled photos. It is now opt-in.

### Verified against

- Lightroom Classic catalog schema **18.0.0** (Lightroom Classic 14), a real
  9,452-file / 337 GiB library on exFAT.
- End-to-end apply / re-plan / undo cycles on reduced working copies (40 and 30
  files, single- and four-level structures): catalog integrity `ok`, foreign key
  check clean, folder tree valid, all paths resolving, virtual copy still
  attached to its master, and a hash over `Adobe_images`,
  `Adobe_imageDevelopSettings`, `AgLibraryKeywordImage` and
  `AgLibraryCollectionImage` **unchanged** before and after. Re-planning after a
  run reports every file as already in place, and `undo` restores the catalog,
  the files and the directory tree exactly.
- The macOS installer, executed for real: install, run from a clean environment
  with no `PYTHONPATH`, read a live catalog, uninstall.
- **A full production migration** (2026-08-22): the reference library's 9,452
  files / 337 GiB reorganised into 152 day folders, then independently checked —
  every file present at an unchanged size, `integrity_check` ok,
  `foreign_key_check` clean, no orphan folders, all catalog paths resolving, all
  32 virtual copies still attached, and the develop/keyword/collection hash
  identical to a pre-run copy. Re-planning afterwards reports nothing to do.

### Known limits

See [docs/en/open-issues.md](docs/en/open-issues.md).

[1.0.0]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.0
