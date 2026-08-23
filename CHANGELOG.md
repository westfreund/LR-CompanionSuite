# Changelog

All notable changes to LR-FolderCraft are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows the project rule that **every feature extension is a major
change** — see [docs/en/11-versioning.md](docs/en/11-versioning.md).

For **why** each change was made, and what happened between the releases, see
[docs/en/12-history.md](docs/en/12-history.md) /
[docs/de/12-historie.md](docs/de/12-historie.md).

Alle wesentlichen Änderungen an LR-FolderCraft sind hier dokumentiert. Die
Versionierung folgt der Projektregel, dass **jede Feature-Erweiterung eine
große Änderung** ist — siehe [docs/de/11-versionierung.md](docs/de/11-versionierung.md).

---

## [17.0.0] — 2026-08-23 — "Beisammen"

### Changed

- **The collection folder for files not in the catalog now sits in the target
  tree.** It used to stay behind in the source tree, so a run into a new folder
  left its results in two places and it was not clear afterwards which one held
  the outcome — the very confusion the sweep exists to remove. Reported by the
  user.

  Sorting in place is unaffected: the two roots are the same directory.

### Fixed

- **A collection folder on another drive would have failed.** Moving an orphan
  was hard-coded as a rename, which raises `EXDEV` across a device boundary —
  harmless while the folder stayed beside the source, fatal the moment it
  follows the target. Orphans now carry the scope's cross-volume flag and are
  copied and verified like any other file that crosses.

- **The free-space check ignored them.** With the collection in the target tree
  those bytes land on the target volume too, and are now counted.

---

## [16.1.0] — 2026-08-23

### Changed

- **The history now records every revision.** It had drifted to covering
  eighteen of thirty-nine, its prose stopping at r6.1.0 while the changelog
  went on: releasing touches the changelog, and nothing touched the history.
  Reconstructed from the commits, the changelog and the session record — a
  one-line entry per revision in both languages, plus the narrative for r7 to
  r16 and a table of all sixteen runs against real libraries.

- **A test now keeps it current**: the history must name every revision the
  changelog records as released, and the changelog must name every tag. That is
  the actual fix; the reconstruction alone would drift again.

---

## [16.0.1] — 2026-08-23

### Fixed

- **An interrupted reversal was diagnosed from the filesystem, and got it
  wrong.** A run whose reversal had completed hours earlier was reported as
  half done, because a later run into the same target tree had recreated the
  very paths the earlier one left behind. Files at their old places look
  identical whether a reversal was cut short or another run put them there, so
  the filesystem must not be asked.

  A reversal now records that it started, before a single file is touched, and
  an interrupted one is the record saying started-but-not-finished. A run
  marked undone is never reported again whatever the paths look like.

  It mattered because the false positive raised a *blocking* pre-flight error
  against a library that was perfectly sound. A check that refuses good work is
  worse than no check.

---

## [16.0.0] — 2026-08-23 — "Wiederaufnahme"

### Added

- **A run cut short can be finished.** `lrfc resume JOURNAL` reads the journal,
  compares it with what is on disk now, states what it found, and completes the
  job. Prompted by an interruption I caused myself while driving the window
  from a script: 27,660 files back, 23,050 still at their new paths, and
  nothing in the tool to say so.

  The direction is decided by where it stopped, not guessed:

  | Where it stopped | What happens |
  | --- | --- |
  | Before the catalog was committed | the files go back — SQLite discarded the staged transaction, so the catalog still describes the old layout |
  | After the commit | nothing moves — catalog and files already agree |
  | During a reversal | continue with `lrfc undo`, which is safe to repeat |

  The list of files to move back is **empty unless reverting is right**, so a
  caller cannot revert a committed run by reading the obvious-looking field.
  That distinction is tested, because it is the one that would do damage.

- **A new run is refused while one is unfinished** — a new pre-flight check.
  Planning on top of a half-moved library produces a plan for a library that
  does not exist. `lrfc history` marks the run and prints the command to settle
  it, the window offers to do it when the catalog is loaded, and the text
  interface has it on `Ctrl+E`.

---

## [15.0.2] — 2026-08-23

### Fixed

- **A superseded plan could become the one that Apply ran.** Changing a setting
  re-plans, and on a large catalog two plans overlap; the slower, earlier one
  landed last and replaced the newer. What Apply would then have executed was
  not what the window showed. Each request now carries a ticket and only the
  newest result is accepted.

  Found while driving a full cycle through the window: the run used a profile's
  settings rather than the rules set afterwards, and the run record proved it.

- **The first attempt at that fix introduced a worse bug**, which is worth
  recording. Passing the ticket through a lambda around the slot removed the
  QObject receiver from the connection, so Qt made it *direct* rather than
  queued and ran the handler on the worker thread — where building the folder
  table's combo boxes is illegal. Qt warns on stderr and then hands back
  widgets whose signals never fire, so the folder decisions silently stopped
  working. The ticket now travels in the signal and the bound method is
  connected, with a test that asserts results arrive on the main thread.

  The test for it had to use a real subclass: assigning a plain function to the
  instance recreates exactly the bug being tested for.

---

## [15.0.1] — 2026-08-23

### Fixed

- **`refile` repeated a label the structure had already placed.** A structure
  containing `{folder_label}` renders the text into the deepest level, and
  `refile` then appended it a second time: `2026-06-18 Voelki Voelki`. Two
  mechanisms doing the same job, with nothing to say so. `refile` now leaves
  the level alone when it already carries the folder's text, compared after the
  same ASCII folding so the check holds with that option on.

  Found by driving a full cycle through the command line with a structure that
  used both, which is a mistake a reader of the documentation could easily make.

---

## [15.0.0] — 2026-08-23 — "Gleichstand"

The text interface is a peer again. It had fallen behind by seven settings and
six whole capabilities — not through neglect, but one revision at a time, each
feature landing in the window and nowhere else.

### Added

- **`tests/test_parity.py`, written first and failing on purpose.** It reads
  the source of both front ends, collects the settings each one assigns, and
  fails when they differ. Separately it requires that any interface which
  *writes* offers the preconditions, the history and the undo. Twelve failures
  on its first run; the rest of this release is making them pass.

- **The safety net in the text interface.** The preconditions are shown before
  anything is written and must be acknowledged with a tick rather than a click,
  with a blocking finding refusing the acknowledgement in the rule and not
  merely by disabling a box. `Ctrl+Z` lists the runs recorded beside the
  catalog and reverses one. `Esc` closes a dialog by declining it.

  Until now this interface could move fifty thousand files with less protection
  than either of the others.

- **The seven missing settings**: cumulative dates, orphan collection and its
  folder name, the extension filters, the root folder to work on, and the rule
  list — typed as one comma separated line, in order, first match wins.

- **Profiles and the findings list**, so the text interface reports what the
  plan could not decide alone, each with the option that governs it, exactly as
  the window does.

---

## [14.0.1] — 2026-08-23

### Fixed

