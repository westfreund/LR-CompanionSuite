# Posts, English

Every draft below discloses authorship in the first lines. Keep that.
Site: <https://andy-freund.gitlab.io/LR-FolderCraft> ·
Source: <https://gitlab.com/andy-freund/LR-FolderCraft>

---

## 1. Lightroom Queen Forums — the highest-value single post

*Why here:* it is the place people go with catalog questions, and the answers
stay findable for years. Post in whichever section allows tool announcements,
and read the forum rules first. Do not post and vanish — answer the questions
that follow.

**Subject:** A free tool to reorganise Lightroom Classic folders without breaking the catalog

> I hope this is the right place for it — please move it if not.
>
> I wrote a tool for a problem I had myself, and since a few people here seem
> to run into the same thing, I thought I would offer it. It is free, open
> source, and I have nothing to sell.
>
> **The problem.** My master catalog had grown into a handful of huge year
> folders — 51,049 photos over 2.36 TB. I wanted year / month / day. Every
> obvious route was blocked: moving folders in Finder breaks the catalog,
> dragging them inside Lightroom's Folders panel works but takes days at that
> size and cannot be interrupted safely, and re-importing loses develop
> settings, collections and keywords.
>
> **What it does.** LR-FolderCraft reads the catalog, works out where each
> photo should live under the structure you pick, then moves the files *and*
> rewrites the catalog's folder records to match. Lightroom opens afterwards
> with everything where it expects it. It took minutes rather than days.
>
> **Why I would trust it, and why you might not have to take my word for it.**
> This writes into the catalog database, so I understand the hesitation — I
> had it about my own code.
>
> - The dry run is the default: `plan` writes nothing at all, anywhere, and
>   you read the whole plan first.
> - The catalog is backed up and the backup verified before anything is
>   touched, and Lightroom has to be closed or the tool refuses to start.
> - Files move first, each move written to a journal as it happens; the
>   catalog is committed last. So a crash mid-run leaves the catalog
>   untouched, and there is a `resume` that either puts the files back or
>   carries the run to the end.
> - Every run can be undone exactly, because the journal records what actually
>   happened rather than what was planned.
> - I ran my own 51,049-photo library through it and back many times, and
>   compared ten catalog tables, all 51,049 paths and every file on disk
>   against a baseline each time. Byte-identical every round.
>
> **What it will not do.** Lightroom Classic only — the cloud-based Lightroom
> has no folder tree to rebuild. It needs Python 3.9 or newer; macOS and
> Windows. And it is one person's project, not a company's.
>
> It also handles the awkward parts: XMP sidecars, virtual copies, stacks,
> raw+JPEG pairs, folders you want left alone, folders already named
> `2019-01-03 Wedding` that should keep their text, and files on disk the
> catalog does not know about.
>
> Documentation is complete in English and German:
> https://andy-freund.gitlab.io/LR-FolderCraft
>
> If anyone tries it, I would genuinely like to hear where it was confusing.
> That is more useful to me than praise.

---

## 2. Adobe Community — Lightroom Classic

*Why here:* enormous search traffic; a good answer ranks for years. Best used
as a **reply to an existing question**, not as a new thread. Search for
"moved folders missing photos", "reorganise folder structure", "change folder
structure by date".

> *(as a reply)*
>
> If you are still looking for a way to do this in bulk: what you want is for
> the files and the catalog to move *together*, which is exactly what
> Lightroom's Folders panel does — just one folder at a time.
>
> Two routes, depending on size:
>
> **Under a few thousand photos:** do it inside Lightroom. In the Folders
> panel, create the target folders and drag. It is slow but it is Adobe's own
> code and it cannot lose the connection.
>
> **Tens of thousands:** dragging is no longer realistic. I wrote a free open
> source tool for this because I had the same problem with a 51,049-photo
> catalog — LR-FolderCraft. It rewrites the folder tree on disk and in the
> catalog in one operation, with a dry run first, a verified catalog backup,
> and a full undo. Disclosure: it is mine, and it is free with no strings.
> https://andy-freund.gitlab.io/LR-FolderCraft
>
> Whatever you use: close Lightroom, back up the catalog yourself as well, and
> never move the folders in Finder or Explorer first — that is what produces
> the question marks.

