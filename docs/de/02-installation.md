# Installation

**Revision r13.0.1 · Build-Datum 2026-08-23**

LR-FolderCraft ist ein Python-Paket. Die Installationsskripte legen eine
isolierte virtuelle Umgebung an, sodass am System-Python nichts verändert wird.

## Voraussetzungen

| | |
| --- | --- |
| Python | 3.9 oder neuer, mit `sqlite3` und `venv` |
| Speicherplatz | 5 MB nur Kommandozeile, 60 MB mit TUI, 380 MB mit Qt-Oberfläche |
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
6. **nimmt dieses Verzeichnis in den PATH auf**, indem es eine Zeile an die
   Startdatei anhängt, die Ihre Shell tatsächlich liest (`~/.zshrc` bei zsh,
   `~/.bash_profile` oder `~/.bashrc` bei bash,
   `~/.config/fish/config.fish` bei fish) — sofern sie nicht schon dort steht,
7. ruft `lrfc --version` auf, um die Installation zu belegen.

**Danach ein neues Terminalfenster öffnen.** Eine bereits laufende Shell behält
den PATH, mit dem sie gestartet ist, dort bleibt `lrfc` also unauffindbar. Oder
ohne Neustart nachladen: `source ~/.zshrc`.

Optionen:

| Schalter | Wirkung |
| --- | --- |
| `--no-tui` | nur Kommandozeile, ohne Textual |
| `--with-gui` | zusätzlich PySide6 für `lrfc gui` (rund 100 MB) |
| `--no-gui` | nicht nach der grafischen Oberfläche fragen |
| `--check` | Installation prüfen und Fehlendes nachinstallieren |
| `--recreate` | Umgebung von Grund auf neu bauen |
| `--prefix VERZ` | anderes Installationsverzeichnis |
| `--bin VERZ` | anderes Starterverzeichnis |
| `--no-path` | die Shell-Startdatei nicht anfassen |
| `--uninstall` | Umgebung, Starter und PATH-Zeile entfernen |

Mit `--no-path` gibt das Skript die Zeile nur aus, statt sie selbst zu setzen.

### Was das Installationsskript prüft

Es installiert nicht nur, es verifiziert — und nennt nur Oberflächen, die
tatsächlich funktionieren:

1. sucht ein Python ≥ 3.9 und stellt sicher, dass `venv` und `sqlite3` da sind,
2. verwendet eine vorhandene Umgebung weiter oder legt eine an (`--recreate`
   erzwingt einen Neuaufbau),
3. installiert LR-FolderCraft und **aktualisiert** dabei alles bereits
   Vorhandene, das veraltet ist,
4. installiert jede gewünschte Oberfläche und **importiert sie anschließend**,
   um zu belegen, dass sie läuft,
5. merkt sich, welche Oberflächen zu dieser Installation gehören, damit eine
   spätere Reparatur „nie gewollt" von „kaputt" unterscheiden kann,
6. nimmt den Starter in den PATH auf,
7. listet die wirklich verfügbaren Oberflächen auf und gibt für fehlende den
   genauen Befehl zum Nachrüsten aus.

Scheitert ein Bestandteil, nennt das Skript welcher, warum, und was von Hand zu
tun ist — statt Erfolg zu melden und Sie es bei `lrfc gui` herausfinden zu
lassen.

### Eine Installation reparieren

```bash
./install/install-macos.sh --check
```

Prüft die Umgebung und installiert nach, was fehlt, ohne Funktionierendes
anzufassen. Es meldet auch, wenn von einem Bestandteil eine neuere Fassung
vorliegt; ohne `--check` erneut ausführen, um sie zu übernehmen.

Das Skript erneut auszuführen ist immer unbedenklich: Es verwendet die
Umgebung weiter, hebt Veraltetes an und dupliziert nichts.

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

Optionen: `-NoTui`, `-WithGui`, `-NoGui`, `-Check`, `-Recreate`, `-Prefix VERZ`,
`-BinDir VERZ`, `-Uninstall`. Es prüft und repariert genauso wie das
macOS-Skript.

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
# nur Kommandozeile -- ganz ohne Abhängigkeiten
python3 -m pip install --user 'git+https://gitlab.com/andy-freund/LR-FolderCraft.git'
# mit Textoberfläche
python3 -m pip install --user 'git+https://gitlab.com/andy-freund/LR-FolderCraft.git#egg=lr-foldercraft[tui]'
# mit grafischer Oberfläche
python3 -m pip install --user 'git+https://gitlab.com/andy-freund/LR-FolderCraft.git#egg=lr-foldercraft[gui]'
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

Die Deinstallation nimmt auch ihre eigene PATH-Zeile zurück und lässt den Rest
Ihrer Startdatei unangetastet.

Kataloge, Fotos, Profile, Logdateien und Backups werden nie entfernt. Das
Konfigurationsverzeichnis gegebenenfalls von Hand löschen.
