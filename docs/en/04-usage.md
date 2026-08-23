# Usage

**Revision r8.0.0 · Build date 2026-08-23**

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
additional root folder in the catalog. The target does not have to exist -- it
and every missing level above it are created, and removed again by a rollback
or `lrfc undo`:

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

## The graphical interface

```bash
lrfc gui                                          # English
lrfc gui --lang de                                # German
lrfc gui --lang de /Volumes/Photos/2019/2019.lrcat  # German, catalog chosen
```

The language can also be switched inside the window without restarting: the
menu entry at the top always names the **other** language, so in the English
interface it reads "Deutsch".

### What the window remembers

Settings you make in the window are kept, so the next start begins where you
left off: the language, the catalog, the target folder and its mode, the
structure, the extension filters, the folder actions, the rule list, the window
size and the splitter positions. They live in `gui-state.json` in the
configuration directory; deleting that file restores the defaults.

Two things are deliberately **not** remembered:

| | Why not |
| --- | --- |
| Per-folder decisions | They are catalog folder ids. Restoring them against a different catalog would apply an answer given about one folder to whatever unrelated folder happens to share that number. |
| The "make a backup" switch | It always starts on. Turning the safety net off should be decided for the run at hand, not inherited from a run three weeks ago. |

It needs the `gui` extra: `pip install 'lr-foldercraft[gui]'`. Without it the
command explains how to install it rather than failing with a traceback.

One window, top to bottom:

| Section | What it holds |
| --- | --- |
| **Catalog** | the `.lrcat` path with a Browse button, and a one-line summary once loaded: files, images, virtual copies, capture range |
| **Source** | the root folder to work on (or all of them), and extension filters |
| **Target** | below the current folder, or into a new folder chosen with the system dialog — its *New Folder* button creates one, and a path that does not exist yet is created during the run |
| **Folder structure** | a preset, or your own template, with a live preview that updates as you type, and a Placeholders button listing all 25 |
| **Options** | name conflicts, photos without a date, and the three decisions about existing folders, plus sidecars, catalog backup and ASCII names |
| **Needs your answer** | one row per cause with the file count, the option that governs it and that option's current value — selecting a row lists the files it concerns |
| **Folders found** | the rule list, and below it one row per folder with its kind, photo count, the rule that decided it and a dropdown — changing one re-plans immediately |
| **Buttons** | Plan changes nothing; Apply asks for confirmation first |
| **Progress** | a bar and a counter during the run, and the full result afterwards |
| **Log** | what happened, including every warning from the pre-flight checks |

The menu bar switches between English and German at any time.

### The sections can be pulled open — important

Between the four large sections — **settings**, **Needs your answer**,
**Folders found** and **Log** — sits a **divider**. It is easy to miss: a thin
horizontal line at the **bottom edge of a section**, formerly just a few grey
dots.

```
┌─ Settings ──────────────────────────────┐
│  Catalog, Source, Target, Structure …   │   ← scrolls within itself
└─────────────────────────────────────────┘
 ────────────────────────────────────────      ← divider: drag here
┌─ Needs your answer ─────────────────────┐
```

The pointer turns into a double arrow over a divider, and a tooltip says what
it does. With it:

- **Dragging** gives the section above more or less room.
- **Dragging it fully shut** hides a section. It is not gone — the divider
  stays, and pulling it back open brings the section out again. If you have no
  use for the log, that is room won for the folder table.
- The sizes you set are **remembered** and restored at the next start.

The **settings** section additionally has a **scrollbar of its own**: on a
small screen Target, Folder structure and Options start below the visible edge
and are reached by scrolling *inside* the section — or by dragging the divider
below it downwards.

So if a table looks cut off or a setting seems to be missing: the section is
too small, not empty.

The window fits small screens: it opens no larger than the space the screen
offers, the settings scroll when they do not fit, and the buttons and the
progress bar stay put outside the scrolling area. Settings, folder table and
log share a splitter, so you can give the room to whichever you are using.