---

## 3. Reddit — r/Lightroom, r/postprocessing, r/DataHoarder

*Why here:* the right people, the least patience for advertising. Several
subreddits ban self-promotion outright or require a ratio of ordinary
participation. **Read the sidebar and the rules before posting**, and prefer
commenting on existing threads.

**Title:** I had 51,000 photos in five giant year folders and no safe way to reorganise them, so I wrote one

> Disclosure up front: this is my own tool, it is free, open source, and there
> is nothing to buy.
>
> The trap everyone hits: move the folders in Finder and Lightroom loses every
> file. Drag them in Lightroom's Folders panel and it works, but at 51,000
> photos that is days of clicking. Re-import and you lose your edits.
>
> LR-FolderCraft moves the files and rewrites the catalog's folder records
> together, so the catalog never notices. Year/month/day, ISO week, by camera,
> or your own template.
>
> The part I care about more than the features: it shows you the whole plan
> before touching anything, backs up and verifies the catalog, writes the
> catalog last so an interrupted run leaves it intact, journals every single
> move, and can undo a run exactly. I put my own library through it and back
> repeatedly and diffed ten catalog tables plus every path and file each time.
>
> Lightroom **Classic** only. macOS and Windows, needs Python.
>
> https://andy-freund.gitlab.io/LR-FolderCraft
>
> Happy to answer anything, including "why should I trust this with my
> catalog", which is the right question.

---

## 4. Hacker News — Show HN

*Why here:* one sharp spike of technically minded readers, and useful
scrutiny. Lead with the engineering, not the photography. Post it yourself,
be around for the whole day to answer, and never ask anyone to upvote.

**Title:** Show HN: Rewriting Lightroom's SQLite catalog to reorganise 51k photos safely

> A Lightroom Classic catalog is a SQLite database, and the folder tree on disk
> is mirrored in it as root folders plus relative paths. Move files behind
> Lightroom's back and every reference dangles. Move them inside Lightroom and
> it is one folder at a time.
>
> LR-FolderCraft does both halves as one operation. The interesting parts were
> not the SQL:
>
> - **Ordering for crash safety.** Files move first, journalled; the catalog
>   transaction commits last. Kill the process at any moment and SQLite
>   discards the transaction, so the catalog is consistent and only the
>   filesystem is half-done — which a journal can put right in either
>   direction. Undo restores the catalog last for the same reason, which makes
>   an interrupted undo re-runnable.
> - **macOS hands you NFD.** Filenames come back decomposed, so a naive
>   character map for transliteration silently matches nothing. Everything is
>   NFC-composed before it is compared.
> - **A counter column whose storage class matters.** Lightroom stores an
>   entity-ID counter as REAL. Write an INTEGER back into it and Lightroom
>   will not open the catalog.
> - **Deciding what "interrupted" means is harder than repairing it.** The
>   first version inferred it from the filesystem and got it wrong: a later
>   run had recreated the same paths, so the repair would have torn the
>   standing run apart. It now records the state rather than guessing it.
>
> Verification is the reason I would use it: a real 51,049-photo, 2.36 TB
> library migrated and reversed many times, compared byte for byte across ten
> catalog tables, all paths and all files on disk.
>
> Python 3.9+, MIT or GPL-3.0, no telemetry, three front ends.
> https://gitlab.com/andy-freund/LR-FolderCraft

---

## 5. Directory listings — low effort, lasting

Write once, then leave alone:

- **AlternativeTo** — list it against "Adobe Bridge", "digiKam", "Photo
  Mechanic" as a folder-organisation tool.
- **Awesome lists** on GitHub for photography and self-hosted tooling — a
  pull request adding one line.
- **Wikipedia** is *not* one of these. Do not add it there.
