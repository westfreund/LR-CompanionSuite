# Open issues and roadmap

**Revision r4.0.0 · Build date 2026-08-23**

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

## Ideas, not commitments

### O-15 · GUI ✔
Closed in r3.0.0: a Qt front end with all settings, per-folder decisions, a
native target-folder chooser and a progress bar. `textual serve` would still be
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
