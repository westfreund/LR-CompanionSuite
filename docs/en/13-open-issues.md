# Open issues and roadmap

**Revision r20.0.2 · Build date 2026-09-15**

An honest list of what is not done, not verified, or deliberately left out.
Each item is a starting point for the next session.

## Not yet verified

### O-1 · The reference library is migrated and accepted by Lightroom ✔
Closed on 2026-08-22. The 9,452-file / 337 GiB catalog on `/Volumes/1TB-2` was
reorganised into 152 day folders, and **Lightroom Classic opens the result with
every photo selectable in its new folder**.

Verified independently of the tool: all 9,489 files present at an unchanged
size, `integrity_check` ok, `foreign_key_check` clean, no orphan folders, no bad
path prefixes, all 9,452 catalog paths resolving, all 32 virtual copies still
attached to their masters, no SQLite storage-class drift across 272,962 rows,
the write-ahead log checkpointed to zero, and a hash over `Adobe_images`,
`Adobe_imageDevelopSettings`, `AgLibraryKeywordImage` and
`AgLibraryCollectionImage` identical to the pre-run copy. Re-planning reports
0 to move and 9,452 already in place.

It took three attempts, and each failure was worth more than the success:

1. Aborted at file 850 on the AppleDouble defect (r1.0.3). The rollback restored
   all 850 files, removed 152 directories and left the catalog byte-identical —
   an unplanned but conclusive test of the rollback path on a real library.
2. Completed, but Lightroom refused to open the result and repaired it into a
   byte-identical file, over and over. The cause was the storage-class defect
   (r1.0.5): the id counter written as TEXT instead of REAL. Every check the
   tool ran passed, because none of them looked at `typeof()`.
3. Completed and accepted.

### O-2 · A migrated catalog has been opened in Lightroom ✔
Closed on 2026-08-22 together with O-1. Confirmed twice: first on a corrected
copy of the rejected catalog — one value cast back to REAL and nothing else —
which proved the diagnosis, and then on the freshly migrated library.

### O-3 · The Windows installer has not run on Windows
`install/install-windows.ps1` was written carefully and structurally checked,
but no Windows machine was available. **Next:** run it on Windows 10/11, then
`lrfc info` on a catalog there.

### O-4 · Only one catalog schema version tested
Verified against 18.0.0 (Lightroom Classic 14). 11.x–19.x are accepted with a
warning. **Next:** test against an older catalog and add verified versions to
`VERIFIED_CATALOG_VERSIONS`.

### O-5 · Cloud-synced catalogs untested
Sync tables (`AgPendingOz*`) are not touched and photo ids do not change, so it
should be fine — but it is unproven. **Next:** test with a synced catalog and a
backup, then document the outcome.

### O-6 · Network volumes untested
SMB and NFS behave differently around locking and atomic renames. **Next:**
test, and add a pre-flight warning if a network path is detected.

## Known limits

### O-7 · Several root folders in one run ✔
Closed in r3.0.0. Each root folder becomes a scope with its own anchor, and all
of them are handled in one transaction and one journal. Verified across two
physical volumes: four files sorted below two different roots, all catalog
paths resolving, and a second run reporting nothing to do.

### O-8 · No resume after interruption
The journal records enough to resume, but only `undo` is implemented. A
`lrfc resume JOURNAL` that continues where a run stopped would be useful for
very large libraries. **Effort:** moderate; the data is already there.

### O-9 · No file renaming as a feature
Files are renamed only to resolve a collision. Renaming as a goal — say to
`{yyyy}-{mm}-{dd}_{camera}_{seq}` — is a natural extension, but it multiplies
the risk surface and belongs in its own major release.

### O-10 · No dry-run diff against a previous plan
Comparing two plans ("what changed since yesterday?") would help on libraries
that keep growing. The plan JSON already contains everything needed.

### O-11 · Progress reporting is coarse
The console updates every 25 files and the TUI likewise. Fine for renames,
coarse for a slow cross-volume copy where per-file byte progress would be
better.

