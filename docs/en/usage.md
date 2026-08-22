# Usage

**Revision r2.0.0 · Build date 2026-08-22**

> **Close Lightroom Classic before running `apply`.** The tool refuses to start
> if it finds Lightroom's lock file, but a catalog that Lightroom opens *while*
> a run is in progress can still be damaged.

## The workflow

```
   info  ──►  plan  ──►  review  ──►  apply  ──►  open in Lightroom
   read       read       you           writes     confirm it looks right
   only       only
```

Never skip `plan`. It costs seconds and shows you the exact list of moves.

---

## `lrfc info CATALOG`

Reads the catalog and prints a summary: schema version, folder and file counts,
virtual copies, capture time range, cameras and file formats. Writes nothing.

```console
$ lrfc info /Volumes/Photos/2019/2019.lrcat
  Catalog                       : /Volumes/Photos/2019/2019.lrcat
  Schema version                : 18.0.0
  Root folders                  : 1
  Folders                       : 1
  Files                         : 9,452
  Images (incl. virtual copies) : 9,484
  Virtual copies                : 32
  Without capture date          : 0
  Capture range                 : 2019-01-03T17:42:29.18 .. 2019-12-29T13:39:50.98

Cameras:
  Canon EOS 5D Mark IV                        8,216
  Canon EOS 70D                               1,236
```

## `lrfc folders CATALOG [--counts]`

Prints the folder tree with catalog folder ids. You need those ids for
`--folder` and `--anchor-folder`.

```console
$ lrfc folders /Volumes/Photos/2019/2019.lrcat --counts
[4908476] /Volumes/Photos/2019/raw2019/
    [1971944] .  (9,452 files)
```

## `lrfc plan CATALOG -s STRUCTURE`

Builds the complete plan and prints it, together with the pre-flight checks.
**Writes nothing.**

```console
$ lrfc plan /Volumes/Photos/2019/2019.lrcat -s day
  Structure   : {yyyy}-{mm}-{dd}
  Example     : 2019-01-03
  Placement   : in-place
  Target root : /Volumes/Photos/2019/raw2019
  Anchor      : (root)

Summary:
  To be moved                   : 9,452
  Already in place              : 0
  Skipped                       : 0
  New folders                   : 152
  Virtual copies carried along  : 32
  Data volume                   : 337.1 GiB
```

Output formats:

| Flag | Result |
| --- | --- |
| *(none)* | human readable report plus pre-flight checks |
| `--json` | the complete plan, every move, machine readable |
| `--csv` | one row per file — open it in a spreadsheet |
| `--out DIR` | additionally write `plan-<timestamp>.json` and `.csv` |
| `--all` | do not truncate the target folder listing |

Reviewing a large plan in a spreadsheet is worth the minute:

```bash
lrfc plan CATALOG -s day --csv > plan.csv
```

## `lrfc apply CATALOG -s STRUCTURE`

Does the work. Prints the plan, runs the pre-flight checks, asks for
confirmation, then executes.

```bash
lrfc apply /Volumes/Photos/2019/2019.lrcat -s day        # asks first
lrfc apply /Volumes/Photos/2019/2019.lrcat -s day --yes  # no question
```

| Flag | Effect |
| --- | --- |
| `-y`, `--yes` | skip the confirmation question |
| `--no-backup` | do not back the catalog up — **strongly discouraged** |
| `--no-verify` | skip the post-run verification pass |
| `--keep-empty-folders` | keep folder entries that fell empty |
| `--out DIR` | write the plan files into `DIR` |

Exit codes: `0` success · `1` error · `2` usage · `3` pre-flight failed ·
`4` finished but verification found problems · `5` aborted.

## `lrfc undo JOURNAL`

Reverses a completed run: files go back to where they came from and the catalog
is restored from the backup that run wrote.

```bash
lrfc undo ~/Library/Application\ Support/LR-FolderCraft/backups/2019-20260822-162631.lrfc-journal.jsonl
```

The journal path is printed at the end of every run and recorded in the log.

## `lrfc tui`

The interactive interface. Pick a catalog, choose a structure and watch the
live preview, plan, review the target folders in a table, then apply behind a
confirmation dialog.

