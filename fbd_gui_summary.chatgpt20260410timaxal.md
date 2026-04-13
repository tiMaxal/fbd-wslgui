# FBD GUI App – Capability Summary - v6-0-0

**Stable production-ready build** with comprehensive node, mining, wallet, and auction management.

## Overall
- Full GUI for FBD node management, mining (solo + pool), wallet operations, and name auctions
- Tab-based interface with background automation and real-time monitoring
- Cross-platform (Native Linux, WSL, Windows)
- Optional auto-restart and recovery

---

## Node & Mining
- Start/stop FBD node with real-time status, log monitoring
- Solo mining (100% rewards, needs full node)
- Pool mining (shared rewards, lower variance, no node required)
- Configurable threads (0=auto recommended), network (main/testnet/regtest/simnet), indexes
- Auto-version checking for miner and FBD binaries
- Safe auto-update with hash verification

---

## Wallet
- Create/list/delete wallets with mnemonic backup
- Check balance and view addresses
- Send FBC payments to wallet addresses
- Transaction history and import/export
- Multi-wallet support

---

## Auctions
- Complete lifecycle automation (OPEN → BIDDING → REVEAL → REGISTER)
- Background job engine with retry logic and recovery
- Competing bid detection and wallet balance checking
- Email notifications (optional SMTP setup)
- Scan wallets for existing auctions
- Auction phase timing calculator
- Personal watched names and rollout reminders

---

## Block & Auction Calculator
- Real-time block height and node status display
- Auction state analysis and phase timing
- Name availability and auction schedule prediction

---

## Settings & Persistence
- Multi-profile configuration (save/load for different setups)
- FBD path and RPC host/port configuration
- Email notification settings
- Binary auto-update configuration
- Export/import settings backup

---

## System Features
-

---

## Summary
A unified GUI control panel for FBD that automates complex workflows, especially auctions, while providing full node and wallet control.
