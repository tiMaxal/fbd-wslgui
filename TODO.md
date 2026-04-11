# FBD GUI - TODO List

## High Priority

### Binary Management & Version Checking
**Status:** In Progress  
**Created:** April 8, 2026

Since `fbd` and `fbdctl` binaries are not included in the repository (due to file size), users must download and maintain them manually. This feature would automate that process.

**Requirements:**
- [ ] Check for presence of `fbd` and `fbdctl` binaries on app startup
- [x] Detect current binary versions (if present)
- [ ] Check GitHub releases API for latest available version
- [x] Display version comparison in UI (current vs. available)
- [x] Provide download button/wizard to fetch latest binaries
- [x] Auto-extract and set permissions (chmod +x)
- [ ] Optional: Periodic update checks (configurable frequency)
- [x] Optional: Backup old binaries before updating

**Implementation Notes:**
- Download URL: `https://fbd.dev/download/fbd-latest-linux-x86_64.zip`
- Auto-extract zip and set permissions (chmod +x)
- Current app already supports manual version checks, hash comparison, download/update, extraction, chmod, and backup rotation
- Startup update-check helper exists but still needs wiring into app startup flow
- Current implementation uses direct download URLs plus hash/version comparison, not GitHub Releases API
- Consider version checking endpoint if available
- Optional next step: add a configurable periodic update check interval

---

### Wallet Transfer + Name Transfer Integration
**Status:** Planned  
**Created:** April 10, 2026

The wallet transfer interface should cover both FBC transfers and protocol-level name transfers so users can manage ownership changes from the same wallet workflow.

**Requirements:**
- [ ] Add wallet UI for protocol-level name transfer operations
- [ ] Integrate name transfer into the existing wallet usage flow, not as a separate hidden/admin-only tool
- [ ] Let users select an owned name from the active wallet and transfer it to a recipient
- [ ] Validate ownership, wallet selection, recipient format, and protocol preconditions before submission
- [ ] Show transaction result, pending status, and any follow-up steps needed for the transfer lifecycle
- [ ] Keep FBC send/receive and name transfer actions clearly separated in the UI while sharing wallet context

**Implementation Notes:**
- Treat name transfer as part of day-to-day wallet operations
- Reuse active wallet selection and existing RPC/fbdctl command plumbing where possible
- Add clear status/error handling so protocol failures are understandable from the wallet screen

---

## Medium Priority

_Add future enhancements here_

---

## Low Priority / Ideas

_Add nice-to-have features here_
