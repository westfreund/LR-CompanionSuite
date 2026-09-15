#!/usr/bin/env bash
#
# LR-CompanionSuite -- installer for macOS and Linux
#
# Creates a self contained virtual environment, installs LR-CompanionSuite with
# the TUI extra, and puts `lrcs`, `lrfc` and `lrms` on your PATH. Nothing outside the
# install prefix and the launcher directory is touched.
#
# Usage:
#   ./install/install-macos.sh                 # install into ~/.local/share
#   ./install/install-macos.sh --no-tui        # skip the Textual dependency
#   ./install/install-macos.sh --with-gui      # add the Qt graphical interface
#   ./install/install-macos.sh --no-gui        # never ask about the Qt interface
#   ./install/install-macos.sh --no-path       # do not touch the shell startup file
#   ./install/install-macos.sh --check         # verify an installation and repair it
#   ./install/install-macos.sh --recreate      # build the environment from scratch
#   ./install/install-macos.sh --prefix DIR    # choose the install location
#   ./install/install-macos.sh --bin DIR       # choose the launcher location
#   ./install/install-macos.sh --uninstall
#
# SPDX-License-Identifier: MIT OR GPL-3.0-or-later

set -euo pipefail

APP_NAME="LR-CompanionSuite"
MIN_PY_MAJOR=3
MIN_PY_MINOR=9

PREFIX="${LRFC_PREFIX:-$HOME/.local/share/lr-companion-suite}"
BIN_DIR="${LRFC_BIN:-$HOME/.local/bin}"
WITH_TUI=1
WITH_GUI=-1          # -1 = ask when interactive, 0 = no, 1 = yes
UNINSTALL=0
EDIT_PATH=1
RECREATE=0
CHECK_ONLY=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"


# -- components ----------------------------------------------------------------
#
# Each optional interface is one importable module and one pip requirement.
# Everything below drives off this table, so a component can never be installed
# without being verified, or advertised without being installed.

component_module() {
    case "$1" in
        tui) printf 'textual' ;;
        gui) printf 'PySide6.QtWidgets' ;;
    esac
}

component_requirement() {
    case "$1" in
        tui) printf 'textual>=0.47' ;;
        gui) printf 'PySide6-Essentials>=6.5' ;;
    esac
}

component_command() {
    case "$1" in
        tui) printf 'lrfc tui' ;;
        gui) printf 'lrfc gui' ;;
    esac
}

#: True when the component's module actually imports in the installed venv.
component_works() {
    "$VENV_PY" -c "import $(component_module "$1")" >/dev/null 2>&1
}

#: Version of a component's distribution, or empty when it is absent.
component_version() {
    "$VENV_PY" - "$1" <<'PY' 2>/dev/null
import sys
try:
    from importlib.metadata import version
except ImportError:  # pragma: no cover - Python < 3.8
    sys.exit(0)
name = {"tui": "textual", "gui": "PySide6-Essentials"}.get(sys.argv[1])
try:
    print(version(name))
except Exception:
    pass
PY
}

#: Install or update a component, then confirm it imports. Reporting a
#: successful installation of something that cannot be imported is worse than
#: reporting nothing at all.
#:
#: A present but out-of-date module counts as work to do: half the reason to
#: re-run an installer is to refresh what has aged. Only --check leaves a
#: working component alone, and even then it says when a newer one exists.
install_component() {
    local name="$1" before after
    before="$(component_version "$name")"

    if component_works "$name" && [ "$CHECK_ONLY" -eq 1 ]; then
        info "$name: working (version ${before:-?})"
        if "$VENV_PY" -m pip list --outdated 2>/dev/null \
             | grep -qi "^$(component_module "$name" | cut -d. -f1) "; then
            warn "$name: a newer version is available -- re-run without --check to update"
        fi
        return 0
    fi

    if [ -n "$before" ]; then
        info "$name: updating $(component_requirement "$name") (have $before)"
    else
        info "$name: installing $(component_requirement "$name")"
    fi
    if ! "$VENV_PY" -m pip install --quiet --upgrade "$(component_requirement "$name")"; then
        warn "$name: installation failed"
        return 1
    fi
    if ! component_works "$name"; then
        warn "$name: installed but $(component_module "$name") still does not import"
        return 1
    fi
    after="$(component_version "$name")"
    if [ -n "$before" ] && [ "$before" != "$after" ]; then
        info "$name: updated $before -> $after"
    elif [ -n "$before" ]; then
        info "$name: already up to date ($after)"
    else
        info "$name: installed and verified ($after)"
    fi
    return 0
}

