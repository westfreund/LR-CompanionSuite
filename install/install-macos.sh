#!/usr/bin/env bash
#
# LR-FolderCraft -- installer for macOS and Linux
#
# Creates a self contained virtual environment, installs LR-FolderCraft with
# the TUI extra, and puts an `lrfc` launcher on your PATH. Nothing outside the
# install prefix and the launcher directory is touched.
#
# Usage:
#   ./install/install-macos.sh                 # install into ~/.local/share
#   ./install/install-macos.sh --no-tui        # skip the Textual dependency
#   ./install/install-macos.sh --with-gui      # add the Qt graphical interface
#   ./install/install-macos.sh --no-path       # do not touch the shell startup file
#   ./install/install-macos.sh --prefix DIR    # choose the install location
#   ./install/install-macos.sh --bin DIR       # choose the launcher location
#   ./install/install-macos.sh --uninstall
#
# SPDX-License-Identifier: MIT OR GPL-3.0-or-later

set -euo pipefail

APP_NAME="LR-FolderCraft"
MIN_PY_MAJOR=3
MIN_PY_MINOR=9

PREFIX="${LRFC_PREFIX:-$HOME/.local/share/lr-foldercraft}"
BIN_DIR="${LRFC_BIN:-$HOME/.local/bin}"
WITH_TUI=1
WITH_GUI=0
UNINSTALL=0
EDIT_PATH=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"


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
        --no-path)   EDIT_PATH=0; shift ;;
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
    rm -f "$BIN_DIR/lrfc" "$BIN_DIR/lr-foldercraft"
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
        "$HOME/Library/Application Support/LR-FolderCraft"
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
    which LR-FolderCraft needs to read Lightroom catalogs."

# -- 2. create the virtual environment -----------------------------------------

info "Creating the virtual environment in $PREFIX"
mkdir -p "$PREFIX"
if [ -d "$PREFIX/venv" ]; then
    warn "An existing installation was found and will be replaced."
    rm -rf "$PREFIX/venv"
fi
"$PYTHON" -m venv "$PREFIX/venv"
VENV_PY="$PREFIX/venv/bin/python"

info "Updating pip"
"$VENV_PY" -m pip install --quiet --upgrade pip setuptools wheel

# -- 3. install ------------------------------------------------------------------

EXTRAS=""
if [ "$WITH_TUI" -eq 1 ] && [ "$WITH_GUI" -eq 1 ]; then
    EXTRAS="[tui,gui]"; info "Installing $APP_NAME with the text and graphical interfaces"
elif [ "$WITH_GUI" -eq 1 ]; then
    EXTRAS="[gui]";     info "Installing $APP_NAME with the graphical interface"
elif [ "$WITH_TUI" -eq 1 ]; then
    EXTRAS="[tui]";     info "Installing $APP_NAME with the TUI"
else
    info "Installing $APP_NAME (command line only)"
fi
if [ "$WITH_GUI" -eq 1 ]; then
    info "PySide6 is about 100 MB -- this takes a moment"
fi
"$VENV_PY" -m pip install --quiet "$PROJECT_DIR$EXTRAS"

# -- 4. launcher -------------------------------------------------------------------

info "Installing the launcher in $BIN_DIR"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/lrfc" <<LAUNCHER
#!/usr/bin/env bash
# Generated by the $APP_NAME installer.
exec "$PREFIX/venv/bin/lrfc" "\$@"
LAUNCHER
chmod +x "$BIN_DIR/lrfc"
ln -sf "$BIN_DIR/lrfc" "$BIN_DIR/lr-foldercraft"

# -- 5. verify -----------------------------------------------------------------------

info "Verifying the installation"
"$PREFIX/venv/bin/lrfc" --version || die "the installed command did not start"

echo
info "$APP_NAME is installed."
printf '    Command      : %s\n' "$BIN_DIR/lrfc"
printf '    Environment  : %s\n' "$PREFIX/venv"
printf '    Logs         : %s\n' "$HOME/Library/Logs/LR-FolderCraft"
echo
ensure_on_path
cat <<'NEXT'
Next steps:

    lrfc info /path/to/your.lrcat          # inspect a catalog, read only
    lrfc presets                           # see the ready made structures
    lrfc plan /path/to/your.lrcat -s day   # see what would happen
    lrfc tui                               # interactive text interface
    lrfc gui                               # graphical interface (needs --with-gui)

Quit Lightroom Classic before running 'lrfc apply'.
NEXT
