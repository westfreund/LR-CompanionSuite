# Installation

**Revision r2.0.1 · Build-Datum 2026-08-22**

LR-FolderCraft ist ein Python-Paket. Die Installationsskripte legen eine
isolierte virtuelle Umgebung an, sodass am System-Python nichts verändert wird.

## Voraussetzungen

| | |
| --- | --- |
| Python | 3.9 oder neuer, mit `sqlite3` und `venv` |
| Speicherplatz | rund 60 MB für die Umgebung (5 MB ohne TUI) |
| Lightroom Classic | muss **geschlossen** sein, während das Werkzeug läuft |
| Katalogschema | 11.x–19.x, verifiziert gegen 18.0.0 (Lightroom Classic 14) |

macOS 12 und neuer bringen unter `/usr/bin/python3` bereits ein passendes
Python mit.

## macOS

```bash
git clone https://gitlab.com/andy-freund/LR-FolderCraft.git
cd LR-FolderCraft
./install/install-macos.sh
```

Das Skript:

1. sucht das neueste Python ≥ 3.9 (`python3.13` … `python3`),
2. prüft, ob `venv` und `sqlite3` vorhanden sind,
3. legt `~/.local/share/lr-foldercraft/venv` an,
4. installiert LR-FolderCraft samt TUI,
5. schreibt die Starter `lrfc` und `lr-foldercraft` nach `~/.local/bin`,
6. ruft `lrfc --version` auf, um die Installation zu belegen.

Optionen:

| Schalter | Wirkung |
| --- | --- |
| `--no-tui` | nur Kommandozeile, ohne Textual |
| `--prefix VERZ` | anderes Installationsverzeichnis |
| `--bin VERZ` | anderes Starterverzeichnis |
| `--uninstall` | Umgebung und Starter entfernen |

Liegt `~/.local/bin` nicht im `PATH`, weist das Skript darauf hin und nennt die
Zeile für `~/.zshrc`.

### Kein Python vorhanden?

```bash
xcode-select --install       # Apples Kommandozeilenwerkzeuge, enthält Python 3
# oder
brew install python@3.12
```

## Windows

```powershell
git clone https://gitlab.com/andy-freund/LR-FolderCraft.git
cd LR-FolderCraft
powershell -ExecutionPolicy Bypass -File .\install\install-windows.ps1
```

`-ExecutionPolicy Bypass` gilt nur für diesen einen Aufruf und ändert die
Systemrichtlinie nicht.

Das Skript legt `%LOCALAPPDATA%\LR-FolderCraft\venv` an, schreibt `lrfc.cmd`
nach `%LOCALAPPDATA%\Programs\bin` und ergänzt dieses Verzeichnis im
**Benutzer**-PATH (nicht im System-PATH). **Danach ein neues Terminalfenster
öffnen**, damit die PATH-Änderung wirkt.

Optionen: `-NoTui`, `-Prefix VERZ`, `-BinDir VERZ`, `-Uninstall`.

### Kein Python vorhanden?

Von [python.org](https://www.python.org/downloads/windows/) oder aus dem
Microsoft Store installieren und bei der Einrichtung **„Add python.exe to
PATH“** ankreuzen.

## Linux

Dasselbe Skript wie unter macOS, es ist dieselbe Datei:

```bash
./install/install-linux.sh
```

Unter Debian und Ubuntu ist unter Umständen vorher
`sudo apt install python3-venv` nötig.

## Installation mit pip

```bash
python3 -m pip install --user 'git+https://gitlab.com/andy-freund/LR-FolderCraft.git#egg=lr-foldercraft[tui]'
```

Oder aus einem Klon heraus, für die Entwicklung:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
pytest
```

## Überprüfen

```bash
lrfc --version
lrfc presets
lrfc info /pfad/zu/einem.lrcat
```

`lrfc info` liest ausschließlich. Es ist der sichere Weg, vor jeder Planung zu
bestätigen, dass das Werkzeug den Katalog öffnen kann.

## Wo was abgelegt wird

| | macOS | Windows | Linux |
| --- | --- | --- | --- |
| Profile | `~/Library/Application Support/LR-FolderCraft` | `%APPDATA%\LR-FolderCraft` | `~/.config/lr-foldercraft` |
| Logdateien | `~/Library/Logs/LR-FolderCraft` | `%LOCALAPPDATA%\LR-FolderCraft\logs` | `~/.local/state/lr-foldercraft/logs` |
| Backups & Journale | `<Profile>/backups` | `<Profile>\backups` | `<Profile>/backups` |
| Berichte | `<Profile>/reports` | `<Profile>\reports` | `<Profile>/reports` |

Überschreibbar über die Umgebungsvariablen `LRFC_CONFIG_DIR`, `LRFC_LOG_DIR`,
`LRFC_BACKUP_DIR` und `LRFC_REPORT_DIR`.

Backups nach Möglichkeit auf einen **anderen Datenträger** als den Katalog
legen:

```bash
export LRFC_BACKUP_DIR=/Volumes/Backup/lrfc
```

## Deinstallation

```bash
./install/install-macos.sh --uninstall
# Windows: powershell -File .\install\install-windows.ps1 -Uninstall
```

Kataloge, Fotos, Profile, Logdateien und Backups werden dabei nie entfernt. Das
Konfigurationsverzeichnis gegebenenfalls von Hand löschen.
