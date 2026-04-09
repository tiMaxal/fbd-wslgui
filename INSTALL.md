# Installation Guide - FBD Node Manager GUI

## 🐧 Linux-Native Installation

This is a **Linux-native Python application** that runs directly on any Linux distribution.

### Prerequisites

- Python 3.6 or higher
- Linux distribution (Ubuntu, Debian, Fedora, Arch, etc.)

### Step 1: Install Python Dependencies

The app requires only **2 external packages**:

#### Ubuntu / Debian / Mint / Xubuntu:
```bash
sudo apt update
sudo apt install -y python3-tk python3-requests libsqlite3-dev
```

#### Fedora / RHEL / CentOS:
```bash
sudo dnf install -y python3-tkinter python3-requests libsqlite3-dev
```

#### Arch Linux / Manjaro:
```bash
sudo pacman -S tk python-requests sqlite3
```

#### OpenSUSE:
```bash
sudo zypper install python3-tk python3-requests sqlite3-devel
```

### Step 2: Download FBD Binaries

⚠️ **IMPORTANT:** The `fbd` and `fbdctl` binaries are **NOT included** in this repository.

1. Download the latest Linux binaries:
   ```bash
   wget https://fbd.dev/download/fbd-latest-linux-x86_64.zip
   ```

2. Extract the archive:
   ```bash
   unzip fbd-latest-linux-x86_64.zip
   ```

3. Make the binaries executable:
   ```bash
   chmod +x fbd fbdctl
   ```

4. Place them in the same directory as `fbd_wslgui.py` or update the FBD path in Settings

### Step 3: Download pool miner

⚠ **IMPORTANT:** The `pool` binary is **NOT included** in this repository.

1. Download the Linux binary and make it executable:
   ```bash
   wget https://l.woodburn.au/miner
   chmod +x miner
   ```

2. Place the binary in the same directory as fbd_wslgui.py


### Step 4: Run the Application

```bash
python3 fbd_wslgui.py
```

The app will:
- ✅ Auto-check for missing dependencies
- ✅ Offer to install missing packages (with sudo)
- ✅ Launch the GUI if all dependencies are satisfied

---

## 🪟 Windows (via WSL) Installation

For Windows users who want to run this via Windows Subsystem for Linux:

### Step 1: Install WSL

```powershell
# In PowerShell (Run as Administrator)
wsl --install
```

Restart your computer after installation.

### Step 2: Inside WSL, Install Dependencies

```bash
# Update package list
sudo apt update

# Install Python and dependencies
sudo apt install -y python3 python3-tk python3-requests

# Download FBD binaries
wget https://fbd.dev/download/fbd-latest-linux-x86_64.zip
unzip fbd-latest-linux-x86_64.zip
chmod +x fbd fbdctl

# Download pool
wget https://l.woodburn.au/miner
chmod +x miner
```

### Step 3: Launch Options

**Option A - Easy (Windows launcher):**
```
Double-click: fbd-wslgui_launch.bat
```
This handles X11 server setup automatically.

**Option B - Manual (WSL terminal):**
```bash
# Requires X11 server running on Windows (VcXsrv)
export DISPLAY=:0
python3 fbd_wslgui.py
```

---

## 🔍 Troubleshooting

### "No module named 'tkinter'" Error

**If you get this error even after installing `python3-tk`:**

1. **Check which Python version you're using:**
   ```bash
   which python3
   python3 --version
   ```

2. **Test if tkinter is available:**
   ```bash
   python3 -c "import tkinter; print('✓ tkinter OK')"
   ```

3. **Possible causes:**
   - **Multiple Python versions**: You may have installed `python3-tk` for system Python but are running a different version (e.g., `python3.9`, `python3.10`, `python3.11`)
   - **Virtual environment**: If you're in a venv, tkinter may not be available (it doesn't install via pip)

4. **Solutions:**
   ```bash
   # Ensure using system Python
   /usr/bin/python3 fbd_wslgui.py
   
   # OR install for specific Python version
   sudo apt install python3.11-tk  # Replace 3.11 with your version
   ```

### "No module named 'requests'" Error

```bash
# Install requests
sudo apt install python3-requests

# OR use pip (if you prefer)
pip3 install requests
```

### Display Issues (WSL/X11)

If the GUI doesn't appear on Windows via WSL:

1. Install VcXsrv (X11 server for Windows)
2. Use the launcher script: `fbd-wslgui_launch.bat`
3. Or manually set DISPLAY:
   ```bash
   export DISPLAY=:0
   python3 fbd_wslgui.py
   ```

---

## 📋 Dependency Overview

### Required (must install):
- `python3-tk` - GUI framework
- `python3-requests` - HTTP library for RPC

### Included with Python (no installation needed):
- `json`, `os`, `sys`, `pathlib`
- `subprocess`, `threading`
- `datetime`, `time`, `uuid`
- `smtplib`, `email`, `base64`

### Minimum Python Version:
- Python 3.6 or higher

---

## 📝 Files Overview

```
fbd-wslgui/
├── fbd_wslgui.py              # Main application
├── fbd_wslgui.test.py         # Test version
├── fbd-wslgui_launch.bat      # Windows/WSL launcher
├── fbd-wslgui_run.sh          # Linux shell wrapper (optional)
├── requirements.txt           # Dependency documentation
├── INSTALL.md                 # This file
├── README.md                  # Feature documentation
├── QUICKSTART.txt             # Quick reference
└── ai-hist_fbd-wslgui/        # Archived docs
```

---

## ✅ Post-Installation

After successful installation:

1. **First Run:** The app will auto-check dependencies
2. **Configure Settings Tab:**
   - Set FBD binary path
   - Configure RPC settings (auto-detected by network)
3. **Start Mining:**
   - Configure miner address
   - Set thread count
   - Enable/disable mining as needed

For detailed usage, see [README.md](README.md)
