# Agentic Implementation Plan

Date: 2026-04-21
Scope: remaining TODO facets + new atomic swap capability.

**Agent Work Restriction:**
All agentic implementation and edits must be performed exclusively in `fbd-wslgui/fbd_wslgui.test.py`. No changes are to be made in `fbd-wslgui/fbd_wslgui.py` during this phase. However, all code and design choices must preserve the ability for later smooth integration or migration of features into `fbd_wslgui.py` if/when required. This means:
- Use modular, well-documented, and non-breaking patterns.
- Avoid hard-coding file-specific logic that would block future refactoring.
- Where possible, encapsulate new logic in functions/classes that could be ported.

## Objectives

1. Complete wallet-level name transfer integration.
2. Add advanced manual `fbdctl` CLI interface tab.
3. Implement interval-based "Current" phase status in block calculator.
4. Add Donate and Github links in Settings.
5. Add atomic swap workflow for TLD + FBC private trustless sales.

## Subagent delegation strategy

- `Explore` subagent
  - Purpose: fast codebase discovery and cross-file impact map before edits.
  - Deliverables:
    - all call sites and UI sections touched by wallet actions
    - command execution helpers reusable for CLI/swap
    - settings tab insertion anchors for Donate/Github block
    - block-calc status rendering hooks

- `AIAgentExpert` subagent
  - Purpose: design robust state-machine workflow for atomic-swap UX and failure handling.
  - Deliverables:
    - concise swap lifecycle state model
    - edge-case matrix (timeout, partial completion, invalid payload)
    - minimal operator prompts and confirmations

- `Explore` subagent (second pass)
  - Purpose: validation and regression check after implementation.
  - Deliverables:
    - check for dead methods/unwired UI controls
    - confirm all new actions are reachable from tabs
    - identify missing tests/docs updates


## QA Checkpoints (Required)

After completion of each workstream (WS), a QA checkpoint must be performed:
- All new/modified features must be tested for correct function and non-regression of existing features.
- QA checkpoint must be documented (test cases, results, and any issues found).
- Only after passing the QA checkpoint may the next workstream begin.
- If a QA checkpoint fails, fixes must be made and retested before proceeding.

## Workstreams
### WS1: Wallet Name-Transfer Integration

Tasks:
1. Extend Wallet tab with transfer mode selector (`FBC Send` vs `Name Transfer`).
2. Add owned-name selector sourced from active wallet names.
3. Add recipient field validation and transfer precheck.
4. Execute name-transfer command via existing command builder.
5. Present tx result + pending/follow-up guidance.

Output files (expected):
- `fbd-wslgui/fbd_wslgui.test.py` (only)
  - All new logic must be in this file for this phase.
  - README/help text updates may be noted for later, but not implemented until integration phase.

### WS2: Manual `fbdctl` CLI Tab

Tasks:
1. Add a new notebook tab: `CLI`.
2. Add command input, run button, output console, and exit status display.
3. Add session history with optional persisted history file.
4. Add confirmation prompts for dangerous command patterns.
5. Add quick templates (read-only helper commands).

Output files (expected):
- `fbd-wslgui/fbd_wslgui.test.py` (only)

### WS3: Block-Calc Phase Status

Tasks:
1. Keep existing timeline rows.
2. Add interval-aware status resolver:
   - BIDDING current when `bid_start <= current < reveal_start`
   - REVEAL current when `reveal_start <= current < closed_block`
   - CLOSED/REGISTER current when `current >= closed_block`
3. Preserve `Past` for fully elapsed and `Upcoming` for future rows.
4. Ensure offline/manual mode remains stable.

Output files (expected):
- `fbd-wslgui/fbd_wslgui.test.py` (only)

### WS4: Donate + Github Settings Footer

Tasks:
1. Add bottom settings section (`Support / Project Links`).
2. Add Donate action and project Github action.
3. Add wallet/address display and optional copy actions.
4. Keep layout/style consistent in ttk and CTK modes.

Output files (expected):
- `fbd-wslgui/fbd_wslgui.test.py` (only)

### WS5: Atomic Swap (TLD + FBC)

Tasks:
1. Define swap offer payload format (human-readable + parseable).
2. Build offer creation UI with optional partner email/wallet fields.
3. Add one-click copy payload and import payload flows.
4. Validate preconditions before submit/fulfill.
5. Add status tracking and cancellation/expiry handling.
6. Provide clear fulfillment instructions for out-of-band sharing.

Output files (expected):
- `fbd-wslgui/fbd_wslgui.test.py` (only)
  - Documentation or help text changes should be planned but not implemented until integration phase.


## QA Checkpoint Sequence

1. After each WS (workstream), run a full QA test suite:
  - Validate new feature(s) and all previously implemented features for correct interaction.
  - Document test results and any issues.
  - Only proceed to the next WS if all tests pass.

## Suggested execution order

1. WS3 (small, low-risk) and WS4 (small UI addition)
2. WS1 (name-transfer integration)
3. WS2 (manual CLI tab)
4. WS5 (atomic swap, largest scope)

## Acceptance criteria

- Name transfer is executable from Wallet tab with clear validation and tx feedback.
- CLI tab runs manual commands and surfaces stdout/stderr/exit code with history and confirmations.
- Block calculator visibly marks current phase by interval logic.
- Settings tab contains working Donate and Github actions.
- Atomic swap flow supports offer creation, optional partner contact fields, copy/share payload, import/fulfill path, and lifecycle status visibility.

## Risks and mitigations

- Risk: command misuse in manual CLI.
  - Mitigation: confirmation prompts + denylist warnings.
- Risk: atomic swap UX complexity.
  - Mitigation: explicit stepper flow + deterministic status states.
- Risk: wallet/name state drift while UI is open.
  - Mitigation: pre-submit refresh and optimistic UI disabled until checks pass.
