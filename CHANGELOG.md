# Changelog

All notable changes to LR-FolderCraft are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows the project rule that **every feature extension is a major
change** — see [docs/en/versioning.md](docs/en/versioning.md).

Alle wesentlichen Änderungen an LR-FolderCraft sind hier dokumentiert. Die
Versionierung folgt der Projektregel, dass **jede Feature-Erweiterung eine
große Änderung** ist — siehe [docs/de/versionierung.md](docs/de/versionierung.md).

---

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
- 153 tests, 88 % coverage, built on a synthetic catalog fixture so no
  Lightroom installation is needed.
- GitLab CI: lint, tests on Python 3.9–3.13, a dedicated safety job, build.
- Installers for macOS, Linux and Windows.
- Complete documentation in English and German.
- Dual licensed MIT OR GPL-3.0-or-later.

### Verified against

- Lightroom Classic catalog schema **18.0.0** (Lightroom Classic 14), a real
  9,452-file / 337 GiB library on exFAT.
- End-to-end run on a 40-file working copy: catalog integrity `ok`, foreign key
  check clean, folder tree valid, all paths resolving, virtual copy still
  attached to its master, and a hash over `Adobe_images`,
  `Adobe_imageDevelopSettings`, `AgLibraryKeywordImage` and
  `AgLibraryCollectionImage` **unchanged** before and after.

### Known limits

See [docs/en/open-issues.md](docs/en/open-issues.md).

[1.0.0]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.0
