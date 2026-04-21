#!/bin/bash
# FBD GUI Runner Script for WSL
# This script sets up the environment and launches the Python GUI


echo "=== FBD-WSLGUI_RUN.SH START ==="
# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"


# Automatically set DISPLAY for WSL2/WSL1 compatibility
WSL_HOST_IP=$(grep -m 1 nameserver /etc/resolv.conf | awk '{print $2}')
if [ -n "$WSL_HOST_IP" ]; then
    export DISPLAY="$WSL_HOST_IP:0"
    echo "[INFO] DISPLAY set to $DISPLAY (WSL2 mode)"
else
    export DISPLAY=":0"
    echo "[INFO] DISPLAY set to :0 (WSL1 fallback)"
fi

# Check if DISPLAY is accessible
if ! timeout 2 xset q &>/dev/null; then
    echo "ERROR: Cannot connect to X11 server on DISPLAY=$DISPLAY"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Make sure VcXsrv or Xming is running on Windows"
    echo "  2. Check that it was started with '-ac' flag"
    echo "  3. Verify Windows Firewall allows VcXsrv"
    echo "  4. If using WSL2, ensure your X server allows connections from $WSL_HOST_IP"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi


# Auto-install python3 if missing
if ! command -v python3 &> /dev/null; then
    echo "[INFO] python3 not found. Installing python3..."
    sudo apt-get update && sudo apt-get install -y python3
fi


# Auto-install python3-tk if missing
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "[INFO] python3-tk not found. Installing python3-tk..."
    sudo apt-get install -y python3-tk
fi


# Auto-install x11-apps if missing (for xeyes/xclock troubleshooting)
if ! command -v xeyes &> /dev/null; then
    echo "[INFO] x11-apps not found. Installing x11-apps (for X11 test utilities)..."
    sudo apt-get install -y x11-apps
fi

# Check if requests module is available
if ! python3 -c "import requests" 2>/dev/null; then
    echo "WARNING: requests module is not installed"
    echo ""
    echo "Install with: pip3 install requests"
    echo ""
    echo "Continuing anyway (some features may not work)..."
    echo ""
fi


echo "[DEBUG] DISPLAY is $DISPLAY"
env | grep DISPLAY
echo "Starting FBD GUI..."
echo ""

# Run the Python GUI application with unbuffered output
python3 -u fbd_wslgui.py

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "GUI exited with error code: $EXIT_CODE"
    read -p "Press Enter to exit..."
fi

exit $EXIT_CODE
