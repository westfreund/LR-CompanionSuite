# How it works

**Revision r7.1.0 · Build date 2026-08-23**

## Why the catalog has to be edited directly

A Lightroom Classic catalog (`.lrcat`) is an SQLite database. There is no
supported programmatic way to move a photo between folders:

| Route | Verdict |
| --- | --- |
| Lightroom Lua SDK | Can read photos and metadata. Has **no** API to move a photo to another folder. |
| Finder / Explorer | Moves the file, breaks the catalog reference. Everything shows as missing. |
| Folders panel drag & drop | Correct, but manual. Not viable for thousands of photos. |
| Editing the catalog directly | The only automatable route. What this tool does. |

So LR-FolderCraft opens the SQLite file while Lightroom is closed, changes as
little as possible, and moves the files to match.

## What Lightroom stores about a file's location

Three tables describe where a photo lives.

### `AgLibraryRootFolder`

One row per top-level location you imported from.

```
id_local      4908476
id_global     6A431BCE-A7FF-49DF-A64D-6AEE1B782A4F
absolutePath  /Volumes/Photos/2019/raw2019/          <- note the trailing slash
name          raw2019
```

### `AgLibraryFolder`

One row per folder, relative to a root folder.

```
id_local      1971944
id_global     BE11D36B-3F56-44E7-81C2-EBB52FC9B21D
parentId      NULL                 <- the root-level row
pathFromRoot  ''                   <- empty string for the root itself
rootFolder    4908476
```

`pathFromRoot` is the empty string for the root folder and otherwise a POSIX
path **with a trailing slash**: `2019/`, `2019/01/`, `2019/01/03/`. Each row
points at its parent via `parentId`, and a `UNIQUE(rootFolder, pathFromRoot)`
index enforces that a path exists once.

### `AgLibraryFile`

One row per file on disk.

```
id_local        812768
baseName        IMG_5047
extension       CR2
folder          1971944            <- the only column this tool changes
idx_filename    IMG_5047.CR2
lc_idx_filename img_5047.cr2       <- part of UNIQUE(lc_idx_filename, folder)
```

The absolute path of a file is therefore:

```
AgLibraryRootFolder.absolutePath + AgLibraryFolder.pathFromRoot + AgLibraryFile.idx_filename
```

## What the tool changes — and nothing else

| Change | Table | When |
| --- | --- | --- |
| Insert folder rows | `AgLibraryFolder` | when a target folder does not exist yet |
| Re-point a file | `AgLibraryFile.folder` | for every moved file |
| Update the name columns | `AgLibraryFile.baseName`, `extension`, `idx_filename`, `lc_idx_filename`, `lc_idx_filenameExtension` | only when a collision forced a rename |
| Advance the id counter | `Adobe_variablesTable` (`Adobe_entityIDCounter`) | when new rows are created |
| Insert a root folder row | `AgLibraryRootFolder` | only with `--placement new-tree` |
| Delete empty folder rows | `AgLibraryFolder` | only folders that fell empty, never a root-level row |

Everything else is untouched — verified by comparing a hash over
`Adobe_images`, `Adobe_imageDevelopSettings`, `AgLibraryKeywordImage` and
`AgLibraryCollectionImage` before and after a run: identical.

## Why nothing is lost

Every other table refers to a photo through `AgLibraryFile.id_local` or
`Adobe_images.id_local`, and **neither value ever changes**:

```
AgLibraryFile.id_local  ◄── Adobe_images.rootFile
                                 ▲
                                 ├── Adobe_imageDevelopSettings.image
                                 ├── AgLibraryKeywordImage.image
                                 ├── AgLibraryCollectionImage.image
                                 ├── Adobe_images.masterImage   (virtual copies)
                                 └── ...
```

Only the `folder` column of `AgLibraryFile` moves. A virtual copy is a separate
`Adobe_images` row whose `rootFile` is the *same* `AgLibraryFile` — so it
follows its master automatically and cannot be orphaned.

Previews live in `<Catalog> Previews.lrdata`, addressed by the image UUID, not
by path. They survive too.

## Row ids come from Lightroom's own counter

Lightroom hands out every `id_local` from a single catalog-wide counter stored
in `Adobe_variablesTable` under `Adobe_entityIDCounter`. New folder rows take
their ids from that same counter, and the counter is advanced by exactly the
number of rows created. Inventing ids — `MAX(id_local) + 1`, say — would
eventually collide with an id Lightroom itself allocates later.

