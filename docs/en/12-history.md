# Project history

**Revision r13.0.1 · Build date 2026-08-23**

The [CHANGELOG](../../CHANGELOG.md) says what changed in each revision. This
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
| What each revision contains | [CHANGELOG.md](../../CHANGELOG.md) | Yes — written at the time |
| Test results and their numbers | Run output, quoted in the commits | Yes |
| Reasoning, alternatives, what was learned | Reconstructed from the record | The account is faithful, but it is a narrative written afterwards |

So it is a companion to the change history, not a replacement for it. **To trace
an individual change**, use the tools that record it exactly:

```bash
git log --oneline --reverse          # every step, in order
git show v5.0.0                      # what one revision was
git log -p -- src/lrfoldercraft/planner.py    # one file's whole life
```

The CHANGELOG lists releases newest first. This document reads **forwards**,
oldest first, because it is meant to be read as a story rather than looked up.

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

## What the real tests have shown

| Date | Library | Photos | Result |
| --- | --- | --- | --- |
| 2026-08-22 | `2019.lrcat` | 9,489 | Aborted at file 850 — AppleDouble collision |
| 2026-08-22 | `2019.lrcat` | 9,489 | Ran, verified, **Lightroom refused the catalog** — id counter written as TEXT |
| 2026-08-22 | `2019.lrcat` | 9,489 | Ran, verified, **Lightroom opened it**, photos selectable |
| 2026-08-23 | `2019.lrcat` | 9,489 | `camera/year/month/day` via the GUI, **opened, photo edited afterwards** |
| pending | `Masterkatalog.Neu.lrcat` | 51,049 | Simulated only; needs reconnecting first |

Three of the four defects that mattered were found by running against a real
library, and none of them by the test suite. The suite's job is to keep them
fixed.

---

## See also

- [CHANGELOG.md](../../CHANGELOG.md) — what changed, per revision
- [13-open-issues.md](13-open-issues.md) — what is known to be missing
- [14-prompts.md](14-prompts.md) — the original brief and the regeneration prompt
- [10-development.md](10-development.md) — how to continue the work