The option defaults are taken from the same `Settings` object the command line
uses, so the interface cannot quietly disagree with the documentation. There is
a test asserting exactly that.

Long operations run on worker threads, so the window stays responsive while
nine thousand files are moved, and closing it waits for the work to finish
rather than killing it.

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

### The four actions

| Action | What it does |
| --- | --- |
| `consolidate` | move the photos up and sort them below the run's anchor |
| `sort-inside` | keep the folder and build the structure *inside* it |
| `resort` | rebuild the folder **where it stands**, below its own parent |
| `relocate` | carry the folder to the new location **unchanged** — same name, same contents, no sorting |
| `leave` | do not touch the photos in this folder at all |
| `keep` | a dated folder: leave the photos it correctly describes |

`resort` is the one that needs an example. Given
`raw2026/2026-06-28 Makro Blume im Garten` and the structure
`{yyyy}-{mm}-{dd}/{folder_label}`:

| Action | Result |
| --- | --- |
| `consolidate` | `2026-06-28/Makro Blume im Garten` — pulled out of `raw2026` |
| `sort-inside` | `raw2026/2026-06-28 Makro Blume im Garten/2026-06-28/…` — nested |
| `resort` | `raw2026/2026-06-28/Makro Blume im Garten` — split, in place |
| `relocate` | `<new root>/raw2026/2026-06-28 Makro Blume im Garten` — carried over as it is |

`relocate` is the one for material that should come along without being
touched: a `_fineart` folder, an `_extern` drop box, a job folder with its own
order. It keeps the folder's whole sub-structure and its path below the source
root, so `_extern/2020/Fest` lands as `_extern/2020/Fest` under the new root.
The run's structure is not rendered for it at all, and the anchor is ignored —
burying the folder one level deeper is not what "move this there" means.

It only does something when the run has somewhere else to put the folder, that
is with a target folder set. Sorting in place leaves a relocated folder exactly
where it is, which `plan` reports as "already in place".

### The three defaults

| Situation | Flag | Default |
| --- | --- | --- |
| A topic subfolder | `--subfolder-action` | `consolidate` |
| A dated folder | `--dated-folder-action` | `keep` |
| A photo in a kept or resorted dated folder whose date does not match | `--mismatch-action` | `move-out` |

With the defaults, `2019-04-15 Ostern in Tirol` keeps its name and its photos,
while a photo in it that was shot on a different day moves to its own date
folder. Topic folders are merged into the shared date structure.

`--mismatch-action leave` matters more than it looks. A shoot that runs past
midnight leaves photos whose own date disagrees with the folder naming the
session. Under `keep` those photos simply stay. Under `resort` they follow the
**folder's** date rather than their own, so the session is rebuilt whole
instead of being torn across two day folders.

### Rules: deciding whole classes of folders at once

Answering one folder at a time does not scale. A grown library has dozens of
folders and perhaps four distinct intentions. `--rule` expresses the
intentions:

```bash
lrfc plan CATALOG -s '{yyyy}-{mm}-{dd}/{folder_label}' \
    --rule '_extern=leave' \
    --rule '_fineart=leave' \
    --rule 'dated+label=resort' \
    --rule 'dated=keep' \
    --rule '*=sort-inside' \
    --mismatch-action leave
```

Rules are **ordered** and the **first match wins**, so put the specific ones
first. A pattern is either a path glob or one of five keywords:

| Pattern | Selects |
| --- | --- |
| `*` | every folder no earlier rule matched |
| `dated` | folders whose name starts with a date |
| `dated+label` | dated folders that also carry descriptive text |
| `dated-only` | dated folders with nothing but the date |
| `plain` | folders without a date in the name |
| `_extern`, `raw20*`, `_in_Arbeit/*` | a folder path or name, `*` and `?` allowed |

