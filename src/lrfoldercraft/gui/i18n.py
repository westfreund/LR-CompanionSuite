"""Interface strings for the graphical front end, in both project languages."""

from __future__ import annotations

from typing import Dict, Tuple

TEXT: Dict[str, Tuple[str, str]] = {
    # window and sections
    "title": ("LR-FolderCraft", "LR-FolderCraft"),
    "catalog": ("Catalog", "Katalog"),
    "source": ("Source", "Quelle"),
    "target": ("Target", "Ziel"),
    "structure": ("Folder structure", "Ordnerstruktur"),
    "options": ("Options", "Optionen"),
    "existing": ("Folders found", "Vorgefundene Ordner"),
    "result": ("Result", "Ergebnis"),
    "log": ("Log", "Protokoll"),
    # catalog
    "browse": ("Browse…", "Durchsuchen…"),
    "load": ("Load", "Laden"),
    "pick_catalog": ("Choose a Lightroom catalog", "Lightroom-Katalog auswählen"),
    "catalog_filter": ("Lightroom catalog (*.lrcat)", "Lightroom-Katalog (*.lrcat)"),
    "no_catalog": ("No catalog loaded", "Kein Katalog geladen"),
    # source
    "root_folder": ("Root folder", "Stammordner"),
    "all_roots": ("All root folders", "Alle Stammordner"),
    "include_ext": ("Only these extensions", "Nur diese Endungen"),
    "exclude_ext": ("Skip these extensions", "Diese Endungen auslassen"),
    "ext_hint": ("comma separated, e.g. cr2, dng", "kommagetrennt, z. B. cr2, dng"),
    # target
    "in_place": (
        "Below the folder the photos are in now",
        "Unterhalb des Ordners, in dem die Bilder jetzt liegen",
    ),
    "new_tree": ("Into a new folder", "In einen neuen Ordner"),
    "pick_target": ("Choose a target folder", "Zielordner auswählen"),
    "target_hint": (
        "The folder is created if it does not exist. Use the dialog's New Folder "
        "button to make one.",
        "Der Ordner wird angelegt, falls er fehlt. Im Dialog legt die Schaltfläche "
        "„Neuer Ordner“ einen an.",
    ),
    # structure
    "preset": ("Preset", "Vorlage"),
    "custom": ("Own template", "Eigenes Template"),
    "preview": ("Preview", "Vorschau"),
    "tokens": ("Placeholders…", "Platzhalter…"),
    # options
    "conflict": ("Name conflicts", "Namenskonflikte"),
    "missing_date": ("Without capture date", "Ohne Aufnahmedatum"),
    "subfolder_action": ("Topic subfolders", "Thematische Unterordner"),
    "dated_action": ("Dated folders", "Datierte Ordner"),
    "mismatch_action": ("Wrong date inside", "Falsches Datum darin"),
    "sidecars": ("Move sidecar files", "Sidecar-Dateien mitnehmen"),
    "backup": ("Back up the catalog first", "Katalog vorher sichern"),
    "ascii": ("ASCII-only folder names", "Ordnernamen nur ASCII"),
    # folder table
    "col_folder": ("Folder", "Ordner"),
    "col_kind": ("Kind", "Art"),
    "col_photos": ("Photos", "Fotos"),
    "col_decision": ("Decision", "Entscheidung"),
    "kind_dated": ("dated", "datiert"),
    "kind_plain": ("topic", "thematisch"),
    "kind_anchor": ("anchor", "Anker"),
    "mismatched": ("{n} with a different date", "{n} mit abweichendem Datum"),
    # actions
    "plan": ("Plan (changes nothing)", "Planen (ändert nichts)"),
    "apply": ("Apply", "Ausführen"),
    "cancel": ("Cancel", "Abbrechen"),
    "quit": ("Quit", "Beenden"),
    "ready": ("Ready", "Bereit"),
    "loading": ("Reading the catalog…", "Katalog wird gelesen…"),
    "planning": ("Planning…", "Plan wird erstellt…"),
    "applying": ("Moving files…", "Dateien werden verschoben…"),
    "done": ("Done", "Fertig"),
    # confirmation
    "confirm_title": ("Really apply?", "Wirklich ausführen?"),
    "confirm_text": (
        "{n} file(s) will be moved and the catalog will be modified.\n\n"
        "A verified backup of the catalog is written first, and the run can be "
        "undone.\n\nMake sure Lightroom Classic is closed.",
        "{n} Datei(en) werden verschoben und der Katalog wird verändert.\n\n"
        "Zuvor wird ein geprüftes Backup des Katalogs angelegt, und der Lauf lässt "
        "sich rückgängig machen.\n\nBitte sicherstellen, dass Lightroom Classic "
        "geschlossen ist.",
    ),
    "nothing_to_do": ("Nothing to do.", "Nichts zu tun."),
    "plan_first": ("Please plan first.", "Bitte zuerst planen."),
    # summary labels
    "to_move": ("To be moved", "Zu verschieben"),
    "in_place_count": ("Already in place", "Bereits am Ziel"),
    "skipped": ("Skipped", "Übersprungen"),
    "new_folders": ("New folders", "Neue Ordner"),
    "volume": ("Data volume", "Datenvolumen"),
    "virtual_copies": ("Virtual copies carried", "Mitgeführte virtuelle Kopien"),
    "language": ("Deutsch", "English"),
    # the ordered rule list
    "rules_hint": (
        "Rules, in order -- the first one that matches decides a folder. A pattern is "
        "a folder path (covering everything below it) or one of: *, dated, "
        "dated+label, dated-only, plain. A decision you make in the table below "
        "still wins.",
        "Regeln, der Reihe nach -- die erste passende entscheidet einen Ordner. Ein "
        "Muster ist ein Ordnerpfad (der alles darunter mit einschliesst) oder eines "
        "von: *, dated, dated+label, dated-only, plain. Eine Entscheidung, die Sie "
        "unten in der Tabelle treffen, sticht trotzdem.",
    ),
    "col_pattern": ("Pattern", "Muster"),
    "col_decided_by": ("Decided by", "Entschieden durch"),
    "decided_by_you": ("you", "von Ihnen"),
    "decided_by_default": ("default", "Voreinstellung"),
    "rule_add": ("Add rule", "Regel hinzufügen"),
    "rule_remove": ("Remove", "Entfernen"),
    "rule_up": ("Move up -- earlier rules win", "Nach oben -- frühere Regeln gewinnen"),
    "rule_down": ("Move down", "Nach unten"),
    # what the plan could not decide alone
    "findings": ("Needs your answer", "Braucht Ihre Antwort"),
    "level_error": ("BLOCKS", "BLOCKIERT"),
    "level_warning": ("Warning", "Warnung"),
    "level_exception": ("Exception", "Ausnahme"),
    "level_note": ("Note", "Hinweis"),
    "col_count": ("Files", "Dateien"),
    "col_what": ("What was found", "Was gefunden wurde"),
    "col_setting": ("Governed by", "Gesteuert durch"),
    "col_current": ("Currently", "Derzeit"),
    "findings_none": (
        "Nothing needs an answer -- the plan is unambiguous.",
        "Nichts zu beantworten -- der Plan ist eindeutig.",
    ),
    "findings_hint": (
        "Select a row to see which files it concerns. Change the setting named in "
        "'Governed by' and plan again.",
        "Eine Zeile auswählen, um die betroffenen Dateien zu sehen. Die unter "
        "'Gesteuert durch' genannte Einstellung ändern und erneut planen.",
    ),
    "findings_more": ("... and {n:,} more", "... und {n:,} weitere"),
    "collect_orphans": (
        "Collect files not in the catalog",
        "Nicht im Katalog enthaltene Dateien einsammeln",
    ),
    "collect_orphans_hint": (
        "Files lying in the library's folders that Lightroom does not know: "
        "exports, round trips, stale sidecars. Nothing is deleted -- they are "
        "moved into one folder, keeping the path they came from, and undoing "
        "the run puts them back.",
        "Dateien in den Ordnern der Bibliothek, die Lightroom nicht kennt: "
        "Exporte, Zwischenstände, verwaiste Sidecars. Nichts wird gelöscht — sie "
        "wandern in einen Ordner und behalten dabei ihren Herkunftspfad, und das "
        "Zurücknehmen des Laufs holt sie wieder heraus.",
    ),
    "orphan_folder_hint": (
        "Name of that folder, created below each source root",
        "Name dieses Ordners, unterhalb jeder Quellwurzel angelegt",
    ),
    "purpose": (
        "Reorganise a Lightroom Classic library's folders — moving the files and "
        "rewriting the catalog together, so nothing is lost.",
        "Die Ordner einer Lightroom-Classic-Bibliothek umsortieren — Dateien "
        "verschieben und Katalog umschreiben in einem Zug, damit nichts verloren "
        "geht.",
    ),
    "about": ("About LR-FolderCraft", "Über LR-FolderCraft"),
    "about_what": (
        "Groups the photos of a Lightroom Classic library into a new folder "
        "structure — by capture date, camera, calendar week, in freely "
        "combinable levels. The image files are moved on disk and the catalog is "
        "rewritten in the same operation, so develop settings, virtual copies, "
        "collections, keywords and history all survive.",
        "Gruppiert die Fotos einer Lightroom-Classic-Bibliothek in eine neue "
        "Ordnerstruktur — nach Aufnahmedatum, Kamera, Kalenderwoche, in frei "
        "kombinierbaren Ebenen. Die Bilddateien werden auf der Platte verschoben "
        "und der Katalog im selben Zug umgeschrieben, sodass "
        "Entwicklungseinstellungen, virtuelle Kopien, Sammlungen, Stichwörter "
        "und Historie erhalten bleiben.",
    ),
    "about_promise": (
        "<b>What it touches:</b> only the folder rows and each file's folder "
        "column. Nothing else in the catalog is ever written. A verified backup "
        "is made first, every step is journalled, and any run can be undone.",
        "<b>Was es anfasst:</b> nur die Ordnerzeilen und die Ordnerspalte jeder "
        "Datei. Sonst wird im Katalog nichts geschrieben. Zuvor wird eine "
        "geprüfte Sicherung angelegt, jeder Schritt wird journalisiert, und jeder "
        "Lauf lässt sich rückgängig machen.",
    ),
    "about_licence": (
        "Licence: MIT or GPL-3.0-or-later, at your choice.",
        "Lizenz: MIT oder GPL-3.0-or-later, nach Ihrer Wahl.",
    ),
    "preconditions_title": ("Before this run", "Vor diesem Lauf"),
    "preconditions_intro": (
        "This is what was found about the library. Please read it -- these are "
        "the things that decide whether the run can succeed:",
        "Das wurde über die Bibliothek festgestellt. Bitte lesen — davon hängt "
        "ab, ob der Lauf gelingen kann:",
    ),
    "preconditions_ack": (
        "I have read this, Lightroom Classic is closed, and I have a backup of my own",
        "Ich habe das gelesen, Lightroom Classic ist geschlossen, und ich habe "
        "eine eigene Sicherung",
    ),
    "preconditions_blocked": (
        "Something above prevents the run. Put it right first — it cannot be acknowledged away.",
        "Etwas davon verhindert den Lauf. Bitte zuerst beheben — es lässt sich "
        "nicht wegbestätigen.",
    ),
    "menu_actions": ("Actions", "Aktionen"),
    "undo_run": ("Undo a run…", "Lauf rückgängig machen…"),
    "undo_button": ("Undo…", "Rückgängig…"),
    "pick_journal": (
        "Choose the journal of the run to undo",
        "Journal des rückgängig zu machenden Laufs wählen",
    ),
    "confirm_undo": (
        "Reverse the run recorded in\n\n{j}\n\nEvery file it moved goes back to "
        "where it was, the folders it created are removed if empty, and the "
        "catalog is restored from the backup that run made.\n\nMake sure "
        "Lightroom Classic is closed.",
        "Den in\n\n{j}\n\naufgezeichneten Lauf rückgängig machen? Jede verschobene "
        "Datei kehrt an ihren Platz zurück, die angelegten Ordner werden entfernt, "
        "sofern sie leer sind, und der Katalog wird aus der Sicherung dieses Laufs "
        "zurückgespielt.\n\nBitte sicherstellen, dass Lightroom Classic geschlossen "
        "ist.",
    ),
    "undoing": ("Undoing the run…", "Lauf wird rückgängig gemacht…"),
    "undo_done": (
        "{n:,} file(s) put back, and the catalog restored from its backup.",
        "{n:,} Datei(en) zurückgestellt und der Katalog aus seiner Sicherung wiederhergestellt.",
    ),
    "undo_failed": (
        "The run was only partly reversed:\n\n{e}",
        "Der Lauf wurde nur teilweise rückgängig gemacht:\n\n{e}",
    ),
    "splitter_hint": (
        "Drag to give this section more or less room -- drag it fully shut to "
        "hide the section, and back open to bring it out again",
        "Ziehen, um diesem Bereich mehr oder weniger Platz zu geben -- ganz "
        "zuziehen blendet den Bereich aus, wieder aufziehen holt ihn zurück",
    ),
}


def tr(key: str, language: str) -> str:
    en, de = TEXT[key]
    return de if language == "de" else en
