# 🎯 FBD Node Manager GUI v3.0.0

> **Created by 'voding' [vibe-coding] - copilot+timaxal, April 2026**

A comprehensive graphical interface for managing FBD (Fistbump) nodes, mining, wallets, and name auctions.

## 🐧 Platform Compatibility

**This is a Linux-native Python application** that runs on:
- ✅ **Native Linux** - Run directly with `python3 fbd_wslgui.py`
- ✅ **WSL (Windows Subsystem for Linux)** - Run directly or use wrapper scripts
- ✅ **Windows (via WSL)** - Use included `.bat` launcher scripts for convenience

> 💡 **Note:** The "wslgui" naming reflects its original WSL development environment and community introduction, but the core app is standard cross-platform Python/Tkinter that runs natively on any Linux system.

## 📦 Dependencies

**Only 3 packages needed:**
- `python3-tk` - GUI framework (tkinter)
- `python3-requests` - HTTP library for RPC calls
- `libsqlite3-dev` - SQLite database support (for local data storage)

**All other imports are Python standard library** (json, os, datetime, email, pathlib, base64, etc.)

**Auto-installation:** The app will check for missing dependencies on startup and offer to install them automatically using your system's package manager (apt, dnf, yum, or pacman).

**For detailed installation instructions, see [INSTALL.md](INSTALL.md)**

**Quick install:**
```bash
# Ubuntu/Debian/Xubuntu
sudo apt update && sudo apt install -y python3-tk python3-requests libsqlite3-dev

# Fedora/RHEL/CentOS
sudo dnf install -y python3-tkinter python3-requests libsqlite3-devel

# Arch Linux
sudo pacman -S tk python-requests sqlite3
```

**Minimum Python version:** 3.6+

## ⚡ Quick Start

**Native Linux:**
```bash
python3 fbd_wslgui.py
```
Direct execution - no additional setup needed!

**Windows Users (via WSL):**
```
Double-click: fbd-wslgui_launch.bat
```
The launcher handles WSL invocation and X11 server setup automatically.

**WSL Direct:**
```bash
python3 fbd_wslgui.py
```
(Requires X11 server on Windows - use fbd-wslgui_launch.bat for auto-setup)

**Test Version:**
```
Double-click: fbdwslgui-test_launch.bat
```
Runs the test version (fbd_wslgui.test.py) separately.

## 📦 What's Included

### Core Files
- **fbd_wslgui.py** - Main application (v3.0.0)
- **fbd_wslgui.test.py** - Test version for development
- **fbd_wslgui.3-0-0.py** - Archived stable v3.0.0

### Launchers
- **fbd-wslgui_launch.bat** - Production launcher (auto X11 setup)
- **fbdwslgui-test_launch.bat** - Test version launcher

### Binaries
#### FBD

⚠️ **IMPORTANT:** The `fbd` and `fbdctl` binaries are NOT included in this repository due to file size.
**You must download them separately:**
1. Download the latest Linux binaries: https://fbd.dev/download/fbd-latest-linux-x86_64.zip
2. Extract the zip file: `unzip fbd-latest-linux-x86_64.zip`
3. Place both `fbd` and `fbdctl` in the same directory as `fbd_wslgui.py`
4. Ensure they have execute permissions: `chmod +x fbd fbdctl`
5. Keep them updated by downloading the latest zip regularly

#### Pool miner

⚠️ **IMPORTANT:** The `miner` binary is NOT included in this repository due to file size.
**You must download it separately:**
1. Download the Linux binary: https://l.woodburn.au/miner
2. Make it executable: `chmod +x miner`
3. Place it in the same directory as `fbd_wslgui.py`


📋 **TODO:** Future versions will include automatic binary version checking and download capability.