### O-12 · No parallel copying
Cross-volume transfers are sequential. Parallelism would help on fast SSDs and
hurt on spinning disks, so it needs to be measured and made optional.

### O-13 · Empty directories on disk are only pruned for source folders
Directories that were empty before the run are left alone. That is deliberate —
deleting directories the tool did not create is not its business — but it can
leave a slightly untidy tree.

### O-14 · `--ignore-lock` is a loaded gun
It exists for inspecting a locked catalog. Nothing stops you passing it to
`apply`. It could be restricted to read-only commands.

## Agreed and deferred

Requested on 2026-08-23 and deliberately postponed until after the second test
run, so the tests are not chasing a moving target. O-21, O-22 and O-24 were
delivered in r5.0.0 because all three serve the master-catalog run directly.
Everything on this list has now been delivered; O-26 awaits only a choice
between the six proposals. The original requirements are kept below each item,
because the reasoning is worth more than the tick.

### O-21 · A page about reconnecting a copied library ✔ r5.0.0
Delivered as [03-before-you-start.md](03-before-you-start.md) /
[vorbereitung.md](../de/03-vorbereitung.md), linked from both indexes. The
original requirement follows.

A catalog records the **absolute** path of its root folders. Copy a library to
another drive, rename a volume, or restore from a backup, and the catalog still
points at the old location: every photo shows as missing, and this tool refuses
the run (r4.0.1 names the cause). Since making a copy first is exactly what the
safety guidance recommends, the guidance has to cover the consequence.

Wanted: a short page of its own, linked from installation, usage and safety in
both languages, showing the symptom, the Lightroom remedy (right-click the
folder, Find Missing Folder), and the alternative of renaming the volume back.
Include how to see the recorded path (`lrfc folders CATALOG`) so the reader can
tell what the catalog expects.

### O-22 · Recommend converting the catalog first ✔ r5.0.0
Delivered as section 2 of the same page. The original requirement follows.

A catalog written by an older Lightroom Classic opens in a newer one only after
conversion. Working on an unconverted catalog with this tool means writing to a
schema the installed Lightroom has not accepted yet. Observed in practice: a
restored library was schema 17.0.0 and became 18.0.0 the moment Lightroom
opened it.

Wanted: an explicit recommendation to open the catalog once in the installed
Lightroom Classic — which reconnects and converts in the same pass — before
running LR-FolderCraft. Belongs next to O-21.

### O-23 · Make both interfaces state the preconditions ✔ r9.0.0
Delivered as `safety.preconditions()` plus a dialog that must be ticked, not
clicked. The original requirement follows.

Wanted: before the first run in a session, the TUI and the GUI should state the
three preconditions — Lightroom closed, catalog opened once in the installed
Lightroom, backup present — and require an explicit acknowledgement. Not a
dialog that is clicked away by reflex: it should show what was actually found
(schema version, whether all paths resolve, whether a backup directory has a
recent copy) so the acknowledgement means something.

The command line has the pre-flight report for this; the two interfaces show it
only after planning.

### O-24 · A move log beside the library ✔ r5.0.0
Delivered in `movelog.py`, controlled by `--no-move-log` and `--move-log-dir`.
Written in the `finally` of the run so a failed or rolled-back run is recorded
too, and strictly non-fatal. The original requirement follows.

Wanted: a human-readable record of what a run did, written into the library's
own folder rather than only into `~/Library/Logs`, so it travels with the
library when it is moved or archived — and so it can be found months later
without knowing where the tool keeps its logs.

Sketch: `LR-FolderCraft_<catalog>_<yyyy-mm-dd_HHMM>.log` next to the `.lrcat`,
holding the revision and build date, the settings, the folder decisions, one
line per file moved (from, to, renamed), the counts, and the result including
the backup and journal paths. The JSON-Lines journal stays what it is -- a
machine-readable record for undo; this is the one a person reads. Make the
location configurable and allow it to be turned off, because a read-only or
full volume must not fail a run.

### O-25 · A short description inside the graphical interface ✔ r9.0.0
Delivered as a purpose line at the top of the window and Actions → About. The
original requirement follows.

