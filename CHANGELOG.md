# Changelog

All notable changes to LR-FolderCraft are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows the project rule that **every feature extension is a major
change** — see [docs/en/versioning.md](docs/en/versioning.md).

Alle wesentlichen Änderungen an LR-FolderCraft sind hier dokumentiert. Die
Versionierung folgt der Projektregel, dass **jede Feature-Erweiterung eine
große Änderung** ist — siehe [docs/de/versionierung.md](docs/de/versionierung.md).

---

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
- 175 tests, 88 % coverage, built on a synthetic catalog fixture so no
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