- **The romanisation added in r14.0.0 did nothing on macOS.** A catalog there
  hands back filenames **decomposed**: `Völki` arrives as `o` followed by a
  combining diaeresis, not as the single character `ö`. A per-character map
  never matches that, so the transliteration silently did not fire and the fold
  dropped the mark exactly as before — `Volki` again. Composing the text first
  fixes it.

  It passed every test because the tests were written with composed literals,
  which is what a Python source file contains. Only a real library on a real
  filesystem produced the other form.

- **The same blindness affected folder rules.** A pattern typed into the window
  arrives composed, a folder name out of the catalog arrives decomposed, and
  `Völki` therefore never matched `Völki`. Both sides are now composed before
  they are compared, so a rule naming a folder with an umlaut works.

---

## [14.0.0] — 2026-08-23 — "Umschrift"

### Added

- **The ASCII option now romanises instead of discarding.** `Völki` became
  `Volki` and `Tabaksmühle` became `Tabaksmuhle` — words that read as different
  words — and `Straße` became `Strae`, the sharp s vanishing outright, which is
  not a romanisation of anything. Letters an accent cannot carry are now
  spelled out: ä ö ü ß æ ø œ å þ ð đ ł ı and their capitals.

  Case follows the neighbouring letter, so `MÜNCHEN` gives `MUENCHEN` while
  `München` gives `Muenchen`. Where dropping the mark *is* the romanisation —
  `Café`, `Señor` — nothing changed. Slugs use the same folding, so
  `{camera_slug}` and friends agree with folder names.

  Noticed in the user's own run: three folders named after a place had come out
  as `Volki`. The existing test asserted the old output, so it had been
  encoding the defect rather than catching it.

---

## [13.0.4] — 2026-08-23

### Fixed

- **A run's record did not say which rules had shaped it.** `settings.json`
  reused the exclusion list that keeps a *profile* portable, which drops the
  rule list, the per-folder decisions and the escape hatches. Right for a
  profile, wrong for a record whose whole job is to answer "what did I actually
  do to this library" — a folder sat somewhere only a rule could explain, and
  no artefact said why.

  A run record now holds everything the run was told to do, `dry_run` aside.
  The move log additionally lists per-folder decisions, which had been recorded
  nowhere at all.

  Found by reading the record of a real run and being unable to explain the
  result from it.

---

## [13.0.3] — 2026-08-23

### Fixed

- **A deliberate refusal was reported as a crash.** `ExecutionError` was not in
  the command line's list of expected failures, so refusing to undo a run twice
  printed a traceback and called it "Unexpected error" — which is precisely
  what it is not. Seen while reversing the master-catalog run.

---

## [13.0.2] — 2026-08-23

Found by driving the text interface headlessly for the first time. It had never
been exercised beyond its own unit tests.

### Fixed

- **Three of the four shortcuts the footer advertises did nothing.** Textual
  reserves `ctrl+p` for its command palette and binds it with priority, so an
  ordinary binding of the same key never fires; `ctrl+r` and `f1` were
  swallowed the same way. Only `ctrl+l` worked. The command palette is now
  switched off — this application does not use it — and the bindings are
  declared with priority, so they also work while the cursor sits in a text
  field, which is where an operator's hands actually are.

  A footer promising four shortcuts and delivering one is worse than promising
  none, so there is now a test asserting every advertised key fires.

- **Escape did not close the confirmation dialog.** A modal that traps the
  operator until they find the right button is bad anywhere; in front of the
  one dialog that starts fifty thousand file moves it is worse than that.

---

## [13.0.1] — 2026-08-23

### Fixed

- **`leave` did not leave anything alone when sorting into a new tree.** It was
  expressed as "the same path, below the target root", which is identical to
  what `relocate` does as soon as the target root differs — so a folder the
  operator had explicitly excluded was carried into the new tree anyway. It now
  means what it says: those photos do not move, whatever the run does around
  them.

  Found by planning a real run before applying it and asking why 51,049 files
  were queued when 340 of them sat in a folder ruled `leave`.

---

## [13.0.0] — 2026-08-23 — "Laufakte"

The user runs this over several libraries on several external drives, and asked
for the rollback records to stop being a hazard. Their own third suggestion was
the right one and this follows it.

### Added

- **One folder per run, beside the catalog it changed**:
  `<catalog folder>/LR-FolderCraft/<timestamp>/` holding `run.json` (what was
  done, how much, whether it has been undone), `settings.json` (every option
  used, in the shape of a profile), `journal.jsonl` and `moves.log`.

  Journals from several libraries used to sit together in one configuration
  directory under names differing only by a timestamp. Reversing the wrong one
  puts a library into a state it was never in, and nothing on screen said which
  was which.

  The **catalog backup deliberately stays out**: a 700 MB copy beside the
  original, on the same drive, survives a mistake but not the drive. It still
  goes to the configuration directory and `run.json` records where.

  A read-only or full volume costs the records, never the run: they fall back
  to the configuration directory and the result says so.

- **`lrfc history CATALOG`** lists what has been done to that catalog, newest
  first, with the command to reverse each run that still stands. In the window
  it is **Actions → Run history…**, and *Undo* now opens that list instead of a
  file chooser, so the run being reversed is always one of this catalog's.

- **A run can only be undone once.** Doing it twice would move whatever now
  sits at those paths, so a run recorded as undone is refused; `--force`
  overrides it and almost never should.

  The journal is **kept rather than deleted**, which is where this departs from
  what was asked. After a partly failed undo the journal is the only account of
  what actually moved, and discarding it exactly when it is needed would be the
  wrong kind of tidiness. Marking the run is what stops it being offered again,
  and it does so without destroying evidence.

### Fixed

- Two runs starting in the same second shared a record folder and the second
  overwrote the first, silently. Unlikely for a large library, trivially
  reachable for a small one.

---

## [12.0.0] — 2026-08-23 — "Arbeitsweise"

For using one way of working across several libraries, which is what the user
asked for.

### Added

- **A switch for the folder decision most libraries need.** Above the rule
  list: *"Take existing day folders into the new structure, keeping their
  text"*. Every dated folder gets `refile` at once, so a library with dozens of
  named sessions needs no rule at all. It drives the *dated folder* box in the
  options rather than duplicating it, so the two can never disagree, and rules
  still win where they are set.

- **Profiles in the graphical interface**: a name field with *Load* and *Save*
  at the top of the window.

### Changed

- **A profile now carries the way of working and nothing of one library.** It
  used to store the catalog, the target folder, the rule list and the
  per-folder decisions, which made it useless for the job profiles exist for.
  Left out now: catalog, target root, root and anchor folder, folder ids, the
  rule list, and the per-folder decisions — the last being catalog row ids that
  would hit unrelated folders in the next library.

  Also left out: `ignore_lock`, `allow_unsupported_catalog` and
  `backup_catalog`. Escape hatches for one awkward run; carrying "ignore the
  lock" or "skip the backup" unnoticed into a different library months later is
  a trap, not a convenience. Loading a profile always leaves the safety net on.

