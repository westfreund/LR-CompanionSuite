# LR-FolderCraft — Overview

**Revision r13.0.2 · Build date 2026-08-23**

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
and reversibly. See [08-how-it-works.md](08-how-it-works.md) for exactly which rows
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

Numbered by weight: the lower the number, the sooner you are likely to need it.

**Using the tool**

- [02-installation.md](02-installation.md) — install on macOS, Windows and Linux
- [03-before-you-start.md](03-before-you-start.md) — **read this first**:
  reconnecting folders and converting the catalog
- [04-usage.md](04-usage.md) — every command, every option, worked examples
- [05-structures.md](05-structures.md) — presets and the full token reference
- [06-safety.md](06-safety.md) — backups, rollback, undo, recovery
- [07-faq.md](07-faq.md) — frequently asked questions

**Understanding it**

- [08-how-it-works.md](08-how-it-works.md) — the catalog internals
- [09-architecture.md](09-architecture.md) — the code layout

**Continuing the work**

- [10-development.md](10-development.md) — how to pick the project up
- [11-versioning.md](11-versioning.md) — the revision scheme
- [12-history.md](12-history.md) — why the project went the way it did
- [13-open-issues.md](13-open-issues.md) — known limits and the roadmap
- [14-prompts.md](14-prompts.md) — original and generic regeneration prompt

## The three commands you need

Two preconditions first — see [03-before-you-start.md](03-before-you-start.md): every
folder connected in Lightroom, and the catalog opened once with your current
Lightroom Classic.

```bash
lrfc info  CATALOG              # what is in this catalog? (read only)
lrfc plan  CATALOG -s day       # what would change? (read only)
lrfc apply CATALOG -s day       # do it
```

Or do the same in a window:

```bash
lrfc gui                        # graphical interface (needs the gui extra)
lrfc tui                        # text interface in the terminal
lrfc gui --lang de              # either of them in German
```

Everything else is a refinement of those three.
