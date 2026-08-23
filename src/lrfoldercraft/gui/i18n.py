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
}


def tr(key: str, language: str) -> str:
    en, de = TEXT[key]
    return de if language == "de" else en