- **The window no longer remembers the rule list**, at the user's request.
  Rules name folders that exist in one particular library, so carrying them
  silently into the next one puts decisions in front of the operator that were
  never made about the folders now on screen. A way of working that *should*
  travel belongs in a profile, which is saved and loaded deliberately.

---

## [11.0.0] — 2026-08-23 — "Vollstaendig"

Two requests from the user, and the documentation checked by machine rather
than by eye.

### Added

- **Cumulative date levels** (`--cumulative-dates`, and a checkbox in the
  window). `{yyyy}/{mm}/{dd}` builds `2019/2019-01/2019-01-03` instead of
  `2019/01/03`, so every folder name is complete on its own — a folder named
  `01` says nothing once it turns up in a search result or a file dialog.

  Only date levels take part: `{camera_slug}/{yyyy}/{mm}` becomes
  `{camera_slug}/{yyyy}/{yyyy}-{mm}`, because a camera is not a date. The
  authored structure is kept exactly as typed and the rewrite happens through
  `Settings.effective_structure`, so switching the option off returns what was
  written rather than an approximation of it. The live preview in the window
  shows the cumulative form as soon as the box is ticked.

  Two presets have it built in: `year/year-month/full-day` and `year/full-day`.

- **`refile`, a seventh folder action.** A dated folder carrying a session name
  is filed into the target structure with its text appended to the deepest date
  level:

      mobileRAW/2026-06-28 Makro Blume im Garten/
        -> 2026/2026-06/2026-06-28 Makro Blume im Garten/
      mobileRAW/(loose photos of 28 June)
        -> 2026/2026-06/2026-06-28/

  The two sit **side by side**, which is the point: merging them would discard
  the only thing distinguishing the session. `--mismatch-action leave` governs
  it as it does `resort`, so a shoot running past midnight stays whole.

- **`tests/test_docs.py`** checks that every folder action, every token, every
  preset and every long command-line flag appears in **both** language trees,
  that the trees hold the same numbered documents, and that every document
  carries the current revision. It found three flags documented nowhere on its
  first run: `--structure` (only ever written as `-s`), `--yes` and
  `--catalog-backup`.

---

## [10.1.0] — 2026-08-23

### Fixed

- **The mark was invisible in the graphical interface.** r10.0.0 set it as the
  window icon, and macOS shows no icon in a window title bar at all — so on the
  platform this tool is developed on, the mark that had just been chosen could
  not be seen anywhere. Reported by the user, who asked whether it was shown.

  It is now drawn **inside** the window, in a masthead above the catalog field:
  the mark, the name, and the one sentence saying what the tool does. Tinted
  from the palette's text colour and re-tinted when the system switches between
  light and dark, so a single-colour mark stays a single-colour mark.

- The icon is now set on the **application** as well as the window, which is
  what the macOS Dock and the Windows task bar actually read.

---

## [10.0.0] — 2026-08-23 — "Signet"

### Added

- **The project has a mark** (O-26 concluded). The user chose proposal 6c:
  scattered frames becoming an ordered set of folders, with the LR monogram set
  below as its own line.

  It ships as **two cuts**, both single-colour SVG taking `currentColor` so
  they adopt the surrounding text colour rather than needing a light and a dark
  copy: `logo.svg` for 32 px and above, and `logo-small.svg` for 24 px and
  below. The small cut exists because the full mark has four elements and none
  of them survive sixteen pixels — that is not a compromise, it is how every
  mark that works as a favicon is made.

  The letters are **drawn as strokes, not set as type**: a logo that depends on
  a font installed on the viewer's machine is not a logo, and stroked forms
  match the weight of the folders and the arrow besides.

- **The window carries it**, as an icon holding every size from 16 to 256 px so
  the system picks the cut drawn for the size it asks for, and in the About box
  beside the text. Both READMEs open with it, light and dark via `<picture>`.

- `scripts/make_brand.py` renders all seven sizes in both inks from the two
  sources. PNGs are never edited: change the SVG and run the script.

### Fixed

- **`logo-small.svg` rendered as an empty image** and nothing said so. A double
  hyphen inside an XML comment is illegal; the renderer reports no error and
  simply draws nothing. Caught by looking at a magnified 16 px probe rather
  than by trusting that a written file is a working file.
  `tests/test_brand.py` now parses both sources, checks they are single-colour,
  and asserts every exported PNG is the right size and not blank.

- The About box built its text and displayed it in one call, so a test could
  only reach it by driving a modal dialog. Text and display are separate now.

---

## [9.0.0] — 2026-08-23 — "Aufgeraeumt"

The last of the deferred backlog, and one new feature.

### Added

- **Files the catalog does not know can be collected** (`--collect-orphans`).
  A library worked in for years accumulates them: an export nobody imported, a
  Photoshop round trip, a stale `.xmp` whose raw file was deleted. They are
  invisible to Lightroom and they are why a reorganised tree still has odds and
  ends lying about. Each source root gets a folder — `_not-in-catalog` by
  default — and each such file is moved into it keeping the path it came from,
  so nothing collides and the origin stays visible. Nothing is deleted, the
  moves are journalled, and undo puts them back. Off by default, and reported
  in the findings list when on. Requested by the user.

  Never swept: anything the catalog references from any root, sidecars of
  catalogued photos, Lightroom's own files (`*.lrdata`, `*.lrcat-data`, the
  catalog and its side files), `.DS_Store` and AppleDouble companions, the
  collection folder itself, and a target tree the run is sorting into.

- **The preconditions are stated and must be acknowledged** (O-23). Before
  Apply starts, the window reports what it actually found — the schema version
  it read, whether every root folder resolves and with how many files, when the
  last backup was made — and requires a tick box, not a click. A finding that
  blocks cannot be acknowledged at all, and the guard is in the rule rather
  than in whether the box is clickable, because a disabled checkbox can still
  be ticked from code. Asked once per catalog per session.
  `safety.preconditions()` answers the same questions without a plan, so any
  front end can put them up front.

- **The window says what the tool is** (O-25): a purpose line above the catalog
  field, visible without opening anything, and **Actions → About** with what it
  does, the promise that only the folder rows and each file's folder column are
  ever written, the revision, the build date and the licence.

- **Six logo proposals** (O-26) in `docs/images/logos/`, single-colour SVG that
  takes the surrounding text colour, with a comparison page showing each at
  96 px, at 40 px on a light and a dark ground, and at 16 px inside a browser
  tab — the size at which most marks fail and the one a window icon is almost
  always seen at. Awaiting a choice.

### Fixed

- **A rule pattern found `_extern` only at the top of a tree** — see r8.0.0;
  the sweep's first nested test found it again from the other side.

- **The sweep would have collected the sidecars of already-sorted photos.** A
  photo that is already in the right place makes no move, so recognising
  sidecars from the moves would have left them unaccounted for on a second run.
  They are now recognised from the catalogued photo they sit beside.

- **The sweep called itself off when sorting in place.** The target root is
  then the source root, and protecting the target tree from being swept ended
  the walk before it began.

---

## [8.0.1] — 2026-08-23

### Fixed

