# Versionierung

**Revision r13.0.4 · Build-Datum 2026-08-23**

## Das Schema

`MAJOR.MINOR.PATCH`, mit einer projektspezifischen Regel:

| Teil | Wird erhöht bei |
| --- | --- |
| **MAJOR** | **jeder Feature-Erweiterung** — ein neuer Platzhalter, eine neue Vorlage, ein neuer Befehl, ein neuer Platzierungsmodus, ein neues Frontend. Das ist Projektregel: Jedes Feature ist eine große Änderung. |
| **MINOR** | verhaltensneutrale Verbesserungen: Refactoring, Dokumentation, Performance, neue Tests. |
| **PATCH** | ausschließlich Fehlerbehebungen. |

Ein einzelner neuer Platzhalter hebt r1.0.0 also auf r2.0.0. Das ist Absicht:
Die Revision sagt dann eindeutig, ob eine bestimmte Fähigkeit vorhanden ist.

## Wo die Revision steht

`src/lrfoldercraft/version.py` ist die einzige Quelle:

```python
__version__    = "13.0.4"
__build_date__ = "2026-08-23"
__codename__   = "Pruefstand"
REVISION       = "r13.0.4 (2026-08-23)"
```

Nirgends sonst steht eine Version fest verdrahtet. Alles leitet sich daraus ab:

- `lrfc --version` und jeder Berichtskopf der CLI
- der TUI-Kopf (`SUB_TITLE`)
- die ersten Zeilen jeder Logdatei
- das Feld `tool_version` im Journal
- das Feld `revision` im exportierten Plan-JSON

## Wo sie angezeigt wird

Gefordert ist, dass das Werkzeug **immer** Revision und Erstellungsdatum
anzeigt. Das tut es an fünf Stellen:

```console
$ lrfc --version
LR-FolderCraft r13.0.4 (2026-08-23) - Laufakte
```

```
LR-FolderCraft r13.0.4 (2026-08-23) - Laufakte      <- jeder Berichtskopf
```

```
LR-FolderCraft — r13.0.4 (2026-08-23) - build 2026-08-23    <- TUI-Kopf
```

```
2026-08-22 16:26:31 | INFO | Revision r13.0.4 (2026-08-23) | version 5.0.0 | build date 2026-08-23
```

```json
{"event": "run-start", "tool_version": "1.0.0", ...}
```

## Eine Version veröffentlichen

1. `__version__`, `__build_date__` und bei einer MAJOR-Erhöhung `__codename__`
   in `src/lrfoldercraft/version.py` aktualisieren.
2. `version` in `pyproject.toml` angleichen.
3. Einen Abschnitt in `CHANGELOG.md` ergänzen.
4. Die Badges und die `**Revision …**`-Zeile am Kopf jedes Dokuments in
   `docs/en/` und `docs/de/` aktualisieren.
5. Wurde gegen ein neues Lightroom-Katalogschema verifiziert, dieses in
   `VERIFIED_CATALOG_VERSIONS` ergänzen.
6. Tests laufen lassen: `pytest`.
7. Als `release: rX.Y.Z — <Zusammenfassung>` committen und taggen:

```bash
git tag -a v13.0.4 -m "LR-FolderCraft r13.0.4"
git push origin main --tags
```

Für Schritt 1–2 gibt es eine Konsistenzprüfung in der Testsuite:
`pyproject.toml` und `version.py` dürfen nicht auseinanderlaufen.

## Katalogschema-Kompatibilität

Zwei Konstanten in `version.py` steuern das:

```python
VERIFIED_CATALOG_VERSIONS       = ("18.0.0",)   # gegen einen echten Katalog getestet
SUPPORTED_CATALOG_VERSION_RANGE = (11, 19)      # ohne Übersteuerung akzeptiert
```

- Eine **verifizierte** Version öffnet kommentarlos.
- Eine Version im Bereich, aber nicht verifiziert, öffnet mit einer Warnung.
- Alles außerhalb des Bereichs wird abgelehnt, sofern nicht
  `--allow-unsupported-catalog` angegeben ist.

Adobe ändert das Schema zwischen den Hauptversionen von Lightroom Classic. Die
von diesem Werkzeug genutzten Tabellen (`AgLibraryRootFolder`,
`AgLibraryFolder`, `AgLibraryFile`, `Adobe_images`) sind seit vielen Jahren
stabil, eine neue Version sollte aber verifiziert werden, bevor sie in
`VERIFIED_CATALOG_VERSIONS` aufgenommen wird.

| Katalogschema | Lightroom Classic | Stand |
| --- | --- | --- |
| 18.0.0 | 14.x | verifiziert gegen einen echten Katalog mit 9.452 Dateien |
| 11.x–17.x | 7.x–13.x | sollte funktionieren, öffnet mit Warnung |
| 19.x | 15.x | im Bereich, noch nicht verifiziert |
| < 11 | ≤ 6 / Lightroom 6 | ohne Übersteuerung abgelehnt |
