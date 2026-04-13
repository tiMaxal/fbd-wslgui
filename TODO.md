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
- [ ] Extend the existing "send from wallet" flow so it supports both FBC coin sends and name transfers from the same wallet context
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

### Manual `fbdctl` CLI Interface

**Status:** Planned  
**Created:** April 13, 2026

The GUI should expose a direct CLI-style interface for advanced/manual `fbdctl` usage without requiring users to leave the app.

**Requirements:**

- [ ] Add a dedicated UI panel/console for entering manual `fbdctl` commands
- [ ] Support running commands against the current active wallet/node context when applicable
- [ ] Show stdout/stderr, exit status, and structured error feedback clearly
- [ ] Preserve command history for the current session and optionally across restarts
- [ ] Guard dangerous/destructive commands with confirmation prompts where appropriate
- [ ] Document supported usage patterns and any intentional restrictions

**Implementation Notes:**

- Reuse existing subprocess / command execution plumbing where possible
- Keep this as an advanced/manual tool distinct from guided wallet actions
- Consider optional shortcuts/templates for common commands to reduce syntax errors

---

## Medium Priority

### Appearance / Theming Follow-Ups

**Status:** Planned  
**Created:** April 11, 2026

Current v0-5-0 behavior already supports Light/Dark/System theme modes in Legacy ttk, with optional rounded CustomTkinter install-on-demand.

**Requirements:**

- [ ] Add a pre-restart preview or clearer summary of selected theme/toolkit changes
- [ ] Offer additional CustomTkinter accent themes beyond the current stable default
- [ ] Consider a small status indicator showing whether optional rounded toolkit support is installed

---

## Low Priority / Ideas

### Donate Button in Settings Tab

**Status:** Planned  
**Created:** April 13, 2026

Add a donation link/button at the bottom of the Settings tab to support project and allow users to contribute.

**Requirements:**

- [ ] Add a "Donate" button/link at the bottom of the Settings tab UI
- [ ] [Link to project donation page wslgui.fb.d/donate]
- [ ] wallet address fb1qztl0v0lf7h7clecqsy9krc97g8daclwxej82qr
- [ ] Keep styling consistent with the rest of the Settings interface

**Implementation Notes:**

- Position at bottom of Settings panel
- Consider icon + text or subtle link styling
- Define donation URL/address before implementing