- **The menu entries were invisible on macOS.** Qt documents that adding an
  action directly to a `QMenuBar` is not supported there, because the bar is
  the system-wide one — and that is exactly what both entries did. The language
  switch nobody had found and the undo shipped in r8.0.0 were therefore
  unreachable on the platform the tool is developed on. Reported by the user,
  who looked for the undo after a real 51,049-file run and could not find it.

  Both now live in an **Actions** menu, and undo is additionally a button
  beside *Apply*: a rollback reachable only through a menu is one nobody finds
  when they need it. Both are disabled while a run is in progress. A test
  asserts that every top-level entry on the bar opens a menu.

- The documentation said the language could be switched "from the menu bar",
  which was advice that could not be followed. It now names the Actions menu.

---

## [8.0.0] — 2026-08-23 — "Rueckfahrkarte"

### Added

- **`relocate`, a sixth folder action**: carry a folder to the new location
  unchanged — same name, same contents, same sub-structure, no sorting applied.
  For material that should come along without being touched: a curated
  `_fineart` folder, an `_extern` drop box, a job folder with an order of its
  own. It keeps the folder's path relative to the source root, renders no
  structure, and ignores the run's anchor, because burying the folder one level
  deeper is not what "move this there" means. Sorting in place leaves such a
  folder where it is, reported as already in place. Requested by the user.

- **Undo is now in the graphical interface.** `lrfc undo` had existed since
  r1.0.0 and was reachable only from the command line — a rollback the operator
  cannot reach from the window they actually use is one they will not have when
  they need it. **Undo a run…** in the menu bar asks for the run's journal (the
  one just made is offered first), states plainly what will happen, and then
  puts every moved file back, removes the folders the run created if empty, and
  restores the catalog from that run's backup. Requested by the user.

### Fixed

- **A rule pattern only matched folders directly below the root.** `_extern`
  found `_extern` but not `raw2019/_extern`, which is not how anyone reads that
  rule. A pattern is now tested against the folder's path, its name and every
  partial path ending at it, and still covers the whole subtree below — so one
  rule reaches `_extern`, `raw2019/_extern` and `raw2019/_extern/2020/Fest`
  alike. Writing a slash still pins it to a path: `_in_Arbeit/2021` does not
  match some other `2021`.

  Found by writing the first `relocate` test against a nested folder; the
  master catalog happens to keep `_extern` at the top, so no run had exposed it.

---

## [7.1.0] — 2026-08-23

### Fixed

- **The log section had no size of its own.** `_balance_splitter` set three
  sizes for what became four sections when the findings table was added in
  r6.0.0; Qt calls a short list undefined. There is now one share per section
  and an assertion that says so, so adding a fifth cannot repeat it.

- **The dividers between the sections were nearly invisible.** Qt draws a
  splitter handle as a few faint dots, so a section that would not show
  everything looked broken rather than merely small — the user found the
  sections "hard to find". The handles are now wider with a rule through them,
  highlight under the pointer, carry a resize cursor and a tooltip saying what
  dragging does.

### Changed

- **Both usage documents explain the dividers**, with a diagram of where they
  sit, what dragging one fully shut does, and the fact that the settings
  section scrolls within itself — plus the sentence that matters when something
  looks wrong: the section is too small, not empty. The FAQ gained the two
  questions in the words someone would actually search for. Requested by the
  user.

- The window-layout tables in both languages now list the findings section and
  the rule list, which had been added without being described.

---

## [7.0.0] — 2026-08-23 — "Gedaechtnis"

### Added

- **The window remembers what you set.** Language, catalog, target folder and
  its mode, structure, extension filters, folder actions, the rule list, window
  size and splitter positions, in `gui-state.json` in the configuration
  directory. The language is written the moment it is toggled; the rest on
  close. A missing, unreadable or outdated file simply means the defaults, and
  a remembered value a later revision no longer offers leaves the default
  standing rather than emptying the control.

  Two things are deliberately never restored. **Per-folder decisions** are
  catalog folder ids, so restoring them against a different catalog would apply
  an answer given about one folder to whatever unrelated folder shares that
  number. **The backup switch** always starts on: turning the safety net off
  should be decided for the run at hand.

- `--lang` is now genuinely optional for `lrfc gui`: given, it wins for the
  session; omitted, the remembered language is used.

### Fixed

- **The target folder could not be named.** The field and its Browse button were
  disabled until the "into a new folder" radio button above them was selected,
  which reads as "this cannot be done" rather than "select that first" and left
  no hint which control to press. Both are now always usable, and naming a
  folder — by typing or by choosing one — selects that mode, because typing a
  target path while sorting in place cannot mean anything else. Reported by the
  user, who could not find a way to give a base folder.

---

## [6.1.0] — 2026-08-23

### Changed

- **The documents are numbered by weight**, at the user's request: the lower the
  number, the sooner a reader is likely to need it. Both languages carry the
  same numbers, so `04-usage.md` and `04-bedienung.md` are the same document.
  Renamed with `git mv`, so each file's history follows it. All 174 internal
  links were rewritten and verified.

- **The history document now states its own provenance.** It was written
  retroactively, and says so in a table separating what is machine-recorded
  (dates, order, revision contents, test output) from what is a narrative
  written afterwards (reasoning, alternatives, lessons) — with the `git`
  commands to trace an individual change exactly.

### Fixed

- Two upper-case German headings still using ASCII substitutes for umlauts,
  missed by the r6.0.0 pass because it matched lower case.

- Photos with no usable capture date were filed into the unsorted folder without
  a word about it. Routing a dateless photo somewhere is a decision the tool
  made for the operator, so it now appears in the findings list with the option
  that governs it, like every other one. Two such photos exist in the master
  catalog.

---

## [6.0.0] — 2026-08-23 — "Klartext"

Saying what the plan could not decide on its own.

### Added

- **A findings report** (`exceptions_report.py`). A plan is not just a count of
  files to move; it also holds the cases the tool decided for you. Reporting
  them as a single "skipped: 43" is the same as not reporting them. Each cause
  now gets its own entry naming the number of files, examples, and — the point —
  **the option that governs it**, so the answer is one setting away rather than
  a search through the documentation.

  Levels: BLOCKS (a file the catalog names but the disk does not have, a failed
  pre-flight check), Warning, Exception (no usable date, a name collision, the
  extension filter, a stray date inside a dated folder), Note (renames, folders
  no rule spoke about).

- **The graphical interface shows them in a table** between the settings and
  the folder table: level colour-coded, the governing option and its current
  value in their own columns, and the affected files listed when a row is
  selected. The counts line above it is now only counts — warnings used to be
  crammed onto it. The command line plan report gained the same list.

- **A project history** in both languages,
  [docs/en/12-history.md](docs/en/12-history.md) /
  [docs/de/12-historie.md](docs/de/12-historie.md), reconstructed retroactively. The
  changelog says what changed; this says why, and what happened in between —
  the decisions and their reasoning, the tests against real libraries, and the
  four occasions on which the tool was wrong in a way that mattered. None of it
  is recoverable from the code.

- **`scripts/make_screenshots.py`.** The images in the READMEs had gone stale
  within one revision because there was no way to remake them. The script
  builds a demonstration catalog, drives both interfaces against it and writes
  all four files.