#: File remembering which optional components this installation wants. Without
#: it a repair run cannot tell "the GUI was never asked for" from "the GUI was
#: installed and is now broken" -- both simply fail to import.
components_file() { printf '%s/components' "$PREFIX"; }

record_components() {
    : > "$(components_file)"
    [ "$WITH_TUI" -eq 1 ] && printf 'tui\n' >> "$(components_file)"
    [ "$WITH_GUI" -eq 1 ] && printf 'gui\n' >> "$(components_file)"
    return 0
}

wanted_previously() {
    [ -f "$(components_file)" ] && grep -qx "$1" "$(components_file)"
}

#: Ask about the graphical interface when nobody said either way and there is
#: someone to ask. Discovering --with-gui from a help text is not a plan.
resolve_gui_choice() {
    [ "$WITH_GUI" -ge 0 ] && return 0
    if [ ! -t 0 ]; then
        WITH_GUI=0
        return 0
    fi
    printf '\n'
    printf 'Also install the graphical interface (lrfc gui)?\n'
    printf 'It needs PySide6, about 100 MB to download. [y/N] '
    local answer
    read -r answer || answer=""
    case "$answer" in
        [yYjJ]*) WITH_GUI=1 ;;
        *)       WITH_GUI=0 ;;
    esac
}


# -- PATH ----------------------------------------------------------------------

#: Startup file the user's login shell actually reads for interactive sessions.
shell_startup_file() {
    case "$(basename "${SHELL:-/bin/sh}")" in
        zsh)  printf '%s' "$HOME/.zshrc" ;;
        bash) if [ -f "$HOME/.bash_profile" ]; then
                  printf '%s' "$HOME/.bash_profile"
              else
                  printf '%s' "$HOME/.bashrc"
              fi ;;
        fish) printf '%s' "$HOME/.config/fish/config.fish" ;;
        *)    printf '%s' "$HOME/.profile" ;;
    esac
}

# An installation that reports success but leaves an un-runnable command is not
# finished. macOS in particular does not put ~/.local/bin on PATH, so without
# this the launcher we just wrote is invisible.
ensure_on_path() {
    case ":$PATH:" in
        *":$BIN_DIR:"*)
            info "$BIN_DIR is already on your PATH."
            return 0 ;;
    esac

    local rc line
    rc="$(shell_startup_file)"
    if [ "$(basename "${SHELL:-/bin/sh}")" = "fish" ]; then
        line="set -gx PATH \"$BIN_DIR\" \$PATH"
    else
        line="export PATH=\"$BIN_DIR:\$PATH\""
    fi

    if [ "$EDIT_PATH" -eq 0 ]; then
        warn "$BIN_DIR is not on your PATH. Add this line to $rc yourself:"
        printf '\n    %s\n\n' "$line"
        return 0
    fi

    if [ -f "$rc" ] && grep -Fq "$BIN_DIR" "$rc"; then
        info "$rc already mentions $BIN_DIR -- open a new terminal window."
        return 0
    fi

    mkdir -p "$(dirname "$rc")"
    {
        printf '\n# Added by the %s installer\n' "$APP_NAME"
        printf '%s\n' "$line"
    } >> "$rc"
    info "Added $BIN_DIR to your PATH in $rc"
    warn "Open a new terminal window, or run:  source $rc"
}

