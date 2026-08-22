# Open issues and roadmap

**Revision r1.0.4 · Build date 2026-08-22**

An honest list of what is not done, not verified, or deliberately left out.
Each item is a starting point for the next session.

## Not yet verified

### O-1 · The real library has been migrated ✔
Done on 2026-08-22. The 9,452-file / 337 GiB catalog on `/Volumes/1TB-2` was
reorganised into 152 day folders. Independently verified afterwards: every one
of the 9,489 files present with an unchanged size, `integrity_check` ok,
`foreign_key_check` clean, no orphan folders, no bad path prefixes, all 9,452
catalog paths resolving on disk, all 32 virtual copies still attached to their
masters, and a hash over `Adobe_images`, `Adobe_imageDevelopSettings`,
`AgLibraryKeywordImage` and `AgLibraryCollectionImage` identical to the pre-run
copy. Re-planning reports 0 to move and 9,452 already in place.

The first attempt aborted at file 850 on the AppleDouble defect (see r1.0.3)
and rolled back completely — 850 files restored, 152 directories removed, the
catalog byte-identical. That was an unplanned but conclusive test of the
rollback path on a real library.

### O-2 · No result has been opened in Lightroom itself
Verification is at the database and filesystem level: integrity check, foreign
key check, folder tree validity, path resolution and an unchanged hash over the
image, develop, keyword and collection tables. The visual confirmation in
Lightroom Classic — open the catalog, check the Folders panel, spot-check a few
develop histories and virtual copies — is the one remaining step. **Next:** open
`/Volumes/1TB-2/Lightroom/2019/2019.lrcat` in Lightroom Classic.

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

### O-7 · One root folder per run
If a selection spans several root folders the planner refuses and asks you to
restrict it. Multi-root runs would need per-root anchors and a per-root
transaction story. **Workaround:** run once per root folder.

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

### O-15 · GUI
The seam is prepared; see [development.md](development.md#the-gui-seam).
Recommended first step: `textual serve` to reuse the existing TUI in a browser,
before committing to Qt.

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
