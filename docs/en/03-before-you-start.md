# Before you start

**Revision r17.0.3 · Build date 2026-08-24**

Two things about your library have to be true before LR-FolderCraft touches
anything. Neither is difficult, both are easy to overlook, and both were found
the hard way during the tool's own testing.

---

## 1. Every folder must be connected in Lightroom

A Lightroom catalog does not store where your photos are today. It stores where
they were when they were imported: an absolute root path such as

```
/Volumes/LR_Master/mobileRAW/
```

plus a path below it for each folder. If the drive is now mounted under a
different name — because it was renamed, cloned, restored from a backup, or
plugged into a different machine — the catalog still names the old path.
Lightroom shows those folders with a **question mark**.

**LR-FolderCraft cannot work on a library in that state.** It resolves every
photo to an absolute path and moves the real file. If the path in the catalog
does not exist, there is no file to move, and pre-flight stops the run rather
than guessing where the photos might be.

### How to tell

Run `lrfc info` against the catalog. It lists each root folder with how many
files were found on disk:

```
Root folders
  /Volumes/LR_Master/mobileRAW/     51,049 files    0 found on disk   <- broken
  /Volumes/Photos/2019/              9,489 files    9,489 found       <- fine
```

`0 found on disk` for a root that holds thousands of files means the path is
stale, not that the photos are gone.

### How to fix it

Do this **in Lightroom, not in the tool**. Lightroom's own reconnect is the
only mechanism that updates the catalog the way Lightroom expects.

1. Open the catalog in Lightroom Classic.
2. In the **Folders** panel, find the topmost folder with a question mark.
   Reconnecting a parent reconnects everything below it, so always start at the
   top of the tree.
3. Right-click it → **Find Missing Folder…**
4. Point the dialog at where that folder actually is now.
5. Repeat for any remaining question marks, then quit Lightroom.

Run `lrfc info` again. Every root should now report its files as found.

### Why the tool does not do this for you

It could — the change is one `UPDATE` on `AgLibraryRootFolder.absolutePath` —
and it deliberately does not. Guessing which directory on which drive is meant
to be the new home of a root folder is exactly the kind of decision that is
cheap to get wrong and expensive to undo. Lightroom asks you to point at the
folder; so should anything that edits its catalog.

---

## 2. The catalog should be on the current Lightroom version

Lightroom Classic upgrades a catalog's schema when a new version opens it for
the first time. Until you do that, the file on disk is still in the old format.

LR-FolderCraft reads the schema version and refuses versions it has not been
verified against, because a schema it does not know may hold a table it does
not know it has to keep consistent. Working on an old catalog and then letting
a new Lightroom upgrade the result afterwards means two migrations stacked on
top of each other, with only the second one covered by a backup you made
deliberately.

**Convert first, reorganise second.** In Lightroom Classic: **File → Open
Catalog…**, pick the `.lrcat`, and accept the upgrade prompt. Lightroom writes
a new file — typically `MyCatalog-v14.lrcat` — and leaves the original
untouched. Point LR-FolderCraft at the upgraded file.

`lrfc info` prints the schema version it found and whether that version has
been verified:

```
Catalog version    18.0.0  (verified)
```

If it says `not verified`, `--allow-unsupported-catalog` will proceed anyway.
Do that only against a copy.

---

## The short checklist

| | |
| --- | --- |
| Catalog opened once with your current Lightroom Classic | so the schema is current |
| No question marks in the Folders panel | so every file can be found |
| `lrfc info` reports files found for every root | the machine-readable version of the above |
| Lightroom Classic **closed** | the catalog must not be open while it is rewritten |
| A backup you made yourself, on a different drive | the tool makes one too, but yours is the one that is somewhere else |

The tool checks all of these in pre-flight and refuses to run if any fails.
The list is here so the failures are not a surprise.

---

## See also

- [04-usage.md](04-usage.md) — the commands and options
- [06-safety.md](06-safety.md) — what the backup covers and how to undo a run
- [07-faq.md](07-faq.md) — including what to do if Lightroom refuses to open a
  catalog afterwards