info()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()   { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --no-tui)    WITH_TUI=0; shift ;;
        --with-gui)  WITH_GUI=1; shift ;;
        --no-gui)    WITH_GUI=0; shift ;;
        --no-path)   EDIT_PATH=0; shift ;;
        --recreate)  RECREATE=1; shift ;;
        --check)     CHECK_ONLY=1; shift ;;
        --prefix)    PREFIX="${2:?--prefix needs a directory}"; shift 2 ;;
        --bin)       BIN_DIR="${2:?--bin needs a directory}"; shift 2 ;;
        --uninstall) UNINSTALL=1; shift ;;
        -h|--help)   sed -n '2,20p' "$0"; exit 0 ;;
        *)           die "unknown option: $1" ;;
    esac
done

if [ "$UNINSTALL" -eq 1 ]; then
    info "Removing $APP_NAME"
    rm -rf "$PREFIX"
    rm -f "$BIN_DIR/lrcs" "$BIN_DIR/lrfc" "$BIN_DIR/lrms" "$BIN_DIR/lr-companion-suite"
    rc="$(shell_startup_file)"
    if [ -f "$rc" ] && grep -Fq "Added by the $APP_NAME installer" "$rc"; then
        # Remove the marker comment and the line after it, nothing else.
        tmp="$(mktemp)"
        awk -v marker="# Added by the $APP_NAME installer" '
            $0 == marker { skip = 2; next }
            skip > 0     { skip--; next }
            { print }
        ' "$rc" > "$tmp" && mv "$tmp" "$rc"
        info "Removed the PATH line from $rc"
    fi
    info "Removed. Your catalogs, photos, logs and profiles were not touched."
    printf '    Config and profiles remain in: %s\n' \
        "$HOME/Library/Application Support/LR-CompanionSuite"
    exit 0
fi

# -- 1. find a suitable Python -------------------------------------------------

find_python() {
    local candidate
    for candidate in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= ($MIN_PY_MAJOR, $MIN_PY_MINOR) else 1)" 2>/dev/null; then
                printf '%s' "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

info "Looking for Python >= $MIN_PY_MAJOR.$MIN_PY_MINOR"
PYTHON="$(find_python)" || die "no Python $MIN_PY_MAJOR.$MIN_PY_MINOR or newer found.
    macOS: install the Xcode command line tools with 'xcode-select --install',
           or run 'brew install python@3.12'.
    Linux: install your distribution's python3 and python3-venv packages."
info "Using $("$PYTHON" -c 'import sys; print(sys.executable)') ($("$PYTHON" -V 2>&1))"

"$PYTHON" -c "import venv" 2>/dev/null || die "the venv module is missing.
    On Debian/Ubuntu install it with: sudo apt install python3-venv"
"$PYTHON" -c "import sqlite3" 2>/dev/null || die "this Python has no sqlite3 support,
    which LR-CompanionSuite needs to read Lightroom catalogs."

# -- 2. create the virtual environment -----------------------------------------

mkdir -p "$PREFIX"
VENV_PY="$PREFIX/venv/bin/python"

if [ -d "$PREFIX/venv" ] && [ "$RECREATE" -eq 1 ]; then
    warn "Rebuilding the existing environment from scratch."
    rm -rf "$PREFIX/venv"
fi

if [ -x "$VENV_PY" ]; then
    # Reusing the environment is what makes "add the graphical interface later"
    # a ten second job instead of a full reinstall.
    info "Reusing the environment in $PREFIX/venv"
else
    info "Creating the virtual environment in $PREFIX"
    "$PYTHON" -m venv "$PREFIX/venv"
fi

if [ "$CHECK_ONLY" -eq 0 ]; then
    info "Updating pip"
    "$VENV_PY" -m pip install --quiet --upgrade pip setuptools wheel
fi

# -- 3. install ------------------------------------------------------------------

