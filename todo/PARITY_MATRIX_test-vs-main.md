# FBD-WSLGUI: Test vs Main Capability Parity Matrix

**Last Updated:** 2026-04-21  
**Test Version:** 6.0.0 (TEST)  
**Main Version:** 6.0.0

---

## Capability Comparison

| Capability | Main | Test | Notes |
|------------|------|------|-------|
| **Core Workflows** |
| Node start/stop/monitor | ✅ | ✅ | Identical |
| Pool miner control | ✅ | ✅ | Identical |
| Wallet CRUD operations | ✅ | ✅ | Identical |
| Auction automation (Stages 0-7) | ✅ | ✅ | Identical |
| Block calculator | ✅ | ✅ | Identical |
| DNS record manager | ✅ | ✅ | Identical |
| Notification system | ✅ | ✅ | Identical |
| Email alerts | ✅ | ✅ | Identical |
| Profile management | ✅ | ✅ | Identical |
| **UI & Themes** |
| Legacy ttk mode | ✅ | ✅ | Identical |
| CustomTkinter rounded mode | ✅ | ✅ | Identical |
| Light/Dark/System themes | ✅ | ✅ | Identical |
| **Testing & Documentation** |
| Automated doc-mode (screenshot orchestration) | ❌ | ✅ | Test-only: `--doc-mode` flag + `_start_doc_mode()` |
| CLI theme override for docs | ❌ | ✅ | Test-only: `--doc-theme=dark/light` |
| **Environment Setup** |
| X11 DISPLAY auto-detection (WSL/Linux) | ❌ | ✅ | Test-only: auto-fixes `:0` → `127.0.0.1:0` |
| Auto-install x11-apps utilities | ❌ | ✅ | Test-only: xeyes/xclock for X11 validation |
| CustomTkinter prompt suppression (doc mode) | ❌ | ✅ | Test-only: skips CTK prompt when `--doc-mode` active |
| **Logging & Diagnostics** |
| Separate test log file | ❌ | ✅ | Test: `fbdgui_test.log`, Main: `fbdgui.log` |
| Startup banner differentiation | ✅ | ✅ | Test adds "(TEST)" suffix |
| Settings UI test tag | ❌ | ✅ | Test labels UI toolkit dropdown with "(test)" |

---

## Risk Assessment


### 🟡 Medium
None currently identified

### 🟢 Low
- **Log file divergence**: Test writes to separate log; merging logs requires manual aggregation
- **UI labels**: Test has visual "TEST" markers; screenshot comparisons will differ

---

## Feature Parity Score

**Core Functionality:** 100% (all production features present in both)  
**Test Infrastructure:** Test +5 capabilities (doc automation, X11 bootstrap)  
**Regression Risk:** Low (shebang placement only affects direct execution)

---

## Maintenance Guidelines

### When updating test:
1. ✅ Add new doc-mode sequences when tabs/UI change
2. ✅ Preserve X11/DISPLAY detection for WSL users
3. ✅ Keep log file separate (`fbdgui_test.log`)
4. ⚠️ Do NOT remove shebang from line 1

### When updating main:
1. ✅ Backport all auction/wallet/node logic from test if diverging
2. ✅ Keep production log file path (`fbdgui.log`)
3. ❌ Do NOT add doc-mode to main (test infrastructure only)

### When merging test → main:
1. Strip doc-mode method `_start_doc_mode()`
2. Strip X11 auto-installer preamble (lines 1-15 in test)
3. Restore shebang to line 1
4. Change log file back to `fbdgui.log`
5. Remove "(TEST)" markers from UI/logs
6. Remove `--doc-mode` CLI handling

---

## Quick Reference

| Item | Main Path | Test Path |
|------|-----------|-----------|
| Script | `fbd-wslgui/fbd_wslgui.py` | `fbd-wslgui/fbd_wslgui.test.py` |
| Log file | `~/.fbdgui/fbdgui.log` | `~/.fbdgui/fbdgui_test.log` |
| Config | `~/.fbdgui/fbdgui_config.json` | `~/.fbdgui/fbdgui_config.json` (shared) |
| Jobs | `~/.fbdgui/auction_jobs.json` | `~/.fbdgui/auction_jobs.json` (shared) |
| Doc output | N/A | `fbdwslgui_docs_screens/docmode/` |

---

## Change History

### 2026-04-21
- Initial matrix created
- Documented doc-mode capability (test-only)
- Documented X11 bootstrap (test-only)
- Identified shebang placement regression