The window says what it is only through its title bar. Someone opening it
without having read the documentation has no statement of what the tool does,
what it will and will not touch, or where its safety net is.

Wanted: a compact "About" reachable from the menu — what LR-FolderCraft does in
three sentences, the promise that only folder rows and the file's folder column
are ever written, the revision and build date, the licence, and a link to the
repository. Plus a one-line description in the window itself, above the catalog
field, so the purpose is visible without opening anything. Both languages, from
the existing `gui/i18n.py` table.

### O-26 · A logo ✔ r10.0.0
Six proposals, then three variants of the chosen one; 6c was picked. The mark
ships as two cuts in `docs/images/brand/`, the letters drawn rather than set,
and appears in the window icon, the About box and both READMEs. The proposals
are kept in `docs/images/logos/` for the record. The original requirement
follows.

The project has no mark of its own: not in the window, not in the READMEs, not
as the GitLab project avatar, not as a favicon for the documentation.

Wanted: a handful of distinct proposals to choose from, as SVG so they scale
and can be recoloured. Constraints worth respecting: it has to read at 16 px
for a favicon and a window icon as well as large; it should work in light and
dark; and it should suggest *ordering photographs into folders* rather than
being a generic camera. Once one is chosen: export the sizes the window icon,
the GitLab avatar and the documentation need, and reference it from both
READMEs.

## Extension: an index across every library

Agreed on **15 September 2026**. Andreas wants to use the tool beyond
reorganising folders. Four wishes were on the table; the decisions are recorded
here so that the shape of the work stays explicable later.

### What was checked first

Against the real catalogs, not from memory:

| Question | Finding |
| --- | --- |
| How many libraries? | **48 catalogs** reachable across several drives, together some 135,000 images and 600,000 keyword assignments |
| Keyword hierarchy | two levels at most; `genealogy` is a path of ids each prefixed by its digit count (`/594387/594391`) — **577 of 577** entries read that way |
| Count bookkeeping | `imageCountCache` is `-1`: Lightroom recomputes it, so nothing has to be kept consistent |
| Cloud sync | `AgRemotePhoto` is empty in the master catalog. **To be checked per catalog**, never assumed |
| Are copies detectable? | yes — `Adobe_images.id_global` is a UUID per photo that a copy carries with it. The trial found two groups of copies, one of them with **different image counts** (3296 / 3298), which any comparison by size or name would have missed |
| Drive identity | macOS gives each volume a `VolumeUUID`, independent of its name |

### The decisions

**It stays in this project**, but strictly separated. The safety machinery —
opening read-only, the backup, the journal, undo, resume — is the hard-won
asset; a second project would either duplicate it or do without. Four promises
go with that:

1. New code lives in modules of its own, **never** in `planner.py`,
   `executor.py` or `folders.py`.
2. A **guard test** checks that the folder path does not so much as import the
   new modules. A fault there cannot then reach it.
3. Subcommands of its own; the existing ones are untouched.
4. The existing tests are the floor, not the target.

**Catalogs and image files are not touched.** The index only reads.

### O-27 · An index across every library ✔ r19.0.0
An index of its own covering every known library, able to answer even when the
drive is in a cupboard — it then says *which* drive to connect.

Per image: **catalog name, folder name, file name, the keywords assigned in the
catalog, and the EXIF data.**

Three requirements shape the design:

- **Copies and backups of catalogs must not appear twice.** The route is proven
  above: the image UUIDs (`Adobe_images.id_global`) identify a copy as a copy.
  One of a group counts, the others are recorded rather than silently dropped —
  which one is the valid one is a person's decision.
- **Several drives, one index.** Its path and file name are chosen, so it can
  live where it is needed.
- **A stable identifier per drive**, not the drive's name: on macOS the
  `VolumeUUID`. On Windows the counterpart is the volume GUID; that is **still
  to be verified**. With neither available, a fingerprint of filesystem, size
  and creation date has to stand in — and must declare itself the weaker
  answer.

The index is a **snapshot**. It has to say, per catalog, when it last read it,
or it claims a currency it does not have.

