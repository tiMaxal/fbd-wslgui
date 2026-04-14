#!/usr/bin/env bash
# fbdwslgui_docmode_capture.sh
#
# Checks WSL dependencies, sets DISPLAY, launches the app in --doc-mode,
# watches for sentinel files, captures screenshots, and writes a README.md.
#
# Run from Windows via:   fbdwslgui_docmode_capture.bat
# Run directly in WSL:    bash scrnshts/fbdwslgui_docmode_capture.sh
#
# Output lands in:  <app-dir>/fbdwslgui_docs_screens/docmode_YYYYMMDD_HHMMSS/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"

echo "[*] FBD GUI doc-mode capture"
echo "    App dir : $APP_DIR"
echo "    Script  : $SCRIPT_DIR"

# ── DISPLAY ───────────────────────────────────────────────────────────────────
if [ -z "${DISPLAY:-}" ]; then
    export DISPLAY=:0
    echo "[*] DISPLAY not set — defaulting to :0"
fi

# Some PyAutoGUI/Xlib stacks fail if XAUTHORITY points to a missing file,
# even when VcXsrv is started with -ac. Ensure a valid, existing path.
if [ -z "${XAUTHORITY:-}" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
fi
if [ ! -f "$XAUTHORITY" ]; then
    mkdir -p "$(dirname "$XAUTHORITY")"
    touch "$XAUTHORITY"
    echo "[*] Created missing Xauthority file at: $XAUTHORITY"
fi

# VcXsrv is X11. Unset WAYLAND_DISPLAY so pyscreeze/scrot don't misdetect Wayland.
if [ -n "${WAYLAND_DISPLAY:-}" ]; then
    echo "[*] Unsetting WAYLAND_DISPLAY (using X11/VcXsrv, not Wayland)"
    unset WAYLAND_DISPLAY
fi

# ── SYSTEM DEPS (apt) ─────────────────────────────────────────────────────────
NEED_APT=()
command -v python3        &>/dev/null || NEED_APT+=(python3)
command -v import         &>/dev/null || NEED_APT+=(imagemagick)
command -v xdotool        &>/dev/null || NEED_APT+=(xdotool)

if [ ${#NEED_APT[@]} -gt 0 ]; then
    echo "[*] Installing system deps: ${NEED_APT[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${NEED_APT[@]}"
fi

# ── PYTHON 'python' ALIAS ─────────────────────────────────────────────────────
# app is launched as 'python3 fbd_wslgui.test.py'; ensure python3 is available
if ! command -v python &>/dev/null; then
    SHIM_DIR="$HOME/.local/bin"
    mkdir -p "$SHIM_DIR"
    if [ ! -f "$SHIM_DIR/python" ]; then
        ln -s "$(command -v python3)" "$SHIM_DIR/python"
        echo "[*] Created python -> python3 symlink at $SHIM_DIR/python"
    fi
    export PATH="$SHIM_DIR:$PATH"
fi

# ── PYTHON DEPS (pip) ─────────────────────────────────────────────────────────
# No extra pip packages needed — capture is done with system ImageMagick.

# ── LAUNCH ────────────────────────────────────────────────────────────────────
echo "[*] Starting capture (cwd: $APP_DIR) ..."
cd "$APP_DIR"
export FBD_APP_DIR="$APP_DIR"

THEME="${1:-light}"

# Call the watcher Python script, which launches the GUI and manages screenshots
python3 scrnshts/fbdwslgui_docmode_capture_watcher.py "$THEME"