if [ "$CHECK_ONLY" -eq 1 ]; then
    info "Checking the existing installation"
    if [ ! -x "$VENV_PY" ]; then
        die "no installation found in $PREFIX -- run without --check first"
    fi
    # Repair exactly the set this installation was set up with. Asking which
    # modules import right now would treat a broken component as an absent one.
    if [ -f "$(components_file)" ]; then
        wanted_previously tui && WITH_TUI=1 || WITH_TUI=0
        [ "$WITH_GUI" -lt 0 ] && { wanted_previously gui && WITH_GUI=1 || WITH_GUI=0; }
    else
        warn "No record of what was installed; checking what is present."
        component_works tui || WITH_TUI=0
        [ "$WITH_GUI" -lt 0 ] && { component_works gui && WITH_GUI=1 || WITH_GUI=0; }
    fi
else
    resolve_gui_choice
    info "Installing $APP_NAME"
    if [ "$WITH_GUI" -eq 1 ]; then
        info "PySide6 is about 100 MB -- this takes a moment"
    fi
    # --upgrade so that re-running the installer also refreshes anything that
    # has gone out of date, which is half of what people re-run it for.
    "$VENV_PY" -m pip install --quiet --upgrade "$PROJECT_DIR"
fi

# Every wanted component is installed and then verified; nothing is reported as
# ready that cannot actually be imported.
FAILED=""
[ "$WITH_TUI" -eq 1 ] && { install_component tui || FAILED="$FAILED tui"; }
[ "$WITH_GUI" -eq 1 ] && { install_component gui || FAILED="$FAILED gui"; }
[ "$CHECK_ONLY" -eq 0 ] && record_components

# -- 4. launcher -------------------------------------------------------------------

info "Installing the launcher in $BIN_DIR"
mkdir -p "$BIN_DIR"
# One launcher per tool, plus the suite's own. They all point into the same
# virtual environment; three names cost nothing and save a person from having
# to remember that searching lives inside the folder tool.
for command in lrcs lrfc lrms; do
    cat > "$BIN_DIR/$command" <<LAUNCHER
#!/bin/sh
# Generated by the $APP_NAME installer.
exec "$PREFIX/venv/bin/$command" "\$@"
LAUNCHER
    chmod +x "$BIN_DIR/$command"
done
ln -sf "$BIN_DIR/lrcs" "$BIN_DIR/lr-companion-suite"

# -- 5. verify and report ------------------------------------------------------

info "Verifying the installation"
for command in lrcs lrfc lrms; do
    "$PREFIX/venv/bin/$command" --version >/dev/null || die "$command did not start"
done
"$PREFIX/venv/bin/lrcs" --version

echo
info "$APP_NAME is installed."
printf '    Command      : %s\n' "$BIN_DIR/lrfc"
printf '    Environment  : %s\n' "$PREFIX/venv"
printf '    Logs         : %s\n' "$HOME/Library/Logs/LR-CompanionSuite"
printf '    Interfaces   :'
for name in tui gui; do
    if component_works "$name"; then printf ' %s' "$name"; fi
done
printf ' cli\n'

if [ -n "$FAILED" ]; then
    echo
    for name in $FAILED; do
        warn "$(component_command "$name") is not available: $(component_module "$name") could not be installed."
        printf '    Try it by hand:  %s -m pip install "%s"\n' \
            "$VENV_PY" "$(component_requirement "$name")"
    done
fi

echo
ensure_on_path

cat <<'NEXT'

Next steps:

    lrfc info /path/to/your.lrcat          # inspect a catalog, read only
    lrfc presets                           # see the ready made structures
    lrfc plan /path/to/your.lrcat -s day   # see what would happen
NEXT
if component_works tui; then
    printf '    lrfc tui                               # interactive text interface\n'
fi
if component_works gui; then
    printf '    lrfc gui                               # graphical interface\n'
else
    printf '\n'
    printf 'The graphical interface is not installed. To add it:\n'
    printf '    %s --with-gui\n' "$0"
fi
cat <<'NEXT'

Quit Lightroom Classic before running 'lrfc apply'.
NEXT