### O-28 · Sameness and similarity ✔ r19.0.0
Finding duplicate files and duplicate catalogs. Two stages that must not be
confused:

- **Sameness** can be answered without the files: capture time, camera, file
  name and pixel dimensions from the catalog together make a dependable key.
  That works with the drive disconnected.
- **Similarity** — series, variants, crops — needs the image data and therefore
  a connected drive. It is a separate, slower pass, and must not pretend to
  come out of the index.

### O-29 · A set from the index, and a catalog from the set ✔ r19.0.0
Assemble a set from the filtered images and make a catalog of it — **across
catalogs**, carrying the settings held in the source catalog, into a catalog to
be newly created or updated.

The proposed route is **subtractive rather than constructive**: writing a
catalog from nothing would mean rebuilding develop settings, collections and
previews. Instead, take a **copy** of each source catalog and remove the images
not chosen. The result is certainly a valid catalog with every setting intact,
without a single new kind of row being written — and the original is never
touched. Merging the reduced catalogs is then Lightroom's own *"Import from
Another Catalog"*.

**Not yet verified**, and to be proven before any implementation: that a
catalog reduced this way opens and imports without complaint.

### What turned out differently

Two things the plan of 15 September did not foresee:

- **Copies are matched by overlap, not by equality.** The first attempt hashed
  a sample of photo UUIDs. It worked against the real catalogs -- but only by
  luck: ordered by UUID, photographs added later scatter evenly through the
  sample. A test with a library of three photographs exposed it. The sample is
  now drawn in insertion order and compared for **overlap**. Against the real
  collection: six copies found instead of three.
- **The command line only, for now.** The index is a tool with questions of its
  own -- searching, drives, duplicates -- and pushing it into the existing
  window as an afterthought would have made both worse. The window and the
  terminal interface are still to come; see O-31.

### O-31 · The index in the window and the terminal interface ✔ r20.0.0 (in part)
The folder reorganisation has three front ends; the index has one. What is
needed at least: search with the criteria from `index find`, the list of drives
with what is attached, and the duplicate report. The export probably belongs
there too, but then with the same confirmation the command line asks for.

### O-32 · A tool of its own, with a name of its own? ✔ r20.0.0
Raised by Andreas on 15 September 2026, once the index existed: the searching
half probably deserves a **window of its own**, and may well be a **tool of its
own** with its own name. His suggestion: *LR-MetaSearch*.

The observation behind it holds. More searching and reassembling is going on
than was expected, and the index answers different questions from the folder
reorganisation, has a different data model, and addresses a different mood --
curating rather than tidying.

**Three things have to be decided, and they are often confused:**

| Question | Note |
| --- | --- |
| Its own name and window? | Everything argues for it. Cheap, and changes nothing technical. |
| Its own command (`lrms` rather than `lrfc index`)? | Follows from the name. An alias will do at first. |
| Its own repository? | This is the expensive question -- and the only one that is hard to undo. |

**Recommendation:** yes to the first two, not yet to the third. One repository
with two tools and a shared core costs one CI, one release ritual and one
documentation tree; two repositories cost all of it twice, and the shared core
-- `catalog/db.py` with its `mode=ro`/`immutable=1` fallback, lock detection and
schema checks -- would have to be duplicated or published as a package of its
own. For one person that is a lot.

The separation already exists in the code (`index/` plus its guard test), and
that is precisely what makes a later split cheap: the package can be lifted out
with its history when the time comes. The other direction is expensive.

**Still open:** whether the name fits. *MetaSearch* describes the searching
well but leaves out finding duplicates and assembling new catalogs. That is not
an objection -- a name need not cover everything -- but it should be a decision
rather than an accident.

### How O-32 was decided
On 15 September 2026: **LR-CompanionSuite**, one repository, two tools. The
name came from Andreas after two others were considered and dropped --
"MasterSuite" collided with his own `Masterkatalog`, and *Companion* says
exactly what relation the tools have to Lightroom.

The rename happened **now** rather than later: the website and the mirror
existed, but nothing had been posted anywhere yet. Today a new name cost close
to nothing; in two months it would have cost everything that had been built up
in findability.

