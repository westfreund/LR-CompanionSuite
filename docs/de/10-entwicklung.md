# Entwicklung und Fortsetzung

**Revision r14.0.1 · Build-Datum 2026-08-23**

Dieses Dokument existiert, damit die Arbeit später fortgesetzt werden kann —
von Ihnen, von jemand anderem oder von einem KI-Assistenten — ohne den Kontext
aus dem Code rekonstruieren zu müssen.

## Aktueller Stand

**r1.0.0 ist vollständig und funktionsfähig.** Ende-zu-Ende verifiziert gegen
einen echten Lightroom-Classic-Katalog (Schema 18.0.0, 9.452 Dateien, 337 GiB,
exFAT).

| Bereich | Stand |
| --- | --- |
| Katalog lesen/schreiben | vollständig, getestet |
| Template-Engine | vollständig, 25 Platzhalter, 12 Vorlagen |
| Planer | vollständig: Anker, Konflikte, Sidecars, Volume-Wechsel, idempotent |
| Sicherheit | vollständig: 8 Prüfungen, Backup, Journal, Rollback, Undo, Verifikation |
| CLI | vollständig: 9 Befehle |
| TUI | vollständig: Laden, Planen, Ausführen, Live-Vorschau, EN/DE |
| GUI | vollständig: Qt, alle Einstellungen, Ordnerentscheidungen, Fortschritt |
| Tests | 270 Tests, 87 % Abdeckung |
| CI | GitLab, Python 3.9–3.13 |
| Dokumentation | vollständig, EN und DE |
| Installationsskripte | macOS, Linux, Windows |

### Was *nicht* erledigt ist

- Der Umgang mit gewachsenen Ordnerstrukturen aus r2.0.0 -- thematische Ordner,
  datierte Ordner, Entscheidungen je Ordner -- ist durch Tests gegen synthetische
  Kataloge abgedeckt, **aber noch nie einer echten Bibliothek mit solcher
  Struktur begegnet**. Das ist der nächste Schritt.
- **Das Windows-PowerShell-Skript wurde nie unter Windows ausgeführt.** Es ist
  sorgfältig geschrieben und strukturell geprüft, es stand aber kein
  Windows-Rechner zur Verfügung. Die erste Installation dort ist als Test zu
  behandeln.
- **Ein Ergebnis wurde noch nicht in Lightroom Classic selbst geöffnet.** Alle
  bisherige Prüfung geschah auf Datenbank- und Dateisystemebene:
  Integritätsprüfung, Fremdschlüsselprüfung, Gültigkeit des Ordnerbaums,
  Pfadauflösung und ein unveränderter Hash über die Bild-, Entwicklungs-,
  Stichwort- und Sammlungstabellen. Die verbleibende Bestätigung ist visuell,
  in Lightroom.

## Einrichtung

```bash
git clone https://gitlab.com/andy-freund/LR-FolderCraft.git
cd LR-FolderCraft
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
pytest
```

Aus dem Quellbaum heraus ohne Installation ausführen:

```bash
PYTHONPATH=src python3 -m lrfoldercraft info /pfad/zu.lrcat
```

## Teststrategie

`tests/conftest.py` baut einen **synthetischen Lightroom-Katalog**, der genau
die Tabellen enthält, die das Werkzeug anfasst — mit denselben Spaltennamen,
der `pathFromRoot`-Konvention mit abschließendem Schrägstrich und einem
funktionierenden `Adobe_entityIDCounter`. Keine Lightroom-Installation, keine
Fixture-Downloads, kein Netzwerk.

```python
def test_irgendwas(simple_catalog):        # sechs Fotos, drei Tage, zwei Kameras
    plan = plan_for(simple_catalog, structure=("{yyyy}-{mm}-{dd}",))
    ...

def test_eigenes(builder):                 # eigenen Fall bauen
    builder.add_photo("A.CR2", "2019-01-03T10:00:00", folder="alt/",
                      sidecars=["A.xmp"], virtual_copies=2)
```

| Datei | Deckt ab |
| --- | --- |
| `test_rules.py` | Platzhalter, Namensbereinigung, Vorlagen, ISO-Wochen-Grenzfälle |
| `test_folders.py` | Datumserkennung in Ordnernamen, Granularität |
| `test_catalog.py` | Reader, Writer, ID-Vergabe, Sperren, Rollback |
| `test_planner.py` | Gruppierung, Anker, Konflikte, Sidecars, Idempotenz |
| `test_executor.py` | Ausführung, Rollback bei eingeschleustem Fehler, Undo, Zyklen |
| `test_config.py` | Validierung, Profile |
| `test_cli.py` | Rückgabewerte, Ausgabeformate, Nur-Lesen-Zusagen |
| `test_tui.py` | Textual-Rauchtests ohne Terminal |
| `test_gui.py` | Qt-Tests ohne Bildschirm (Offscreen-Plattform) |
| `test_version.py` | Revisionskonsistenz über das ganze Repository |

Wer den Executor anfasst, muss
`test_rollback_restores_everything_when_a_move_fails` grün halten. Es ist der
wichtigste Test der Suite.

## Sicher gegen einen echten Katalog testen

Nie einen scharfen Lauf auf die Arbeitsbibliothek richten. Eine verkleinerte
Arbeitskopie anlegen:

