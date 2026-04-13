# fbdwslgui_docmode_capture.py
"""
Pair with --doc-mode.  Launches the app, waits for sentinel files,
captures screenshots, ACKs each one by deleting the sentinel.
No coordinates. No image matching. No calibration.
"""

import subprocess, time, os, pathlib
from datetime import datetime

APP_CMD     = ["python", "fbd_wslgui.py", "--doc-mode"]
SENTINEL    = pathlib.Path("/tmp/fbdwslgui_doc_ready.flag")
OUT_DIR     = pathlib.Path("fbdwslgui_docs_screens") / datetime.now().strftime("docmode_%Y%m%d_%H%M%S")
POLL_DELAY  = 0.1   # seconds between sentinel checks
SCREENSHOT_PAUSE = 0.3  # settle time before capture

try:
    import pyautogui as pag
    CAPTURE = lambda path: pag.screenshot(str(path))
except ImportError:
    # Fallback: scrot (Linux)
    def CAPTURE(path):
        os.system(f"scrot '{path}'")

OUT_DIR.mkdir(parents=True, exist_ok=True)
SENTINEL.unlink(missing_ok=True)

print(f"[*] Output: {OUT_DIR}")
print("[*] Launching app in --doc-mode ...")
proc = subprocess.Popen(APP_CMD)

# Wait for app window to open
time.sleep(3)

try:
    while True:
        if SENTINEL.exists():
            label = SENTINEL.read_text().strip()
            if label == "DONE":
                print("[✓] All tabs captured.")
                SENTINEL.unlink(missing_ok=True)
                break
            # Settle, capture, ACK
            time.sleep(SCREENSHOT_PAUSE)
            out_path = OUT_DIR / f"{label}.png"
            CAPTURE(out_path)
            print(f"  [+] {out_path}")
            SENTINEL.unlink()           # ACK — app proceeds to next tab
        else:
            time.sleep(POLL_DELAY)
finally:
    proc.terminate()

# Generate markdown
md = OUT_DIR / "README.md"
with open(md, "w") as f:
    f.write("# FBD Node Manager — UI Documentation\n\n")
    for img in sorted(OUT_DIR.glob("*.png")):
        label = img.stem.replace("_", " ").title()
        f.write(f"## {label}\n![{img.name}]({img.name})\n\n")
print(f"[+] {md}")