A pattern finds its folder **however deep it sits** and covers everything
**below** it, so the single rule `_extern` reaches `_extern`,
`raw2019/_extern`, and `raw2019/_extern/2020/Fest` alike. Writing a slash makes
it a path: `_in_Arbeit/2021` matches that pair of folders, not any `2021`.

`keep` asked of a folder with no date in its name softens to `leave` — the
honest reading of "honour the date in the name" when there is none.

### Precedence

Strongest first:

1. `--folder-action ID=ACTION` — one named catalog folder
2. the first matching `--rule`
3. your answer under `--interactive`
4. the `--subfolder-action` / `--dated-folder-action` default for its kind

A rule **silences the question it already answers**, which is the point: five
rules and `--interactive` will ask only about folders no rule speaks about.

`plan` lists every folder with which rule decided it, so a rule set can be
checked before it is run.

### Deciding one folder at a time

```bash
lrfc folders CATALOG                      # find the folder ids
lrfc plan CATALOG -s day --folder-action 4711=sort-inside
```

`--folder-action ID=ACTION` is repeatable and beats both the rules and the
global defaults.

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

In the graphical interface the rule list is a small table above the folder
table: add, remove and reorder rules there, and the folder table below shows
which rule decided each folder. A decision made by hand in that table still
beats every rule and is marked as yours.

Whatever you choose, `plan` lists every folder it found, what kind it is, what
was decided and whether that came from a default, a rule, an explicit
`--folder-action` or your own answer. The JSON export carries the same under
`folders`.

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

### Undoing a run from the window

The **Undo a run…** entry in the menu bar reverses a completed run. It asks for
the run's journal — the newest is offered first, because it is nearly always
the one meant — states plainly what will happen, and then puts every moved file
back where it was, removes the folders the run created if they are empty, and
restores the catalog from the backup that run made.

Lightroom Classic must be closed for this, exactly as for the run itself.

Runs are undone newest first. Reversing an older run while a newer one still
stands would restore a catalog that does not describe what is on disk; if you
need to go further back, undo each run in turn. `lrfc undo JOURNAL` does the
same thing from the command line.

### What the plan could not decide alone

Both `plan` and the graphical interface list, separately from the counts, every
case the tool decided for you:

```
Needs your answer:
  [EXCEPTION] 12 photo(s) in 1 dated folder(s) whose own date differs from the
              folder name -- often a shoot that ran past midnight
          --mismatch-action = leave
          - raw2026/2026-06-27 Test 150mm Spiegelobjektiv/ (12)
```

Each entry names the option that governs it and what that option is currently
doing, so changing your mind is one flag away.

| Level | Meaning |
| --- | --- |
| `BLOCKS` | the run will not start: a failed pre-flight check, or a file the catalog names that the disk does not have |
| `Warning` | the run will start, but something is not as expected |
| `Exception` | a decision the tool made for you, which a setting can change |
| `Note` | worth knowing, nothing to answer |

In the graphical interface this is a table of its own between the settings and
the folder table. Selecting a row shows which files it concerns.

### The move log, beside the library

An `apply` run leaves a plain text record next to the `.lrcat` file:

```
Lightroom.Kataloge/Masterkatalog.Neu/
    Masterkatalog.Neu.lrcat
    LR-FolderCraft_2026-08-23_143012_Masterkatalog.Neu.log
```

That is not the debug log. The debug log is for diagnosing the tool; this is
for the person who, months later, wonders where a photo went. It lists every
source and target path, the rules that were used, where the catalog backup and
the journal went, and a summary.

| Flag | Effect |
| --- | --- |
| `--no-move-log` | do not write it |
| `--move-log-dir DIR` | write it here instead of beside the catalog |

Writing it can never fail a run. If the directory is not writable — a
read-only volume, a full disk — the run still succeeds and the result carries a
note saying the record could not be written. By the time it is written the
photos are already moved and verified.

Dry runs write no move log: nothing moved.
