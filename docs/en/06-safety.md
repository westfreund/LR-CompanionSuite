# Safety and recovery

**Revision r17.0.1 · Build date 2026-08-24**

> This tool edits your Lightroom catalog database and moves your photographs.
> It is built carefully and it is tested, but **keep an independent, verified
> backup of both the catalog and the images before your first real run.**

## Before you start

1. **Quit Lightroom Classic.** Not minimised — quit.
2. **Back up the catalog** yourself, in addition to what the tool does. In
   Lightroom: `File ▸ Back Up Catalog…`, or simply copy the `.lrcat` file.
3. **Back up the photos**, or at least confirm your existing backup ran.
4. **Try it on a copy first.** Copy a catalog and a few hundred images to a
   scratch location, run the whole thing there, open the result in Lightroom.
5. **Run `plan` and read it.** Especially the target folder list and the
   warnings.

## The seven layers

### 1. Pre-flight checks

Before anything is written:

| Check | Blocks the run? |
| --- | --- |
| `lightroom-closed` — no `.lrcat.lock` file | yes |
| `catalog-writable` — the file exists and is writable | yes |
| `catalog-side-files` — an interrupted `-journal` | warning |
| `id-counter-type` — catalog damaged by LR-FolderCraft 1.0.0–1.0.4 | warning |
| `target-writable` — the target exists (or can be created) and is writable | yes |
| `free-space` — 105 % of the cross-volume data volume | yes |
| `backup-space` — room for the catalog backup | yes |
| `work-present` — is there anything to do at all | warning |
| `missing-sources` — catalog entries with no file on disk | warning, or error when *every* file is missing |

### 2. Verified catalog backup

The catalog is copied into the backup directory under a timestamped name, and
both copies are SHA-256 compared. If they differ the run stops immediately.

```
~/Library/Application Support/LR-FolderCraft/backups/2019-20260822-162631.lrcat
```

Put backups on a different drive from the catalog:

```bash
export LRFC_BACKUP_DIR=/Volumes/Backup/lrfc
```

`--no-backup` exists, but a run without a backup cannot be undone with
`lrfc undo`. It is not worth it.

### 3. Staged catalog transaction

Every catalog change is made inside one transaction that is **not committed**
until every file has been moved successfully. Discarding it costs nothing and
leaves the database file byte-identical.

### 4. Journalled file moves

Each move is recorded, flushed and `fsync`ed *before* it is attempted. See
[08-how-it-works.md](08-how-it-works.md#the-journal).

### 5. Automatic rollback

If any move fails — disk full, permissions, a disconnected drive — the tool:

1. rolls back the catalog transaction,
2. moves every already-moved file back to where it came from,
3. removes the directories it created,
4. records all of it in the journal,
5. reports what was restored.

This is covered by a test that injects a failure at file 4 of 6 and asserts
that both the catalog and the filesystem come back exactly as they were.

### 6. Never overwrite

`_move_file` refuses to write to a path that already exists, even if the
planner did not see that file. Collisions are resolved by renaming (with the
catalog updated to match) or by skipping — never by overwriting.

### 7. Verification

After the commit, every moved file's catalog path is compared with reality.
Problems are listed and exit code `4` is returned.

## Never delete `.lrcat-wal`

Lightroom catalogs run in **WAL mode**. `<catalog>.lrcat-wal` and
`<catalog>.lrcat-shm` are ordinary working files, not leftovers: the WAL holds
committed transactions that have not yet been folded back into the `.lrcat`
file. Deleting a non-empty write-ahead log **throws those transactions away**.

LR-FolderCraft checkpoints the WAL into the catalog when it commits, so after a
successful run the `.lrcat` stands on its own. If you ever find a non-empty
`-wal`, open and close the catalog once in Lightroom instead of removing
anything.

A `<catalog>.lrcat-journal` file is a different thing: it means a
rollback-journal transaction was interrupted. Also do not delete it — SQLite
uses it to undo the incomplete change.

## Recovery

### The run failed and rolled back itself

Nothing to do. The catalog and the files are as they were. Read the log, fix
the cause, run again.

### The run succeeded but you want it back

```bash
lrfc undo /path/to/<catalog>-<timestamp>.lrfc-journal.jsonl
```

Files go back to their original locations, empty directories are removed and
the catalog is restored from the backup that run wrote. The journal path is
printed at the end of every run.

### The run was interrupted (power cut, forced quit)

Because the catalog is committed last, an interruption almost always leaves the
catalog untouched while some files have already moved.

1. **Do not open Lightroom yet.**
2. Look at the journal — the last `move-done` tells you how far it got.
3. If there is no `catalog-commit` line, the catalog is unchanged. Run
   `lrfc undo JOURNAL` to put the files back, then start over.
4. If `catalog-commit` is there, the run essentially completed; run
   `lrfc plan` again to confirm, and check the report.

### Lightroom shows photos as missing

That means catalog and disk disagree. Restore the catalog backup the run made:

```bash
cp ~/Library/Application\ Support/LR-FolderCraft/backups/<name>-<stamp>.lrcat /path/to/your.lrcat
```

Then `lrfc plan` to see the current state before trying again.

You can also reconnect inside Lightroom: right-click the folder in the Folders
panel, choose **Find Missing Folder…** and point at the new location. That
works, but restoring the backup is cleaner.

### The catalog is damaged

Restore the backup. If you skipped it, Lightroom's own backups are in
`<Catalog folder>/Backups/`; open the newest and let Lightroom check integrity.

## What the tool will not do

- It will not run while Lightroom has the catalog open.
- It will not overwrite an existing file.
- It will not touch `Adobe_images` or any develop, keyword or collection table.
- It will not delete a photo. Ever. There is no code path that deletes an image
  file except removing the source after a *verified* cross-volume copy.
- It will not delete a root-level folder row.
- It will not write anything at all during `info`, `folders` or `plan`.

## Reporting a problem

Include:

1. the log file (`~/Library/Logs/LR-FolderCraft/`), ideally from a `--debug` run,
2. the plan as JSON (`lrfc plan ... --json > plan.json`),
3. the journal, if a run had started,
4. `lrfc --version` and your Lightroom Classic version.

Do not send the catalog itself — it contains the paths of all your images.
