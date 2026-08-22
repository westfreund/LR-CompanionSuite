# Installation

**Revision r1.0.6 · Build date 2026-08-22**

LR-FolderCraft is a Python package. The installers create an isolated virtual
environment so nothing is added to your system Python.

## Requirements

| | |
| --- | --- |
| Python | 3.9 or newer, with `sqlite3` and `venv` |
| Disk space | about 60 MB for the environment (5 MB without the TUI) |
| Lightroom Classic | must be **closed** while the tool runs |
| Catalog schema | 11.x–19.x, verified against 18.0.0 (Lightroom Classic 14) |

macOS 12 and later already ship a suitable Python at `/usr/bin/python3`.

## macOS

```bash
git clone https://gitlab.com/andy-freund/LR-FolderCraft.git
cd LR-FolderCraft
./install/install-macos.sh
```

The installer:

1. finds the newest Python ≥ 3.9 (`python3.13` … `python3`),
2. checks that `venv` and `sqlite3` are available,
3. creates `~/.local/share/lr-foldercraft/venv`,
4. installs LR-FolderCraft with the TUI extra,
5. writes launchers `lrfc` and `lr-foldercraft` into `~/.local/bin`,
6. runs `lrfc --version` to prove the installation works.

Options:

| Flag | Effect |
| --- | --- |
| `--no-tui` | command line only, no Textual dependency |
| `--prefix DIR` | install somewhere else |
| `--bin DIR` | put the launcher somewhere else |
| `--uninstall` | remove the environment and the launchers |

If `~/.local/bin` is not on your `PATH`, the installer tells you and prints the
line to add to `~/.zshrc`.

### No Python?

```bash
xcode-select --install       # Apple's command line tools, includes Python 3
# or
brew install python@3.12
```

## Windows

```powershell
git clone https://gitlab.com/andy-freund/LR-FolderCraft.git
cd LR-FolderCraft
powershell -ExecutionPolicy Bypass -File .\install\install-windows.ps1
```

The `-ExecutionPolicy Bypass` applies to this one invocation only; it does not
change your system policy.

The installer creates `%LOCALAPPDATA%\LR-FolderCraft\venv`, writes `lrfc.cmd`
into `%LOCALAPPDATA%\Programs\bin` and adds that directory to your **user**
PATH (not the system PATH). **Open a new terminal window afterwards** so the
PATH change takes effect.

Options: `-NoTui`, `-Prefix DIR`, `-BinDir DIR`, `-Uninstall`.

### No Python?

Install from [python.org](https://www.python.org/downloads/windows/) or the
Microsoft Store, and tick **“Add python.exe to PATH”** during setup.

## Linux

Use the macOS script; it is the same file:

```bash
./install/install-linux.sh
```

On Debian and Ubuntu you may need `sudo apt install python3-venv` first.

## Installing with pip instead

```bash
python3 -m pip install --user 'git+https://gitlab.com/andy-freund/LR-FolderCraft.git#egg=lr-foldercraft[tui]'
```

Or from a clone, for development:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
pytest
```

## Verifying

```bash
lrfc --version
lrfc presets
lrfc info /path/to/some.lrcat
```

`lrfc info` only reads. It is the safe way to confirm that the tool can open
your catalog before you plan anything.

## Where things are stored

| | macOS | Windows | Linux |
| --- | --- | --- | --- |
| Profiles | `~/Library/Application Support/LR-FolderCraft` | `%APPDATA%\LR-FolderCraft` | `~/.config/lr-foldercraft` |
| Logs | `~/Library/Logs/LR-FolderCraft` | `%LOCALAPPDATA%\LR-FolderCraft\logs` | `~/.local/state/lr-foldercraft/logs` |
| Backups & journals | `<profiles>/backups` | `<profiles>\backups` | `<profiles>/backups` |
| Reports | `<profiles>/reports` | `<profiles>\reports` | `<profiles>/reports` |

Override any of them with the environment variables `LRFC_CONFIG_DIR`,
`LRFC_LOG_DIR`, `LRFC_BACKUP_DIR` and `LRFC_REPORT_DIR`.

Put backups on a **different drive** from the catalog if you can:

```bash
export LRFC_BACKUP_DIR=/Volumes/Backup/lrfc
```

## Uninstalling

```bash
./install/install-macos.sh --uninstall
# Windows: powershell -File .\install\install-windows.ps1 -Uninstall
```

Your catalogs, photos, profiles, logs and backups are never removed by the
uninstaller. Delete the configuration directory by hand if you want it gone.
