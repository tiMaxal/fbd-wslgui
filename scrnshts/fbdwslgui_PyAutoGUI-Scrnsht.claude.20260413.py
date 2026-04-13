# ── PASTE INTO fbd_wslgui.py ──────────────────────────────────────────────────
# Place the run_doc_mode() call at the end of FBDManager.__init__(), gated on
# the CLI flag.  Add _start_doc_mode() as a method of FBDManager.
# ─────────────────────────────────────────────────────────────────────────────

# In main(), replace the body with:
#
#   def main():
#       import sys
#       doc_mode = "--doc-mode" in sys.argv
#       ...existing root / app setup...
#       if doc_mode:
#           app._start_doc_mode()
#       root.mainloop()

import pathlib

DOC_MODE_SCREENSHOT_DIR = pathlib.Path("fbdwslgui_docs_screens") / "docmode"
DOC_MODE_SENTINEL = pathlib.Path("/tmp/fbdwslgui_doc_ready.flag")

# Tab visit sequence: (tab_name_as_in_notebook, screenshot_label, extra_delay_ms)
DOC_MODE_SEQUENCE = [
    ("Node & Mining", "01_node_mining",  500),
    ("Wallet",        "02_wallet",        500),
    ("Auctions",      "03_auctions",      500),
    ("Block Calc",    "04_block_calc",    500),
    ("Settings",      "05_settings",      500),
]


def _start_doc_mode(self):
    """
    Drive the notebook through all tabs and write a sentinel file after each
    tab is selected.  The external capture script watches for the sentinel,
    takes a screenshot, deletes it, and signals readiness for the next tab.
    Runs entirely inside the Tk event loop via root.after().
    """
    DOC_MODE_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    sequence = list(DOC_MODE_SEQUENCE)

    def step(index):
        if index >= len(sequence):
            # All tabs visited — write final sentinel and exit
            DOC_MODE_SENTINEL.write_text("DONE")
            print("[doc-mode] Sequence complete.")
            return

        tab_name, label, delay_ms = sequence[index]
        print(f"[doc-mode] Selecting tab: {tab_name}")
        self._notebook_select(tab_name)

        def signal_ready():
            # Write sentinel with the expected screenshot name
            DOC_MODE_SENTINEL.write_text(label)
            # Poll until the external script deletes the sentinel (ACK)
            def wait_for_ack():
                if DOC_MODE_SENTINEL.exists():
                    self.root.after(100, wait_for_ack)
                else:
                    # Sentinel consumed — move to next tab
                    self.root.after(200, lambda: step(index + 1))
            wait_for_ack()

        self.root.after(delay_ms, signal_ready)

    self.root.after(1000, lambda: step(0))  # 1 s initial settle