| Key | Action |
| --- | --- |
| `Ctrl+L` | load the catalog |
| `Ctrl+P` | plan |
| `Ctrl+R` | apply |
| `F1` | switch between English and German |
| `Ctrl+Q` | quit |

## `lrfc presets` / `lrfc tokens` / `lrfc profiles`

Help surfaces. `presets` lists the ready made structures with an example path,
`tokens` every placeholder, `profiles` your saved settings. All accept
`--lang de`.

---

## Selecting what to work on

By default every file in the catalog is considered.

```bash
lrfc plan CATALOG -s day --root-folder 4908476   # one root folder
lrfc plan CATALOG -s day --folder 1971944        # one catalog folder
lrfc plan CATALOG -s day --folder 12 --folder 13 # several, repeatable
lrfc plan CATALOG -s day --include-ext cr2 --include-ext dng
lrfc plan CATALOG -s day --exclude-ext jpg
```

## Placement: where the new folders go

**`in-place`** (default) builds the structure below the folder that currently
holds your selection:

```
raw2019/                 raw2019/
  IMG_0001.CR2     ──►     2019-01-03/
  IMG_0002.CR2               IMG_0001.CR2
  ...                        IMG_0002.CR2
                           2019-01-06/
```

The anchor is the deepest folder common to every selected photo. If your photos
already live in day folders, the tool notices that the anchor is itself a
rendered level and steps back, so a second run changes nothing.

Override it with `--anchor-folder ID` (see `lrfc folders`).

**`new-tree`** builds a fresh tree somewhere else and registers it as an
additional root folder in the catalog:

```bash
lrfc plan CATALOG -s year/month/day --target-root /Volumes/Photos/sorted
```

Passing `--target-root` switches to `new-tree` automatically. If the target is
on a different volume the files are copied, checksum-verified and only then
removed from the source — much slower, and the pre-flight check will insist on
enough free space.

## Edge cases

### Photos without a capture date

| `--on-missing-date` | Behaviour |
| --- | --- |
| `unsorted` (default) | into a `_unsorted` folder; rename it with `--unsorted-folder` |
| `skip` | left where they are, counted and reported |
| `abort` | refuse to plan at all |

Which timestamp counts is controlled by `--date-source`, repeatable and
order-sensitive. The default is `capture`, then `exif-fields`:

- `capture` — Lightroom's own capture time, the value you see and can edit in
  the Metadata panel. A corrected date wins, which is what you want.
- `exif-fields` — the harvested `dateYear/dateMonth/dateDay` columns.
- `file-mtime` — the file's modification time. **Not a default**: it is usually
  the date the file was copied, not the date the photo was taken, and using it
  silently files photos under the wrong day. Opt in only if you know it fits:

```bash
lrfc plan CATALOG -s day --date-source capture --date-source file-mtime
```

### Name collisions

Two files with the same name can only meet if you merge several source folders
into one target folder.

| `--conflict` | Behaviour |
| --- | --- |
| `rename` (default) | second file becomes `NAME_1.ext`; the catalog is updated so Lightroom follows |
| `skip` | leave it where it is and report it |
| `abort` | refuse to plan |

An existing file at the target is **never** overwritten, in any mode.

### Sidecar files

`IMG_1234.xmp` and `IMG_1234.CR2.xmp` are both recognised and moved with their
photo. If the photo is renamed, the sidecar is renamed to match. Disable with
`--no-sidecars`.

**macOS AppleDouble companions** (`._IMG_1234.CR2`) need no attention from you.
On exFAT and FAT — the usual filesystems on external photo drives — macOS keeps
a file's extended attributes and resource fork in such a companion, and the
kernel moves it together with the file. LR-FolderCraft deliberately leaves that
to macOS; moving it a second time would collide with what the system has
already done.

On Linux and Windows there is no such emulation, so a `._X` written earlier by
a Mac would be left behind by a rename. There the tool carries it along
explicitly, `--no-sidecars` included, so the drive keeps its metadata for the
next time it is plugged into a Mac.

### Non-ASCII folder names

`--ascii` folds folder names to plain ASCII (`Grün` → `Grun`). Useful when the
library is shared with a system that struggles with Unicode. Illegal characters
(`< > : " / \ | ? *`), trailing dots and Windows device names (`CON`, `LPT1`, …)
are always handled, on every platform.

