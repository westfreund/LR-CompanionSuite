"""Every string the LR-MetaSearch window shows, in both languages.

Kept as one table for the same reason the folder tool keeps one: a string that
exists in one language only is invisible until somebody switches, and then it
is glaring.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

TEXT = {
    "window_title": ("LR-MetaSearch", "LR-MetaSearch"),
    "purpose": (
        "Search across every Lightroom Classic library you own — even the ones "
        "whose drive is in a cupboard.",
        "Über alle Lightroom-Classic-Bibliotheken suchen — auch über die, deren "
        "Laufwerk gerade im Schrank liegt.",
    ),
    "tab_search": ("1 · Search", "1 · Suche"),
    "tab_libraries": ("2 · Libraries", "2 · Bibliotheken"),
    "tab_duplicates": ("3 · Duplicates", "3 · Dubletten"),
    "tab_export": ("4 · Export", "4 · Export"),
    "tab_search_hint": (
        "What to look for, across every library in the index.",
        "Wonach gesucht wird, über alle Bibliotheken im Index.",
    ),
    "tab_libraries_hint": (
        "Which libraries and drives the index knows, and when it last read them.",
        "Welche Bibliotheken und Laufwerke der Index kennt, und wann zuletzt gelesen.",
    ),
    "tab_duplicates_hint": (
        "The same photograph held more than once — a report, nothing is changed.",
        "Dasselbe Foto mehrfach vorhanden — ein Bericht, es wird nichts verändert.",
    ),
    "tab_export_hint": (
        "Turn the current search into catalogs Lightroom can merge.",
        "Aus der aktuellen Suche Kataloge machen, die Lightroom zusammenführen kann.",
    ),
    # -- criteria
    "criteria": ("What to look for", "Wonach gesucht wird"),
    "keywords": ("Keywords (all of them)", "Stichwörter (alle davon)"),
    "keywords_hint": ("comma separated", "kommagetrennt"),
    "any_keywords": ("Keywords (any of them)", "Stichwörter (eines genügt)"),
    "text": ("File name or folder", "Dateiname oder Ordner"),
    "camera": ("Camera", "Kamera"),
    "lens": ("Lens", "Objektiv"),
    "catalog": ("Library", "Bibliothek"),
    "extension": ("Extension", "Dateiendung"),
    "since": ("Captured from", "Aufgenommen ab"),
    "until": ("Captured until", "Aufgenommen bis"),
    "any_date": ("any date", "beliebig"),
    "min_rating": ("At least", "Mindestens"),
    "stars": ("{n} star(s)", "{n} Stern(e)"),
    "no_stars": ("any rating", "beliebig"),
    "with_gps": ("Only with a position", "Nur mit Position"),
    "include_copies": ("Include virtual copies", "Virtuelle Kopien einschließen"),
    "search": ("Search", "Suchen"),
    "clear": ("Clear", "Zurücksetzen"),
    "browse_keywords": ("Keywords…", "Stichwörter…"),
    # -- results
    "col_file": ("File", "Datei"),
    "col_catalog": ("Library", "Bibliothek"),
    "col_captured": ("Captured", "Aufnahme"),
    "col_camera": ("Camera", "Kamera"),
    "col_rating": ("★", "★"),
    "col_drive": ("Drive", "Laufwerk"),
    "col_folder": ("Folder", "Ordner"),
    "col_keywords": ("Keywords", "Stichwörter"),
    "hits": ("{n} match(es), showing {s}", "{n} Treffer, davon {s} gezeigt"),
    "no_hits": ("Nothing matches.", "Nichts gefunden."),
    "give_a_criterion": (
        "Give at least one criterion.",
        "Bitte mindestens ein Kriterium angeben.",
    ),
    "not_attached": (
        "! not where the catalog says — the drive may be detached, or the library "
        "was moved without telling Lightroom",
        "! nicht dort, wo der Katalog sagt — Laufwerk nicht angeschlossen, oder die "
        "Bibliothek wurde verschoben, ohne es Lightroom zu sagen",
    ),
    # -- libraries
    "scan": ("Read libraries in…", "Bibliotheken einlesen…"),
    "scan_running": ("Reading {n}…", "Liest {n}…"),
    "scan_where": ("Choose a folder or a drive to look in", "Ordner oder Laufwerk zum Durchsuchen"),
    "scan_done": (
        "Read {r} librar(ies); {c} were copies. The index holds {p} photographs.",
        "{r} Bibliothek(en) gelesen, {c} davon Kopien. Der Index enthält {p} Fotos.",
    ),
    "drives": ("Drives", "Laufwerke"),
    "libraries": ("Libraries", "Bibliotheken"),
    "col_drive_id": ("Identifier", "Kennung"),
    "col_certain": ("How", "Woher"),
    "certain": ("from the system", "vom System"),
    "guessed": ("guessed", "geraten"),
    "attached": ("attached", "angeschlossen"),
    "detached": ("not attached", "nicht angeschlossen"),
    "col_photos": ("Photographs", "Fotos"),
    "col_read": ("Last read", "Zuletzt gelesen"),
    "col_state": ("State", "Zustand"),
    "state_copy": ("a copy", "Kopie"),
    "state_current": ("current", "aktuell"),
    "show_copies": (
        "Show libraries judged to be copies",
        "Als Kopien erkannte Bibliotheken zeigen",
    ),
    "index_empty": (
        "The index is empty. Read some libraries in first.",
        "Der Index ist leer. Bitte zuerst Bibliotheken einlesen.",
    ),
    "index_file": ("Index file", "Indexdatei"),
    # -- duplicates
    "find_duplicates": ("Look for duplicates", "Nach Dubletten suchen"),
    "across_only": ("Only across libraries", "Nur über Bibliotheken hinweg"),
    "near_instead": ("Bursts and brackets instead", "Stattdessen Serien und Reihen"),
    "dup_summary": (
        "{g} group(s) of identical files, {s} surplus copies, {a} spanning libraries.",
        "{g} Gruppe(n) gleicher Dateien, {s} überzählige Kopien, {a} über Bibliotheken hinweg.",
    ),
    "dup_note": (
        "A report. Nothing is changed, and nothing is deleted.",
        "Ein Bericht. Es wird nichts verändert und nichts gelöscht.",
    ),
    "no_similarity": (
        "Visual similarity is not offered: it needs the pixels, and reading a raw "
        "file needs a decoder this tool does not ship.",
        "Visuelle Ähnlichkeit gibt es hier nicht: Sie braucht die Bildpunkte, und ein "
        "RAW-Format zu lesen braucht einen Decoder, den dieses Werkzeug nicht mitbringt.",
    ),
    # -- export
    "export_intro": (
        "Every library the search touched is copied, and the copy reduced to the "
        "photographs found. The originals are only read.",
        "Jede Bibliothek, die die Suche berührt, wird kopiert und die Kopie auf die "
        "gefundenen Fotos verkleinert. Die Originale werden nur gelesen.",
    ),
    "export_target": ("Into this empty folder", "In diesen leeren Ordner"),
    "with_data": (
        "Take the .lrcat-data directory along (Lightroom needs it)",
        "Das Verzeichnis .lrcat-data mitnehmen (Lightroom braucht es)",
    ),
    "with_data_hint": (
        "Lightroom Classic 11 and later keeps masking data in a directory beside "
        "the catalog. It cannot be reduced and is often several times the size of "
        "the catalog — but without it Lightroom refuses the result.",
        "Lightroom Classic 11 und neuer legt Maskendaten in einem Verzeichnis "
        "neben dem Katalog ab. Es lässt sich nicht verkleinern und ist oft ein "
        "Vielfaches des Katalogs groß — ohne es verweigert Lightroom das Ergebnis.",
    ),
    "browse": ("Browse…", "Durchsuchen…"),
    "export": ("Export…", "Exportieren…"),
    "export_nothing": (
        "Search something first — the export works on what the search found.",
        "Bitte zuerst suchen — der Export arbeitet mit dem, was die Suche gefunden hat.",
    ),
    "export_confirm": (
        "{n} photograph(s) from {c} librar(ies) will be written to\n\n{p}\n\n"
        "The original catalogs are only read. Continue?",
        "{n} Foto(s) aus {c} Bibliothek(en) werden geschrieben nach\n\n{p}\n\n"
        "Die Ursprungskataloge werden nur gelesen. Fortfahren?",
    ),
    "export_done": (
        "Done. Open each in Lightroom and use File > Import from Another Catalog to merge them.",
        "Fertig. Jeden in Lightroom öffnen und über Datei > Aus anderem Katalog "
        "importieren zusammenführen.",
    ),
    "export_not_empty": ("{p} is not empty.", "{p} ist nicht leer."),
    # -- general
    "ready": ("Ready", "Fertig"),
    "working": ("Working…", "Arbeitet…"),
    "menu_actions": ("Actions", "Aktionen"),
    "language": ("Deutsch / English", "Deutsch / English"),
    "about": ("About", "Über"),
    "close": ("Close", "Schließen"),
}


def tr(key: str, language: str = "en") -> str:
    english, german = TEXT[key]
    return german if language == "de" else english
