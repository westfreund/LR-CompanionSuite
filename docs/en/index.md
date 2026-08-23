# LR-FolderCraft — Overview

**Revision r4.0.2 · Build date 2026-08-23**

LR-FolderCraft reorganises the folder tree of an Adobe Lightroom Classic
library. It moves the image files on disk and rewrites the catalog in the same
operation, so every reference Lightroom holds stays intact.

## Why a separate tool is necessary

Lightroom Classic offers no programmable way to do this:

- The **Lua SDK** can read photos and metadata, but it has no API for moving a
  photo from one folder to another. Plug-ins simply cannot do it.
- **Finder / Explorer** can move the files, but Lightroom then shows every one
  of them as missing and you have to reconnect folders by hand.
- **Dragging in the Folders panel** works correctly but is a manual operation.
  For 152 target folders and nearly ten thousand photos it is not realistic.

The only remaining route is to change the catalog database directly while
Lightroom is closed. That is what LR-FolderCraft does — narrowly, transactionally
and reversibly. See [how-it-works.md](how-it-works.md) for exactly which rows
are touched.

## What is preserved

Because a photo's identity in the catalog is its `AgLibraryFile.id_local`, and
that value never changes, everything hanging off it survives:

| | |
| --- | --- |
| Develop settings and history | preserved |
| Virtual copies | preserved, they follow their master |
| Snapshots | preserved |
| Collections and smart collections | preserved |
| Keywords, ratings, flags, colour labels | preserved |
| Stacks | preserved |
| Previews and smart previews | preserved (keyed by image UUID, not by path) |
| Face regions, map data | preserved |
| XMP sidecar files | moved along with the photo |
| Publish service connections | preserved |

## Documents

- [installation.md](installation.md) — install on macOS, Windows and Linux
- [usage.md](usage.md) — every command, every option, worked examples
- [structures.md](structures.md) — presets and the full token reference
- [how-it-works.md](how-it-works.md) — the catalog internals
- [safety.md](safety.md) — backups, rollback, undo, recovery
- [architecture.md](architecture.md) — the code layout
- [development.md](development.md) — how to continue the work
- [versioning.md](versioning.md) — the revision scheme
- [faq.md](faq.md) — frequently asked questions
- [open-issues.md](open-issues.md) — known limits and the roadmap
- [prompts.md](prompts.md) — original and generic regeneration prompt

## The three commands you need

```bash
lrfc info  CATALOG              # what is in this catalog? (read only)
lrfc plan  CATALOG -s day       # what would change? (read only)
lrfc apply CATALOG -s day       # do it
```

Or do the same in a window:

```bash
lrfc gui                        # graphical interface (needs the gui extra)
lrfc tui                        # text interface in the terminal
```

Everything else is a refinement of those three.