## Folders your library already has

A library that has grown over years is rarely one flat folder. It holds topic
folders — `Urlaub`, `Hochzeit Meyer` — and folders that already carry a date —
`2019-04-15 Ostern in Tirol`. What should happen to those is a judgement call,
so LR-FolderCraft recognises them, states what it found, and lets you decide.

### What counts as a dated folder

A name that **begins** with a date, optionally followed by descriptive text:

| Name | Recognised as |
| --- | --- |
| `2019-04-15 Ostern in Tirol` | day |
| `2019_06_01 Hochzeit` | day |
| `20190415_Hochzeit` | day |
| `2019.03.10` | day |
| `2019-04` | month |
| `2019 Jahresrueckblick` | year |
| `Urlaub`, `Sommer 2019`, `raw2019` | not a date |

A date in the middle of a name is ignored: guessing there would invent intent.

A dated folder only counts when it is **at least as fine** as the structure
asks for. A folder called `2019` is no answer to a request for day folders, so
it is treated as a topic folder and its photos are sorted properly. A day
folder does satisfy a request for year folders. If the structure has no date
tokens at all, folder dates say nothing and are ignored.

### The three decisions

| Situation | Flag | Choices | Default |
| --- | --- | --- | --- |
| A topic subfolder | `--subfolder-action` | `consolidate` · `sort-inside` · `leave` | `consolidate` |
| A dated folder | `--dated-folder-action` | `keep` · `consolidate` · `sort-inside` · `leave` | `keep` |
| A photo in a kept dated folder whose date does not match | `--mismatch-action` | `move-out` · `leave` | `move-out` |

- `consolidate` — move the photos up and sort them below the run's anchor.
- `sort-inside` — keep the folder and build the structure *inside* it.
- `leave` — do not touch the photos in this folder at all.
- `keep` — a dated folder: leave the photos it correctly describes.

With the defaults, `2019-04-15 Ostern in Tirol` keeps its name and its photos,
while a photo in it that was shot on a different day moves to its own date
folder. Topic folders are merged into the shared date structure.

### Deciding one folder at a time

```bash
lrfc folders CATALOG                      # find the folder ids
lrfc plan CATALOG -s day --folder-action 4711=sort-inside
```

`--folder-action ID=ACTION` is repeatable and beats the global defaults.

### Being asked

```bash
lrfc plan CATALOG -s day --interactive
```

Every folder that could reasonably go either way is put to you, with what was
found, how many photos it holds, how many carry a different date, and which
option is the default. Enter accepts the default, so nothing happens by
accident. The anchor folder is never offered: it is the container the run sorts
into, not a subfolder whose fate is in question.

In the TUI the same choice is made by pressing Enter on a row of the folder
table — it cycles that folder's decision and re-plans immediately.

Whatever you choose, `plan` lists every folder it found, what kind it is, what
was decided and whether that came from a default, an explicit `--folder-action`
or your own answer. The JSON export carries the same under `folders`.

## Profiles

Save a configuration once, reuse it:

```bash
lrfc plan CATALOG -s '{camera_slug}/{yyyy}-{mm}-{dd}' --save-profile by-camera
lrfc apply OTHER_CATALOG --profile by-camera
lrfc profiles
```

A profile stores *how* to sort, never `dry_run` — so loading one can never
start a live run by accident. `--config FILE.json` loads settings from an
explicit file instead.

## Logging and debugging

Every run writes a log file with a numbered `STEP` trail:

```
2026-08-22 16:26:31,412 | INFO | lrfoldercraft | STEP 004 | Anchor resolved: ...
2026-08-22 16:26:31,502 | INFO | lrfoldercraft | STEP 007 | Moved 40 file(s) and 1 sidecar(s)
```

| Flag | Effect |
| --- | --- |
| `--debug` | DEBUG level with file, line and function; every SQL statement |
| `--verbose` | show progress on the console too |
| `--quiet` | console shows errors only |
| `--log-file PATH` | write the log somewhere specific |
| `--log-dir DIR` | choose the directory for the auto-named log |

The log file always records the revision, build date, Python version, platform
and full command line, so a log can be tied to an exact tool revision later.

Attach the log **and** the plan JSON when reporting a problem.
