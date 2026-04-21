# Assessment: test app vs TODO

Date: 2026-04-21
Scope: `fbd-wslgui/fbd_wslgui.test.py` compared to requested TODO facets.

## Summary

- Name-transfer wallet integration: partial groundwork only
- Manual `fbdctl` CLI tab/interface: not implemented
- Block-calc phase "Current" labeling: not implemented
- Donate button/link in Settings: not implemented
- Github button/link in Settings: not implemented

## Evidence by facet

1. Wallet transfer + name transfer integration
- Present:
  - Wallet send UI is implemented in `create_wallet_tab` ("Send Payment").
  - FBC transfer execution exists in `send_payment` via `sendnone`.
  - Transaction table already recognizes covenant type `TRANSFER` in `_tx_action_label`.
- Missing:
  - No wallet UI action to initiate protocol-level name transfer.
  - No integrated flow for selecting owned name + recipient + transfer lifecycle feedback.
- Verdict: Partial.

2. Manual `fbdctl` CLI interface
- Present:
  - Shared command builder exists (`get_fbdctl_command`) and many structured actions use it.
- Missing:
  - No dedicated CLI tab/panel for arbitrary command input.
  - No command history console for manual execution.
  - No destructive-command guardrail UX.
- Verdict: Missing.

3. Block calc "Current" phase status label
- Present:
  - Block calculator timeline exists and computes auction boundaries.
  - `_display_calc_results` displays status per row.
- Missing:
  - Status is event-relative (`Past`, `Upcoming`, `NOW`), not interval-aware phase status.
  - No explicit phase-window logic to mark BIDDING/REVEAL/CLOSED as `Current` across ranges.
- Verdict: Missing.

4. Donate button in Settings
- Present:
  - Settings tab sections are implemented.
- Missing:
  - No donate link/button block in `create_settings_tab`.
- Verdict: Missing.

5. Github link in Settings
- Present:
  - Settings layout supports additional button rows.
- Missing:
  - No project Github link/button in settings.
- Verdict: Missing.

## Implementation risk notes

- Name-transfer and atomic-swap features share wallet/name selection and status UX needs; implementing them together avoids duplicate flows.
- Manual CLI panel should enforce allow/confirm policies for destructive commands to prevent accidental chain/wallet damage.
- Block-calc status update should preserve existing manual/offline mode behavior.