### Fixed

- **Global command line flags were ignored before the subcommand.** Every
  sub-parser redeclares `--lang`, `--debug`, `--verbose`, `--quiet`,
  `--log-file` and `--log-dir`, and a sub-parser's default overwrites what the
  top level already parsed. `lrfc --lang de plan X` therefore ran in English and
  `lrfc --debug plan X` ran without debug logging — since r1.0.0. Found by
  reading the German output of the new findings report and noticing it was
  English. There is now a test per flag and position.

- **German messages used ASCII substitutes for umlauts** — "ueber Mitternacht",
  "zusammenfuehren", "Uebersprungen" — while the graphical interface's own text
  used real ones, so the two disagreed on screen. All of it now uses proper
  umlauts.

---

## [5.0.0] — 2026-08-23 — "Regelwerk"

Expressing what a grown library actually needs. Prompted by a master catalog
whose 39 folders held four distinct intentions and could not be described with
the vocabulary the tool had.

### Added

- **`resort`, a fifth folder action.** Rebuilds a folder *where it stands*,
  below its own parent: `raw2026/2026-06-28 Makro Blume im Garten` becomes
  `raw2026/2026-06-28/Makro Blume im Garten`. Neither `consolidate` (which
  drags the photos out of `raw2026`) nor `sort-inside` (which nests the
  structure below the folder itself) could express this.

- **The `{folder_label}` token** — the descriptive text after a folder name's
  date prefix, empty when there is none. Together with `resort` this is what
  splits a dated folder into a date level and a description level instead of
  losing the description.

- **Levels that render empty now collapse** instead of becoming a folder called
  `unnamed`, which is what makes `{folder_label}` usable as a level of its own:
  `{yyyy}-{mm}-{dd}/{folder_label}` gives a plain day folder for a photo whose
  folder carries no text.

- **An ordered rule list**, `PATTERN=ACTION`, first match wins, via `--rule`
  and the `folder_rules` setting. Patterns are path globs — covering everything
  below the folder they name — or the keywords `dated`, `dated+label`,
  `dated-only`, `plain` and `*`. Precedence: per-folder override, then rule,
  then the interactive question, then the kind default. A rule silences the
  question it already answers, and each folder records which rule decided it.

  The master catalog's 39 folders are now five lines rather than 39 dropdowns.

- **A rule table in the graphical interface**, above the folder table, with
  add, remove and reorder. The folder table gains a "Decided by" column naming
  the rule that settled each row, or marking the decision as the user's own.
  Changing a rule clears the manual decisions it might have made and replans.

- **A move log beside the library** (O-24). A plain text record named after the
  tool, the date and the catalog, written next to the `.lrcat` file: every
  source and target path, the rules used, the backup and journal locations, and
  a summary. The JSON-Lines journal remains what it was — a machine-readable
  record for undo; this is the one a person reads months later. Written in the
  run's `finally`, so a failed run is recorded too, and strictly non-fatal: an
  unwritable directory leaves a note on the result and nothing else.
  `--no-move-log` and `--move-log-dir` control it.

- **A preparation page** in both languages (O-21, O-22):
  [before-you-start.md](docs/en/03-before-you-start.md) /
  [vorbereitung.md](docs/de/03-vorbereitung.md) — reconnecting a library whose
  drive was renamed or restored, and converting the catalog to the installed
  Lightroom Classic first. Linked from both indexes.

### Fixed

- **`resort` tore sessions in two.** A shoot that runs past midnight leaves
  photos whose own date disagrees with the folder naming the session. Rebuilding
  such a folder filed each photo by its own date, which is precisely what
  `--mismatch-action leave` says must not happen. That setting now governs
  `resort` as well, so a stray photo follows its folder's date and the session
  stays whole.

  Found by simulating the new rules against the real master catalog before
  writing a line of it to disk: 1 of 23 sessions split, the twelve frames of
  `2026-06-27 Test 150mm Spiegelobjektiv` that were shot the evening before.
  The fault is invisible in the counts and does not occur in any synthetic
  catalog.

---

## [4.0.2] — 2026-08-23

### Fixed

- **A repeated `new-tree` run was not a no-op.** Whether a photo already sits
  where it belongs was decided by comparing paths *and* requiring in-place
  placement. Running the same `new-tree` migration twice therefore planned
  every file as a move onto itself, which then tripped the "never overwrite an
  existing file" guard and rolled the whole run back. The check is now purely
  about the paths, as it should always have been.

  Found by verifying a real run: after 9,452 files had been sorted into a new
  tree, planning the identical run again still offered to move all of them.

### Added

- **A guard that only four tables may ever be written.** The promise that
  develop settings, virtual copies, collections and keywords survive rests on
  the tool touching nothing but `AgLibraryFolder`, `AgLibraryFile`,
  `AgLibraryRootFolder` and `Adobe_variablesTable`. A test now hashes every
  table before and after a run and fails if anything else differs.

  Motivated by that same verification: six further tables had changed in the
  live catalog, and the only way to answer "was that us?" was to grep the
  source for SQL statements. It was not — the user had edited a photo in
  Lightroom to check that access worked. But that should be a property the
  suite enforces, not an argument made after the fact.

### Verified against

- The reference library reorganised through the graphical interface with
  `{camera_slug}/{yyyy}/{mm}/{dd}` and `new-tree` placement: 9,452 files into a
  second root folder in ten seconds, every file present at an unchanged size,
  `integrity_check` ok, `foreign_key_check` clean, 210 folder rows with no
  orphans and no bad prefixes, all 9,452 catalog paths resolving, the id
  counter still REAL, and the write-ahead log checkpointed away.

- **And then actually used.** Editing a photo in Lightroom afterwards shows the
  whole chain intact: the file is found at its new path, its develop history
  from 2022 is still there, a new step ("convert to black and white") is added
  on top, and the result is written back. A migrated library is not merely
  readable, it is fully workable.

## [4.0.1] — 2026-08-23

### Fixed

- **A catalog that has lost track of its photos is now named as such.** When
  the drive is mounted under a different name than the catalog records — which
  happens whenever a volume is renamed or a library is restored elsewhere — the
  pre-flight reported "No write permission for /Volumes", because the search
  for an existing parent directory had walked all the way up. That sends the
  operator looking for a permission problem that is not there.

  With in-place placement the target *is* the catalog's own root folder, so a
  missing one now says exactly that, names the path, and points at Lightroom's
  Find Missing Folder.

- **Every file missing is an error, not a warning.** A few strays in a large
  library are normal and must not block a run. All of them missing means the
  catalog is disconnected from its photos, and sorting it would be meaningless.
  The warning also states the total now ("3 of 9,452"), so the scale is visible
  at a glance.

  Found while preparing a test: a restored 2019 library recorded its root as
  `/Volumes/LR_Archiv/...` while the drive was mounted as `/Volumes/1TB-2`.

## [4.0.0] — 2026-08-23 — "Prüfstand"

The installer now verifies what it installed, repairs what is missing, updates
what has aged, and only advertises interfaces that actually work.

