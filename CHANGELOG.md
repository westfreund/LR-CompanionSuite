# Changelog

All notable changes to LR-FolderCraft are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows the project rule that **every feature extension is a major
change** — see [docs/en/versioning.md](docs/en/versioning.md).

Alle wesentlichen Änderungen an LR-FolderCraft sind hier dokumentiert. Die
Versionierung folgt der Projektregel, dass **jede Feature-Erweiterung eine
große Änderung** ist — siehe [docs/de/versionierung.md](docs/de/versionierung.md).

---

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
- 233 tests, 88 % coverage, built on a synthetic catalog fixture so no
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