At Andreas's request the **old GitLab repository is left standing untouched**.
The new one is a project of its own, not a renamed one.

Not decided, because it did not need to be: a second repository. The separation
exists in the code (`metasearch/` plus its guard test), which keeps that cut
cheap for whenever it is wanted.

### O-33 · LR-MetaSearch in the terminal interface
r20.0.0 brought the window, not the text interface. The folder reorganisation
has three front ends, LR-MetaSearch has two. Searching and the list of drives
would be the minimum; the export probably does not belong in a terminal.

### O-30 · Writing keywords — deferred
Originally the first wish, **deferred entirely** at Andreas's decision.

Why it deserves its own thought: the tool is as safe as it is today because it
**touches no photo row** — it changes `AgLibraryFolder` and
`AgLibraryFile.folder` and nothing else. Keywords hang directly off the images
through `AgLibraryKeywordImage` and break that promise.

If it is ever taken up, two routes are open: directly in the catalog with the
existing safety machinery, or a Lightroom plugin through the Lua SDK — Adobe's
intended route, which brings a second language, a second way to install, and
the limit of one open catalog at a time. The derivation itself, which is the
hard part, would be the same either way: getting the keywords *Andreas
Vorreyer* and *Kathrin* out of `2025.05.17 Andreas Vorreyer - Kathrin/` is
pattern work of the kind the existing rule engine already does.

## Ideas, not commitments

### O-15 · GUI ✔
Closed in r3.0.0: a Qt front end with all settings, per-folder decisions, a
native target-folder chooser and a progress bar. Rearranged into tabs in
r18.0.0, once it became clear the settings no longer fit in one window. `textual serve` would still be
a cheap way to reach the text interface remotely, if that is ever wanted.

### O-16 · More grouping criteria
Candidates: ISO speed band, lens focal length band, GPS location (city from
reverse geocoding — needs a data source), keyword, colour label, rating, import
session, `{orig_folder}` sub-patterns.

### O-17 · Undo history / multiple journals
A `lrfc history` listing past runs with their journals, so you can undo the run
before last.

### O-18 · Catalog health report
`lrfc doctor`: missing files, duplicate names, folders with no rows, photos
outside every root folder, capture times far in the future.

### O-19 · Preset sharing
Profiles are JSON already. A small library of community structures would be
easy.

### O-20 · Localisation beyond EN/DE
`rules.py` holds month and weekday names in a dictionary keyed by language, and
`Check`/`TokenSpec` carry both strings inline. A third language means extending
those structures — the architecture is ready, the text is not externalised into
`.po` files yet, which it would need to be at that point.

## Answered questions

Kept so the reasoning is not lost.

| Question | Decision |
| --- | --- |
| Where do new folders go? | Both modes implemented; `in-place` is the default. |
| Which TUI framework? | Textual — widgets, mouse, and a path to Textual Web. |
| Python baseline? | 3.9, so macOS's own Python works with no install. |
| How far to go on the sample catalog? | Analysis and dry-run only; the live run stays with the user. |
| Rename or skip on collision? | Rename by default, with the catalog updated so nothing is lost. Every rename is in the plan, the report and the journal. |
| Is `file-mtime` a good default date source? | No. It is usually the copy date and would misfile photos silently. Opt-in only. |

## Open questions

**Q-1 · Should `apply` refuse `--ignore-lock`?** Safer, but it removes an
escape hatch for a stale lock file after a Lightroom crash. Perhaps require an
additional `--i-know-what-i-am-doing`.

**Q-2 · Should the unsorted folder be inside the anchor or beside it?** It is
currently inside, next to the day folders. Beside it would keep the sorted tree
clean.

**Q-3 · Should `apply` write a report file by default?** It currently writes
the plan into the reports directory. A machine readable *result* file could be
useful for automation.

**Q-4 · How should a resume distinguish "interrupted" from "finished"?** The
journal has `run-end`, but a hard power cut leaves none. Absence of `run-end`
plus a `catalog-commit` is ambiguous for exactly one instant.