```python
import sqlite3, shutil, os
shutil.copy2("/pfad/original.lrcat", "/tmp/work/test.lrcat")
c = sqlite3.connect("/tmp/work/test.lrcat")
keep = [ ... 40 Datei-IDs ... ]
c.execute("DELETE FROM Adobe_images  WHERE rootFile  NOT IN (...)", keep)
c.execute("DELETE FROM AgLibraryFile WHERE id_local NOT IN (...)", keep)
c.execute("UPDATE AgLibraryRootFolder SET absolutePath = '/tmp/work/images/'")
c.commit(); c.execute("VACUUM"); c.commit()
```

Dann diese 40 Bilddateien nach `/tmp/work/images/` kopieren und gegen die Kopie
arbeiten. Genau so wurde r1.0.0 validiert.

Anschließend die Invarianten prüfen:

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;

-- keine verwaisten Ordner
SELECT COUNT(*) FROM AgLibraryFolder f WHERE f.pathFromRoot <> ''
  AND NOT EXISTS (SELECT 1 FROM AgLibraryFolder p WHERE p.id_local = f.parentId);

-- jeder Elternpfad ist Präfix seines Kindes
SELECT COUNT(*) FROM AgLibraryFolder f JOIN AgLibraryFolder p ON p.id_local = f.parentId
  WHERE substr(f.pathFromRoot, 1, length(p.pathFromRoot)) <> p.pathFromRoot;

-- jeder Katalogpfad existiert auf der Platte
SELECT rf.absolutePath || fo.pathFromRoot || f.idx_filename
  FROM AgLibraryFile f
  JOIN AgLibraryFolder fo     ON fo.id_local = f.folder
  JOIN AgLibraryRootFolder rf ON rf.id_local = fo.rootFolder;
```

## Wo welche Änderung hingehört

| Aufgabe | Dateien |
| --- | --- |
| Neuer Platzhalter | `rules.py` (`TOKEN_SPECS`, `TokenContext.values`), `tests/test_rules.py` |
| Neue Vorlage | `rules.py` (`PRESETS`, `PRESET_DESCRIPTIONS`) |
| Neues Katalogfeld | `catalog/model.py` (`Photo`), `catalog/reader.py` (`_PHOTO_SELECT`) |
| Neue CLI-Option | `cli.py` (`_add_plan_flags`, `settings_from_args`), `config.py` |
| Neue Ordnerart oder Entscheidung | `folders.py`, dann `planner._segments_for` |
| Neue Vorprüfung | `safety.py` — ein zweisprachiges `Check` zurückgeben |
| Neues Ausführungsverhalten | `executor.py`, plus passender Rollback-Test |
| Neues TUI-Element | `tui/app.py`, `tui/app.tcss` |
| Neues GUI-Element | `gui/app.py`, Texte in `gui/i18n.py` |

Jeder Platzhalter, jede Vorlage und jede Prüfung trägt beide Sprachen in ihrer
eigenen Definition, sodass Hilfeausgabe, Dokumentationstabellen und TUI sich
selbst aktualisieren.

## Konventionen

- Python-3.9-Basis. `from __future__ import annotations` am Kopf jedes Moduls;
  `typing.List`/`Dict`/`Optional` statt `list[...]`.
- `str.format()` in Log- und Benutzermeldungen statt f-Strings — Logaufrufe
  bleiben lazy und das 3.9-Ziel ehrlich.
- Jede öffentliche Funktion hat einen Docstring, der das *Warum* erklärt, nicht
  das *Was*.
- Kein Kernmodul importiert aus `cli` oder `tui`.
- Alles, was Zustand ändert, läuft über `logging_setup.step()`.
- Vor dem Commit `ruff check src tests` und `ruff format --check src tests`.

## Commits und Releases

Zu jedem funktionsfähigen Meilenstein wird committet und gepusht. Stil der
Nachrichten:

```
feat: <was geändert wurde>     Feature, MAJOR erhöhen
fix: <was kaputt war>          Fehlerbehebung, PATCH erhöhen
docs: <was dokumentiert wurde>
refactor: / test: / chore:     höchstens MINOR erhöhen
release: rX.Y.Z — <Zusammenfassung>
```

Die Release-Schritte stehen in [11-versionierung.md](11-versionierung.md).

## Die drei Frontends

`cli.py`, `tui/` und `gui/` erreichen den Kern über dieselben drei Aufrufe:

```python
with open_catalog(pfad) as conn:
    plan = build_plan(CatalogReader(conn), settings, decide=frage_zu_ordner)
checks = preflight(plan)
result = execute(plan, settings, progress=lambda done, total, msg: ...)
```

Ein viertes Frontend zu ergänzen heißt, diese drei Aufrufe zu schreiben und
sonst nichts. Zwei Regeln, welche die bestehenden schmerzhaft gelernt haben:

* Vorgabewerte der Oberfläche aus einem frischen `Settings()` nehmen, nie aus
  dem ersten Eintrag eines Auswahlfeldes — die GUI widersprach der
  Dokumentation stillschweigend, bis ein Test es fand.
* Beim Schließen des Fensters auf die Worker-Threads warten. Ein laufender
  QThread, der zerstört wird, bricht den Prozess ab.

Die Qt-Tests laufen ohne Bildschirm mit
`QT_QPA_PLATFORM=offscreen pytest tests/test_gui.py`.

## Fahrplan

Die priorisierte Liste steht in [13-offene-punkte.md](13-offene-punkte.md).