The counter must also be written back in the **same SQLite storage class**.
`Adobe_variablesTable.value` is declared without a type, so it has BLOB affinity
and keeps whatever it is handed. Lightroom stores the counter as a REAL; writing
the string `'4914941.0'` instead of the number `4914941.0` yields a value that
reads the same, passes `integrity_check`, and is invisible to a row-value
comparison — but Lightroom then refuses to open the catalog, and its own repair
copies the value through unchanged, so it repairs into a byte-identical file
forever. `allocate_ids()` re-reads `typeof()` after writing and aborts the run
if the storage class changed.

## The execution order

The order is chosen so that the step which is *cheapest to undo* happens last.

```
1  pre-flight   Lightroom closed? permissions? disk space?     ── abort here costs nothing
2  backup       copy the catalog, verify with SHA-256
3  catalog      open read-write, BEGIN, create folder rows,
                re-point files                                 ── still uncommitted
4  filesystem   create directories, move every file,
                journal each one before attempting it
5  commit       only now is the catalog transaction committed
6  cleanup      prune folder rows and directories that fell empty
7  verify       re-read the catalog, check every path on disk
```

If step 4 fails at file 3,000 of 9,452:

- the catalog transaction is **rolled back** — the database on disk is
  byte-identical to how the run found it;
- the 2,999 files that had already moved are put back, using the journal;
- the journal records the failure and the restore.

Because the catalog is only committed after every file has arrived, there is no
window in which the database describes a layout the disk does not have.

## Moving files

Within one volume a move is `os.replace()` — an atomic rename, instant even for
300 GB, because no data is copied.

Across volumes the file is copied, both copies are SHA-256 compared, and only
then is the source removed. That is slow but safe, and the pre-flight check
refuses to start without 105 % of the required free space.

An existing file at the target is never overwritten. The executor checks again
immediately before each move, so even a file that appeared after planning is
safe.

A file may have companions that must move with it. XMP sidecars are planned as
part of the photo's move and appear in the journal under the same `file_id`.

The macOS AppleDouble file `._<name>`, which holds extended attributes and the
resource fork on exFAT/FAT, is a special case: on macOS the kernel moves it
together with the file, so the tool must *not* move it as well — doing so
collides with what the system has already done. On other platforms it is an
ordinary file and is carried along explicitly.

## The journal

Every run writes a JSON-Lines journal, each line flushed and `fsync`ed before
the action it describes is attempted:

```json
{"ts": "...", "event": "run-start",  "tool_version": "1.0.0", "catalog": "...", "plan": {...}}
{"ts": "...", "event": "backup",     "source": "...", "target": "..."}
{"ts": "...", "event": "mkdir",      "path": "..."}
{"ts": "...", "event": "move-begin", "file_id": 812768, "source": "...", "target": "..."}
{"ts": "...", "event": "move-done",  "file_id": 812768}
{"ts": "...", "event": "catalog-commit", "folders": 152, "files": 9452}
{"ts": "...", "event": "run-end",    "status": "success", "moved": 9452}
```

Even a power cut leaves a usable record: a torn final line is ignored and
everything before it is trusted. `lrfc undo` replays it backwards.

## Reading the catalog safely

Read access uses SQLite's `mode=ro` URI so the driver itself refuses a write.

There is one wrinkle worth knowing: on filesystems without POSIX advisory
locking — notably exFAT and FAT, which is what most external photo drives use —
`mode=ro` fails outright with *“unable to open database file”*, because SQLite
cannot take its shared lock. The tool detects that and retries with
`immutable=1`, which skips locking entirely. That is only safe while nobody
else writes to the catalog, which the lock-file check has already established.

## Locking

Lightroom creates `<Catalog>.lrcat.lock` while it has a catalog open. The tool
refuses to run when that file exists. `--ignore-lock` exists for forensic
inspection of a locked catalog; do not use it for `apply`.

Leftover `.lrcat-wal` and `.lrcat-shm` files are reported as a warning. They are
harmless in themselves, but opening and closing the catalog once in Lightroom
lets it flush them properly.

## Idempotency

Running the same structure twice must be a no-op, and it is. On the second run
every photo is already in its target folder and reports `already in place`.

The subtle part is the anchor. In `in-place` mode the structure is built below
the deepest folder common to all selected photos. After a first run into day
folders, that common folder may *be* a day folder — so a naive second run would
create `2019-01-03/2019-01-03/`. The planner detects that the anchor already
ends with what the structure renders and steps back accordingly.

## Verification

After the commit, the catalog is re-read and, for every moved file, checked
that the path the catalog now describes is exactly the planned target and that
the file is there. Problems are listed in the result and exit code `4` is
returned. Skip it with `--no-verify` on very large runs, but there is rarely a
reason to.
