"""The ``lrfc index`` commands.

Kept beside the index rather than in ``cli.py``: the folder tool's command
module has no business growing by three hundred lines for a feature that does
not touch a photograph.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ..logging_setup import get_logger
from . import default_index_path
from .duplicates import catalog_copies, identical, near, summary
from .query import Filter, cameras, count, keywords, search
from .scan import scan
from .store import Index, IndexError_
from .subset import SubsetError, build

log = get_logger("metasearch.cli")

OK, ERROR, USAGE = 0, 1, 2


def _(language: str, english: str, german: str) -> str:
    """Two languages, one line, like the rest of the command line."""
    return german if language == "de" else english


def _n(number: int, language: str) -> str:
    """Group the digits the way the reader's language does.

    ``{:,}`` is English. A German reader sees 183,407 as a decimal.
    """
    grouped = "{n:,}".format(n=int(number))
    return grouped.replace(",", ".") if language == "de" else grouped


def add_filter_flags(parser: argparse.ArgumentParser) -> None:
    """The criteria shared by ``find`` and ``export``."""
    group = parser.add_argument_group("criteria")
    group.add_argument("--keyword", action="append", default=[], help="must carry this keyword")
    group.add_argument(
        "--any-keyword", action="append", default=[], help="carries at least one of these"
    )
    group.add_argument("--text", default="", help="file name or folder contains this")
    group.add_argument("--camera", default="", help="camera model contains this")
    group.add_argument("--lens", default="", help="lens contains this")
    group.add_argument("--catalog", default="", help="catalog name contains this")
    group.add_argument("--ext", default="", help="file extension, e.g. cr3")
    group.add_argument("--since", default="", help="captured on or after YYYY-MM-DD")
    group.add_argument("--until", default="", help="captured on or before YYYY-MM-DD")
    group.add_argument("--min-rating", type=int, default=0, help="at least this many stars")
    group.add_argument("--with-gps", action="store_true", help="only photographs with a position")
    group.add_argument("--include-copies", action="store_true", help="include virtual copies")
    group.add_argument(
        "--include-superseded",
        action="store_true",
        help="include catalogs the scan judged to be copies",
    )


def filter_from(args: argparse.Namespace) -> Filter:
    return Filter(
        keywords=tuple(args.keyword),
        any_keywords=tuple(args.any_keyword),
        text=args.text,
        camera=args.camera,
        lens=args.lens,
        catalog=args.catalog,
        extension=args.ext,
        since=args.since,
        until=args.until,
        min_rating=args.min_rating,
        with_gps=args.with_gps,
        include_copies=args.include_copies,
        include_superseded=args.include_superseded,
        limit=getattr(args, "limit", 0) or 0,
    )


def add_parser(sub, add_global_flags) -> None:
    """Hang ``index`` and its subcommands off another parser."""
    p_index = sub.add_parser("index", help="an index across every known library (read only)")
    inner = p_index.add_subparsers(dest="index_command", metavar="SUBCOMMAND")
    add_subcommands(inner, add_global_flags)


def add_subcommands(inner, add_global_flags) -> None:
    """The subcommands themselves, so `lrms` and `lrfc index` share them."""

    p_scan = inner.add_parser("scan", help="read catalogs into the index")
    p_scan.add_argument("paths", nargs="*", help="folders or .lrcat files to look in")
    p_scan.add_argument("--index", default="", help="where the index file lives")
    p_scan.add_argument(
        "--include-locked", action="store_true", help="read catalogs Lightroom has open"
    )
    add_global_flags(p_scan)

    p_status = inner.add_parser("status", help="what the index holds")
    p_status.add_argument("--index", default="")
    p_status.add_argument("--all", action="store_true", help="list copies too")
    add_global_flags(p_status)

    p_find = inner.add_parser("find", help="search across every library")
    p_find.add_argument("--index", default="")
    p_find.add_argument("--limit", type=int, default=40)
    p_find.add_argument("--paths", action="store_true", help="print full paths, one per line")
    add_filter_flags(p_find)
    add_global_flags(p_find)

    p_keywords = inner.add_parser("keywords", help="every keyword, with counts")
    p_keywords.add_argument("--index", default="")
    p_keywords.add_argument("--like", default="", help="only keywords containing this")
    p_keywords.add_argument("--limit", type=int, default=60)
    p_keywords.add_argument("--cameras", action="store_true", help="list cameras instead")
    add_global_flags(p_keywords)

    p_dupes = inner.add_parser("duplicates", help="the same photograph more than once")
    p_dupes.add_argument("--index", default="")
    p_dupes.add_argument("--limit", type=int, default=20)
    p_dupes.add_argument(
        "--across-catalogs", action="store_true", help="only what spans two libraries"
    )
    p_dupes.add_argument(
        "--near", action="store_true", help="bursts and brackets instead of exact copies"
    )
    add_global_flags(p_dupes)

    p_gui = inner.add_parser("gui", help="open the LR-MetaSearch window")
    p_gui.add_argument("--index", default="")
    add_global_flags(p_gui)

    p_export = inner.add_parser(
        "export", help="reduce catalogs to a selection, for Lightroom to merge"
    )
    p_export.add_argument("--index", default="")
    p_export.add_argument("--to", required=True, help="an empty directory for the result")
    p_export.add_argument("-y", "--yes", action="store_true", help="do not ask")
    add_filter_flags(p_export)
    add_global_flags(p_export)


def _open(args) -> Index:
    return Index.open(args.index or None, create=getattr(args, "index_command", "") == "scan")


def cmd_index(args: argparse.Namespace) -> int:
    language = args.lang or "en"
    if not getattr(args, "index_command", None):
        print(
            _(
                language,
                "Say what to do: scan, status, find, keywords, duplicates, export.",
                "Bitte angeben, was zu tun ist: scan, status, find, keywords, duplicates, export.",
            )
        )
        return USAGE
    try:
        handler = HANDLERS[args.index_command]
    except KeyError:  # pragma: no cover - argparse rejects unknown names first
        return USAGE
    try:
        return handler(args, language)
    except IndexError_ as exc:
        print(str(exc))
        return ERROR


# -- the subcommands ----------------------------------------------------


def _scan(args, language: str) -> int:
    roots = args.paths or _default_roots()
    if not roots:
        print(
            _(
                language,
                "Nothing to look in. Name a folder or a drive.",
                "Es gibt nichts zu durchsuchen. Bitte einen Ordner oder ein Laufwerk nennen.",
            )
        )
        return USAGE
    print(_(language, "Looking in: ", "Es wird gesucht in: ") + ", ".join(str(r) for r in roots))
    with Index.open(args.index or None) as index:
        outcomes = scan(
            roots,
            index,
            progress=lambda n, total, name: print(
                "  [{n}/{t}] {name}".format(n=n, t=total, name=name), flush=True
            ),
            include_locked=args.include_locked,
        )
        counts = index.counts()

    states: dict[str, int] = {}
    for outcome in outcomes:
        states[outcome.state] = states.get(outcome.state, 0) + 1
    print()
    print(
        _(
            language,
            "Read {r} catalog(s); {c} were copies.",
            "{r} Katalog(e) gelesen, {c} davon Kopien.",
        ).format(r=states.get("read", 0), c=states.get("copy", 0))
    )
    for outcome in outcomes:
        if outcome.state in ("failed", "locked"):
            print(
                "  {s:<8} {n}  {d}".format(s=outcome.state, n=outcome.path.name, d=outcome.detail)
            )
    print()
    print(_(language, "The index now holds:", "Der Index enthält jetzt:"))
    print(
        "  {p} {ph}, {k} {kw}, {c} {ca}, {v} {vo}".format(
            p=_n(counts["photos"], language),
            ph=_(language, "photographs", "Fotos"),
            k=_n(counts["keywords"], language),
            kw=_(language, "keywords", "Stichwörter"),
            c=counts["catalogs"],
            ca=_(language, "catalogs", "Kataloge"),
            v=counts["volumes"],
            vo=_(language, "drives", "Laufwerke"),
        )
    )
    print("  " + str(Path(args.index) if args.index else default_index_path()))
    return OK


def _default_roots() -> list[str]:
    """Everywhere a catalog is likely to be, when nobody said."""
    roots = [str(Path.home() / "Pictures")]
    volumes = Path("/Volumes")
    if volumes.is_dir():
        roots += [str(p) for p in volumes.iterdir() if p.is_dir() and not p.is_symlink()]
    return [r for r in roots if Path(r).exists()]


def _status(args, language: str) -> int:
    with _open(args) as index:
        counts = index.counts()
        print(_(language, "Index: {p}", "Index: {p}").format(p=args.index or default_index_path()))
        print(
            "  {c} {ca}, {p} {ph}, {k} {kw}, {v} {vo}, {x} {co}".format(
                c=counts["catalogs"],
                ca=_(language, "catalogs", "Kataloge"),
                p=_n(counts["photos"], language),
                ph=_(language, "photographs", "Fotos"),
                k=_n(counts["keywords"], language),
                kw=_(language, "keywords", "Stichwörter"),
                v=counts["volumes"],
                vo=_(language, "drives", "Laufwerke"),
                x=counts["copies"],
                co=_(language, "known copies", "erkannte Kopien"),
            )
        )
        print()
        print(_(language, "Drives:", "Laufwerke:"))
        for row in index.db.execute(
            "select label, kind, mount, identity, last_seen from volumes order by label"
        ):
            attached = bool(row[2]) and os.path.ismount(row[2])
            print(
                "  {mark} {label:<24} {kind:<12} {id}".format(
                    mark="*" if attached else " ",
                    label=(row[0] or "")[:24],
                    kind=_(language, "certain", "eindeutig")
                    if row[1] == "uuid"
                    else _(language, "guessed", "geraten"),
                    id=row[3][:36],
                )
            )
        print("  " + _(language, "* attached right now", "* gerade angeschlossen"))
        print()
        print(_(language, "Catalogs:", "Kataloge:"))
        for catalog in index.catalogs(include_superseded=args.all):
            mark = " " if catalog.superseded_by is None else "="
            print(
                "  {m} {n:<40} {i:>9} {ph}  {v:<18} {when}".format(
                    m=mark,
                    n=catalog.name[:40],
                    i=_n(catalog.images, language),
                    ph=_(language, "photos", "Fotos"),
                    v=catalog.volume_label[:18],
                    when=catalog.last_read[:16].replace("T", "  "),
                )
            )
        if args.all:
            print("  " + _(language, "= a copy of another", "= Kopie eines anderen"))
    return OK


def _find(args, language: str) -> int:
    criteria = filter_from(args)
    if criteria.is_empty:
        print(
            _(
                language,
                "Give at least one criterion.",
                "Bitte mindestens ein Kriterium angeben.",
            )
        )
        return USAGE
    with _open(args) as index:
        total = count(index, criteria._replace(limit=0))
        hits = search(index, criteria)
        if args.paths:
            for hit in hits:
                print(os.path.join(hit.folder, hit.file_name))
            return OK
        print(
            _(
                language,
                "{n} match(es); showing {s}.",
                "{n} Treffer, davon {s} gezeigt.",
            ).format(n=_n(total, language), s=len(hits))
        )
        print()
        for hit in hits:
            print(
                "  {mark} {f:<36} {c:<22} {t:<16} {v}".format(
                    mark=" " if hit.volume_attached else "!",
                    f=hit.file_name[:36],
                    c=hit.catalog[:22],
                    t=hit.capture_time[:16].replace("T", " "),
                    v=hit.volume[:16],
                )
            )
            if hit.keywords:
                print("      {k}".format(k=hit.keywords[:100]))
        if any(not hit.volume_attached for hit in hits):
            print()
            print(
                _(
                    language,
                    "! the drive holding this one is not attached.",
                    "! das Laufwerk dieses Treffers ist nicht angeschlossen.",
                )
            )
    return OK


def _keywords(args, language: str) -> int:
    with _open(args) as index:
        if args.cameras:
            for name, number in cameras(index)[: args.limit or None]:
                print("  {n:<36} {c:>9}".format(n=name[:36], c=_n(number, language)))
            return OK
        rows = keywords(index, like=args.like, limit=args.limit)
        if not rows:
            print(_(language, "No keywords in the index.", "Keine Stichwörter im Index."))
            return OK
        for name, number in rows:
            print("  {n:<40} {c:>9}".format(n=name[:40], c=_n(number, language)))
    return OK


def _duplicates(args, language: str) -> int:
    with _open(args) as index:
        if args.near:
            groups = near(index, limit=args.limit)
            print(
                _(
                    language,
                    "{n} group(s) of frames from the same camera in the same minute.",
                    "{n} Gruppe(n) Aufnahmen derselben Kamera in derselben Minute.",
                ).format(n=len(groups))
            )
        else:
            totals = summary(index)
            print(
                _(
                    language,
                    "{g} group(s) of identical files, {s} surplus copies, "
                    "{a} of them spanning libraries. {c} catalog(s) are copies.",
                    "{g} Gruppe(n) gleicher Dateien, {s} überzählige Kopien, "
                    "davon {a} über Bibliotheken hinweg. {c} Katalog(e) sind Kopien.",
                ).format(
                    g=_n(totals["groups"], language),
                    s=_n(totals["surplus"], language),
                    a=_n(totals["across_catalogs"], language),
                    c=totals["catalog_copies"],
                )
            )
            for name, _path, other, _note in catalog_copies(index):
                # Rendered here rather than read from the stored note: the note
                # was written in one language at scan time, and the reader may
                # want the other one.
                where = Path(other)
                print(
                    "  {n:<30} {d}".format(
                        n=name[:30],
                        d=_(language, "a copy of {o}", "Kopie von {o}").format(
                            o="{p}/{f}".format(p=where.parent.name, f=where.name) if other else "?"
                        ),
                    )
                )
            print()
            groups = identical(index, across_catalogs_only=args.across_catalogs, limit=args.limit)
        for group in groups:
            print("  {f}  ({n}x)".format(f=group.members[0].file_name[:48], n=len(group.members)))
            for member in group.members:
                print("      {c:<22} {f}".format(c=member.catalog[:22], f=member.folder[-60:]))
        print()
        print(
            _(
                language,
                "Nothing was changed. This is a report.",
                "Es wurde nichts verändert. Dies ist ein Bericht.",
            )
        )
    return OK


def _export(args, language: str) -> int:
    criteria = filter_from(args)
    if criteria.is_empty:
        print(
            _(
                language,
                "Give at least one criterion.",
                "Bitte mindestens ein Kriterium angeben.",
            )
        )
        return USAGE
    target = Path(args.to).expanduser()
    if target.exists() and any(target.iterdir()):
        print(_(language, "{p} is not empty.", "{p} ist nicht leer.").format(p=target))
        return ERROR

    with _open(args) as index:
        hits = search(index, criteria._replace(limit=0))
        if not hits:
            print(_(language, "Nothing matches.", "Nichts gefunden."))
            return OK
        libraries = sorted({hit.catalog for hit in hits})
        print(
            _(
                language,
                "{n} photograph(s) from {c} librar(ies):",
                "{n} Foto(s) aus {c} Bibliothek(en):",
            ).format(n=_n(len(hits), language), c=len(libraries))
        )
        for name in libraries:
            print("  {n}".format(n=name))
        print()
        print(
            _(
                language,
                "Each library is copied and the copy reduced to these photographs. "
                "The originals are only read.",
                "Jede Bibliothek wird kopiert und die Kopie auf diese Fotos verkleinert. "
                "Die Originale werden nur gelesen.",
            )
        )
        if not args.yes:
            answer = input(_(language, "Go ahead? [y/N] ", "Fortfahren? [j/N] ")).strip().lower()
            if answer not in ("y", "yes", "j", "ja"):
                print(_(language, "Nothing was done.", "Es wurde nichts getan."))
                return OK
        try:
            results = build(
                index,
                [hit.photo_id for hit in hits],
                target,
                progress=lambda message: print("    {m}".format(m=message), flush=True),
            )
        except SubsetError as exc:
            print(str(exc))
            return ERROR

    print()
    for result in results:
        if not str(result.target):
            print(
                _(
                    language,
                    "  skipped {n}: the drive is not attached",
                    "  übersprungen: {n} — das Laufwerk ist nicht angeschlossen",
                ).format(n=result.source.name)
            )
            continue
        print(
            "  {n:<34} {k} {of} {t}  ({a:.1f} MB)".format(
                n=result.target.name[:34],
                k=_n(result.kept, language),
                of=_(language, "of", "von"),
                t=_n(result.kept + result.removed, language),
                a=result.bytes_after / 1e6,
            )
        )
    print()
    print(
        _(
            language,
            "Open each in Lightroom, then use File > Import from Another Catalog "
            "to merge them into the catalog you want.",
            "Jeden in Lightroom öffnen und über Datei > Aus anderem Katalog importieren "
            "in den gewünschten Katalog zusammenführen.",
        )
    )
    return OK


def _gui(args, language: str) -> int:
    """Open the window, explaining rather than failing if Qt is absent."""
    try:
        from .gui.app import run
    except ImportError:
        print(
            _(
                language,
                "The window needs the graphical extra:\n  pip install 'lr-companion-suite[gui]'",
                "Das Fenster braucht das grafische Extra:\n  pip install 'lr-companion-suite[gui]'",
            )
        )
        return ERROR
    return run(["lrms"] + (["--lang=de"] if language == "de" else []))


HANDLERS = {
    "gui": _gui,
    "scan": _scan,
    "status": _status,
    "find": _find,
    "keywords": _keywords,
    "duplicates": _duplicates,
    "export": _export,
}
