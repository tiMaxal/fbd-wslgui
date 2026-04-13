# App capability precis - v6-0-0

[chatgpt20260410timaxal, updated for v6-0-0]

A full-stack GUI control panel for FBD that combines node management, mining, wallet operations, and highly automated name-auction participation with monitoring, notifications, and recovery.

All-in-one GUI for node, mining, wallet, and auctions
Node control + monitoring (start/stop, stats, logs, auto-restart)
Mining support (solo + pool, configurable threads/wallet)
Wallet functions (send FBC, view transactions, manage addresses)
Auction automation (open → bid → reveal → register lifecycle)
Background job engine (auto actions, retries, recovery)
Block/auction timing calculator
Notifications system (UI + optional email alerts)
Config profiles + persistence (multi-setup support)
Dependency + update handling (auto-check/install basics)

Bottom line: a semi-automated control hub that reduces manual CLI work, especially for auctions.

[Perplexity20260410-553rdd4]

## Node Mining

- Starts and stops the FBD node.
- Shows node status, current block height, peer count, restart count, blocks won this session, and total chain blocks.
- Lets you set network, host, log level, agent name, miner address, miner threads, and mining enable/disable.
- Supports pool miner settings, including pool wallet address, host, and threads.
- Lets you enable chain indexing for transactions, addresses, and auctions, with warnings about existing chain data.
- Includes controls for refresh status, mining stats, and deleting chain data.
- Shows node output logs and lets you clear or open the log file.

## Wallet

- Selects an active wallet and shows wallet balance and address.
- Creates, imports, deletes, and copies wallet addresses.
- Sends FBC payments to saved or entered addresses.
- Requires the node to be running for wallet actions.
- Lets you load transaction history for the selected wallet.

## Auctions

- Looks up auction/name information by name.
- Lets you open an auction, place a bid, reveal a bid, and register a winning name.
- Supports bid amount and lockup amount entry.
- Can auto-continue through OPEN, BID, REVEAL, and REGISTER phases.
- Shows wallet balance info relevant to bidding.
- Includes active automation jobs with refresh, view details, cancel, and clear completed actions.
- Can scan a wallet for existing auctions and import them into automation, including unrevealed bids, won auctions, and lost-auction redemption handling.
- Provides notifications, a personal names list, rollout reminders, and watchlist management.
- Shows auction details and name/auction state guidance.

## Block Calc

- Calculates auction timelines and approximate datetime values from block heights.
- Supports lookup by name using a running node or manual block entry offline.
- Shows current blockchain status, including current block and node status.
- Calculates OPEN, BIDDING, REVEAL, CLOSED, REGISTERED, and REDEEM deadline phases.
- Explains block timing assumptions and displays results in a table.
- Can clear calculator results.

## Settings

- Manages configuration profiles: load, save as new, update, and delete.
- Stores and edits FBD executable path, RPC host and port, and custom data directory.
- Lets you change node/mining defaults, mining enablement, and related launch settings.
- Includes advanced options such as custom DNS port and checks for running FBD instances.
- Supports email notification settings and test email sending.
- Provides saved addresses and other persisted GUI preferences.

## Brief summary

- GUI for node control, wallet management, auctions, block timing, and saved configuration.
