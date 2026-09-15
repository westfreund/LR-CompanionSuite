# Project history

**Revision r20.0.3 · Build date 2026-09-15**

The [CHANGELOG](https://gitlab.com/andy-freund/LR-CompanionSuite/-/blob/main/CHANGELOG.md) says what changed in each revision. This
document says **why**, and what happened in between: the decisions taken, the
tests run against real libraries, and the four occasions on which the tool was
wrong in a way that mattered.

It is written for whoever picks the project up later — including a future
version of its own authors — because the reasoning behind a fix is worth more
than the fix, and none of it is recoverable from the code.

## How this document came about, and what it can be trusted for

It was written **retroactively on 2026-08-23**, not kept as the work went along.
Entries from that date onward are written as the work happens.

That distinction matters, so here is exactly what it rests on:

| Part | Source | Reliable? |
| --- | --- | --- |
| Dates, order, what changed when | Commit history and tags | Yes — machine recorded |
| What each revision contains | [CHANGELOG.md](https://gitlab.com/andy-freund/LR-CompanionSuite/-/blob/main/CHANGELOG.md) | Yes — written at the time |
| Test results and their numbers | Run output, quoted in the commits | Yes |
| Reasoning, alternatives, what was learned | Reconstructed from the record | The account is faithful, but it is a narrative written afterwards |

So it is a companion to the change history, not a replacement for it. **To trace
an individual change**, use the tools that record it exactly:

```bash
git log --oneline --reverse          # every step, in order
git show v5.0.0                      # what one revision was
git log -p -- src/lrcompanion/planner.py    # one file's whole life
```

The CHANGELOG lists releases newest first. This document reads **forwards**,
oldest first, because it is meant to be read as a story rather than looked up.

---

---

## Every revision, in order

Thirty-nine revisions in a day, from the core to resumption. The times are when
each was released; a name appears where a revision carries one, since the
project rule makes every feature extension a major version and only those get
named.

For *what* changed, one line each is here; for *why*, read the sections below
and the [CHANGELOG](https://gitlab.com/andy-freund/LR-CompanionSuite/-/blob/main/CHANGELOG.md).

| Revision | Time | Name | What it was about |
| --- | --- | --- | --- |
| **r1.0.0** | 16:28 | Daybreak | The core: catalog reader and writer, planner, executor, journal, pre-flight checks, CLI. The write surface is fixed at five statements against four tables. |
| **r1.0.1** | 18:06 |  | AppleDouble companions `._X` are moved along. This change caused the first live run to abort. |
| **r1.0.2** | 18:23 |  | The exFAT fallback was dead code: `sqlite3.connect()` is lazy, so the failure came only at the first query. Fixed with a probe query. |
| **r1.0.3** | 18:30 |  | Measured what the kernel does on exFAT: it moves `._X` itself. On macOS the companion is now left alone; elsewhere it travels along. |
| **r1.0.4** | 19:42 |  | Pre-flight called `.lrcat-wal` a stale side file. Wrong and dangerous: a non-empty write-ahead log holds committed transactions. |
| **r1.0.5** | 20:05 |  | The cause of Lightroom refusing the catalog: the id counter was written as TEXT instead of REAL. The storage class is now read, preserved and verified. |
| **r1.0.6** | 20:41 |  | Detection of catalogs already damaged by r1.0.0 to r1.0.4. |
| **r2.0.0** | 22:19 | Wegweiser | Grown libraries: folder classification, dated versus topic, a granularity rule, and the decision callback front ends supply. The planner never prompts. |
| **r2.0.1** | 22:43 |  | A target root that does not exist yet is created, which is the whole point of a new tree. |
| **r3.0.0** | 23:19 | Weitwinkel | The graphical interface (PySide6/Qt) and runs spanning several root folders. Across volumes: copy, verify by SHA-256, delete. |
| **r3.0.1** | 00:08 |  | `lrfc` was not on PATH after installing. The installer now edits the shell startup file. |
| **r3.0.2** | 07:02 |  | The window was taller than a small screen. Settings scroll and the action row is pinned. |
| **r4.0.0** | 07:29 | Pruefstand | The installer verifies each component by importing it and advertises only what works. It had been offering `lrfc gui` without PySide6. |
| **r4.0.1** | 07:40 |  | A catalog whose root folder no longer exists was reported as a permissions problem. The disconnected path is now named. |
| **r4.0.2** | 08:08 |  | A repeated new-tree run was not a no-op and rolled itself back. The already-in-place check now compares paths only. |
| **r5.0.0** | 09:26 | Regelwerk | Folder rules, the `{folder_label}` token and the `resort` action. Thirty-nine folders become five lines. Simulation revealed that `resort` tore a session that ran past midnight. |
| **r6.0.0** | 10:22 | Klartext | The findings report: each cause with its file count, examples and the option that governs it. Plus the project history and reproducible screenshots. Found: `--lang de` before the subcommand had no effect. |
| **r6.1.0** | 10:41 |  | Documents numbered by weight, the same numbers in both languages. The history now states its own provenance. |
| **r7.0.0** | 10:56 | Gedaechtnis | The window remembers its settings. Not remembered: per-folder decisions (catalog ids) and the backup switch. Fixed: the target folder was unreachable because field and button looked disabled. |
| **r7.1.0** | 11:06 |  | The dividers between sections were nearly invisible. Also fixed: the log section had no size of its own since the findings table arrived. |
| **r8.0.0** | 11:29 | Rueckfahrkarte | The `relocate` action carries a folder across unchanged, and undo reaches the window. Fixed: a rule pattern matched only folders directly below the root. |
| **r8.0.1** | 11:50 |  | The menu entries were invisible on macOS: Qt does not support actions directly on the menu bar there. Undo is now also a button. |
| **r9.0.0** | 13:12 | Aufgeraeumt | Collect files not in the catalog, acknowledge the preconditions, a purpose line and About box, six logo proposals. Two of the sweep's exclusions were found only by testing. |
| **r10.0.0** | 13:50 | Signet | The mark, in two cuts with drawn letters. On the way: `logo-small.svg` drew nothing, because of a double hyphen inside an XML comment. |
| **r10.1.0** | 16:17 |  | The mark was invisible: macOS shows no icon in a window title bar. It is now inside the window. |
| **r11.0.0** | 16:33 | Vollstaendig | Cumulative date levels and the `refile` action. Plus a test requiring every action, token and flag in both language trees; it found three undocumented flags at once. |
| **r12.0.0** | 17:10 | Arbeitsweise | A switch for the commonest folder decision, and profiles that carry the way of working only: no catalog, no target, no rules, no escape hatches. |
| **r13.0.0** | 17:20 | Laufakte | One record folder per run, beside the catalog. A history, and a run can be undone only once. Fixed: two runs in the same second shared a folder. |
| **r13.0.1** | 17:33 |  | `leave` left nothing alone under new-tree: it was identical to `relocate` as soon as the target root differed. |
| **r13.0.2** | 18:31 |  | Three of the four TUI shortcuts never fired; Textual claims `ctrl+p` with priority. Escape did not close the confirmation dialog. |
| **r13.0.3** | 18:42 |  | A deliberate refusal was reported as a crash, with a traceback and the words 'Unexpected error'. |
| **r13.0.4** | 19:03 |  | The run record did not name the rules that shaped the run: it reused the profile's exclusion list, which is wrong for a record. |
| **r14.0.0** | 19:07 | Umschrift | ASCII names spell out umlauts instead of discarding them. `Straße` had become `Strae`. The existing test had enshrined the wrong output as correct. |
| **r14.0.1** | 20:33 |  | The romanisation did nothing: macOS hands back decomposed filenames, so the character map never matched. The same blindness affected rule patterns. |
| **r15.0.0** | 21:26 | Gleichstand | The text interface becomes a peer: seven missing settings, preconditions, history, undo, profiles. A parity test prevents the drift recurring. |
| **r15.0.1** | 21:46 |  | `refile` repeated a label the structure had already placed: `2026-06-18 Voelki Voelki`. |
| **r15.0.2** | 22:00 |  | A superseded plan could become the one that ran. The first attempt at fixing it was worse: a lambda around the slot made the connection direct rather than queued, and widgets were built on the worker thread. |
| **r16.0.0** | 22:17 | Wiederaufnahme | A run cut short can be finished. The direction follows from where it stopped, not from a guess. A new run is refused while one is unfinished. |
| **r16.0.1** | 22:37 |  | A completed reversal was reported as interrupted, because a later run had recreated the same paths. The false positive blocked sound libraries. |
| **r16.1.0** | 22:52 |  | The history names every released revision, and a test holds it to that. It had been covering 18 of 39. |
| **r17.0.0** | 23:—  | Beisammen | The collection folder for files not in the catalog moves into the target tree rather than staying in the source: a run's result had been split across two places. Fixed on the way: across a drive boundary the move would have failed. |
| **r17.0.1** | 06:30 |  | The list of runs showed placeholders instead of a path, and the clock was cut off at `06:1`. |
| **r17.0.2** | 07:20 |  | A repaired run was reported as interrupted again — and the files it offered to put back belonged to the standing run. Also: the window came back 640×480 with two panes collapsed. |
| **r17.0.3** | 07:50 |  | Undo could not find this morning's run: with the remembered catalog gone, the window said no runs were recorded and opened a chooser in a folder that has held no journal for revisions. It now names the real reason and starts where the journals are. |
| **r18.0.0** | 30 Aug | Übersicht | The window stacked everything in one scrolling column, so the structure, the options and the rules sat below the visible edge. Now five tabs, one per step, buttons in the order the work is done -- and profiles can be made and deleted rather than coming into being by typing a name nobody had used. |
| **r19.0.0** | 15 Sep | Fundort | An index across every library: 47 catalogs, 183,407 photographs, read-only. Catalog copies are matched by the overlap of their photo UUIDs -- a test with three photographs exposed that the first design worked only by luck. With it a duplicate report, and an export that copies and reduces catalogs rather than writing new ones. |
| **r20.0.0** | 15 Sep | Zu zweit | The project becomes a suite: **LR-CompanionSuite**, holding LR-FolderCraft and LR-MetaSearch, each with its own name, command, mark and window, plus a launcher. The configuration, index of 183,407 photographs included, moves with it. Fixed on the way: the r19 release had overwritten the verified catalog schema version with the tool's own. |
| **r20.0.1** | 15 Sep |  | An exported catalog would not open: Lightroom has kept a `.lrcat-data` directory beside the catalog since version 11, and the export left it behind. Found by Andreas in Lightroom — the only place it could have been. |
| **r20.0.2** | 15 Sep |  | The exported catalog opened but found no photographs: the source catalog names a drive that no longer exists. The export puts that right now — but only once six photographs are proven to be where it thinks. Also fixed: searching judged reachability by the catalog's drive rather than the photographs' folder. |
| **r20.0.3** | 15 Sep |  | The reduction had deleted the root folder's own row — nine folder rows became two. Folders are left alone now. The second fault in a row that only a look in Lightroom could find. |

---

## 2026-08-22 — the brief

Andreas Freund asked for a tool that reorganises a Lightroom Classic folder
tree — by capture date, camera, calendar week, in freely combinable levels —
**without losing the catalog connection**. Develop settings, virtual copies and
collections had to survive.

Decisions taken at the start, all of which still hold:

| Decision | Why |
| --- | --- |
| Edit the catalog database directly | There is no alternative. The Lua SDK cannot move a photo between folders; Finder can move files but leaves every photo missing; dragging in the Folders panel is correct but manual. |
| No core module knows about a user interface | So a command line, a text interface and a graphical one are three thin front ends over the same three calls, and a fourth costs nothing. |
| Every feature extension is a major version | The user's rule. It makes the revision number say *how much has changed* rather than how carefully it was numbered. |
| Dual licence GPL v3 and MIT | The user's requirement. |
| Everything documented in English and German | The user's requirement. Both trees are complete, not one translated on demand. |
| Commit and push every intermediate state | The user's requirement, and it turned out to matter: the id-counter defect below was diagnosed by comparing tagged revisions. |

### r1.0.0 — the core

Catalog reader and writer, planner, executor, journal, pre-flight checks, CLI.
The write surface was fixed at five statements against four tables and has not
grown since; a test asserts it.

---

## 2026-08-22, afternoon — the first real library

Test library: `2019.lrcat`, 9,489 photos, 337 GiB, on an exFAT external drive.
A full copy was made first, on the user's initiative.

**The first live run aborted at file 850.** Cause: macOS AppleDouble companions.
On exFAT the kernel moves `._X` together with `X` on rename, and the tool moved
it a second time, onto a file that was already there.

This was then got **wrong twice**:

- **r1.0.1** moved `._X` explicitly. That was the change that caused the abort.
- **r1.0.3** measured what the kernel actually does on exFAT and made the
  behaviour platform-aware: on macOS, leave the companion alone; elsewhere `._X`
  is an ordinary file a rename leaves behind, so it must be carried along.

The lesson recorded in the generic prompt: *measure what the platform does
before compensating for it.*

**r1.0.2** fixed a fallback that had never run. `sqlite3.connect()` is lazy, so
the `mode=ro` connection that exFAT cannot support did not fail until the first
query — by which time the `immutable=1` fallback had been skipped. Fixed with a
probe query.

### r1.0.4 — dangerous advice, twice followed

Pre-flight called `.lrcat-wal` and `.lrcat-shm` "stale side files" to be
cleared. That is wrong: a non-empty write-ahead log holds committed
transactions. The tool said so, and its own author acted on it twice. The check
and the documentation were corrected, and the FAQ now states plainly that a
non-empty WAL must never be deleted.

---

## 2026-08-22, evening — Lightroom refuses the catalog

After a migration that reported success and passed verification, **Lightroom
would not open the catalog**: "cannot be opened because of an unexpected error."

The diagnosis took three experiments run by the user:

| | Setup | Result |
| --- | --- | --- |
| Test A | Migrated catalog, copied to APFS | Lightroom tries to repair, does not open |
| Test B | Original catalog on exFAT | Opens, but finds no photos |
| Test C | Migrated catalog, one value cast back to REAL | **Opens, all photos selectable** |

Test C identified the cause exactly. `Adobe_variablesTable.Adobe_entityIDCounter`
had been written as **TEXT** instead of **REAL**. SQLite is happy to store a
number as text in a column with no strict type; Lightroom is not. One value in
one row, in a table that has nothing to do with folders, made the entire catalog
unopenable.

**r1.0.5** reads the stored type before writing, writes back in the same storage
class, and verifies afterwards that the class did not change — refusing to
continue if it did. Two tests now guard it: one for the counter, one asserting
that a whole run changes the storage class of no existing row anywhere.

**r1.0.6** added detection for catalogs already damaged by r1.0.0–r1.0.4, so an
affected library can be identified rather than merely failing.

Two further findings from the same episode:

- **The verification was blind.** It read with `immutable=1`, which ignores the
  write-ahead log — so it validated a view Lightroom would never see.
- **The tests were writing into the user's real configuration directory.** An
  autouse fixture now redirects every user path.

### The migration, repeated and verified

With r1.0.5 the user restored the copy as a fresh original and the run was
repeated. It was then verified independently: integrity check, foreign keys,
the folder tree, every path, storage-class drift across 272,962 rows, a hash
over the develop, keyword and collection tables, and the WAL checkpointed.

**Lightroom opened it, and the photos were selectable in their new folders.**

---

## 2026-08-22, night — what a grown library actually looks like

The user's next requirement: real libraries have subfolders, and a folder that
already carries a date must not be moved or renamed. Asked whether these should
be global switches, the answer was **case-by-case consultation of the
operator**.

**r2.0.0** added folder classification — dated versus topic, with a granularity
rule so that a folder called `2019` is no answer to a request for day folders —
and the decision callback that front ends supply. The planner itself never
prompts.

**r3.0.0** added the graphical interface (PySide6/Qt, chosen by the user over
the alternatives) and support for runs spanning several root folders, after the
user asked whether the tool works across all reachable drives and whether
moving integrates copying across volumes. It does both: same volume is an
atomic rename, across volumes is copy, SHA-256 verify, delete.

---

## 2026-08-23, morning — the installation, from the user's side

Three defects reported by the user from a real installation, none of which any
test could have found:

- **r3.0.1** — `lrfc` was not on `PATH` after installing. The installer now
  edits the shell startup file. (My first verification of the fix was wrong:
  `zsh -l -c` does not read `.zshrc`.)
- **r3.0.2** — the window was taller than a small screen. Settings now scroll
  and the action row is pinned.
- **r4.0.0** — the installer advertised `lrfc gui` without having installed
  PySide6. It now verifies each component by importing it, and only advertises
  what actually works. A `components` file records what was wanted, so `--check`
  can tell "never installed" from "broken".

**r4.0.1** — pre-flight blamed permissions for a catalog whose root folder no
longer exists. It now names the disconnected path, which is the actual problem.

**r4.0.2** — a repeated `new-tree` run was not a no-op: whether a photo was
already in place was decided by comparing paths *and* requiring in-place
placement. Running the same migration twice therefore planned every file as a
move onto itself and rolled the whole run back.

### The second real test

The user ran the 2019 library again through the GUI, this time into
`camera/year/month/day`. Lightroom opened the result without complaint. The
user then edited a photo to confirm the library was genuinely workable — the
2022 develop history was intact.

---

## 2026-08-23, midday — the master catalog

A second library, `Masterkatalog.Neu.lrcat`, 51,049 photos, on a different
drive, with a genuinely complex structure: 16 topic folders (`_extern`,
`_fineart`, `_in_Arbeit/2020…2026`, `raw2020…raw2026`) and 23 dated folders
carrying descriptive text under `raw2026`.

Two things were established before anything ran:

- **The catalog is disconnected.** It records `/Volumes/LR_Master/mobileRAW/`
  while the drive is mounted as `/Volumes/Extreme Pro`; 0 of 51,049 paths
  resolve. The copy itself was verified complete — all 51,049 files present
  under the substituted path, a 300-file sample all non-empty. It must be
  reconnected in Lightroom before any run.
- **Five of the six root folders hold no files at all** — import leftovers.

Asked what should happen to the structure, the user's answer named four
distinct intentions across 39 folders. The vocabulary the tool had could not
express them, which produced **r5.0.0**:

- `resort`, an action that rebuilds a folder *where it stands*, below its own
  parent — neither `consolidate` nor `sort-inside` could say that;
- `{folder_label}`, the descriptive text after a folder name's date, with empty
  levels collapsing so the token is usable as a level of its own;
- an ordered rule list, first match wins, so 39 folders are five lines;
- the move log beside the library (O-24) and the preparation page (O-21, O-22).

### A fault the simulation caught

Simulating the new rules against a scratch copy of the master catalog — before
writing a single byte — showed `resort` filing each photo by its own date, which
tore `2026-06-27 Test 150mm Spiegelobjektiv` in two because twelve of its frames
were shot the evening before. That is precisely what the user had said must not
happen.

`--mismatch-action leave` now governs `resort` as well. 1 of 23 sessions split
before the fix, 0 after. **The fault is invisible in the counts and does not
occur in any synthetic catalog** — only a real library has a shoot that runs
past midnight.

### And one found by reading the output

Checking that report in German revealed that `lrfc --lang de plan X` ran in
English. Every sub-parser redeclares the global flags, and a sub-parser's
default overwrites what the top level already parsed. `--debug` before the
subcommand was silently ignored too, since r1.0.0.

---

## 2026-08-23, afternoon — plain words

Two questions from the user, each of which found a gap.

**"Does the interface show which exceptions were found, so preferences can be
set on them?"** — Only inadequately. Warnings sat on the same line as the
counts, and the exceptions were *one* number, "skipped". That is as good as no
report at all. **r6.0.0** gives each cause its own entry with the file count,
examples and the option that governs it — a table of its own in the graphical
interface, a section of its own on the command line.

**"We have no history file."** — True. This document is the answer.

Checking the new output turned up two old faults: `lrfc --lang de plan X` ran in
English, because every sub-parser redeclares the global flags and their defaults
overwrite what the top level already parsed (since r1.0.0, and `--debug` with
it). And German messages used ASCII substitutes for umlauts while the graphical
interface's own text used real ones — the two stood side by side on screen.

**r6.1.0** numbered the documents by weight, at the user's request, with the
same numbers in both languages.

---

## 2026-08-23, late afternoon — the return ticket

Two more requests, and the second is the one that mattered.

**"Could a topic folder be moved to the new location unchanged?"** — It could
not; every action either sorted the folder's contents or left them alone. The
`relocate` action fills the gap, for material that should come along without
being touched.

**"Could we build a rollback?"** — It had been there since r1.0.0, and could be
reached only from the command line. A rollback the operator cannot reach from
the window they actually use is a rollback they will not have when they need
it, so **Undo a run…** went into the menu bar. Reversing means files and
catalog together: the moves are undone in reverse order, the created folders
removed if empty, and the catalog restored from that run's own backup.

Writing the first `relocate` test against a nested folder exposed an older
fault: a rule pattern only ever matched folders sitting directly below the
root, so `_extern` found `_extern` but not `raw2019/_extern`. No run had shown
it, because the master catalog happens to keep `_extern` at the top.

---

## 2026-08-23, afternoon to night — what using it turns up

From r7 to r16 barely a revision came out of a plan. Nearly every one existed
because the user was using the tool and something was wrong.

**What the interface would not give up.** The target folder could not be
reached, because field and button *looked* disabled (r7.0.0). The dividers
between sections were all but invisible (r7.1.0). The menu entries were missing
entirely on macOS, where Qt does not support actions directly on the menu bar
— which made the undo just built unreachable (r8.0.1). And the newly chosen
mark was nowhere to be seen, because macOS shows no icon in a window title bar
(r10.1.0). Four times the same shape: built, present, unusable.

**What only real data showed.** A rule pattern matched only folders directly
below the root (r8.0.0). `leave` left nothing alone under new-tree, being
identical to `relocate` (r13.0.1). The run record did not name the rules that
had shaped the run, so the result could not be explained from it (r13.0.4).
`Straße` became `Strae`, the sharp s vanishing outright (r14.0.0). And the fix
for that did nothing, because macOS hands back decomposed filenames and the
character map never matched (r14.0.1).

**Two tests that enshrined the wrong answer.** The ASCII test asserted
`"Grun Strae"` as correct: it had not caught the defect, it had recorded it.
And the test for the romanisation used a source literal, which cannot produce
the decomposed form at all.

**And fixes worse than the fault.** To discard a superseded plan I passed a
ticket through a lambda around the slot, which removed the QObject receiver, so
Qt made the connection direct rather than queued and widgets were built on the
worker thread. The folder decisions silently stopped working (r15.0.2). And the
first detector for interrupted runs read the state from paths; a later run into
the same target turned that into a false positive that blocked sound libraries
(r16.0.1).

**Guards rather than good intentions.** Three times the answer was not a fix
but a check that makes the regression impossible: that every action, token and
flag appears in both language trees (r11.0.0); that both interfaces can set the
same settings and every writing interface offers preconditions, history and
undo (r15.0.0); and that this history names every released revision.

**Finally, the interruption.** Driving the window from a script I killed a
process partway through a reversal: 27,660 files back, 23,050 still at their
new paths. Recoverable, because the catalog is restored last — but nothing in
the tool said so or helped. That became r16.0.0.


---

## 30 August 2026 — the window no longer fitted in a window

Andreas reported that the settings were too many for one window. They were.
Everything was stacked in a single scrolling column: the window showed the
catalog and hid the structure, the options and the rules below the visible
edge, behind a scrollbar nobody had reason to suspect.

The prehistory is the interesting part. This exact problem had been reported
once before — then as "the collapsible sections are hard to find" — and the
answer had been to make the dividers easier to grab: wider, with a rule, a
cursor and a tooltip. A better handle on the wrong shape. Only r18.0.0 changed
the shape.

**r18.0.0 "Übersicht"** put the window into five tabs, one per step of the
work, and left the mark, the profile row, the log and the buttons in place. The
log stayed outside the tabs deliberately: it is where an error appears, and an
error behind a tab is an error nobody sees. The buttons got the order of the
work and a rule between forward and back — *Undo* had been sitting next to
*Apply* as though it were the next step.

Building it produced a fresh instance of the same mistake at once: after a plan
the window brings the result forward, which is helpful — except that changing a
rule re-plans *automatically*, so it would have thrown the operator out of the
folder table on every rule. The same crowding in a different coat.

Profiles were straightened out in the same pass. Until then a profile came into
being by typing a name nobody had used yet and pressing *Save* —
undiscoverable, and a typo silently made a second one.

Incidentally: the test suite was taking ten minutes instead of eighteen
seconds. One test hung on a modal warning, and that had gone past me as "the
GUI tests are just slow".

## 15 September 2026 — four wishes, and which one had to go first

Andreas came with four: edit keywords automatically, derive them from file and
folder names, build a new catalog out of a search, and index keywords across
every library. Explicitly asking to agree and document before anything was
built.

Checking against the real catalogs first settled three of the four:

| Question | Finding |
| --- | --- |
| How many libraries? | **48** across several drives, some 135,000 images |
| Keyword hierarchy | two levels at most; `genealogy` is a path of digit-count-prefixed ids — 577 of 577 read that way |
| Count bookkeeping | `imageCountCache` is `-1`; Lightroom recomputes it |
| Copies detectable? | yes, via `Adobe_images.id_global` — the trial found a pair with **different image counts** (3296/3298) |

**The first wish was deferred entirely**, at Andreas's decision. The reason
deserves recording: the tool is as safe as it is because it **touches no photo
row**. Keywords hang directly off the images through `AgLibraryKeywordImage`
and break that promise. The index, by contrast, only reads.

**r19.0.0 "Fundort"** brought the index: 47 libraries, 183,407 photographs,
1,054 keywords, read in 26 seconds without opening a single image file. A guard
test seals the new package off from the folder path — `cli.py`, `planner.py`,
`executor.py` and `folders.py` may not so much as import it.

Recognising copies was the most instructive part. The first design hashed a
sample of photo UUIDs. It worked against the real catalogs — and **only by
luck**: ordered by UUID, photographs added later scatter evenly through the
sample. A test with a library of *three* photographs exposed it. Insertion
order plus an overlap test instead of equality took the count of recognised
copies from three to six, all genuine.

The export runs deliberately backwards: rather than writing a catalog, copy the
existing one and remove from the copy what was not selected. What survives was
written by Lightroom itself.

## What the real tests have shown

All runs against `Masterkatalog.Neu.lrcat`, 51,049 photos, 2.36 TB, unless
noted otherwise.

| Date | Library | What was run | Result |
| --- | --- | --- | --- |
| 22 Aug | `2019.lrcat`, 9,489 | first live run | aborted at file 850 — AppleDouble collision |
| 22 Aug | `2019.lrcat` | repeated | ran and verified, **Lightroom refused the catalog** |
| 22 Aug | `2019.lrcat` | after r1.0.5 | ran, **Lightroom opened it**, photos selectable |
| 23 Aug | `2019.lrcat` | `camera/year/month/day` via the window | opened, a photo edited afterwards |
| 23 Aug 11:40 | master catalog | `{yyyy}/{mm}/{dd}`, command line | 51,049 moved, Lightroom opened, undone |
| 23 Aug 16:52 | master catalog | cumulative date levels | verified, undone |
| 23 Aug 17:34 | master catalog | all four folder actions at once, orphans | verified, undone |
| 23 Aug 18:50 | master catalog | window, with per-folder decisions | verified, undone |
| 23 Aug 20:25 | master catalog | window, ASCII names | showed the romanisation was not firing |
| 23 Aug 21:05 | master catalog | window after r14.0.1 | `Voelki` correct, undone |
| 23 Aug 21:35 | master catalog | **text interface**, writing | 50,709 moved, undone via `Ctrl+Z` |
| 23 Aug 21:40 | master catalog | **command line**, `{folder_label}` + `refile` | exposed the doubled label |
| 23 Aug 22:24 | master catalog | **window** after r15.0.2 | verified, undone |
| 23 Aug 22:31 | master catalog | command line, **killed after 35 s** | 13,605 moved, `resume` put them all back |
| 23 Aug 22:41 | master catalog | **text interface** after r16.0.1 | verified, undone via `Ctrl+Z` |
| 23 Aug 22:46 | master catalog | text interface, **killed after 45 s** | resumed from within it via `Ctrl+E` |
| 30 Aug | GUI after r18.0.0 | window in tabs, profiles made and deleted | 633 tests, confirmed in use by Andreas |
| 15 Sep | **48 catalogs**, several drives | first index run | 43 of 54 failed — cursor `lastrowid` read after the child insert |
| 15 Sep | the same | after the fix | 47 libraries, 183,407 photographs, 1,054 keywords in 26 s |
| 15 Sep | the same | copy detection by equality | 3 copies — as it turned out, by luck |
| 15 Sep | the same | by overlap, insertion order | **6 copies**, all genuine (`_Archiv`, `-v13`) |
| 15 Sep | `shootings.lrcat`, 6,043 | export: copy reduced to 7 photographs | 10.0 MB instead of 78.3 MB, original byte-identical |

Every cycle ended byte-identical to where it started: ten catalog tables, every
path, and all 51,063 files on disk.

**Most of the defects that mattered were found by real runs, not by the test
suite.** Its job is to keep them fixed — 653 tests by now.

## See also

- [CHANGELOG.md](https://gitlab.com/andy-freund/LR-CompanionSuite/-/blob/main/CHANGELOG.md) — what changed, per revision
- [13-open-issues.md](13-open-issues.md) — what is known to be missing
- [14-prompts.md](14-prompts.md) — the original brief and the regeneration prompt
- [10-development.md](10-development.md) — how to continue the work
