# Development and continuation

**Revision r8.0.1 · Build date 2026-08-23**

This document exists so that work can be picked up later — by you, by someone
else, or by an AI assistant — without reconstructing context from the code.

## Current state

**r1.0.0 is complete and working.** Verified end to end against a real
Lightroom Classic catalog (schema 18.0.0, 9,452 files, 337 GiB, exFAT).

| Area | State |
| --- | --- |
| Catalog read/write | complete, tested |
| Template engine | complete, 25 tokens, 12 presets |
| Planner | complete: anchors, conflicts, sidecars, cross-volume, idempotent |
| Safety | complete: 8 checks, backup, journal, rollback, undo, verification |
| CLI | complete: 9 commands |
| TUI | complete: load, plan, apply, live preview, EN/DE |
| GUI | complete: Qt, all settings, folder decisions, progress |
| Tests | 270 tests, 87 % coverage |
| CI | GitLab, Python 3.9–3.13 |
| Docs | complete, EN and DE |
| Installers | macOS, Linux, Windows |

### What has *not* been done

- The r2.0.0 handling of grown folder structures -- topic folders, dated
  folders, per-folder decisions -- is covered by tests against synthetic
  catalogs but **has not yet met a real library with such a structure**. That is
  the next thing to try.
- **The Windows PowerShell installer has not been executed on Windows.** It was
  written carefully and structurally checked, but no Windows machine was
  available. Treat the first Windows install as a test.
- **A result has not been opened in Lightroom Classic itself.** All verification
  so far is at the database and filesystem level: integrity check, foreign key
  check, folder tree validity, path resolution and an unchanged hash over the
  image, develop, keyword and collection tables. The remaining confirmation is
  visual, in Lightroom.

## Getting set up

```bash
git clone https://gitlab.com/andy-freund/LR-FolderCraft.git
cd LR-FolderCraft
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
pytest
```

Run the tool from the source tree without installing:

```bash
PYTHONPATH=src python3 -m lrfoldercraft info /path/to.lrcat
```

## Test strategy

`tests/conftest.py` builds a **synthetic Lightroom catalog** carrying exactly
the tables the tool touches, with the same column names, the trailing-slash
`pathFromRoot` convention and a working `Adobe_entityIDCounter`. No Lightroom
installation, no fixture downloads, no network.

```python
def test_something(simple_catalog):        # six photos, three days, two cameras
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",))
    ...

def test_custom(builder):                  # build your own case
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="old/",
                      sidecars=["A.xmp"], virtual_copies=2)
```

| File | Covers |
| --- | --- |
| `test_rules.py` | tokens, sanitising, presets, ISO week edges |
| `test_folders.py` | date recognition in folder names, granularity |
| `test_catalog.py` | reader, writer, id allocation, locking, rollback |
| `test_planner.py` | grouping, anchors, conflicts, sidecars, idempotency |
| `test_executor.py` | apply, rollback under injected failure, undo, cycles |
| `test_config.py` | validation, profiles |
| `test_cli.py` | exit codes, output formats, read-only guarantees |
| `test_tui.py` | headless Textual smoke tests |
| `test_gui.py` | headless Qt tests (offscreen platform) |
| `test_version.py` | revision consistency across the repository |

When you touch the executor, keep `test_rollback_restores_everything_when_a_move_fails`
passing. It is the single most important test in the suite.

## Testing against a real catalog safely

Never point a live run at your working library. Make a reduced working copy:

```python
import sqlite3, shutil, os
shutil.copy2("/path/original.lrcat", "/tmp/work/test.lrcat")
c = sqlite3.connect("/tmp/work/test.lrcat")
keep = [ ... 40 file ids ... ]
c.execute("DELETE FROM Adobe_images  WHERE rootFile  NOT IN (...)", keep)
c.execute("DELETE FROM AgLibraryFile WHERE id_local NOT IN (...)", keep)
c.execute("UPDATE AgLibraryRootFolder SET absolutePath = '/tmp/work/images/'")
c.commit(); c.execute("VACUUM"); c.commit()
```