### Documentation
- **README.md** - This file (feature overview)
- **INSTALL.md** - Complete installation guide with troubleshooting
- **QUICKSTART.txt** - Quick reference guide
- **requirements.txt** - Python dependency documentation
- **ai-hist_fbd-wslgui/** - Archived docs, scripts, and older versions

## ✨ Key Features

### 🖥️ Node Management
- Start/stop FBD node with custom parameters
- Real-time monitoring (block height, peer count)
- Network selection: main, testnet, regtest, simnet
- Index options: transactions, addresses, auctions
- Live log output with auto-scroll
- Auto-restart on crash (optional)

### ⛏️ Mining Configuration
- Toggle mining on/off independently of node
- Set miner address for coinbase rewards
- Configure thread count (0 = auto)
- Launch a pool miner with wallet address, host, and thread count
- Agent name customization
- Node-only mode available (sync without mining)

### 💰 Wallet Operations
- List and create wallets
- Check balances and get addresses
- Send FBC payments
- View transaction history
- Wallet info with balance breakdown
- Multi-wallet support

### 🏆 Name Auctions
- Get comprehensive name information
- Open new name auctions
- Place blind bids with lockup amounts
- Reveal bids after bidding period
- Register won names
- View all owned names
- Track auction status and timing

### 🤖 Auction Automation (Advanced)
- Create automated auction workflows
- Schedule bids with reveal automation
- Email notifications for auction events
- Job monitoring and management
- Batch operations

### ⚙️ Settings & Persistence
- Save/load configurations
- Export/import for backup
- Profile management
- Configurable FBD paths
- RPC host/port customization

## 📖 Usage Guide

### First Time Setup

1. **Launch the GUI:**
   - Windows: Double-click `fbd-wslgui_launch.bat`
   - WSL: `python3 fbd_wslgui.py` (X11 required)

2. **Configure Settings Tab:**
   ```
   FBD Path: ./fbd-latest-linux-x86_64/fbd
   RPC Host: localhost
   RPC Port: (auto-set by network)
   ```
   Click "Save Settings"

3. **Setup Node & Mining:**
   - Network: Select "main" (or testnet for testing)
   - Miner Address: Your FBC wallet address for rewards
   - Miner Threads: 12 (or 0 for auto)
   - Enable Mining: ✓ (or uncheck for node-only)
   - Index Options: Enable as needed

4. **Start Node:**
   - Click "Start Node"
   - Monitor log output
   - Wait for sync to complete

### Wallet Operations

**List Available Wallets:**
```
Wallet Tab → Enter wallet name → List Wallets
```

**Create New Wallet:**
```
Wallet Tab → Create Wallet → Save mnemonic! → OK
```

**Check Balance:**
```
Wallet Tab → Get Wallet Info
```

**Send Payment:**
```
Wallet Tab → Enter address & amount → Send
```

**View Transactions:**
```
Wallet Tab → Load Transactions
```

### Name Auctions

**Check Name Status:**
```
Auctions Tab → Enter name → Get Name Info
```

**Open Auction:**
```
1. Enter name
2. Click "Open Auction"
3. Wait for confirmation in log
```

**Place Bid:**
```
1. Get name info (check state = BIDDING)
2. Enter bid amount (FBC)
3. Enter lockup (>= bid)
4. Click "Place Bid"
```

**Reveal Bid:**
```
1. Wait for REVEAL period
2. Click "Reveal Bid"
3. Confirm in log
```

**Register Name:**
```
1. Wait for auction to close
2. If you won, click "Register"
3. Name transfers to your wallet
```

**View Your Names:**
```
Auctions Tab → Load My Names
```

## 🔧 Advanced Features

### Node-Only Mode
Run a full validating node without mining:
- Uncheck "Enable Mining"
- Start Node
- Node syncs/validates but doesn't mine

Benefits:
- Lower CPU usage
- Participate in network
- Serve RPC requests
- Support decentralization

### Auto-Restart
Enable in Settings to automatically restart crashed nodes:
- Useful for long-running operations
- Configurable in Settings tab
- Monitor via log output

### Index Options
Enable as needed (uses disk space):
- **Transactions**: Required for tx history
- **Addresses**: Required for address queries
- **Auctions**: Required for browsing auctions

### Configuration Profiles
Save multiple configurations for different use cases:
```
Settings Tab → Save Settings → profiles/myprofile.json
Settings Tab → Load Settings → Select profile
```

## 🆘 Troubleshooting

### GUI Won't Start
```bash
# Check Python/tkinter installed
python3 --version
python3 -c "import tkinter; tkinter.Tk().mainloop()"

# On Windows: make sure X11 server is running
# Use fbd-wslgui_launch.bat for auto-setup
```

### RPC Connection Failed
1. Wait 5-10 seconds after starting node
2. Check node is running (see log)
3. Verify RPC port matches network:
   - main: 32868
   - testnet: 42868
   - regtest: 52868
   - simnet: 62868

### Permission Errors (WSL)
```bash
chmod +x fbd fbdctl fbd_wslgui.py
cd fbd-latest-linux-x86_64
chmod +x fbd fbdctl
```

### Node Won't Start
1. Check FBD path in Settings
2. Verify fbd executable exists and is executable
3. Review log output for errors
4. Test manually: `./fbd-latest-linux-x86_64/fbd --help`

## 📊 Network Reference

| Network  | P2P   | RPC   | DNS   | NS    | Address Prefix |
|----------|-------|-------|-------|-------|----------------|
| main     | 32867 | 32868 | 32869 | 32870 | fb             |
| testnet  | 42867 | 42868 | 42869 | 42870 | ft             |
| regtest  | 52867 | 52868 | 52869 | 52870 | fr             |
| simnet   | 62867 | 62868 | 62869 | 62870 | fs             |

## 💾 File Locations

### Configuration
- **GUI Config**: `~/.fbdgui/fbdgui_config.json`
- **Profiles**: `~/.fbdgui/profiles/*.json`
- **Logs**: `~/.fbdgui/fbdgui.log`

### Node Data
- **Default Datadir**: `~/.fbd/`
- **RPC Cookie**: `~/.fbd/.cookie`
- **Node Logs**: `~/.fbd/debug.log`

### Archived Files
- **Documentation**: `./ai-hist_fbd-wslgui/`
- **Old Versions**: `./ai-hist_fbd-wslgui/fbd_wslgui.*.py`
- **Setup Scripts**: `./ai-hist_fbd-wslgui/*.sh`

## � Example Workflows

### Solo Mining Setup
```
1. Double-click fbd-wslgui_launch.bat
2. Settings → Set miner address
3. Node & Mining → Enable Mining ✓
4. Node & Mining → Set threads (12)
5. Start Node
6. Monitor log for "Mined block..." messages
7. Wallet → Check balance for rewards
```

### Name Registration
```
1. Launch GUI
2. Auctions → Enter name → Get Name Info
3. If INACTIVE → Open Auction
4. Wait for BIDDING state
5. Place Bid (bid + lockup amounts)
6. Wait for REVEAL state
7. Reveal Bid
8. Wait for close
9. If won → Register
10. Load My Names to confirm
```

### Sync-Only Node
```
1. Launch GUI
2. Node & Mining → UNCHECK "Enable Mining"
3. Node & Mining → Check needed indexes
4. Start Node
5. Monitor sync in log
6. Use as RPC server for other apps
```

## 🎁 Tips & Tricks

1. **Desktop Shortcut**: Right-click fbd-wslgui_launch.bat → Send to Desktop
2. **Keep Settings**: Use Save/Load Settings for different configs
3. **Monitor Resources**: Task Manager → watch fbd CPU/RAM
4. **Backup Wallet**: Always save mnemonic when creating wallets
5. **Test First**: Use testnet for learning auctions
6. **Schedule Bids**: Use Auction Automation for timed operations
7. **Quick Access**: File → Open GUI Config Directory

## 🔗 Resources

- **FBD Documentation**: https://fbd.dev
- **Whitepaper**: https://fistbump.org/fistbump.txt
- **Block Explorer**: https://explorer.fistbump.org/
- **Source Code**: https://github.com/fistbump-org/fbd
- **Community**: Discord/Telegram (check fistbump.org)

## 🗂️ Version History

- **v3.0.0** (Current) - Production release with auction automation
- **v2.0.0** - Enhanced auction features (archived)
- **v1.0.0** - Initial release (archived)

Older versions and detailed change history in `ai-hist_fbd-wslgui/`

## 📄 License

This GUI tool is provided as-is for the Fistbump community.  
FBD itself is developed by eskimo and contributors.

---

**Need Help?**
- Check `QUICKSTART.txt` for quick reference
- See `ai-hist_fbd-wslgui/GUI_README.md` for detailed features
- Run in-app Help (? button) for quick guide
- Check `ai-hist_fbd-wslgui/` for additional documentation

**Ready to Start?**
→ Double-click `fbd-wslgui_launch.bat`! 🚀