### Added

- **Verification.** Each optional interface is one importable module and one
  pip requirement, and the installer imports it after installing. Nothing is
  reported as ready that cannot be imported.

- **`--check` / `-Check`** verifies an existing installation and reinstalls
  whatever is missing, without touching what works. It also reports when a
  newer version of a component is available.

- **The installation remembers its components.** A `components` file in the
  install prefix records which interfaces were asked for, so a repair can tell
  "never asked for" from "installed and broken" — the two are indistinguishable
  by import alone.

- **Updating.** Re-running the installer upgrades anything already present that
  has gone out of date, instead of leaving an old version in place.

- **The environment is reused** rather than deleted and rebuilt, which makes
  adding the graphical interface later a matter of seconds. `--recreate` /
  `-Recreate` forces a clean build.

- **It asks about the graphical interface** when run in a terminal and nobody
  said either way. `--with-gui` / `--no-gui` (and `-WithGui` / `-NoGui`) skip
  the question for scripted installs; a non-interactive run never prompts.

### Fixed

- **The installer advertised `lrfc gui` even when it had not installed it.**
  Reported from use: a run without `--with-gui` finished with `lrfc gui` in its
  list of next steps, and the command then said PySide6 was missing. The final
  report now lists only the interfaces that were installed and verified, and
  prints the exact command to add anything that is not there.

- A component that fails to install is named explicitly, with the reason and
  the command to try by hand, rather than being passed over in a run that
  reports success.

## [3.0.2] — 2026-08-23

### Fixed

- **The window did not fit a small screen.** It opened at a fixed 1024x860,
  which is taller than the usable area of a 13-inch laptop once the menu bar
  and the dock are taken off, leaving the Plan and Apply buttons below the
  bottom edge with no way to reach them.

  The settings now live in a scroll area, and the action row with the progress
  bar sits outside it so it can never be the thing that scrolls away. The
  window opens at the smaller of a comfortable size and the space the screen
  actually offers, and its minimum is 720x420. Settings, folder table and log
  share one splitter, so the space can be given to whichever part is in use.

  Five regression tests: the window never opens larger than the screen, the
  minimum fits a small laptop, the action row stays inside the window at five
  heights down to 420, the settings scroll when they do not fit, and shrinking
  below the minimum is refused.

## [3.0.1] — 2026-08-23

### Fixed

- **The installer left an un-runnable command.** It wrote the launcher into
  `~/.local/bin` and then only *printed* a note that the directory is not on
  the PATH — which macOS never puts there by itself. Reported from a real
  installation: the script finished, said it had verified itself, and the
  terminal answered `lrfc: command not found`.

  The installer now appends the PATH line to the startup file the user's shell
  actually reads (`~/.zshrc`, `~/.bash_profile`/`~/.bashrc`,
  `~/.config/fish/config.fish`, else `~/.profile`), skips it when the directory
  is already listed, and takes exactly that line back out on `--uninstall`,
  leaving the rest of the file untouched. `--no-path` keeps the old
  print-only behaviour.

  On Windows the entry was already added; the uninstaller now removes it again,
  and the message says plainly that an open terminal keeps its old PATH.

- The installation guides and both FAQs explain the "command not found" case,
  including how to tell a PATH problem from a broken installation.

## [3.0.0] — 2026-08-22 — "Weitwinkel"

Two large additions: a graphical interface, and runs that span several root
folders.

### Added

- **A Qt graphical interface**, `lrfc gui`, as the optional `gui` extra.
  One window holds the catalog with a file chooser and a summary, the source
  root folder and extension filters, the target (in place, or a new folder
  picked with the system dialog — its *New Folder* button creates one, and a
  path that does not exist yet is created during the run), the structure with a
  live preview and a placeholder reference, every option, the folders that were
  found with a dropdown each for their decision, a progress bar with a counter,
  and a log. English and German, switchable at any time.

  Catalog reading, planning and execution run on worker threads, so the window
  stays responsive; closing it waits for the work rather than killing it.

- **A run can span several root folders.** Each becomes a `RootScope` with its
  own anchor, and all of them are handled in one transaction and one journal.
  With `new-tree` placement they share a single scope and everything is
  consolidated into the new tree. Verified across two physical volumes.
  Closes O-7.

- Pre-flight now checks every scope: each target must be writable or creatable,
  and free space is summed **per target volume**, so two scopes copying onto
  the same drive cannot both pass while together they do not fit.

- The plan lists every root folder with its anchor when there is more than one,
  in the text report and under `scopes` in the JSON export.

- Installers grew `--with-gui` (macOS/Linux) and `-WithGui` (Windows), and CI
  gained a headless Qt job.

### Fixed

- **The graphical interface used the first entry of each dropdown as its
  default** instead of the documented one, so `subfolder_action` silently
  started at `sort-inside` rather than `consolidate`. Every option default is
  now read from a fresh `Settings()`, and a test compares the two.

- **Closing the window while a worker was running aborted the process.**
  Destroying a running `QThread` does that. Threads are now awaited on close
  and dropped from the list when they finish.

### Changed

- `Plan.root_folder`, `.anchor_segments` and `.target_root_path` are now
  convenience properties for the first scope; `Plan.scopes` is the real model
  and `PlannedMove.scope` says which one a move belongs to.

## [2.0.1] — 2026-08-22

### Fixed

- **A target root that does not exist yet is now created.** Naming a new
  location is the whole point of `--placement new-tree`, but the run aborted
  with `FileNotFoundError` because only the folders *below* the root were
  created. Every missing level is now made, and journalled individually, so a
  rollback or `lrfc undo` takes the whole tree back down again.

- The `target-writable` pre-flight check said "target location is writable" for
  a path that did not exist, because it walked up to the nearest existing
  parent. It now says plainly that the target will be created, and where.

## [2.0.0] — 2026-08-22 — "Wegweiser"

A grown library is not one flat folder. It has topic folders and folders that
already carry a date, and what should happen to them is a judgement call. This
release makes the tool **recognise** those folders and lets the operator decide
— per folder if they want to.

### Added

- **Folder classification.** Every source folder is examined. A name that
  *begins* with a date is a dated folder: `2019-04-15 Ostern in Tirol`,
  `2019_06_01 Hochzeit`, `20190415_Hochzeit`, `2019.03.10`, `2019-04`, `2019`.
  Anything else is a topic folder. A date in the middle of a name is ignored —
  guessing there would invent intent.

- **A dated folder only counts when it is fine enough.** A folder called `2019`
  is no answer to a request for day folders, so it is treated as a topic folder
  and its photos are sorted properly. A day folder does satisfy a request for
  year folders. With a structure that has no date tokens at all, folder dates
  are irrelevant and ignored.

