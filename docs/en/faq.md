# FAQ

**Revision r6.0.0 · Build date 2026-08-23**

## Safety and data

### Will I lose my develop settings?

No. Edits hang off the photo's row id, which never changes. Only the folder a
file points at is changed. This is verified by a test that hashes
`Adobe_images`, `Adobe_imageDevelopSettings`, `AgLibraryKeywordImage` and
`AgLibraryCollectionImage` before and after a run and requires them to be
identical.

### What happens to my virtual copies?

They follow automatically. A virtual copy is a separate `Adobe_images` row that
points at the *same* file row, so moving the file carries every copy with it.
The plan reports how many are involved.

### And collections, keywords, ratings, flags, stacks?

All preserved, for the same reason. So are previews and smart previews, which
are addressed by image UUID rather than by path.

### Do I need a backup if the tool makes one?

Yes. The tool's backup covers the catalog, not your photographs, and it is only
as good as the drive it sits on. Keep your own backup.

### Can I undo a run?

Yes: `lrfc undo <journal>`. Files go back and the catalog is restored from the
backup the run wrote. The journal path is printed at the end of every run.

### What if the power fails mid-run?

The catalog is committed *last*, so an interruption almost always leaves the
database untouched while some files have moved. The journal tells you exactly
how far it got, and `lrfc undo` puts the files back. See
[safety.md](safety.md#the-run-was-interrupted-power-cut-forced-quit).

### Can it overwrite one of my photos?

No. Every move checks the target first and refuses to write over an existing
file, even one that appeared after planning.

## Using it

### Does Lightroom have to be closed?

Yes. The tool refuses to start while Lightroom's `.lrcat.lock` file exists.
Quit Lightroom Classic — do not just minimise it.

### How long does it take?

On one volume, seconds. Moving a file within a filesystem is a rename; no data
is copied. A 9,452-file, 337 GiB library plans in about two seconds and moves
almost as fast.

Across volumes it is a real copy with a checksum, so it runs at drive speed.

### Can I run it again with a different structure?

Yes. Run it as often as you like; each run re-sorts from the current state.
Running the *same* structure twice does nothing — the second run reports
everything as already in place.

### What about photos with no capture date?

By default they go to a `_unsorted` folder next to the day folders. Use
`--on-missing-date skip` to leave them alone, or `abort` to refuse to plan.
Rename the folder with `--unsorted-folder`.

### Can I sort only part of a catalog?

Yes: `--root-folder ID`, `--folder ID` (repeatable), `--include-ext`,
`--exclude-ext`. Get the ids from `lrfc folders CATALOG`.

### Can I have a folder per camera *and* per day?

Yes, that is what multiple levels are for:

```bash
lrfc apply CATALOG -s '{camera_slug}/{yyyy}-{mm}-{dd}'   # camera, then day
lrfc apply CATALOG -s '{yyyy}-{mm}-{dd}/{camera_slug}'   # day, then camera
```

### Do XMP sidecars come along?

Yes, both `IMG_1234.xmp` and `IMG_1234.CR2.xmp`. If a collision forces the
photo to be renamed, the sidecar is renamed to match. Disable with
`--no-sidecars`.

### Does it work with a catalog that syncs to Lightroom (cloud)?

Sync data lives in separate tables that this tool does not touch, and the photo
ids are unchanged, so a synced catalog should be fine. It has **not** been
tested against one. Take a backup and check the sync status afterwards.

### Multiple root folders / drives?

Each run works on one root folder. If your selection spans several, the planner
says so and asks you to restrict it with `--root-folder`. Run once per root.

### Can I move photos to a completely different drive?

Yes, with `--placement new-tree --target-root /Volumes/Other/Sorted`. Files are
copied, checksum-verified and only then removed from the source; the target is
registered as an additional root folder in the catalog.

## Structures

### Why is my December photo in a week folder for next year?

Because ISO 8601 says so: a week belongs to the year containing its Thursday,
so 30 December 2019 is week 1 of 2020. Always pair `{iso_week}` with
`{iso_year}`, never with `{yyyy}`. See
[structures.md](structures.md#iso-calendar-weeks).

### Can I get German month names?

`--lang de`, or `F1` in the TUI. `{month_name}` then renders `Januar`.

### Which date is used — the file date or the EXIF date?

Lightroom's capture time, which is the EXIF date unless you corrected it in the
Metadata panel — in which case your correction wins. The file modification date
is **not** used by default: it is usually the date the file was copied, and
using it would silently misfile photos. Opt in with
`--date-source capture --date-source file-mtime` if it suits your archive.

### Where do the new folders appear?

By default inside the folder your photos are in now. `raw2019/` becomes
`raw2019/2019-01-03/`, `raw2019/2019-01-06/` and so on. Use
`--anchor-folder ID` for a different parent, or `--placement new-tree` for a
separate tree.

## Technical

### Why can't this be a Lightroom plug-in?

The Lightroom Lua SDK can read photos and metadata but offers no API to move a
photo to another folder. No plug-in can do this. Editing the catalog directly
while Lightroom is closed is the only automatable route.

### Is editing the catalog supported by Adobe?

No. The catalog format is undocumented. This tool restricts itself to four
long-stable tables, uses Lightroom's own id counter and follows its path
conventions — but it is reverse engineering, which is why the safety machinery
exists. Verify the result in Lightroom after your first run.

### Which catalog versions work?

Verified against schema 18.0.0 (Lightroom Classic 14). Schemas 11.x–19.x are
accepted, with a warning if not explicitly verified. Older ones need
`--allow-unsupported-catalog`.

### Why does it need Python 3.9 and not something newer?

So it runs on the Python macOS already ships. No installation step for most
users.

### Do I need the TUI?

No. `pip install lr-foldercraft` without extras has no dependencies at all; the
CLI does everything. Textual is only needed for `lrfc tui`.

### I installed it but the terminal says `lrfc: command not found`

The launcher lives in `~/.local/bin`, and macOS does not put that on the PATH by
itself. Since r3.0.1 the installer adds it for you — but **a terminal window
that was already open keeps the PATH it started with**. Open a new window, or
run `source ~/.zshrc`.

Check what is going on:

```bash
ls -l ~/.local/bin/lrfc          # is the launcher there?
~/.local/bin/lrfc --version      # does it work by full path?
echo $PATH | tr ':' '\n'         # is ~/.local/bin listed?
```

If the launcher works by full path but is not found by name, it is only the
PATH. Add this to `~/.zshrc` and open a new window:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### `lrfc gui` says PySide6 is missing

The graphical interface is an optional extra of about 100 MB, so the installer
only adds it when asked. Since r4.0.0 it asks when run in a terminal; before
that you had to know about `--with-gui`, and the "next steps" list advertised
`lrfc gui` whether or not it had been installed.

Add it to an existing installation — the environment is reused, so it takes
seconds:

```bash
./install/install-macos.sh --with-gui
```

Or check and repair the whole installation:

```bash
./install/install-macos.sh --check
```

### Where are logs, profiles and backups?

See [installation.md](installation.md#where-things-are-stored). Override with
`LRFC_CONFIG_DIR`, `LRFC_LOG_DIR`, `LRFC_BACKUP_DIR`, `LRFC_REPORT_DIR`.

### What are `.lrcat-wal` and `.lrcat-shm`? Should I delete them?

**No — never delete a non-empty `.lrcat-wal`.** Lightroom catalogs run in WAL
mode, and that file holds committed transactions not yet folded back into the
`.lrcat`. Deleting it throws them away. LR-FolderCraft checkpoints the WAL when
it commits, so after a successful run the catalog stands on its own. A
`.lrcat-journal` means an interrupted transaction; do not delete that either —
open and close the catalog in Lightroom and let SQLite recover.

### It says “unable to open database file” — but the file is there.

That was a real symptom on exFAT drives, which do not support the locking
SQLite needs for read-only access. The tool detects it and retries with
`immutable=1`. If you still see it, the file is genuinely unreadable — check
permissions and whether the drive is mounted read-only.

### Can I script it?

Yes. Every command has a defined exit code, `plan --json` gives you the whole
plan, and `apply --yes` skips the question. Profiles keep long option lists out
of your scripts.
