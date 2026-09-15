# Installation

**Revision r20.0.0 · Build date 2026-09-15**

LR-FolderCraft is a Python package. The installers create an isolated virtual
environment so nothing is added to your system Python.

## Requirements

| | |
| --- | --- |
| Python | 3.9 or newer, with `sqlite3` and `venv` |
| Disk space | 5 MB command line only, 60 MB with the TUI, 380 MB with the Qt interface |
| Lightroom Classic | must be **closed** while the tool runs |
| Catalog schema | 11.x–19.x, verified against 18.0.0 (Lightroom Classic 14) |

macOS 12 and later already ship a suitable Python at `/usr/bin/python3`.

## macOS

```bash
git clone https://gitlab.com/andy-freund/LR-CompanionSuite.git
cd LR-FolderCraft
./install/install-macos.sh
```

The installer:

1. finds the newest Python ≥ 3.9 (`python3.13` … `python3`),
2. checks that `venv` and `sqlite3` are available,
3. creates `~/.local/share/lr-companion-suite/venv`,
4. installs LR-FolderCraft with the TUI extra,
5. writes launchers `lrcs`, `lrfc` and `lrms` into `~/.local/bin`,
6. **puts that directory on your PATH** by appending one line to the startup
   file your shell actually reads (`~/.zshrc` for zsh, `~/.bash_profile` or
   `~/.bashrc` for bash, `~/.config/fish/config.fish` for fish), unless it is
   already there,
7. runs `lrfc --version` to prove the installation works.

**Open a new terminal window afterwards.** A shell that is already running
keeps the PATH it started with, so `lrfc` stays "command not found" in it. Or
reload without restarting: `source ~/.zshrc`.

Options:

| Flag | Effect |
| --- | --- |
| `--no-tui` | command line only, no Textual dependency |
| `--with-gui` | also install PySide6 for `lrfc gui` (about 100 MB) |
| `--no-gui` | never ask about the graphical interface |
| `--check` | verify an installation and repair what is missing |
| `--recreate` | build the environment from scratch |
| `--prefix DIR` | install somewhere else |
| `--bin DIR` | put the launcher somewhere else |
| `--no-path` | do not touch the shell startup file |
| `--uninstall` | remove the environment, the launchers and the PATH line |

With `--no-path` the installer only prints the line for you to add yourself.

### What the installer checks

It does not just install; it verifies, and it only tells you about interfaces
that actually work:

1. finds a Python ≥ 3.9 and confirms `venv` and `sqlite3` are there,
2. reuses an existing environment, or creates one (`--recreate` forces a fresh
   build),
3. installs LR-FolderCraft, **upgrading** anything already present that has
   gone out of date,
4. installs each wanted interface and then **imports it** to prove it works,
5. records which interfaces this installation wants, so a later repair knows
   the difference between "never asked for" and "broken",
6. puts the launcher on your PATH,
7. lists the interfaces that are genuinely available, and for anything missing
   prints the exact command to add it.

If a component fails, the installer says which one, why, and what to run by
hand — instead of reporting success and letting you find out at `lrfc gui`.

### Repairing an installation

```bash
./install/install-macos.sh --check
```

Verifies the environment and reinstalls whatever is missing, without touching
anything that works. It also says when a newer version of a component is
available; re-run without `--check` to take it.

Re-running the installer normally is always safe: it reuses the environment,
updates what has aged, and does not duplicate anything.

### No Python?

```bash
xcode-select --install       # Apple's command line tools, includes Python 3
# or
brew install python@3.12
```

## Windows

```powershell
git clone https://gitlab.com/andy-freund/LR-CompanionSuite.git
cd LR-FolderCraft
powershell -ExecutionPolicy Bypass -File .\install\install-windows.ps1
```

The `-ExecutionPolicy Bypass` applies to this one invocation only; it does not
change your system policy.

The installer creates `%LOCALAPPDATA%\LR-CompanionSuite\venv`, writes `lrfc.cmd`
into `%LOCALAPPDATA%\Programs\bin` and adds that directory to your **user**
PATH (not the system PATH). **Open a new terminal window afterwards** so the
PATH change takes effect.

Options: `-NoTui`, `-WithGui`, `-NoGui`, `-Check`, `-Recreate`, `-Prefix DIR`,
`-BinDir DIR`, `-Uninstall`. It checks and repairs the same way the macOS
script does.

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
# command line only -- no dependencies at all
python3 -m pip install --user 'git+https://gitlab.com/andy-freund/LR-CompanionSuite.git'
# with the text interface
python3 -m pip install --user 'git+https://gitlab.com/andy-freund/LR-CompanionSuite.git#egg=lr-companion-suite[tui]'
# with the graphical interface
python3 -m pip install --user 'git+https://gitlab.com/andy-freund/LR-CompanionSuite.git#egg=lr-companion-suite[gui]'
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
| Profiles | `~/Library/Application Support/LR-CompanionSuite` | `%APPDATA%\LR-CompanionSuite` | `~/.config/lr-companion-suite` |
| Logs | `~/Library/Logs/LR-CompanionSuite` | `%LOCALAPPDATA%\LR-CompanionSuite\logs` | `~/.local/state/lr-companion-suite/logs` |
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

The uninstaller also takes its own PATH line back out, leaving the rest of your
startup file untouched.

Your catalogs, photos, profiles, logs and backups are never removed. Delete the
configuration directory by hand if you want it gone.