- **Three decisions, each with a default, a global switch and a per-folder
  override:**

  | setting | flag | choices | default |
  | --- | --- | --- | --- |
  | `subfolder_action` | `--subfolder-action` | `consolidate`, `sort-inside`, `leave` | `consolidate` |
  | `dated_folder_action` | `--dated-folder-action` | `keep`, `consolidate`, `sort-inside`, `leave` | `keep` |
  | `mismatch_action` | `--mismatch-action` | `move-out`, `leave` | `move-out` |

  `--folder-action ID=ACTION` decides one catalog folder explicitly and beats
  the defaults. Decisions live in `Settings.folder_actions`, so a profile can
  carry them.

- **Asking the operator.** `lrfc plan|apply --interactive` puts every folder
  that could reasonably go either way to the operator, showing what was found,
  how many photos are affected, how many carry a different date, and which
  option is the default. Enter accepts the default. The planner itself never
  prompts: front ends pass a `decide` callback, so the core stays free of any
  user interface. In the TUI the same choice is made by pressing Enter on a row
  of the folder table, which cycles the decision and re-plans.

- **The plan shows its findings**: which folders exist, what kind each is, how
  many photos, what was decided and whether that came from a default, an
  explicit override or the operator. Also in the JSON export, under `folders`.

### Changed

- **A dated folder's photos now stay put by default.** Previously
  `2019-04-15 Ostern in Tirol` was dissolved into a bare `2019-04-15`, losing
  the description. Photos inside it whose capture date does *not* match still
  move out to their own date folder — a photo filed in the wrong place gets
  corrected. Set `--dated-folder-action consolidate` for the old behaviour, or
  `--mismatch-action leave` to make a dated folder entirely off limits.

- The anchor folder is never offered as a decision and always sorts its own
  photos: "leave subfolders alone" must not silently mean "do nothing at all".

[2.0.0]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v2.0.0

## [1.0.6] — 2026-08-22

### Added

- **Pre-flight now detects a catalog damaged by 1.0.0–1.0.4.** If
  `Adobe_entityIDCounter` has storage class `text` instead of a number, the
  check reports it, names the revisions responsible, and prints the one
  statement that repairs it. Such a catalog cannot be opened by Lightroom at
  all, so reusing it silently would only deepen the confusion.

### Confirmed

The r1.0.5 diagnosis is verified against the reference library: a copy of the
rejected catalog with `Adobe_entityIDCounter` cast back to REAL — and nothing
else changed — opens in Lightroom Classic, with all 9,452 photos selectable in
their new day folders. One value of the wrong SQLite storage class was the
entire fault; the folder reorganisation itself had been correct from the start.

[1.0.6]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.6

## [1.0.5] — 2026-08-22

**Root cause of the failure reported in 1.0.4.** Lightroom Classic could not
open the reorganised catalog because the id counter had changed SQLite storage
class.

### Fixed

- **`Adobe_entityIDCounter` was written back as TEXT instead of REAL.**
  `allocate_ids()` stored the new value with `repr(float)`, producing the string
  `'4914941.0'` where Lightroom keeps the number `4914941.0`.
  `Adobe_variablesTable.value` is declared without a type, so it has BLOB
  affinity and stores exactly what it is handed — the value *reads* the same and
  nothing flags it:

  * `PRAGMA integrity_check` and `foreign_key_check` pass;
  * the schema is unchanged;
  * comparing row values finds no difference, because both sides print
    `4914941.0`;
  * **Lightroom's own catalog repair copies the value through unchanged**, so it
    produced a byte-identical file and failed again — repairing in a loop that
    could never converge.

  The counter is now written back in whatever storage class it already had, and
  `allocate_ids()` re-reads `typeof()` afterwards and aborts the run if it
  changed. Recovering an affected catalog needs one statement:

  ```sql
  UPDATE Adobe_variablesTable
     SET value = CAST(value AS REAL)
   WHERE name = 'Adobe_entityIDCounter';
  ```

### Added

- Three regression tests: the counter keeps REAL, a catalog that genuinely uses
  TEXT is not converted either, and a broad guard that compares the SQLite
  storage class of every column of every row that exists before *and* after a
  run. Type drift is invisible to both value comparison and `integrity_check`,
  so it needs a check of its own.

### How it was found