Then copy those 40 image files into `/tmp/work/images/` and run against the
copy. That is exactly how r1.0.0 was validated.

Afterwards, assert the invariants:

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;

-- no orphan folders
SELECT COUNT(*) FROM AgLibraryFolder f WHERE f.pathFromRoot <> ''
  AND NOT EXISTS (SELECT 1 FROM AgLibraryFolder p WHERE p.id_local = f.parentId);

-- every parent path is a prefix of its child
SELECT COUNT(*) FROM AgLibraryFolder f JOIN AgLibraryFolder p ON p.id_local = f.parentId
  WHERE substr(f.pathFromRoot, 1, length(p.pathFromRoot)) <> p.pathFromRoot;

-- every catalog path resolves on disk
SELECT rf.absolutePath || fo.pathFromRoot || f.idx_filename
  FROM AgLibraryFile f
  JOIN AgLibraryFolder fo     ON fo.id_local = f.folder
  JOIN AgLibraryRootFolder rf ON rf.id_local = fo.rootFolder;
```

## Where to make which change

| Task | Files |
| --- | --- |
| New token | `rules.py` (`TOKEN_SPECS`, `TokenContext.values`), `tests/test_rules.py` |
| New preset | `rules.py` (`PRESETS`, `PRESET_DESCRIPTIONS`) |
| New catalog field | `catalog/model.py` (`Photo`), `catalog/reader.py` (`_PHOTO_SELECT`) |
| New CLI option | `cli.py` (`_add_plan_flags`, `settings_from_args`), `config.py` |
| New folder kind or decision | `folders.py`, then `planner._segments_for` |
| New pre-flight check | `safety.py` — return a bilingual `Check` |
| New execution behaviour | `executor.py`, and a matching rollback test |
| New TUI widget | `tui/app.py`, `tui/app.tcss` |
| New GUI control | `gui/app.py`, strings in `gui/i18n.py` |

Every token, preset and check carries both languages in its own definition, so
help output, the docs tables and the TUI update themselves.

## Coding conventions

- Python 3.9 baseline. `from __future__ import annotations` at the top of every
  module; `typing.List`/`Dict`/`Optional` rather than `list[...]`.
- `str.format()` in log and user-facing messages, not f-strings — log calls stay
  lazy and the 3.9 target stays honest.
- Every public function has a docstring saying *why*, not *what*.
- No core module imports from `cli` or `tui`.
- Anything that changes state goes through `logging_setup.step()`.
- `ruff check src tests` and `ruff format --check src tests` before committing.

## Commit and release

Commits are made and pushed at every working milestone. Message style:

```
feat: <what changed>          feature, bump MAJOR
fix: <what was broken>        bug fix, bump PATCH
docs: <what was documented>
refactor: / test: / chore:    bump MINOR at most
release: rX.Y.Z — <summary>
```

Release steps are in [11-versioning.md](11-versioning.md).

## The three front ends

`cli.py`, `tui/` and `gui/` reach the core through the same three calls:

```python
with open_catalog(path) as conn:
    plan = build_plan(CatalogReader(conn), settings, decide=ask_about_folder)
checks = preflight(plan)
result = execute(plan, settings, progress=lambda done, total, msg: ...)
```

Adding a fourth front end means writing those three calls and nothing else. Two
rules the existing ones learned the hard way:

* Take interface defaults from a fresh `Settings()`, never from the first entry
  of a dropdown -- the GUI silently disagreed with the documentation until a
  test caught it.
* Wait for worker threads when the window closes. Destroying a running QThread
  aborts the process.

Run the Qt tests headless with `QT_QPA_PLATFORM=offscreen pytest tests/test_gui.py`.

## Roadmap

See [13-open-issues.md](13-open-issues.md) for the prioritised list.