Two controlled tests separated content from environment: the migrated catalog
on an internal APFS disk still failed to open, while the untouched original on
the same exFAT volume opened fine. That ruled out the filesystem and pointed at
the data — after which comparing `typeof()` against the *original* (rather than
against Lightroom's repair, where both sides were already TEXT) showed the one
differing value.

[1.0.5]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.5

## [1.0.4] — 2026-08-22

Lightroom Classic refused to open the reorganised reference catalog with an
"unexpected error" and quarantined it. Its own repair then produced a catalog
whose **135 tables are byte-for-byte identical in content** to what this tool
had written — every folder row, every file-to-folder mapping, every variable.
The reorganisation was correct; what Lightroom objected to was the state of the
*file*, and the investigation exposed three genuine defects.

### Fixed

- **The catalog is left self-contained after a run.** Lightroom catalogs run in
  WAL mode. A plain commit leaves new data in `<catalog>.lrcat-wal` until
  something checkpoints it, so the `.lrcat` file alone did not describe the
  finished state. `commit()` now runs `PRAGMA wal_checkpoint(TRUNCATE)` and logs
  the outcome, including when the checkpoint reports busy.

- **Verification no longer looks through a blind view.** On filesystems without
  POSIX locking — exFAT, i.e. the drive this library lives on — reads fall back
  to `immutable=1`, and *that mode ignores the write-ahead log entirely*. The
  post-run verification therefore validated the main database file rather than
  what Lightroom would see, and reported "passed" regardless. Connections now
  record whether they ignore the WAL, and verification fails with an explicit
  problem if it had to read past a non-empty one.

- **The pre-flight check no longer gives dangerous advice.** It called
  `.lrcat-wal` and `.lrcat-shm` "stale side files" and suggested clearing them.
  For a WAL-mode catalog they are ordinary working files, and deleting a
  non-empty write-ahead log throws away committed transactions. The check now
  reports how much the catalog depends on its WAL and says never to delete it,
  and warns separately about a `-journal`, which really does indicate an
  interrupted transaction.

- **The test suite no longer writes into the user's directories.** Tests that
  exercised `apply` deposited catalog backups, journals and reports in the
  caller's real LR-FolderCraft configuration directory. An autouse fixture now
  redirects all four location variables into the pytest temp tree.

### Still unexplained

The precise trigger for Lightroom's error could not be determined from outside
the application: the file passed `integrity_check` and `foreign_key_check`, its
schema was identical to the original, and its contents matched Lightroom's own
repair exactly. The defects above are real and were worth fixing on their own
merits, but none of them is *proven* to be the cause.

[1.0.4]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.4

## [1.0.3] — 2026-08-22

### Fixed

- **macOS already moves AppleDouble companions; 1.0.1 moved them a second
  time.** The premise of the previous release was wrong. Measured on an exFAT
  volume: writing an extended attribute to `X.dat` creates `._X.dat`, and after
  `os.replace("X.dat", "sub/X.dat")` the companion has moved to `sub/` on its
  own, with the attributes still readable on the moved file. The kernel's
  AppleDouble emulation handles it transparently.

  The explicit move therefore collided with the file macOS had already placed
  at the target, and aborted the first live run against the reference library
  at file 850 of 9,452. The rollback did its job: 850 files were restored, 152
  directories removed, the catalog transaction discarded, and the library came
  back byte-identical — catalog SHA-256 unchanged, all 9,489 files present with
  identical sizes.

  Companion handling is now platform-aware. On macOS the kernel is left to it.
  On other platforms `._X` is an ordinary file that a rename leaves behind, so
  it is still carried along explicitly to preserve the metadata of a drive that
  will go back to a Mac. Both branches are covered by tests.

[1.0.3]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.3

## [1.0.2] — 2026-08-22

### Fixed

- **The read-only fallback for lock-less filesystems never actually ran.**
  `sqlite3.connect()` is lazy: it opens nothing, so a volume that cannot
  provide SQLite's shared lock — exFAT and FAT, i.e. most external photo
  drives — raises on the first *statement*, not on connecting. The `try` only
  wrapped the connect call, so the `immutable=1` fallback was dead code and the
  failure surfaced as an unhandled `unable to open database file` deep inside
  the caller.

  The fallback is now driven by a probe query. Two regression tests cover it: a
  connection that connects and then refuses every statement must fall back, and
  a genuinely unreadable file must still raise rather than be masked.

  This hid itself for a long time: a stray `.lrcat-shm` file left behind by an
  earlier read-write connection happened to make `mode=ro` succeed. Removing
  that file exposed the defect.

[1.0.2]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.2

## [1.0.1] — 2026-08-22

### Fixed

- **macOS AppleDouble companions are moved with their photo.** On filesystems
  that cannot store extended attributes and resource forks natively — exFAT and
  FAT, which is what most external photo drives use — macOS keeps them in a
  `._<filename>` companion. A plain rename does not carry it, so the companion
  was orphaned in the source folder and the moved file lost its attributes.
  Found on the reference library, where 37 of 9,452 files had one.

  Companions move unconditionally, including with `--no-sidecars`: `._X` is the
  other half of `X`, not an independent document like an XMP sidecar. A renamed
  photo takes its companion under the new name.

[1.0.1]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.1

## [1.0.0] — 2026-08-22 — “Daybreak”

First release. Reorganises a Lightroom Classic folder tree by moving the files
and rewriting the catalog in one reversible operation.

### Added

**Core**
- Direct, narrowly scoped access to the `.lrcat` SQLite database. Only
  `AgLibraryFolder` rows and `AgLibraryFile.folder` (plus the name columns on a
  forced rename) are ever changed. Row ids come from Lightroom's own
  `Adobe_entityIDCounter`.
- Token based folder templates with 25 placeholders across date, camera and
  file categories, and 12 presets. Unlimited grouping levels.
- Bilingual month and weekday names (EN/DE) without a system locale.
- Portable name sanitising for Windows, macOS and Linux, including reserved
  device names, trailing dots and an optional ASCII fold.
- Two placement modes: `in-place` (structure below the current folder) and
  `new-tree` (a fresh tree registered as an additional root folder).
- Selection by root folder, catalog folder and file extension.
- Configurable capture-date resolution (`capture`, `exif-fields`,
  `file-mtime`), collision handling (`rename`, `skip`, `abort`) and
  missing-date handling (`unsorted`, `skip`, `abort`).
- XMP sidecar detection for both naming conventions, moved with their photo and
  renamed alongside it.
- Reusable JSON profiles.

**Safety**
- Eight pre-flight checks before anything is written.
- SHA-256 verified catalog backup.
- Staged catalog transaction committed only after every file has moved.
- Append-only, fsynced JSON-Lines journal.
- Automatic rollback of both the catalog and the filesystem on any failure.
- `lrfc undo` to reverse a completed run.
- Post-run verification of every catalog path against the filesystem.
- Existing files are never overwritten.
- Cross-volume transfers are copy-verify-delete, with a free-space check.

**Interfaces**
- CLI: `info`, `folders`, `plan`, `apply`, `undo`, `profiles`, `tokens`,
  `presets`, `tui`. Plans export as JSON and CSV.
- Textual TUI with a live folder-name preview, target folder table, progress
  bar, log pane, confirmation dialog and EN/DE switching.
- Debug mode and a per-run log file carrying a numbered `STEP` audit trail.

**Project**
- 270 tests, 87 % coverage, built on a synthetic catalog fixture so no
  Lightroom installation is needed.
- GitLab CI: lint, tests on Python 3.9–3.13, a dedicated safety job, build.
- Installers for macOS, Linux and Windows.
- Complete documentation in English and German.
- Dual licensed MIT OR GPL-3.0-or-later.

### Fixed during development

Defects the test suite and the end-to-end runs exposed before release, recorded
because the same traps await anyone working on this kind of tool:

- Sidecars were discovered twice on case-insensitive filesystems, because
  `name.xmp` and `name.XMP` resolve to the same file. Replaced per-name probing
  with a cached, case-insensitive directory index.
- Re-running on an already sorted library nested the structure inside itself.
  The anchor now drops any trailing segments that match a *prefix* of what the
  structure renders — a partial overlap, not just a full one, since a common
  parent folder may cover only the first levels of a multi-level structure.
- Re-parenting a file and renaming it as two statements briefly violated the
  UNIQUE index on `(lc_idx_filename, folder)`. Folder and name now change in one
  statement, with a deferral loop and a temporary-name pass for rename cycles.
- `mkdir(parents=True)` created several directory levels but journalled only the
  leaf, so `undo` left empty intermediates behind. Every created level is now
  journalled.
- `file-mtime` was a default date source. It is usually the copy date, not the
  capture date, and silently misfiled photos. It is now opt-in.

### Verified against

- Lightroom Classic catalog schema **18.0.0** (Lightroom Classic 14), a real
  9,452-file / 337 GiB library on exFAT.
- End-to-end apply / re-plan / undo cycles on reduced working copies (40 and 30
  files, single- and four-level structures): catalog integrity `ok`, foreign key
  check clean, folder tree valid, all paths resolving, virtual copy still
  attached to its master, and a hash over `Adobe_images`,
  `Adobe_imageDevelopSettings`, `AgLibraryKeywordImage` and
  `AgLibraryCollectionImage` **unchanged** before and after. Re-planning after a
  run reports every file as already in place, and `undo` restores the catalog,
  the files and the directory tree exactly.
- The macOS installer, executed for real: install, run from a clean environment
  with no `PYTHONPATH`, read a live catalog, uninstall.
- **A full production migration** (2026-08-22): the reference library's 9,452
  files / 337 GiB reorganised into 152 day folders, then independently checked —
  every file present at an unchanged size, `integrity_check` ok,
  `foreign_key_check` clean, no orphan folders, all catalog paths resolving, all
  32 virtual copies still attached, and the develop/keyword/collection hash
  identical to a pre-run copy. Re-planning afterwards reports nothing to do.

### Known limits

See [docs/en/13-open-issues.md](docs/en/13-open-issues.md).

[1.0.0]: https://gitlab.com/andy-freund/LR-FolderCraft/-/tags/v1.0.0
