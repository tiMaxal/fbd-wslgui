#!/usr/bin/env python3
"""
FBD Node Manager GUI
A graphical interface for managing FBD node, mining, wallet, and auctions.
Linux-native Python app (runs on native Linux, WSL, or Windows via WSL).

Created by 'voding' [vibe-coding] - copilot+timaxal, April 2026
"""

# ============================================================================
# DEPENDENCY CHECKER - Runs before imports to ensure packages are available
# ============================================================================

import os
import sys
import subprocess
import signal


def check_and_install_dependencies():
  """Check for required Python packages and offer to install if missing"""
  missing_packages = []
  install_commands = {}

  # Check for tkinter
  try:
    import tkinter
  except ImportError:
    missing_packages.append("tkinter")
    install_commands["tkinter"] = "python3-tk"

  # Check for requests
  try:
    import requests
  except ImportError:
    missing_packages.append("requests")
    install_commands["requests"] = "python3-requests"

  if not missing_packages:
    return True # All dependencies satisfied

  # Determine package manager
  pkg_manager = None
  install_cmd_template = None

  if os.path.exists("/usr/bin/apt") or os.path.exists("/usr/bin/apt-get"):
    pkg_manager = "apt"
    install_cmd_template = "sudo apt update && sudo apt install -y {packages}"
  elif os.path.exists("/usr/bin/dnf"):
    pkg_manager = "dnf"
    install_cmd_template = "sudo dnf install -y {packages}"
  elif os.path.exists("/usr/bin/yum"):
    pkg_manager = "yum"
    install_cmd_template = "sudo yum install -y {packages}"
  elif os.path.exists("/usr/bin/pacman"):
    pkg_manager = "pacman"
    # Pacman package names might differ
    install_commands["tkinter"] = "tk"
    install_commands["requests"] = "python-requests"
    install_cmd_template = "sudo pacman -S --noconfirm {packages}"

  # Build package list
  if pkg_manager in ["apt", "dnf", "yum"]:
    packages_to_install = " ".join(install_commands.values())
  else:
    packages_to_install = " ".join(install_commands.values())

  # Display error and offer to install
  print("\n" + "=" * 70)
  print("[!] MISSING DEPENDENCIES")
  print("=" * 70)
  print(f"\nThe following Python packages are required but not installed:")
  for pkg in missing_packages:
    print(f" * {pkg}")

  if pkg_manager:
    install_cmd = install_cmd_template.format(packages=packages_to_install)
    print(f"\n[*][|] Detected package manager: {pkg_manager}")
    print(f"\n[*][SECT] Install command:\n  {install_cmd}")

    # Ask if user wants to auto-install
    try:
      response = (
        input("\nWould you like to install these packages now? [Y/n]: ")
        .strip()
        .lower()
      )
      if response in ["", "y", "yes"]:
        print(f"\n[*] Installing packages with {pkg_manager}...")
        if pkg_manager == "apt":
          # Run apt update first
          result = subprocess.run(
            ["sudo", "apt", "update"], capture_output=True, text=True
          )
          if result.returncode != 0:
            print(f"[!] apt update failed: {result.stderr}")

        # Install packages
        result = subprocess.run(
          install_cmd.split(), capture_output=True, text=True
        )

        if result.returncode == 0:
          print("[OK] Installation successful!")
          print("\n[*] Please restart the application:")
          print("  python3 fbd_wslgui.py")
          print("=" * 70 + "\n")
          sys.exit(0)
        else:
          print(f"\n[X] Installation failed!")
          print(f"Error: {result.stderr}")

    except KeyboardInterrupt:
      print("\n\n[!] Installation cancelled by user.")
  else:
    print("\n[!] Could not detect package manager.")
    print("Please install the required packages manually.")

  # Manual installation instructions
  print("\n" + "=" * 70)
  print("[*]< MANUAL INSTALLATION INSTRUCTIONS")
  print("=" * 70)
  print("\nUbuntu / Debian:")
  print("  sudo apt update && sudo apt install -y python3-tk python3-requests")
  print("\nFedora / RHEL / CentOS:")
  print("  sudo dnf install -y python3-tkinter python3-requests")
  print("\nArch Linux:")
  print("  sudo pacman -S tk python-requests")
  print("\nOther distributions:")
  print("  pip3 install requests")
  print("  (tkinter package name varies - search for python3-tk or python-tkinter)")
  print("=" * 70 + "\n")

  sys.exit(1)


# Run dependency check before imports
check_and_install_dependencies()


def format_process_exit_code(exit_code):
  """Format process exit code and include signal name for signal-terminated processes."""
  if exit_code is None:
    return "unknown"

  if exit_code < 0:
    signal_number = -exit_code
    try:
      signal_name = signal.Signals(signal_number).name
    except ValueError:
      signal_name = f"SIG{signal_number}"
    return f"{exit_code} (signal {signal_name})"

  return str(exit_code)


def get_process_exit_hint(exit_code):
  """Return a short diagnostic hint for notable process exit codes."""
  if exit_code is None or exit_code >= 0:
    return None

  signal_number = -exit_code
  if signal_number == signal.SIGILL:
    return (
      "Likely cause: unsupported CPU instruction set in this miner build "
      "or a corrupted binary."
    )

  return None

# ============================================================================
# IMPORTS - Only reached if dependencies are satisfied
# ============================================================================
import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
from pathlib import Path
import hashlib
import zipfile
import requests
from requests.auth import HTTPBasicAuth
import time
import uuid # For generating unique job IDs
from datetime import datetime, timedelta
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import shutil # For chain data deletion

try:
  import customtkinter as ctk
except ImportError:
  ctk = None

UI_TOOLKIT_ENV_VAR = "FBD_WSLGUI_TEST_TOOLKIT"
UI_TOOLKIT_TTK = "ttk"
UI_TOOLKIT_CUSTOMTK = "customtkinter"
SUPPORTED_UI_TOOLKITS = {UI_TOOLKIT_TTK, UI_TOOLKIT_CUSTOMTK}


def _normalize_ui_toolkit(value):
  """Normalize UI toolkit flag values to supported identifiers."""
  mode = (value or "").strip().lower()
  if mode in ("ctk", "customtk", "customtkinter"):
    return UI_TOOLKIT_CUSTOMTK
  if mode in ("ttk", "tk", "legacy"):
    return UI_TOOLKIT_TTK
  return ""


def _resolve_startup_ui_toolkit():
  """Resolve requested toolkit from env var first, then config file."""
  env_mode = _normalize_ui_toolkit(os.environ.get(UI_TOOLKIT_ENV_VAR, ""))
  if env_mode:
    return env_mode

  config_path = Path.home() / ".fbdgui" / "fbdgui_config.json"
  try:
    if config_path.exists():
      with open(config_path, "r") as handle:
        cfg = json.load(handle)
      cfg_mode = _normalize_ui_toolkit(cfg.get("ui_toolkit", ""))
      if cfg_mode:
        return cfg_mode
  except Exception:
    pass

  return UI_TOOLKIT_TTK

# ============================================================================
# AUCTION AUTOMATION - STAGE 4: NOTIFICATION MANAGER
# ============================================================================


class NotificationManager:
  """
  Manages in-app notifications for auction automation events
  Provides a centralized notification system with persistence and UI integration
  """

  def __init__(self, manager):
    """Initialize the instance state."""
    self.manager = manager
    self.notifications = [] # List of notification dicts
    self.max_notifications = 100 # Keep last 100 notifications
    self.notification_file = Path.home() / ".fbdgui" / "notifications.json"
    self.notification_widget = None # Will be set by UI
    self._ensure_notification_file()
    self._load_notifications()

  def _ensure_notification_file(self):
    """Ensure notification file exists"""
    if not self.notification_file.exists():
      initial_data = {"notifications": []}
      try:
        with open(self.notification_file, "w") as f:
          json.dump(initial_data, f, indent=2)
      except Exception as e:
        self.manager.log(f"Error creating notifications file: {e}")

  def _load_notifications(self):
    """Load notifications from file"""
    try:
      if self.notification_file.exists():
        with open(self.notification_file, "r") as f:
          data = json.load(f)
          self.notifications = data.get("notifications", [])
          # Keep only last max_notifications
          if len(self.notifications) > self.max_notifications:
            self.notifications = self.notifications[
              -self.max_notifications :
            ]
    except Exception as e:
      self.manager.log(f"Error loading notifications: {e}")
      self.notifications = []

  def _save_notifications(self):
    """Save notifications to file"""
    try:
      with open(self.notification_file, "w") as f:
        json.dump({"notifications": self.notifications}, f, indent=2)
    except Exception as e:
      self.manager.log(f"Error saving notifications: {e}")

  def add_notification(self, event_type, name, message, job_id=None, level="info"):
    """
    Add a new notification

    Args:
      event_type: Type of event (opened, bid_placed, revealed, registered, lost, failed, competing_bid)
      name: Name related to the notification
      message: Notification message
      job_id: Optional job ID
      level: Notification level (info, warning, error, success)
    """
    notification = {
      "id": str(uuid.uuid4()),
      "timestamp": datetime.now().isoformat(),
      "event_type": event_type,
      "name": name,
      "message": message,
      "job_id": job_id,
      "level": level,
      "read": False,
    }

    self.notifications.append(notification)

    # Keep only last max_notifications
    if len(self.notifications) > self.max_notifications:
      self.notifications = self.notifications[-self.max_notifications :]

    self._save_notifications()
    self._update_ui()

    # Log to console
    icon = self._get_level_icon(level)
    self.manager.log(f"{icon} NOTIFICATION: {message}")

  def _get_level_icon(self, level):
    """Get icon for notification level"""
    icons = {"info": "[i]", "success": "[OK]", "warning": "[!]", "error": "[X]"}
    return icons.get(level, "[*]")

  def _update_ui(self):
    """Update notification widget if available"""
    if self.notification_widget:
      try:
        # Schedule UI update on main thread
        self.manager.root.after(0, self._refresh_widget)
      except Exception as e:
        self.manager.log(f"Error updating notification UI: {e}")

  def _refresh_widget(self):
    """Refresh the notification widget display"""
    if not self.notification_widget:
      return

    try:
      # Clear current content
      self.notification_widget.configure(state="normal")
      self.notification_widget.delete("1.0", tk.END)

      # Show recent notifications (last 20, newest first)
      recent = self.notifications[-20:]
      recent.reverse()

      if not recent:
        self.notification_widget.insert("1.0", "No notifications yet.\n")
      else:
        for notif in recent:
          timestamp = datetime.fromisoformat(notif["timestamp"]).strftime(
            "%Y-%m-%d %H:%M:%S"
          )
          icon = self._get_level_icon(notif["level"])
          name = notif["name"]
          message = notif["message"]

          line = f"{icon} [{timestamp}] '{name}': {message}\n"
          self.notification_widget.insert(tk.END, line)

          # Color code by level
          if notif["level"] == "error":
            # Find the last line and apply red color
            last_line = self.notification_widget.index(tk.END + "-2l")
            self.notification_widget.tag_add(
              "error", last_line, tk.END + "-1c"
            )
            self.notification_widget.tag_config("error", foreground="red")
          elif notif["level"] == "success":
            last_line = self.notification_widget.index(tk.END + "-2l")
            self.notification_widget.tag_add(
              "success", last_line, tk.END + "-1c"
            )
            self.notification_widget.tag_config(
              "success", foreground="green"
            )
          elif notif["level"] == "warning":
            last_line = self.notification_widget.index(tk.END + "-2l")
            self.notification_widget.tag_add(
              "warning", last_line, tk.END + "-1c"
            )
            self.notification_widget.tag_config(
              "warning", foreground="orange"
            )

      self.notification_widget.configure(state="disabled")
      self.notification_widget.see("1.0") # Scroll to top (newest)

    except Exception as e:
      self.manager.log(f"Error refreshing notification widget: {e}")

  def set_widget(self, widget):
    """Set the notification display widget"""
    self.notification_widget = widget
    self._refresh_widget()

  def get_unread_count(self):
    """Get count of unread notifications"""
    return sum(1 for n in self.notifications if not n.get("read", False))

  def mark_all_read(self):
    """Mark all notifications as read"""
    for notif in self.notifications:
      notif["read"] = True
    self._save_notifications()

  def clear_notifications(self):
    """Clear all notifications"""
    self.notifications = []
    self._save_notifications()
    self._update_ui()

  # Event-specific notification methods
  def notify_opened(self, name, job_id, txid):
    """Notify auction opened"""
    self.add_notification(
      "opened",
      name,
      f"Auction opened successfully. TXID: {txid[:12]}...",
      job_id,
      "success",
    )

  def notify_bid_placed(self, name, job_id, txid, bid_amount):
    """Notify bid placed"""
    self.add_notification(
      "bid_placed",
      name,
      f"Bid placed: {bid_amount} FBC. TXID: {txid[:12]}...",
      job_id,
      "success",
    )

  def notify_revealed(self, name, job_id, num_bids):
    """Notify bids revealed"""
    self.add_notification(
      "revealed",
      name,
      f"Submitted reveal for {num_bids} bid(s)",
      job_id,
      "success",
    )

  def notify_registered(self, name, job_id, txid):
    """Notify name registered (WON!)"""
    message = f"[*] AUCTION WON! Name registered. TXID: {txid[:12]}..."
    self.add_notification("registered", name, message, job_id, "success")
    # Stage 5: Send email for critical event
    if hasattr(self.manager, "email_manager"):
      details = f"Name: {name}\nTransaction ID: {txid}\nJob ID: {job_id}"
      self.manager.email_manager.notify_critical_event(
        "registered", name, details
      )

  def notify_lost(self, name, job_id, reason="Bid was not highest"):
    """Notify auction lost"""
    message = f"Auction lost: {reason}"
    self.add_notification("lost", name, message, job_id, "warning")
    # Stage 5: Send email for critical event
    if hasattr(self.manager, "email_manager"):
      details = f"Name: {name}\nReason: {reason}\nJob ID: {job_id}"
      self.manager.email_manager.notify_critical_event("lost", name, details)

  def notify_failed(self, name, job_id, error):
    """Notify automation failed"""
    message = f"Automation failed: {error}"
    self.add_notification("failed", name, message, job_id, "error")
    # Stage 5: Send email for critical event
    if hasattr(self.manager, "email_manager"):
      details = f"Name: {name}\nError: {error}\nJob ID: {job_id}"
      self.manager.email_manager.notify_critical_event("failed", name, details)

  def notify_competing_bid(self, name, our_bid, competing_bid, job_id=None):
    """Notify about competing bids detected"""
    message = f"[!] COMPETING BID DETECTED! Our bid: {our_bid} FBC, Competing: {competing_bid} FBC"
    self.add_notification("competing_bid", name, message, job_id, "warning")
    # Stage 5: Send email for critical event (as competing_threat)
    if hasattr(self.manager, "email_manager"):
      details = f"Name: {name}\nYour Bid: {our_bid} FBC\nCompeting Bid: {competing_bid} FBC\nJob ID: {job_id if job_id else 'N/A'}"
      self.manager.email_manager.notify_critical_event(
        "competing_threat", name, details
      )


# ============================================================================
# AUCTION AUTOMATION - STAGE 5: EMAIL NOTIFICATIONS
# ============================================================================


class EmailManager:
  """
  Manages email notifications for critical auction automation events
  Supports SMTP with basic authentication and password encryption
  """

  def __init__(self, manager):
    """Initialize the instance state."""
    self.manager = manager
    self.config_file = Path.home() / ".fbdgui" / "email_config.json"
    self.config = self._load_config()
    self._ensure_config_file()

  def _ensure_config_file(self):
    """Ensure email config file exists"""
    if not self.config_file.exists():
      self._save_config()

  def _load_config(self):
    """Load email configuration"""
    default_config = {
      "enabled": False,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "from_email": "",
      "password": "", # Base64 encoded
      "to_email": "",
    }

    try:
      if self.config_file.exists():
        with open(self.config_file, "r") as f:
          loaded = json.load(f)
          default_config.update(loaded)
    except Exception as e:
      self.manager.log(f"Error loading email config: {e}")

    return default_config

  def _save_config(self):
    """Save email configuration"""
    try:
      self.config_file.parent.mkdir(parents=True, exist_ok=True)
      with open(self.config_file, "w") as f:
        json.dump(self.config, f, indent=2)
    except Exception as e:
      self.manager.log(f"Error saving email config: {e}")

  def update_config(
    self, enabled, smtp_server, smtp_port, from_email, password, to_email
  ):
    """Update email configuration"""
    # Encode password with base64 (basic obfuscation)
    encoded_password = (
      base64.b64encode(password.encode()).decode() if password else ""
    )

    self.config = {
      "enabled": enabled,
      "smtp_server": smtp_server,
      "smtp_port": smtp_port,
      "from_email": from_email,
      "password": encoded_password,
      "to_email": to_email,
    }
    self._save_config()
    self.manager.log("Email configuration updated")

  def get_password(self):
    """Get decoded password"""
    try:
      if self.config.get("password"):
        return base64.b64decode(self.config["password"].encode()).decode()
      return ""
    except:
      return ""

  def send_email(self, subject, body):
    """
    Send email notification (non-blocking, threaded)
    Only sends if email notifications are enabled
    """
    if not self.config.get("enabled"):
      return

    # Send in background thread to avoid blocking UI
    thread = threading.Thread(
      target=self._send_email_thread, args=(subject, body), daemon=True
    )
    thread.start()

  def _send_email_thread(self, subject, body):
    """Internal method to send email (runs in thread)"""
    try:
      # Get config
      smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
      smtp_port = self.config.get("smtp_port", 587)
      from_email = self.config.get("from_email", "")
      to_email = self.config.get("to_email", "")
      password = self.get_password()

      if not all([smtp_server, smtp_port, from_email, to_email, password]):
        self.manager.log(
          "Email configuration incomplete, skipping email notification",
          "warning",
        )
        return

      # Create message
      msg = MIMEMultipart()
      msg["From"] = from_email
      msg["To"] = to_email
      msg["Subject"] = subject

      msg.attach(MIMEText(body, "plain"))

      # Send email
      with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)

      self.manager.log(f"Email sent successfully: {subject}")

    except Exception as e:
      self.manager.log(f"Failed to send email: {e}", "error")

  def send_test_email(self):
    """Send a test email (blocking, for UI button)"""
    try:
      # Get config
      smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
      smtp_port = self.config.get("smtp_port", 587)
      from_email = self.config.get("from_email", "")
      to_email = self.config.get("to_email", "")
      password = self.get_password()

      if not all([smtp_server, smtp_port, from_email, to_email, password]):
        return False, "Email configuration incomplete. Please fill all fields."

      # Create message
      msg = MIMEMultipart()
      msg["From"] = from_email
      msg["To"] = to_email
      msg["Subject"] = "FBD-WSLGUI Test Email"

      body = f"""This is a test email from FBD-WSLGUI.

Your email notifications are configured correctly!

Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FBD Node Manager - Auction Automation
"""
      msg.attach(MIMEText(body, "plain"))

      # Send email
      with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)

      return True, "Test email sent successfully!"

    except smtplib.SMTPAuthenticationError:
      return (
        False,
        "Authentication failed. Please check your email and password.\n\nFor Gmail: Use an App Password, not your regular password.",
      )
    except smtplib.SMTPException as e:
      return False, f"SMTP error: {str(e)}"
    except Exception as e:
      return False, f"Error sending test email: {str(e)}"

  def notify_critical_event(self, event_type, name, details):
    """
    Send email for critical events only:
    - registered (won auction)
    - lost (lost auction)
    - failed (automation error)
    - competing_threat (high competing bid detected)
    """
    if event_type not in ["registered", "lost", "failed", "competing_threat"]:
      return # Only send emails for critical events

    # Build subject and body based on event type
    if event_type == "registered":
      subject = f"[*] AUCTION WON - {name}"
      body = f"""CONGRATULATIONS! You won the auction for '{name}'!

The name has been successfully registered to your wallet.

{details}

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FBD Node Manager - Auction Automation
"""

    elif event_type == "lost":
      subject = f"[X] Auction Lost - {name}"
      body = f"""Unfortunately, the auction for '{name}' was lost.

{details}

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FBD Node Manager - Auction Automation
"""

    elif event_type == "failed":
      subject = f"[!] AUTOMATION FAILED - {name}"
      body = f"""ALERT: Automation failed for '{name}'

Error Details:
{details}

Please check the application logs for more information.

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FBD Node Manager - Auction Automation
"""

    elif event_type == "competing_threat":
      subject = f"[!] COMPETING BID ALERT - {name}"
      body = f"""WARNING: A competing bid has been detected!

{details}

You may want to check the auction status and consider adjusting your strategy.

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FBD Node Manager - Auction Automation
"""

    # Send the email
    self.send_email(subject, body)


# ============================================================================
# AUCTION AUTOMATION - STAGE 2: BACKGROUND MONITORING
# ============================================================================


class AuctionMonitor:
  """
  Background monitoring thread for auction automation
  Polls auction states and triggers automated actions
  """

  def __init__(self, manager):
    """Initialize the instance state."""
    self.manager = manager
    self.running = False
    self.thread = None
    self.check_interval = 300 # 5 minutes (300 seconds)
    self.last_check = {} # job_id -> last_checked_timestamp
    self.last_offline_log = 0 # Timestamp of last offline warning

  def start(self):
    """Start the monitoring thread"""
    if not self.running:
      self.running = True
      self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
      self.thread.start()
      self.manager.log("[OK] Auction monitor started (checking every 5 minutes)")

  def stop(self):
    """Stop the monitoring thread"""
    if self.running:
      self.running = False
      self.manager.log("Stopping auction monitor...")
      if self.thread:
        self.thread.join(timeout=5)
      self.manager.log("[OK] Auction monitor stopped")

  def _monitor_loop(self):
    """Main monitoring loop - runs in background thread"""
    while self.running:
      try:
        self._check_all_jobs()
      except Exception as e:
        self.manager.log(f"[!] Auction monitor error: {e}")

      # Sleep in small increments to allow quick shutdown
      for _ in range(self.check_interval):
        if not self.running:
          break
        time.sleep(1)

  def _check_all_jobs(self):
    """Check all active auction jobs"""
    # Check if node is running
    if not self._is_node_running():
      # Don't spam logs - only warn once per hour
      if time.time() - self.last_offline_log > 3600:
        self.manager.log("[!] Node offline, auction monitor paused")
        self.last_offline_log = time.time()
      return

    # Get current block height
    try:
      current_height = self._get_current_height()
      if current_height is None:
        return
    except Exception as e:
      self.manager.log(f"[!] Could not get block height: {e}")
      return

    # Load and check jobs
    jobs_data = self.manager.load_auction_jobs()
    active_jobs = [
      job
      for job in jobs_data["jobs"]
      if (job.get("auto_enabled", False) or job.get("auto_bid_enabled", False))
      and job.get("status") not in ["registered", "lost", "failed"]
    ]
    self.manager.log(
      f"Automation check: block={current_height}, active_jobs={len(active_jobs)}",
      "debug",
    )

    for job in jobs_data["jobs"]:
      # Skip if automation disabled
      if not (job.get("auto_enabled", False) or job.get("auto_bid_enabled", False)):
        continue

      # Skip terminal states
      if job["status"] in ["registered", "lost", "failed"]:
        continue

      # Process this job
      try:
        self._process_job(job, current_height)
      except Exception as e:
        self.manager.log(f"[!] Error processing job {job['id'][:8]}...: {e}")

  def _process_job(self, job, current_height):
    """
    Process a single job - check state and trigger actions
    Stage 3: Add automatic phase transitions
    Stage 4: Add notification triggers
    """
    # Get current name state
    name_info = self.manager.get_name_info_silent(job["name"])

    if not name_info:
      # Could not get name info
      return

    state = name_info.get("state", "UNKNOWN")
    self.manager.log(
      f"Automation check: {job['name']} state={state}, status={job['status']}",
      "debug",
    )

    # Log state checks (debug level - only occasionally)
    if (
      job["id"] not in self.last_check
      or time.time() - self.last_check[job["id"]] > 3600
    ):
      self.manager.log(
        f"Monitor: Job {job['id'][:8]}... - '{job['name']}' state={state}, job_status={job['status']}"
      )
      self.last_check[job["id"]] = time.time()

    # Stage 4: Check for competing bids (if index-auctions is enabled)
    if state == "BIDDING" and job["status"] == "bid_placed":
      self._check_competing_bids(job, name_info)

    # Stage 3: Automatic phase transitions
    # State machine logic
    auto_bid_enabled = job.get("auto_bid_enabled", job.get("auto_enabled", False))
    auto_enabled = job.get("auto_enabled", False)

    if job["status"] == "opened" and state == "BIDDING" and auto_bid_enabled:
      # Time to place bid
      self._execute_bid(job)

    elif job["status"] == "bid_placed" and state == "REVEAL" and auto_enabled:
      # Time to reveal
      self._execute_reveal(job)

    elif job["status"] == "revealed" and state == "CLOSED" and auto_enabled:
      # Check if we won, then register
      if self._did_we_win(job, name_info):
        self._execute_register(job)
      else:
        # We lost the auction
        self.manager.update_job_status(
          job["id"], "lost", message="Our bid did not win the auction"
        )
        self.manager.log(
          f"[!] Auction lost for '{job['name']}' - our bid was not highest"
        )
        # Stage 4: Notify loss
        self.manager.notification_manager.notify_lost(job["name"], job["id"])

  def _execute_bid(self, job):
    """Execute BID transaction automatically (Stage 3 + Stage 4 notifications + Stage 7 checks)"""
    try:
      # Stage 7: Check wallet unlocked
      if not self.manager.check_wallet_unlocked_before_automation(job):
        return # Wallet locked, job paused

      # Stage 7: Check sufficient funds
      if not self.manager.check_sufficient_funds(job, "bid"):
        return # Insufficient funds, job failed

      self.manager.log(f"[*]- Auto-bidding on '{job['name']}'...")

      wallet = job["wallet"]
      name = job["name"]
      bid = job["bid_amount"]
      lockup = job["lockup_amount"]

      # Execute bid (silent, no confirmation)
      result = self.manager.execute_send_bid_silent(name, wallet, bid, lockup)

      if result.get("success"):
        txid = result.get("txid")
        self.manager.update_job_status(
          job["id"],
          "bid_placed",
          txid=txid,
          block_height=self._get_current_height(),
        )

        self.manager.log(f"[OK] Auto-bid placed for '{name}': {txid[:12]}...")
        # Stage 4: Notify bid placed
        self.manager.notification_manager.notify_bid_placed(
          name, job["id"], txid, bid
        )
      else:
        # Retry logic
        job["retry_count"] = job.get("retry_count", 0) + 1
        error = result.get("error", "Unknown error")

        if job["retry_count"] < 3:
          self.manager.log(
            f"[!] Bid failed for '{name}', will retry (attempt {job['retry_count']}/3): {error}"
          )
          # Will retry on next poll
        else:
          self.manager.update_job_status(
            job["id"],
            "failed",
            error=f"Bid failed after 3 retries: {error}",
          )
          self.manager.log(
            f"[OK]- Bid failed for '{name}' after 3 retries: {error}"
          )
          # Stage 4: Notify failure
          self.manager.notification_manager.notify_failed(
            name, job["id"], error
          )

    except Exception as e:
      self.manager.log(f"[OK]- Error executing auto-bid for '{job['name']}': {e}")
      # Stage 4: Notify error
      self.manager.notification_manager.notify_failed(
        job["name"], job["id"], str(e)
      )

  def _execute_reveal(self, job):
    """Execute REVEAL transaction automatically (Stage 3 + Stage 4 notifications + Stage 7 checks)"""
    try:
      # Stage 7: Check wallet unlocked
      if not self.manager.check_wallet_unlocked_before_automation(job):
        return # Wallet locked, job paused

      self.manager.log(f"[*]- Auto-revealing bids for '{job['name']}'...")

      wallet = job["wallet"]
      name = job["name"]

      # Execute reveal (silent)
      result = self.manager.execute_send_reveal_silent(name, wallet)

      if result.get("success"):
        txids = result.get("txids", [])
        self.manager.update_job_status(
          job["id"],
          "revealed",
          txid=txids,
          block_height=self._get_current_height(),
        )

        self.manager.log(f"[OK] Auto-revealed {len(txids)} bid(s) for '{name}'")
        # Stage 4: Notify revealed
        self.manager.notification_manager.notify_revealed(
          name, job["id"], len(txids)
        )
      else:
        # Retry logic
        job["retry_count"] = job.get("retry_count", 0) + 1
        error = result.get("error", "Unknown error")

        if job["retry_count"] < 3:
          self.manager.log(
            f"[!] Reveal failed for '{name}', will retry (attempt {job['retry_count']}/3): {error}"
          )
        else:
          self.manager.update_job_status(
            job["id"],
            "failed",
            error=f"Reveal failed after 3 retries: {error}",
          )
          self.manager.log(
            f"[OK]- Reveal failed for '{name}' after 3 retries: {error}"
          )
          # Stage 4: Notify failure
          self.manager.notification_manager.notify_failed(
            name, job["id"], error
          )

    except Exception as e:
      self.manager.log(f"[OK]- Error executing auto-reveal for '{job['name']}': {e}")
      # Stage 4: Notify error
      self.manager.notification_manager.notify_failed(
        job["name"], job["id"], str(e)
      )

  def _execute_register(self, job):
    """Execute REGISTER transaction automatically (Stage 3 + Stage 4 notifications + Stage 7 checks)"""
    try:
      # Stage 7: Check wallet unlocked
      if not self.manager.check_wallet_unlocked_before_automation(job):
        return # Wallet locked, job paused

      # Stage 7: Check sufficient funds
      if not self.manager.check_sufficient_funds(job, "register"):
        return # Insufficient funds, job failed

      self.manager.log(f"[*]- Auto-registering '{job['name']}'...")

      wallet = job["wallet"]
      name = job["name"]

      # Execute register (silent)
      result = self.manager.execute_send_register_silent(name, wallet)

      if result.get("success"):
        txid = result.get("txid")
        self.manager.update_job_status(
          job["id"],
          "registered",
          txid=txid,
          block_height=self._get_current_height(),
        )

        self.manager.log(f"[OK] Auto-registered '{name}'! TXID: {txid[:12]}...")
        self.manager.log(f"[*] AUCTION WON: '{name}' successfully registered!")
        # Stage 4: Notify win!
        self.manager.notification_manager.notify_registered(
          name, job["id"], txid
        )
      else:
        # Retry logic
        job["retry_count"] = job.get("retry_count", 0) + 1
        error = result.get("error", "Unknown error")

        if job["retry_count"] < 3:
          self.manager.log(
            f"[!] Register failed for '{name}', will retry (attempt {job['retry_count']}/3): {error}"
          )
        else:
          self.manager.update_job_status(
            job["id"],
            "failed",
            error=f"Register failed after 3 retries: {error}",
          )
          self.manager.log(
            f"[OK]- Register failed for '{name}' after 3 retries: {error}"
          )
          # Stage 4: Notify failure
          self.manager.notification_manager.notify_failed(
            name, job["id"], error
          )

    except Exception as e:
      self.manager.log(
        f"[OK]- Error executing auto-register for '{job['name']}': {e}"
      )
      # Stage 4: Notify error
      self.manager.notification_manager.notify_failed(
        job["name"], job["id"], str(e)
      )

  def _did_we_win(self, job, name_info):
    """
    Check if our bid won the auction (Stage 3)

    Args:
      job: Job data
      name_info: Current name info from getnameinfo

    Returns:
      bool: True if we won, False otherwise
    """
    try:
      # Get our wallet's bids
      wallet = job["wallet"]
      name = job["name"]

      bids = self.manager.get_wallet_bids_silent(wallet, name)

      if not bids:
        self.manager.log(f"[!] No bids found for wallet '{wallet}' on '{name}'")
        return False

      # Find our revealed bids
      our_revealed_bids = [b for b in bids if b.get("revealed", False)]

      if not our_revealed_bids:
        self.manager.log(f"[!] No revealed bids found for '{name}'")
        return False

      # Get our highest bid value
      our_highest = max([float(b.get("value", 0)) for b in our_revealed_bids])

      # Get auction's highest bid (from canRegister field or highest field)
      can_register = name_info.get("canRegister", False)

      # If canRegister is true, we definitely won
      if can_register:
        self.manager.log(f"[OK] We won auction for '{name}' (canRegister=true)")
        return True

      # Otherwise, check if our bid is highest
      auction_highest = float(name_info.get("highest", 0))

      if our_highest >= auction_highest and auction_highest > 0:
        self.manager.log(
          f"[OK] We likely won auction for '{name}' (our bid: {our_highest}, highest: {auction_highest})"
        )
        return True
      else:
        self.manager.log(
          f"[!] We did not win auction for '{name}' (our bid: {our_highest}, highest: {auction_highest})"
        )
        return False

    except Exception as e:
      self.manager.log(f"[!] Error checking win status for '{job['name']}': {e}")
      return False

  def _check_competing_bids(self, job, name_info):
    """
    Check for competing bids (Stage 4)
    Only works if --index-auctions is enabled

    Args:
      job: Job data
      name_info: Current name info from getnameinfo
    """
    try:
      # Only check if we haven't notified about competing bids recently
      last_competing_check = job.get("_last_competing_check", 0)
      if time.time() - last_competing_check < 3600: # Check at most once per hour
        return

      # Get our bid amount
      our_bid = float(job["bid_amount"])

      # Try to get auction bids (requires --index-auctions)
      try:
        cmd, _ = self.manager.get_fbdctl_command("getauctionbids", job["name"])
        result = subprocess.run(
          cmd,
          capture_output=True,
          text=True,
          cwd=Path(self.manager.fbd_path_var.get()).parent,
          timeout=10,
        )

        if result.returncode == 0:
          response = json.loads(result.stdout)
          data = (
            response.get("result", {})
            if isinstance(response, dict)
            else response
          )

          # Get all bids
          all_bids = data.get("bids", [])

          # Check for higher bids from other bidders
          for bid in all_bids:
            bid_value = float(bid.get("value", 0))
            bid_address = bid.get("address", "")

            # Get our wallet address to compare
            wallet = job["wallet"]
            wallet_info_result = self.manager.rpc_call(
              "selectwallet", wallet
            )

            # If this is not our bid and it's higher, notify
            if bid_value > our_bid:
              # Update last check
              job["_last_competing_check"] = time.time()

              # Notify
              self.manager.notification_manager.notify_competing_bid(
                job["name"], our_bid, bid_value, job["id"]
              )
              self.manager.log(
                f"[!] Competing bid detected on '{job['name']}': {bid_value} FBC (ours: {our_bid} FBC)"
              )
              break

      except Exception:
        # --index-auctions not enabled or command failed
        # Silently skip - this is optional functionality
        pass

    except Exception as e:
      # Don't spam errors - this is optional functionality
      pass

  def _is_node_running(self):
    """Check if FBD node is running"""
    try:
      # Check if process exists
      if (
        not self.manager.fbd_process
        or self.manager.fbd_process.poll() is not None
      ):
        return False

      # Quick RPC ping
      result = self.manager.rpc_call("getblockchaininfo")
      return result is not None
    except:
      return False

  def _get_current_height(self):
    """Get current blockchain height"""
    try:
      info = self.manager.rpc_call("getblockchaininfo")
      if info:
        return info.get("blocks", None)
      return None
    except Exception as e:
      self.manager.log(f"Error getting blockchain height: {e}")
      return None


# ============================================================================
# MAIN FBD MANAGER CLASS
# ============================================================================


class FBDManager:
  """Main FBDManager class."""
  def __init__(self, root):
    """Initialize the instance state."""
    self.root = root
    self.ui_toolkit_mode = _normalize_ui_toolkit(getattr(root, "_ui_toolkit_mode", "")) or UI_TOOLKIT_TTK
    self.customtkinter_active = self.ui_toolkit_mode == UI_TOOLKIT_CUSTOMTK and ctk is not None
    self.root.title("FBD Node Manager")
    self.root.geometry("1125x875") # 25% larger (was 900x700)

    # Configuration
    self.config_file = Path.home() / ".fbdgui" / "fbdgui_config.json"
    self.config = self.load_config()
    self.theme_mode_labels = {
      "system": "Same as system",
      "dark": "Dark",
      "light": "Light",
    }
    self.theme_label_to_mode = {
      label: mode for mode, label in self.theme_mode_labels.items()
    }
    self.theme_mode_var = tk.StringVar(value="system")
    self.theme_choice_var = tk.StringVar(value=self.theme_mode_labels["system"])
    self.ui_toolkit_labels = {
      UI_TOOLKIT_TTK: "Legacy ttk (current)",
      UI_TOOLKIT_CUSTOMTK: "Rounded CustomTkinter (test)",
    }
    self.ui_toolkit_label_to_mode = {
      label: mode for mode, label in self.ui_toolkit_labels.items()
    }
    self.ui_toolkit_var = tk.StringVar(value=self.ui_toolkit_mode)
    self.ui_toolkit_choice_var = tk.StringVar(
      value=self.ui_toolkit_labels.get(self.ui_toolkit_mode, self.ui_toolkit_labels[UI_TOOLKIT_TTK])
    )

    # Setup log file
    self.log_file = Path.home() / ".fbdgui" / "fbdgui_test.log"
    self.log_file.parent.mkdir(parents=True, exist_ok=True)

    # Auction automation - Stage 0: Foundation
    self.auction_jobs_file = Path.home() / ".fbdgui" / "auction_jobs.json"
    self._ensure_auction_jobs_file()

    # Stage 2: Background monitoring
    self.auction_monitor = None # Will be initialized after UI creation

    # Process tracking
    self.fbd_process = None
    self.pool_miner_process = None
    self.monitoring = False
    self.restart_count = 0
    self.restart_in_progress = False
    self.blocks_mined_session = 0 # Blocks won this session
    self.total_blocks_mined = 0 # Total blocks from blockchain

    # RPC settings
    self.rpc_host = "127.0.0.1"
    self.rpc_port = 32869 # mainnet default
    self.rpc_user = "x"
    self.rpc_password = None

    # Paths to FBD executables (relative to this script)
    self.script_dir = Path(__file__).parent
    self.fbd_dir = self.script_dir.parent / "fbd_node" / "fbd-latest-linux-x86_64"

    # Stage 4: Initialize notification manager (BEFORE UI creation)
    self.notification_manager = NotificationManager(self)

    # Stage 5: Initialize email manager (BEFORE UI creation)
    self.email_manager = EmailManager(self)

    # Stage 2: Initialize auction monitor (BEFORE UI creation)
    self.auction_monitor = AuctionMonitor(self)

    # Block calc refresh state
    self.calc_refresh_in_progress = False
    self.calc_refresh_retry_count = 0
    self.calc_refresh_max_retries = 6 # 6 retries x 5 seconds = 30 seconds max wait
    self.rollout_reminders = []
    self.watchlist = []
    self._watchlist_check_tick = 0
    self._ctk_scrollable_frames = []
    self._ctk_section_outers = []
    self._ctk_section_bodies = []
    self._ctk_section_titles = []
    self._ctk_entries = []
    self._ctk_buttons = []
    self._ctk_textboxes = []

    # Create UI
    self.create_notebook()
    self.create_menu()
    self.create_exit_button()

    # Bind keyboard shortcuts
    self.root.bind("<Control-q>", self.on_ctrl_q)

    # Load saved settings
    self.load_saved_settings()

    # Start status monitoring
    self.start_monitoring()

    # Stage 7: Restore auction jobs on startup (crash recovery)
    self.restore_auction_jobs_on_startup()

    # Start the monitor
    self.auction_monitor.start()

    # Log startup message with diagnostic info
    self.log("=" * 60)
    self.log("FBD Node Manager GUI v4.1.0 Started (TEST)")
    self.log(f"[*][!] Log file: {self.log_file}")
    self.log(f"[*][!] Log directory: {self.log_file.parent}")
    self.log("=" * 60)
    self.log(f"GUI config directory: ~/.fbdgui/")
    self.log(f"Log file: {self.log_file}")
    self.log(f"Profiles directory: ~/.fbdgui/profiles/")
    self.log(f"Notifications file: {self.notification_manager.notification_file}")
    self.log(f"Email config: {self.email_manager.config_file}")
    self.log("=" * 60)

    # Startup check for newer miner/fbd binaries (non-blocking)
    self.root.after(2500, self.startup_binary_update_check)

  def _convert_to_wsl_path(self, windows_path):
    """
    Convert Windows path to WSL path
    E.g., E:\\path\\to\\file -> /mnt/e/path/to/file
    """
    # If already a WSL path, return as-is
    if windows_path.startswith("/"):
      return windows_path

    # Convert backslashes to forward slashes
    path = windows_path.replace("\\", "/")

    # Extract drive letter and path
    if ":" in path:
      parts = path.split(":", 1)
      drive = parts[0].lower()
      rest = parts[1]
      # Convert to WSL format: /mnt/X/path
      wsl_path = f"/mnt/{drive}{rest}"
      return wsl_path

    # If no drive letter, return as-is (might be relative path)
    return path

  def get_fbdctl_command(self, *args):
    """Build fbdctl command with RPC connection parameters"""
    fbd_path = Path(self.fbd_path_var.get()).resolve()
    fbdctl_path = str(fbd_path.parent / "fbdctl")

    # Build command with RPC connection parameters
    cmd = [fbdctl_path]

    # Always add RPC connection parameters to ensure fbdctl connects to the right instance
    rpc_host = self.rpc_host_var.get() or "127.0.0.1"
    rpc_port = self.rpc_port_var.get() or "32869"

    cmd.extend(["--rpc-host", rpc_host])
    cmd.extend(["--rpc-port", rpc_port])

    # Add the actual command arguments
    cmd.extend(args)

    # If running on Windows, wrap command with WSL and convert paths
    if sys.platform == "win32":
      # Convert Windows path to WSL path
      wsl_path = self._convert_to_wsl_path(fbdctl_path)
      cmd[0] = wsl_path # Replace fbdctl path with WSL version
      cmd = ["wsl"] + cmd

    return cmd, fbdctl_path

  def create_menu(self):
    """Create menu bar"""
    menubar = tk.Menu(self.root)
    self.root.configure(menu=menubar)

    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Save Settings", command=self.save_settings)
    file_menu.add_command(label="Load Settings", command=self.load_settings_file)
    file_menu.add_separator()
    file_menu.add_command(label="Open Log File", command=self.open_log_file)
    file_menu.add_command(
      label="Open GUI Config Directory", command=self.open_config_dir
    )
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=self.on_closing)

  def create_exit_button(self):
    """Create help and exit buttons in top-right corner"""
    # Create container frame for both buttons
    button_container = tk.Frame(self.root, bg=self.root["bg"])
    button_container.place(relx=1.0, rely=0, anchor="ne", x=-5, y=5)

    # Help button (blue, on the left)
    help_btn = tk.Button(
      button_container,
      text="? HELP",
      command=self.show_help,
      bg="#0066cc",
      fg="white",
      font=("Arial", 10, "bold"),
      relief="raised",
      bd=2,
      padx=10,
      pady=5,
      activebackground="#004499",
      activeforeground="white",
    )
    help_btn.pack(side="left", padx=(0, 5))

    # Exit button (red, on the right)
    exit_btn = tk.Button(
      button_container,
      text="[X] EXIT",
      command=self.on_closing,
      bg="red",
      fg="white",
      font=("Arial", 10, "bold"),
      relief="raised",
      bd=2,
      padx=10,
      pady=5,
      activebackground="darkred",
      activeforeground="white",
    )
    exit_btn.pack(side="left")

  def create_notebook(self):
    """Create tabbed interface"""
    if self.customtkinter_active:
      self.notebook = ctk.CTkTabview(self.root)
    else:
      self.notebook = ttk.Notebook(self.root)
    self._tab_names = []
    self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

    # Create tabs
    self.create_node_tab()
    self.create_wallet_tab()
    self.create_auction_tab()
    self.create_block_calc_tab()
    self.create_settings_tab()

  def _add_notebook_tab(self, name):
    """Add a tab and return its container frame (works for both ttk and CTK)."""
    if self.customtkinter_active:
      self.notebook.add(name)
      self._tab_names.append(name)
      return self.notebook.tab(name)
    frame = ttk.Frame(self.notebook)
    self.notebook.add(frame, text=name)
    self._tab_names.append(name)
    return frame

  def _notebook_select(self, tab_or_index):
    """Select a tab â€” handles both ttk.Notebook and ctk.CTkTabview APIs."""
    if self.customtkinter_active:
      if isinstance(tab_or_index, int):
        if 0 <= tab_or_index < len(self._tab_names):
          self.notebook.set(self._tab_names[tab_or_index])
      elif isinstance(tab_or_index, str):
        self.notebook.set(tab_or_index)
    else:
      self.notebook.select(tab_or_index)

  def _create_scrollable_frame(self, parent):
    """Create scrollable content frame."""
    if self.customtkinter_active:
      mode = self._get_effective_theme_mode()
      bg = "#000000" if mode == "dark" else "#ececec"
      frame = ctk.CTkFrame(parent, corner_radius=0, fg_color=bg)
      self._ctk_scrollable_frames.append(frame)
      return frame
    return ttk.Frame(parent)

  def _create_section_frame(self, parent, text, padding=10):
    """Create a section with visible title and rounded border in CTK mode."""
    if self.customtkinter_active:
      mode = self._get_effective_theme_mode()
      is_dark = mode == "dark"
      section_bg = "#000000" if is_dark else "#ececec"
      border = "#4a4a4a" if is_dark else "#c3c3c3"
      title_fg = "#f2f2f2" if is_dark else "#111111"

      outer = ctk.CTkFrame(
        parent,
        corner_radius=12,
        fg_color=section_bg,
        border_width=1,
        border_color=border,
      )
      title = ctk.CTkLabel(
        outer,
        text=text,
        font=ctk.CTkFont(family="Arial", size=10, weight="bold", underline=True),
        anchor="w",
        text_color=title_fg,
      )
      title.pack(fill="x", padx=padding, pady=(6, 0))

      body = ctk.CTkFrame(outer, corner_radius=0, fg_color=section_bg)
      body.pack(fill="both", expand=True, padx=padding, pady=(4, padding))
      self._ctk_section_outers.append(outer)
      self._ctk_section_bodies.append(body)
      self._ctk_section_titles.append(title)
      return outer, body

    frame = ttk.LabelFrame(parent, text=text, padding=padding)
    return frame, frame

  def _create_inline_frame(self, parent):
    """Create a lightweight inline container."""
    if self.customtkinter_active:
      return ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
    return ttk.Frame(parent)

  def _create_entry(self, parent, textvariable=None, width=32, **kwargs):
    """Create an entry widget with rounded corners in CTK mode."""
    entry_kwargs = dict(kwargs)
    if textvariable is not None:
      entry_kwargs["textvariable"] = textvariable
    if "width" not in entry_kwargs:
      entry_kwargs["width"] = width

    if self.customtkinter_active:
      mode = self._get_effective_theme_mode()
      is_dark = mode == "dark"
      entry_kwargs.setdefault("corner_radius", 10)
      entry_kwargs.setdefault("fg_color", "#0f0f0f" if is_dark else "#ececec")
      entry_kwargs.setdefault("border_color", "#4a4a4a" if is_dark else "#bdbdbd")
      entry_kwargs.setdefault("text_color", "#f2f2f2" if is_dark else "#111111")
      entry = ctk.CTkEntry(parent, **entry_kwargs)
      self._ctk_entries.append(entry)
      return entry

    return ttk.Entry(parent, **entry_kwargs)

  def _create_button(self, parent, text, command, state="normal", **kwargs):
    """Create a button with rounded corners in CTK mode."""
    button_kwargs = dict(kwargs)
    button_kwargs.update({"text": text, "command": command})

    if self.customtkinter_active:
      mode = self._get_effective_theme_mode()
      is_dark = mode == "dark"
      button_kwargs.setdefault("corner_radius", 10)
      button_kwargs.setdefault("fg_color", "#111111" if is_dark else "#ececec")
      button_kwargs.setdefault("hover_color", "#1f5f9f" if is_dark else "#d9e9f8")
      button_kwargs.setdefault("border_width", 2)
      button_kwargs.setdefault("border_color", "#7a7a7a" if is_dark else "#9a9a9a")
      button_kwargs.setdefault("text_color", "#f2f2f2" if is_dark else "#111111")
      button_kwargs.setdefault("text_color_disabled", "#8a8a8a" if is_dark else "#6e6e6e")
      button = ctk.CTkButton(parent, **button_kwargs)
      self._ctk_buttons.append(button)
      if state != "normal":
        button.configure(state=state)
      return button

    return ttk.Button(parent, state=state, **button_kwargs)

  def _create_log_widget(self, parent, lines=10, **kwargs):
    """Create a themed text area; rounded in CTK mode.

    lines is interpreted as text lines for both ttk and CTK widgets.
    """
    if self.customtkinter_active:
      mode = self._get_effective_theme_mode()
      is_dark = mode == "dark"
      textbox_kwargs = dict(kwargs)
      textbox_kwargs.setdefault("corner_radius", 10)
      textbox_kwargs.setdefault("wrap", "word")
      textbox_kwargs.setdefault("fg_color", "#050505" if is_dark else "#ececec")
      textbox_kwargs.setdefault("border_width", 1)
      textbox_kwargs.setdefault("border_color", "#4a4a4a" if is_dark else "#bdbdbd")
      textbox_kwargs.setdefault("text_color", "#f2f2f2" if is_dark else "#111111")
      # CTkTextbox height is pixels; convert requested line count to approximate pixel height.
      textbox_kwargs.setdefault("height", max(80, int(lines) * 22))
      textbox = ctk.CTkTextbox(parent, **textbox_kwargs)
      self._ctk_textboxes.append(textbox)
      return textbox

    text_kwargs = {"height": lines, "wrap": tk.WORD}
    text_kwargs.update(kwargs)
    return scrolledtext.ScrolledText(parent, **text_kwargs)

  def _create_toplevel(self):
    """Create a popup window that follows the active theme immediately."""
    dialog = tk.Toplevel(self.root)
    self._theme_dialog(dialog)
    return dialog

  def _theme_dialog(self, dialog):
    """Apply current palette to a dialog and its classic tk children."""
    effective_mode = self._get_effective_theme_mode()
    palette = self._get_theme_palette(effective_mode)
    try:
      dialog.configure(bg=palette["bg"])
    except Exception:
      pass
    self._apply_theme_to_tk_widgets(dialog, palette)
  def _bind_canvas_mousewheel(self, canvas, tab_widget):
    """Bind mousewheel scrolling to a tab's canvas only while hovered."""

    def _on_mousewheel(event):
      """ on mousewheel."""
      if hasattr(event, "delta") and event.delta:
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
      elif hasattr(event, "num"):
        if event.num == 4:
          canvas.yview_scroll(-1, "units")
        elif event.num == 5:
          canvas.yview_scroll(1, "units")

    def _bind(_event):
      """ bind."""
      canvas.bind_all("<MouseWheel>", _on_mousewheel)
      canvas.bind_all("<Button-4>", _on_mousewheel)
      canvas.bind_all("<Button-5>", _on_mousewheel)

    def _unbind(_event):
      """ unbind."""
      canvas.unbind_all("<MouseWheel>")
      canvas.unbind_all("<Button-4>")
      canvas.unbind_all("<Button-5>")

    for widget in (tab_widget, canvas):
      widget.bind("<Enter>", _bind)
      widget.bind("<Leave>", _unbind)

  def _get_effective_theme_mode(self):
    """Resolve configured mode to an effective light or dark mode."""
    mode = "system"
    if hasattr(self, "theme_mode_var"):
      mode = (self.theme_mode_var.get() or "system").strip().lower()
    if mode not in ("system", "dark", "light"):
      mode = "system"

    if mode == "system":
      try:
        red, green, blue = self.root.winfo_rgb("SystemWindow")
        luminance = (red * 299 + green * 587 + blue * 114) / 1000
        return "dark" if luminance < 32768 else "light"
      except Exception:
        return "light"

    return mode

  def _get_theme_palette(self, effective_mode):
    """Return color palette for the requested effective mode."""
    if effective_mode == "dark":
      return {
        "bg": "#000000",
        "section": "#111111",
        "line": "#4a4a4a",
        "fg": "#f2f2f2",
        "entry_bg": "#151515",
        "entry_fg": "#ffffff",
        "disabled_bg": "#9a9a9a",
        "disabled_fg": "#1f1f1f",
        "muted_fg": "#7f7f7f",
        "checkbox_bg": "#ffffff",
      }

    return {
      "bg": "#f0f0f0",
      "section": "#ececec",
      "line": "#cfcfcf",
      "fg": "#111111",
      "entry_bg": "#ffffff",
      "entry_fg": "#111111",
      "disabled_bg": "#d0d0d0",
      "disabled_fg": "#5c5c5c",
      "muted_fg": "#7a7a7a",
      "checkbox_bg": "#ffffff",
    }

  def _apply_theme_to_tk_widgets(self, widget, palette):
    """Apply base palette to classic Tk widgets recursively."""
    # Skip styling CTK-managed widgets (they handle their own appearance),
    # but still recurse into their children to reach nested classic tk widgets.
    if ctk is not None and isinstance(widget, ctk.CTkBaseClass):
      for child in widget.winfo_children():
        self._apply_theme_to_tk_widgets(child, palette)
      return
    try:
      if isinstance(widget, (tk.Frame, tk.LabelFrame, tk.Toplevel)):
        widget.configure(bg=palette["bg"])
      elif isinstance(widget, tk.Canvas):
        widget.configure(bg=palette["bg"], highlightbackground=palette["line"])
      elif isinstance(widget, tk.Checkbutton):
        widget.configure(
          bg=palette["bg"],
          fg=palette["fg"],
          activebackground=palette["line"],
          activeforeground="#111111",
          selectcolor=palette["checkbox_bg"],
          disabledforeground=palette["muted_fg"],
        )
      elif isinstance(widget, tk.Entry):
        widget.configure(
          bg=palette["entry_bg"],
          fg=palette["entry_fg"],
          insertbackground=palette["entry_fg"],
          disabledbackground=palette["disabled_bg"],
          disabledforeground=palette["disabled_fg"],
          readonlybackground=palette["disabled_bg"],
          highlightbackground=palette["line"],
        )
      elif isinstance(widget, tk.Text):
        widget.configure(
          bg=palette["entry_bg"],
          fg=palette["entry_fg"],
          insertbackground=palette["entry_fg"],
          highlightbackground=palette["line"],
          selectbackground=palette["section"],
          selectforeground=palette["entry_fg"],
        )
      elif isinstance(widget, tk.Listbox):
        widget.configure(
          bg=palette["entry_bg"],
          fg=palette["entry_fg"],
          disabledforeground=palette["muted_fg"],
          highlightbackground=palette["line"],
          selectbackground=palette["section"],
          selectforeground=palette["entry_fg"],
        )
      elif isinstance(widget, tk.Button):
        # Keep explicitly colored action buttons unchanged.
        pass
      elif isinstance(widget, tk.Label):
        widget.configure(bg=palette["bg"])
        if widget.cget("fg") in ("black", "#000000", "SystemWindowText"):
          widget.configure(fg=palette["fg"])
    except tk.TclError:
      pass

    for child in widget.winfo_children():
      self._apply_theme_to_tk_widgets(child, palette)

  def _refresh_ctk_container_theme(self, effective_mode):
    """Refresh CTK colors when theme mode changes."""
    if not self.customtkinter_active:
      return

    is_dark = effective_mode == "dark"
    section_bg = "#000000" if is_dark else "#ececec"
    border = "#4a4a4a" if is_dark else "#c3c3c3"
    title_fg = "#f2f2f2" if is_dark else "#111111"
    entry_bg = "#0f0f0f" if is_dark else "#ececec"
    entry_border = "#4a4a4a" if is_dark else "#bdbdbd"
    entry_fg = "#f2f2f2" if is_dark else "#111111"
    button_bg = "#111111" if is_dark else "#ececec"
    button_hover = "#1f5f9f" if is_dark else "#d9e9f8"
    button_border = "#7a7a7a" if is_dark else "#9a9a9a"
    button_fg = "#f2f2f2" if is_dark else "#111111"
    button_fg_disabled = "#8a8a8a" if is_dark else "#6e6e6e"
    textbox_bg = "#050505" if is_dark else "#ececec"
    textbox_border = "#4a4a4a" if is_dark else "#bdbdbd"
    textbox_fg = "#f2f2f2" if is_dark else "#111111"

    for frame in self._ctk_scrollable_frames:
      if frame.winfo_exists():
        frame.configure(fg_color=section_bg)

    for frame in self._ctk_section_outers:
      if frame.winfo_exists():
        frame.configure(fg_color=section_bg, border_color=border)

    for frame in self._ctk_section_bodies:
      if frame.winfo_exists():
        frame.configure(fg_color=section_bg)

    for label in self._ctk_section_titles:
      if label.winfo_exists():
        label.configure(text_color=title_fg)

    for entry in self._ctk_entries:
      if entry.winfo_exists():
        entry.configure(fg_color=entry_bg, border_color=entry_border, text_color=entry_fg)

    for button in self._ctk_buttons:
      if button.winfo_exists():
        button.configure(
          fg_color=button_bg,
          hover_color=button_hover,
          border_color=button_border,
          text_color=button_fg,
          text_color_disabled=button_fg_disabled,
        )

    for textbox in self._ctk_textboxes:
      if textbox.winfo_exists():
        textbox.configure(
          fg_color=textbox_bg,
          border_color=textbox_border,
          text_color=textbox_fg,
        )

  def apply_theme(self):
    """Apply selected appearance mode to the whole interface."""
    effective_mode = self._get_effective_theme_mode()
    palette = self._get_theme_palette(effective_mode)

    if self.customtkinter_active:
      ctk.set_appearance_mode(effective_mode)
      # Keep default theme stable during early test migration.
      ctk.set_default_color_theme("dark-blue")
      self._refresh_ctk_container_theme(effective_mode)

    self.root.configure(bg=palette["bg"])
    style = ttk.Style(self.root)
    style.theme_use("clam")

    style.configure(".", background=palette["bg"], foreground=palette["fg"])
    style.configure("TFrame", background=palette["bg"])
    style.configure("TLabelframe", background=palette["bg"], bordercolor=palette["line"])
    style.configure("TLabelframe.Label", background=palette["bg"], foreground=palette["fg"])
    style.configure("TLabel", background=palette["bg"], foreground=palette["fg"])
    style.configure(
      "TButton",
      background=palette["section"],
      foreground=palette["fg"],
      bordercolor=palette["line"],
      lightcolor=palette["line"],
      darkcolor=palette["line"],
      relief="solid",
      borderwidth=1,
    )
    style.map(
      "TButton",
      background=[("active", palette["line"]), ("disabled", palette["disabled_bg"])],
      foreground=[("active", "#111111"), ("disabled", palette["muted_fg"])],
    )
    style.configure(
      "TEntry",
      fieldbackground=palette["entry_bg"],
      foreground=palette["entry_fg"],
      bordercolor=palette["line"],
      insertcolor=palette["entry_fg"],
    )
    style.map(
      "TEntry",
      fieldbackground=[("readonly", palette["disabled_bg"]), ("disabled", palette["disabled_bg"])],
      foreground=[("readonly", palette["disabled_fg"]), ("disabled", palette["disabled_fg"])],
    )
    style.configure(
      "TCombobox",
      fieldbackground=palette["entry_bg"],
      foreground=palette["entry_fg"],
      background=palette["section"],
      arrowcolor=palette["fg"],
      bordercolor=palette["line"],
    )
    style.map(
      "TCombobox",
      fieldbackground=[("readonly", palette["entry_bg"]), ("disabled", palette["disabled_bg"])],
      foreground=[("disabled", palette["disabled_fg"]), ("readonly", palette["entry_fg"])],
      selectbackground=[("readonly", palette["entry_bg"])],
      selectforeground=[("readonly", palette["entry_fg"])],
    )
    style.configure(
      "TCheckbutton",
      background=palette["bg"],
      foreground=palette["fg"],
      indicatorbackground=palette["checkbox_bg"],
      indicatorforeground="#000000",
    )
    style.map(
      "TCheckbutton",
      background=[("active", palette["line"])],
      foreground=[("active", "#111111"), ("disabled", palette["muted_fg"])],
      indicatorbackground=[("selected", palette["checkbox_bg"]), ("!selected", palette["checkbox_bg"])],
    )
    style.configure("TNotebook", background=palette["bg"], bordercolor=palette["line"])
    style.configure(
      "TNotebook.Tab",
      background=palette["section"],
      foreground=palette["fg"],
      bordercolor=palette["line"],
      lightcolor=palette["line"],
      darkcolor=palette["line"],
    )
    style.map(
      "TNotebook.Tab",
      background=[("selected", palette["bg"]), ("active", palette["line"])],
      foreground=[("active", "#111111"), ("disabled", palette["muted_fg"])],
    )
    style.configure(
      "Treeview",
      background=palette["entry_bg"],
      foreground=palette["entry_fg"],
      fieldbackground=palette["entry_bg"],
      bordercolor=palette["line"],
    )
    style.configure(
      "Treeview.Heading",
      background=palette["section"],
      foreground=palette["fg"],
      bordercolor=palette["line"],
    )

    self._apply_theme_to_tk_widgets(self.root, palette)

  def on_ui_toolkit_changed(self, _event=None):
    """Persist UI toolkit choice and prompt restart to apply it."""
    selected_label = (self.ui_toolkit_choice_var.get() or "").strip()
    selected_mode = self.ui_toolkit_label_to_mode.get(selected_label, UI_TOOLKIT_TTK)
    selected_mode = _normalize_ui_toolkit(selected_mode) or UI_TOOLKIT_TTK
    self.ui_toolkit_var.set(selected_mode)

    if selected_mode == self.ui_toolkit_mode:
      return

    if selected_mode == UI_TOOLKIT_CUSTOMTK and ctk is None:
      messagebox.showwarning(
        "CustomTkinter Not Installed",
        "Install CustomTkinter first:\n\n"
        "  pip install customtkinter\n\n"
        "Keeping Legacy ttk mode.",
      )
      self.ui_toolkit_var.set(UI_TOOLKIT_TTK)
      self.ui_toolkit_choice_var.set(self.ui_toolkit_labels[UI_TOOLKIT_TTK])
      return

    self.ui_toolkit_mode = selected_mode
    self.save_config()
    restart_now = messagebox.askyesno(
      "Restart Required",
      "UI toolkit selection saved.\n\n"
      "Restart now to apply the toolkit switch?",
    )
    if not restart_now:
      return

    os.environ[UI_TOOLKIT_ENV_VAR] = selected_mode
    python_executable = sys.executable
    script_path = os.path.abspath(__file__)
    os.execv(python_executable, [python_executable, script_path])

  def on_theme_mode_changed(self, _event=None):
    """Update active theme when the appearance combobox changes."""
    selected_label = (self.theme_choice_var.get() or "").strip()
    selected_mode = self.theme_label_to_mode.get(selected_label, "system")
    self.theme_mode_var.set(selected_mode)
    self.apply_theme()

  def create_node_tab(self):
    """Create node control tab"""
    tab = self._add_notebook_tab("Node & Mining")

    # Create canvas and scrollbar for scrollable content
    canvas = tk.Canvas(tab, highlightthickness=0)
    scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
    scrollable_frame = self._create_scrollable_frame(canvas)

    scrollable_frame.bind(
      "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window(
      (0, 0), window=scrollable_frame, anchor="nw"
    )
    canvas.bind(
      "<Configure>",
      lambda e: canvas.itemconfigure(canvas_window, width=e.width),
    )
    canvas.configure(yscrollcommand=scrollbar.set)

    # Pack canvas and scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Enable mousewheel scrolling while cursor is over this tab
    self._bind_canvas_mousewheel(canvas, tab)

    # Status frame
    status_outer, status_frame = self._create_section_frame(scrollable_frame, "Node Status")
    status_outer.pack(fill="x", padx=10, pady=5)

    self.status_label = ttk.Label(
      status_frame, text="Status: Stopped", font=("Arial", 10, "bold")
    )
    self.status_label.pack()

    self.block_label = ttk.Label(status_frame, text="Block Height: -")
    self.block_label.pack()

    self.peers_label = ttk.Label(status_frame, text="Peers: -")
    self.peers_label.pack()

    self.restart_label = ttk.Label(status_frame, text="Restarts: 0")
    self.restart_label.pack()

    self.blocks_won_label = ttk.Label(
      status_frame,
      text="Blocks Won (Session): 0",
      font=("Arial", 10, "bold"),
      foreground="blue",
    )
    self.blocks_won_label.pack()

    self.total_blocks_label = ttk.Label(
      status_frame, text="Total Blocks (Chain): -"
    )
    self.total_blocks_label.pack()

    # Mining config frame
    config_outer, config_frame = self._create_section_frame(scrollable_frame, "Mining Configuration")
    config_outer.pack(fill="both", expand=True, padx=10, pady=5)

    # Network
    ttk.Label(config_frame, text="Network:").grid(
      row=0, column=0, sticky="w", pady=2
    )
    self.network_var = tk.StringVar(value="main")
    network_combo = ttk.Combobox(
      config_frame,
      textvariable=self.network_var,
      values=["main", "testnet", "regtest", "simnet"],
      width=30,
      state="readonly",
    )
    network_combo.grid(row=0, column=1, sticky="ew", pady=2)

    # Host
    ttk.Label(config_frame, text="Host:").grid(row=1, column=0, sticky="w", pady=2)
    self.host_var = tk.StringVar(value="0.0.0.0")
    self.host_entry = self._create_entry(config_frame, self.host_var, width=32)
    self.host_entry.grid(row=1, column=1, sticky="ew", pady=2)

    # Log level
    ttk.Label(config_frame, text="Log Level:").grid(
      row=2, column=0, sticky="w", pady=2
    )
    self.loglevel_var = tk.StringVar(value="info")
    loglevel_combo = ttk.Combobox(
      config_frame,
      textvariable=self.loglevel_var,
      values=["trace", "debug", "info", "warning", "error"],
      width=30,
      state="readonly",
    )
    loglevel_combo.grid(row=2, column=1, sticky="ew", pady=2)

    # Agent name
    ttk.Label(config_frame, text="Agent:").grid(row=3, column=0, sticky="w", pady=2)
    self.agent_var = tk.StringVar(value="tiMaxal")
    self.agent_entry = self._create_entry(config_frame, self.agent_var, width=32)
    self.agent_entry.grid(row=3, column=1, sticky="ew", pady=2)

    # Enable mining
    self.mining_enabled = tk.BooleanVar(value=True)
    self.mining_checkbox = ttk.Checkbutton(
      config_frame,
      text="Enable Mining",
      variable=self.mining_enabled,
      command=self.toggle_mining_options,
    )
    self.mining_checkbox.grid(row=4, column=0, columnspan=2, sticky="w", pady=5)

    # Miner address
    ttk.Label(config_frame, text="Miner Address:").grid(
      row=5, column=0, sticky="w", pady=2
    )
    self.miner_address_var = tk.StringVar(
      value="fb1qp979k4ell5hvaktk5e3d6man66jrz2ucvkt748"
    )
    self.miner_address_entry = self._create_entry(
      config_frame, self.miner_address_var, width=32
    )
    self.miner_address_entry.grid(row=5, column=1, sticky="ew", pady=2)

    # Miner threads
    max_threads = os.cpu_count() or 1
    default_miner_threads = max(1, max_threads // 2)
    ttk.Label(config_frame, text=f"Miner Threads (max: {max_threads}):").grid(
      row=6, column=0, sticky="w", pady=2
    )
    self.miner_threads_var = tk.StringVar(value=str(default_miner_threads))
    self.miner_threads_entry = self._create_entry(
      config_frame, self.miner_threads_var, width=18
    )
    self.miner_threads_entry.grid(row=6, column=1, sticky="ew", pady=2)

    # Pool miner
    pool_outer, pool_frame = self._create_section_frame(scrollable_frame, "Pool Miner")
    pool_outer.pack(fill="x", padx=10, pady=5)

    ttk.Label(pool_frame, text="Wallet Address:").grid(
      row=0, column=0, sticky="w", pady=2
    )
    self.pool_miner_address_var = tk.StringVar(
      value=self.config.get("pool_miner_address", self.miner_address_var.get())
    )
    self.pool_miner_address_entry = self._create_entry(
      pool_frame, self.pool_miner_address_var, width=32
    )
    self.pool_miner_address_entry.grid(row=0, column=1, sticky="ew", pady=2)

    ttk.Label(pool_frame, text="Host:").grid(row=1, column=0, sticky="w", pady=2)
    self.pool_miner_host_var = tk.StringVar(value="pool.woodburn.au")
    self.pool_miner_host_entry = self._create_entry(
      pool_frame, self.pool_miner_host_var, width=32
    )
    self.pool_miner_host_entry.grid(row=1, column=1, sticky="ew", pady=2)

    ttk.Label(pool_frame, text="Threads (0 = auto):").grid(
      row=2, column=0, sticky="w", pady=2
    )
    self.pool_miner_threads_var = tk.StringVar(value="0")
    self.pool_miner_threads_entry = self._create_entry(
      pool_frame, self.pool_miner_threads_var, width=32
    )
    self.pool_miner_threads_entry.grid(row=2, column=1, sticky="ew", pady=2)

    pool_button_frame = self._create_inline_frame(pool_frame)
    pool_button_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 0))

    self.start_pool_miner_btn = self._create_button(
      pool_button_frame, text="Start Pool Miner", command=self.start_pool_miner
    )
    self.start_pool_miner_btn.pack(side="left", padx=5)

    self.stop_pool_miner_btn = self._create_button(
      pool_button_frame,
      text="Stop Pool Miner",
      command=self.stop_pool_miner,
      state="disabled",
    )
    self.stop_pool_miner_btn.pack(side="left", padx=5)

    pool_frame.columnconfigure(1, weight=1)

    # Index options
    self.index_tx_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(
      config_frame,
      text="Index Transactions (--index-tx)",
      variable=self.index_tx_var,
    ).grid(row=7, column=0, sticky="w", pady=2)
    ttk.Label(
      config_frame,
      text="(General blockchain queries)",
      font=("Arial", 8),
      foreground="gray",
    ).grid(row=7, column=1, sticky="w", padx=(5, 0), pady=2)

    self.index_address_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
      config_frame,
      text="Index Addresses (--index-address)",
      variable=self.index_address_var,
    ).grid(row=8, column=0, sticky="w", pady=2)
    ttk.Label(
      config_frame,
      text="[!] Required for wallet operations",
      font=("Arial", 8, "bold"),
      foreground="#cc6600",
    ).grid(row=8, column=1, sticky="w", padx=(5, 0), pady=2)

    # Warning about enabling on existing chain
    ttk.Label(
      config_frame,
      text="[!] CRITICAL: If enabling on existing chain, delete ~/.fbd/chain first!",
      font=("Arial", 7),
      foreground="#cc0000",
    ).grid(row=8, column=2, sticky="w", padx=(5, 0), pady=2)

    self.index_auctions_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
      config_frame,
      text="Index Auctions (--index-auctions)",
      variable=self.index_auctions_var,
    ).grid(row=9, column=0, sticky="w", pady=2)
    ttk.Label(
      config_frame,
      text="[!] Required for auction operations",
      font=("Arial", 8, "bold"),
      foreground="#cc6600",
    ).grid(row=9, column=1, sticky="w", padx=(5, 0), pady=2)

    # Warning about enabling on existing chain
    ttk.Label(
      config_frame,
      text="[!] CRITICAL: If enabling on existing chain, delete ~/.fbd/chain first!",
      font=("Arial", 7),
      foreground="#cc0000",
    ).grid(row=9, column=2, sticky="w", padx=(5, 0), pady=2)

    config_frame.columnconfigure(1, weight=1)
    config_frame.columnconfigure(2, weight=1)

    # Control buttons
    button_frame = self._create_inline_frame(scrollable_frame)
    button_frame.pack(fill="x", padx=10, pady=5)

    self.start_btn = self._create_button(button_frame, text="Start Node", command=self.start_node)
    self.start_btn.pack(side="left", padx=5)

    self.stop_btn = self._create_button(
      button_frame, text="Stop Node", command=self.stop_node, state="disabled"
    )
    self.stop_btn.pack(side="left", padx=5)

    self._create_button(
      button_frame, text="Refresh Status", command=self.refresh_status
    ).pack(side="left", padx=5)
    self._create_button(
      button_frame, text="Mining Stats", command=self.get_mining_stats
    ).pack(side="left", padx=5)
    self._create_button(
      button_frame, text="Delete Chain Data", command=self.delete_chain_data
    ).pack(side="left", padx=5)

    # Log output
    log_outer, log_frame = self._create_section_frame(scrollable_frame, "Node Output", padding=5)
    log_outer.pack(fill="both", expand=True, padx=10, pady=5)

    self.log_text = self._create_log_widget(log_frame)
    self.log_text.pack(fill="both", expand=True)

    # Log controls
    log_controls = self._create_inline_frame(log_frame)
    log_controls.pack(fill="x", pady=(5, 0))

    self._create_button(
      log_controls, text="Clear Log Display", command=self.clear_log_display
    ).pack(side="left", padx=5)
    self._create_button(log_controls, text="Open Log File", command=self.open_log_file).pack(
      side="left", padx=5
    )

    log_path_label = ttk.Label(
      log_controls,
      text=f"Log: ~/.fbdgui/fbdgui_test.log",
      font=("Arial", 8),
      foreground="gray",
    )
    log_path_label.pack(side="left", padx=10)

  def create_wallet_tab(self):
    """Create wallet operations tab"""
    tab = self._add_notebook_tab("Wallet")

    # Create canvas and scrollbar for scrollable content
    canvas = tk.Canvas(tab, highlightthickness=0)
    scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
    scrollable_frame = self._create_scrollable_frame(canvas)

    scrollable_frame.bind(
      "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window(
      (0, 0), window=scrollable_frame, anchor="nw"
    )
    canvas.bind(
      "<Configure>",
      lambda e: canvas.itemconfigure(canvas_window, width=e.width),
    )
    canvas.configure(yscrollcommand=scrollbar.set)

    # Pack canvas and scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Enable mousewheel scrolling while cursor is over this tab
    self._bind_canvas_mousewheel(canvas, tab)

    # Info message
    info_msg = ttk.Label(
      scrollable_frame,
      text="[!] Note: The FBD node must be running for wallet operations to work",
      font=("Arial", 9),
      foreground="red",
      background="#fff3cd",
      padding=5,
      relief="solid",
      borderwidth=1,
    )
    info_msg.pack(fill="x", padx=10, pady=(5, 0))

    # Wallet selection
    wallet_outer, wallet_frame = self._create_section_frame(
      scrollable_frame, "Wallet Selection", padding=10
    )
    wallet_outer.pack(fill="x", padx=10, pady=5)

    ttk.Label(wallet_frame, text="Active Wallet:").pack(side="left", padx=5)
    self.wallet_name_var = tk.StringVar(value="main")
    self.wallet_combo = ttk.Combobox(
      wallet_frame,
      textvariable=self.wallet_name_var,
      width=20,
      state="readonly",
    )
    self.wallet_combo.pack(side="left", padx=5)
    self.wallet_combo.bind("<<ComboboxSelected>>", self.on_active_wallet_selected)
    self.wallet_combo.bind(
      "<Button-1>", lambda _e: self.list_wallets(show_feedback=False)
    )

    self._create_button(
      wallet_frame, text="Copy Address", command=self.copy_wallet_address_dialog
    ).pack(side="left", padx=5)
    self._create_button(
      wallet_frame, text="Create Wallet", command=self.create_wallet
    ).pack(side="left", padx=5)
    self._create_button(
      wallet_frame, text="Import Wallet", command=self.import_wallet
    ).pack(side="left", padx=5)
    self._create_button(
      wallet_frame, text="Delete Wallet", command=self.delete_wallet
    ).pack(side="left", padx=5)

    self.update_wallet_dropdown([self.wallet_name_var.get() or "main"])

    # Wallet info
    info_outer, info_frame = self._create_section_frame(
      scrollable_frame, "Wallet Information", padding=10
    )
    info_outer.pack(fill="x", padx=10, pady=5)

    self.balance_label = ttk.Label(
      info_frame, text="Balance: -", font=("Arial", 11, "bold")
    )
    self.balance_label.pack()

    self.address_label = ttk.Label(info_frame, text="Address: -")
    self.address_label.pack()

    self._create_button(
      info_frame, text="Get Wallet Info", command=self.get_wallet_info
    ).pack(pady=5)

    # Send payment
    send_outer, send_frame = self._create_section_frame(scrollable_frame, "Send Payment", padding=10)
    send_outer.pack(fill="x", padx=10, pady=5)

    ttk.Label(send_frame, text="To Address:").grid(
      row=0, column=0, sticky="w", pady=2
    )
    self.send_address_var = tk.StringVar()
    # Use Combobox to show saved addresses
    saved_addresses = self.config.get("saved_addresses", [])
    self.send_address_combo = ttk.Combobox(
      send_frame,
      textvariable=self.send_address_var,
      values=saved_addresses,
      width=48,
    )
    self.send_address_combo.grid(row=0, column=1, sticky="ew", pady=2)
    self._create_button(
      send_frame, text="Save", command=self.save_current_address, width=70
    ).grid(row=0, column=2, padx=(2, 0))

    ttk.Label(send_frame, text="Amount (FBC):").grid(
      row=1, column=0, sticky="w", pady=2
    )
    self.send_amount_var = tk.StringVar()
    self._create_entry(send_frame, textvariable=self.send_amount_var, width=50).grid(
      row=1, column=1, columnspan=2, sticky="ew", pady=2
    )

    self._create_button(send_frame, text="Send", command=self.send_payment).grid(
      row=2, column=0, columnspan=3, pady=5
    )

    send_frame.columnconfigure(1, weight=1)

    # Transaction history
    history_outer, history_frame = self._create_section_frame(
      scrollable_frame, "Transaction History", padding=5
    )
    history_outer.pack(fill="both", expand=True, padx=10, pady=5)

    self.tx_text = self._create_log_widget(history_frame)
    self.tx_text.pack(fill="both", expand=True)

    self._create_button(
      history_frame, text="Load Transactions", command=self.load_transactions
    ).pack(pady=5)

  def create_auction_tab(self):
    """Create auction operations tab with scrolling"""
    tab = self._add_notebook_tab("Auctions")

    # Create canvas and scrollbar for scrollable content
    canvas = tk.Canvas(tab, highlightthickness=0)
    scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
    scrollable_frame = self._create_scrollable_frame(canvas)

    scrollable_frame.bind(
      "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window(
      (0, 0), window=scrollable_frame, anchor="nw"
    )
    canvas.bind(
      "<Configure>",
      lambda e: canvas.itemconfigure(canvas_window, width=e.width),
    )
    canvas.configure(yscrollcommand=scrollbar.set)

    # Pack canvas and scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Enable mousewheel scrolling while cursor is over this tab
    self._bind_canvas_mousewheel(canvas, tab)

    # Now use scrollable_frame instead of tab for all content
    # Wallet balance info
    balance_outer, balance_info_frame = self._create_section_frame(
      scrollable_frame, "Wallet Balance", padding=10
    )
    balance_outer.pack(fill="x", padx=10, pady=5)

    # Info label about setting active wallet
    info_label = ttk.Label(
      balance_info_frame,
      text="^1 Set the 'Active Wallet' in the Wallet tab before refreshing balance",
      foreground="#666666",
      font=("Arial", 9, "italic"),
    )
    info_label.pack(pady=(0, 5))

    self.auction_balance_label = ttk.Label(
      balance_info_frame, text="Confirmed: - (Available for bids: -)"
    )
    self.auction_balance_label.pack()

    self._create_button(
      balance_info_frame,
      text="Refresh Balance",
      command=self.refresh_auction_balance,
    ).pack(pady=5)

    # Stage 6: Job Manager UI
    jobs_outer, jobs_frame = self._create_section_frame(
      scrollable_frame, "Active Automation Jobs", padding=5
    )
    jobs_outer.pack(fill="x", padx=10, pady=5)

    # Create TreeView for jobs
    jobs_tree_frame = ttk.Frame(jobs_frame)
    jobs_tree_frame.pack(fill="x")

    # TreeView columns
    columns = (
      "Name",
      "Status",
      "Wallet",
      "Bid Amount",
      "Lockup",
      "Winning Cost",
      "Progress",
      "Created",
    )
    self.jobs_tree = ttk.Treeview(
      jobs_tree_frame, columns=columns, show="headings", height=5
    )

    # Column widths and headings
    self.jobs_tree.heading("Name", text="Name")
    self.jobs_tree.heading("Status", text="Status")
    self.jobs_tree.heading("Wallet", text="Wallet")
    self.jobs_tree.heading("Bid Amount", text="Bid Amount")
    self.jobs_tree.heading("Lockup", text="Lockup (Bid+Blind)")
    self.jobs_tree.heading("Winning Cost", text="Winning Cost")
    self.jobs_tree.heading("Progress", text="Progress")
    self.jobs_tree.heading("Created", text="Created")

    self.jobs_tree.column("Name", width=100)
    self.jobs_tree.column("Status", width=130)
    self.jobs_tree.column("Wallet", width=70)
    self.jobs_tree.column("Bid Amount", width=80)
    self.jobs_tree.column("Lockup", width=90)
    self.jobs_tree.column("Winning Cost", width=95)
    self.jobs_tree.column("Progress", width=180)
    self.jobs_tree.column("Created", width=90)

    # Scrollbar for TreeView
    jobs_scrollbar = ttk.Scrollbar(
      jobs_tree_frame, orient="vertical", command=self.jobs_tree.yview
    )
    self.jobs_tree.configure(yscrollcommand=jobs_scrollbar.set)

    self.jobs_tree.pack(side="left", fill="x", expand=True)
    jobs_scrollbar.pack(side="right", fill="y")

    self.jobs_context_menu = tk.Menu(self.root, tearoff=0)
    self.jobs_context_menu.add_command(
      label="View Details", command=self.view_job_details
    )
    self.jobs_context_menu.add_command(
      label="Block Calc", command=self.show_selected_job_block_calc
    )
    self.jobs_context_menu.add_command(
      label="Cancel Job", command=self.cancel_selected_job
    )
    self.jobs_tree.bind("<Button-3>", self.show_jobs_context_menu)

    # Job control buttons
    jobs_controls = self._create_inline_frame(jobs_frame)
    jobs_controls.pack(fill="x", pady=(5, 0))

    self._create_button(
      jobs_controls, text="Refresh Jobs", command=self.refresh_jobs_list
    ).pack(side="left", padx=2)
    self._create_button(
      jobs_controls, text="View Details", command=self.view_job_details
    ).pack(side="left", padx=2)
    self._create_button(
      jobs_controls, text="Block Calc", command=self.show_selected_job_block_calc
    ).pack(side="left", padx=2)
    self._create_button(
      jobs_controls, text="Cancel Job", command=self.cancel_selected_job
    ).pack(side="left", padx=2)
    self._create_button(
      jobs_controls, text="Clear Completed", command=self.clear_completed_jobs
    ).pack(side="left", padx=2)

    # Auto-refresh label
    self.jobs_refresh_label = ttk.Label(
      jobs_controls,
      text="Auto-refresh: 60s",
      font=("Arial", 8),
      foreground="gray",
    )
    self.jobs_refresh_label.pack(side="right", padx=10)

    # Initialize job refresh timer
    self.jobs_refresh_timer = None
    self.start_jobs_auto_refresh()

    # IMPORT AUCTIONS FROM WALLET
    import_outer, import_frame = self._create_section_frame(
      scrollable_frame, "Import Existing Auctions", padding=10
    )
    import_outer.pack(fill="x", padx=10, pady=5)

    import_info = ttk.Label(
      import_frame,
      text="Scan your active wallet for ongoing auctions and add them to automation.",
      foreground="#666",
      font=("Arial", 9),
    )
    import_info.pack(pady=(0, 10))

    import_btn = self._create_button(
      import_frame,
      text="Scan & Import Wallet Auctions",
      command=self.import_wallet_auctions,
    )
    import_btn.pack()

    import_note = ttk.Label(
      import_frame,
      text="Will automatically: REVEAL unrevealed bids, REGISTER won auctions, REDEEM lost auctions, and add others to automation queue.",
      foreground="#999",
      font=("Arial", 8, "italic"),
      wraplength=700,
    )
    import_note.pack(pady=(5, 0))

    # Name operations
    name_outer, name_frame = self._create_section_frame(
      scrollable_frame, "Name Operations", padding=10
    )
    name_outer.pack(fill="x", padx=10, pady=5)

    ttk.Label(name_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=2)
    self.name_var = tk.StringVar()
    self._create_entry(name_frame, textvariable=self.name_var, width=30).grid(
      row=0, column=1, sticky="ew", pady=2
    )

    self._create_button(name_frame, text="Get Name Info", command=self.get_name_info).grid(
      row=0, column=2, padx=5
    )
    self._create_button(
      name_frame,
      text="Rollout Reminders",
      command=self.show_rollout_reminders_manager,
    ).grid(row=0, column=3, padx=5)
    self._create_button(
      name_frame,
      text="Watchlist",
      command=self.show_watchlist_manager,
    ).grid(row=0, column=4, padx=5)

    # Auction actions
    action_frame = self._create_inline_frame(name_frame)
    action_frame.grid(row=1, column=0, columnspan=5, pady=10)

    self._create_button(action_frame, text="Open Auction", command=self.send_open).pack(
      side="left", padx=2
    )
    self._create_button(action_frame, text="Place Bid", command=self.send_bid).pack(
      side="left", padx=2
    )
    self._create_button(action_frame, text="Reveal Bid", command=self.send_reveal).pack(
      side="left", padx=2
    )
    self._create_button(action_frame, text="Register", command=self.send_register).pack(
      side="left", padx=2
    )

    name_frame.columnconfigure(1, weight=1)

    # Bid parameters
    bid_outer, bid_frame = self._create_section_frame(scrollable_frame, "Bid Parameters", padding=10)
    bid_outer.pack(fill="x", padx=10, pady=5)

    ttk.Label(bid_frame, text="Bid Amount (FBC):").grid(
      row=0, column=0, sticky="w", pady=2
    )
    ttk.Label(
      bid_frame,
      text="(minimum required to win auction)",
      font=("Arial", 8, "italic"),
      foreground="#666",
    ).grid(row=0, column=2, sticky="w", padx=(5, 0))
    self.bid_amount_var = tk.StringVar()
    self._create_entry(bid_frame, textvariable=self.bid_amount_var, width=20).grid(
      row=0, column=1, sticky="w", pady=2
    )

    ttk.Label(bid_frame, text="Lockup Amount (FBC):").grid(
      row=1, column=0, sticky="w", pady=2
    )
    ttk.Label(
      bid_frame,
      text="(total locked: bid + blind amount)",
      font=("Arial", 8, "italic"),
      foreground="#666",
    ).grid(row=1, column=2, sticky="w", padx=(5, 0))
    self.lockup_amount_var = tk.StringVar()
    self._create_entry(bid_frame, textvariable=self.lockup_amount_var, width=20).grid(
      row=1, column=1, sticky="w", pady=2
    )

    # Stage 1: Auto-continue checkbox
    self.auto_continue_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(
      bid_frame,
      text=" Auto-continue through auction phases (OPEN -> BID -> REVEAL -> REGISTER)",
      variable=self.auto_continue_var,
    ).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

    # Stage 4: Notification widget
    notification_outer, notification_frame = self._create_section_frame(
      scrollable_frame, "Automation Notifications", padding=5
    )
    notification_outer.pack(fill="x", padx=10, pady=5)

    # Notification display
    self.notification_text = self._create_log_widget(
      notification_frame, lines=10, wrap="word", state="disabled"
    )
    self.notification_text.pack(fill="both", expand=True)

    # Notification controls
    notif_controls = self._create_inline_frame(notification_frame)
    notif_controls.pack(fill="x", pady=(5, 0))

    self._create_button(
      notif_controls,
      text="Refresh",
      command=lambda: self.notification_manager._refresh_widget(),
    ).pack(side="left", padx=2)
    self._create_button(
      notif_controls, text="Clear All", command=self.clear_all_notifications
    ).pack(side="left", padx=2)
    self._create_button(
      notif_controls,
      text="Mark All Read",
      command=lambda: self.notification_manager.mark_all_read(),
    ).pack(side="left", padx=2)

    # Connect notification widget to manager
    self.notification_manager.set_widget(self.notification_text)

    # My names
    mynames_outer, mynames_frame = self._create_section_frame(scrollable_frame, "My Names", padding=5)
    mynames_outer.pack(fill="x", padx=10, pady=5)

    self.names_text = self._create_log_widget(
      mynames_frame, lines=3, wrap="word"
    )
    self.names_text.pack(fill="both", expand=True)

    self._create_button(
      mynames_frame, text="Load My Names", command=self.load_my_names
    ).pack(pady=5)

    # Auction info
    info_text_outer, info_text_frame = self._create_section_frame(
      scrollable_frame, "Name/Auction Details", padding=5
    )
    info_text_outer.pack(fill="x", padx=10, pady=5)

    # Info label explaining minimumBid
    info_help = ttk.Label(
      info_text_frame,
      text="[i] minimumBid = lowest bid amount required to win (set by protocol). Value conversion: raw / 1,000,000 = FBC",
      font=("Arial", 8, "italic"),
      foreground="#0066cc",
    )
    info_help.pack(anchor="w", pady=(0, 2))

    # Example calculation
    example_help = ttk.Label(
      info_text_frame,
      text="[*] Example: minimumBid: 100000000 -> 100,000,000 units. 1,000,000 = 100 FBC",
      font=("Arial", 8, "italic"),
      foreground="#666666",
    )
    example_help.pack(anchor="w", pady=(0, 2))

    self.auction_info_text = self._create_log_widget(
      info_text_frame, lines=12, wrap="word"
    )
    self.auction_info_text.pack(fill="both", expand=True)

  def create_block_calc_tab(self):
    """Create block calculator tab for auction timing"""
    tab = self._add_notebook_tab("Block Calc")
    self.block_calc_tab = "Block Calc" if self.customtkinter_active else tab

    # Create canvas and scrollbar for scrollable content
    canvas = tk.Canvas(tab, highlightthickness=0)
    scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
    scrollable_frame = self._create_scrollable_frame(canvas)

    scrollable_frame.bind(
      "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window(
      (0, 0), window=scrollable_frame, anchor="nw"
    )
    canvas.bind(
      "<Configure>",
      lambda e: canvas.itemconfigure(canvas_window, width=e.width),
    )
    canvas.configure(yscrollcommand=scrollbar.set)

    # Pack canvas and scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Enable mousewheel scrolling while cursor is over this tab
    self._bind_canvas_mousewheel(canvas, tab)

    # Current Status Section
    status_outer, status_frame = self._create_section_frame(
      scrollable_frame, "Current Blockchain Status", padding=10
    )
    status_outer.pack(fill="x", padx=10, pady=5)

    self.calc_current_height_label = ttk.Label(
      status_frame, text="Current Block: -", font=("Arial", 10, "bold")
    )
    self.calc_current_height_label.pack()

    self.calc_node_status_label = ttk.Label(
      status_frame, text="Node Status: Unknown", foreground="gray"
    )
    self.calc_node_status_label.pack()

    refresh_frame = self._create_inline_frame(status_frame)
    refresh_frame.pack(pady=5)
    self._create_button(
      refresh_frame,
      text="Refresh Current Block",
      command=self.refresh_calc_current_block,
    ).pack(side="left", padx=5)

    # Block Time Information (hard-coded, informational only)
    ttk.Label(
      refresh_frame,
      text="(Average block time: 2 minutes)",
      font=("Arial", 9, "italic"),
      foreground="gray",
    ).pack(side="left", padx=(20, 0))

    # Input Method Selection
    input_outer, input_frame = self._create_section_frame(scrollable_frame, "Input Method", padding=10)
    input_outer.pack(fill="x", padx=10, pady=5)

    self.calc_input_method = tk.StringVar(value="name")

    method_frame = ttk.Frame(input_frame)
    method_frame.pack(fill="x")

    ttk.Radiobutton(
      method_frame,
      text="Lookup by Name (requires running node)",
      variable=self.calc_input_method,
      value="name",
      command=self.toggle_calc_input_method,
    ).pack(side="left", padx=10)
    ttk.Radiobutton(
      method_frame,
      text="Manual Block Entry (works offline)",
      variable=self.calc_input_method,
      value="manual",
      command=self.toggle_calc_input_method,
    ).pack(side="left", padx=10)

    # Name Lookup Section
    self.name_lookup_outer, self.name_lookup_frame = self._create_section_frame(
      scrollable_frame, "Name Lookup", padding=10
    )
    self.name_lookup_outer.pack(fill="x", padx=10, pady=5)

    name_entry_frame = self._create_inline_frame(self.name_lookup_frame)
    name_entry_frame.pack(fill="x")

    ttk.Label(name_entry_frame, text="Name:").pack(side="left", padx=5)
    self.calc_name_var = tk.StringVar()
    name_field_width = 260 if self.customtkinter_active else 30
    self._create_entry(name_entry_frame, textvariable=self.calc_name_var, width=name_field_width).pack(
      side="left", padx=5
    )
    self._create_button(
      name_entry_frame,
      text="Lookup Auction Info",
      command=self.lookup_name_for_calc,
    ).pack(side="left", padx=5)
    self._create_button(
      name_entry_frame, text="Clear", command=self.clear_calc_results
    ).pack(side="left", padx=5)

    # Manual Entry Section
    self.manual_entry_outer, self.manual_entry_frame = self._create_section_frame(
      scrollable_frame, "Manual Block Heights", padding=10
    )
    self.manual_entry_outer.pack(fill="x", padx=10, pady=5)

    # Timeline info
    timeline_info = ttk.Label(
      self.manual_entry_frame,
      text="[+] FBD Auction Timeline: OPEN ~1hr -> BID 3days -> REVEAL 1day -> CLOSED -> REDEEM 10days",
      font=("Arial", 8, "italic"),
      foreground="#666",
    )
    timeline_info.pack(pady=(0, 5))

    manual_grid = self._create_inline_frame(self.manual_entry_frame)
    manual_grid.pack(fill="x")

    ttk.Label(manual_grid, text="OPEN Block:").grid(
      row=0, column=0, sticky="w", pady=2, padx=5
    )
    self.calc_open_block_var = tk.StringVar()
    self._create_entry(manual_grid, textvariable=self.calc_open_block_var, width=15).grid(
      row=0, column=1, pady=2, padx=5
    )
    ttk.Label(
      manual_grid,
      text="(~1 hour period)",
      font=("Arial", 8, "italic"),
      foreground="#666",
    ).grid(row=0, column=2, sticky="w", padx=5)

    ttk.Label(manual_grid, text="BIDDING Start:").grid(
      row=1, column=0, sticky="w", pady=2, padx=5
    )
    self.calc_bid_start_var = tk.StringVar()
    self._create_entry(manual_grid, textvariable=self.calc_bid_start_var, width=15).grid(
      row=1, column=1, pady=2, padx=5
    )
    ttk.Label(
      manual_grid,
      text="(3 days / 2160 blocks)",
      font=("Arial", 8, "italic"),
      foreground="#666",
    ).grid(row=1, column=2, sticky="w", padx=5)

    ttk.Label(manual_grid, text="REVEAL Start:").grid(
      row=2, column=0, sticky="w", pady=2, padx=5
    )
    self.calc_reveal_start_var = tk.StringVar()
    self._create_entry(manual_grid, textvariable=self.calc_reveal_start_var, width=15).grid(
      row=2, column=1, pady=2, padx=5
    )
    ttk.Label(
      manual_grid,
      text="(1 day / 720 blocks)",
      font=("Arial", 8, "italic"),
      foreground="#666",
    ).grid(row=2, column=2, sticky="w", padx=5)

    ttk.Label(manual_grid, text="CLOSED Block:").grid(
      row=3, column=0, sticky="w", pady=2, padx=5
    )
    self.calc_closed_block_var = tk.StringVar()
    self._create_entry(manual_grid, textvariable=self.calc_closed_block_var, width=15).grid(
      row=3, column=1, pady=2, padx=5
    )
    ttk.Label(
      manual_grid,
      text="(Can register/redeem)",
      font=("Arial", 8, "italic"),
      foreground="#666",
    ).grid(row=3, column=2, sticky="w", padx=5)

    self._create_button(
      self.manual_entry_frame,
      text="Calculate Times",
      command=self.calculate_manual_times,
    ).pack(pady=10)

    calc_note = ttk.Label(
      self.manual_entry_frame,
      text="[i] Enter any ONE block height and others will be calculated automatically",
      font=("Arial", 8, "italic"),
      foreground="#0066cc",
    )
    calc_note.pack()

    # Results Display
    results_outer, results_frame = self._create_section_frame(
      scrollable_frame, "Calculated Date/Time Results", padding=10
    )
    results_outer.pack(fill="both", expand=True, padx=10, pady=5)

    # Create Treeview for results
    columns = ("Phase", "Block Height", "Blocks Remaining", "Date/Time", "Status")
    self.calc_results_tree = ttk.Treeview(
      results_frame, columns=columns, show="headings", height=8
    )

    self.calc_results_tree.heading("Phase", text="Auction Phase")
    self.calc_results_tree.heading("Block Height", text="Block Height")
    self.calc_results_tree.heading("Blocks Remaining", text="Blocks Until")
    self.calc_results_tree.heading("Date/Time", text="Approximate Date/Time")
    self.calc_results_tree.heading("Status", text="Status")

    self.calc_results_tree.column("Phase", width=140)
    self.calc_results_tree.column("Block Height", width=100)
    self.calc_results_tree.column("Blocks Remaining", width=100)
    self.calc_results_tree.column("Date/Time", width=180)
    self.calc_results_tree.column("Status", width=120)

    calc_scrollbar = ttk.Scrollbar(
      results_frame, orient="vertical", command=self.calc_results_tree.yview
    )
    self.calc_results_tree.configure(yscrollcommand=calc_scrollbar.set)

    self.calc_results_tree.pack(side="left", fill="both", expand=True)
    calc_scrollbar.pack(side="right", fill="y")

    # Info footer
    info_footer = ttk.Label(
      results_frame,
      text="[i] Times are approximate based on average block time. Actual times may vary.",
      font=("Arial", 8, "italic"),
      foreground="#666",
    )
    info_footer.pack(pady=5)

    # Initialize visibility
    self.toggle_calc_input_method()

  def toggle_calc_input_method(self):
    """Toggle between name lookup and manual entry"""
    if self.calc_input_method.get() == "name":
      self.name_lookup_outer.pack(fill="x", padx=10, pady=5)
      self.manual_entry_outer.pack_forget()
    else:
      self.name_lookup_outer.pack_forget()
      self.manual_entry_outer.pack(fill="x", padx=10, pady=5)

  def refresh_calc_current_block(self, auto_retry=False):
    """Refresh current block height for calculator

    Args:
      auto_retry: True if this is an automatic retry (don't show popups)
    """
    # Prevent multiple overlapping refresh attempts
    if self.calc_refresh_in_progress and not auto_retry:
      self.log("Block calculator: Refresh already in progress, skipping...")
      return None

    if not auto_retry:
      self.calc_refresh_in_progress = True
      self.calc_refresh_retry_count = 0

    result = self.rpc_call("getblockchaininfo")

    if result:
      # Success! Update display and reset state
      current_height = result.get("blocks", 0)
      self.calc_current_height_label.configure(
        text=f"Current Block: {current_height:,}"
      )
      self.calc_node_status_label.configure(
        text="Node Status: Running [OK]", foreground="green"
      )
      self.log(
        f"Block calculator: Current block height refreshed: {current_height}"
      )
      self.calc_refresh_in_progress = False
      self.calc_refresh_retry_count = 0
      return current_height
    else:
      # RPC call failed - determine why
      node_process_running = self.fbd_process and self.fbd_process.poll() is None

      if node_process_running:
        # Node process is running but RPC not ready yet
        self.calc_node_status_label.configure(
          text="Node Status: Starting... [ ]", foreground="orange"
        )

        # Auto-retry with limit
        if self.calc_refresh_retry_count < self.calc_refresh_max_retries:
          self.calc_refresh_retry_count += 1
          self.log(
            f"Block calculator: Node starting, retry {self.calc_refresh_retry_count}/{self.calc_refresh_max_retries} in 5s..."
          )
          self.root.after(
            5000, lambda: self.refresh_calc_current_block(auto_retry=True)
          )
        else:
          # Max retries reached
          self.log(
            "Block calculator: Max retries reached, node may not be responding"
          )
          self.calc_node_status_label.configure(
            text="Node Status: Not Responding [!] ", foreground="red"
          )
          self.calc_refresh_in_progress = False
          self.calc_refresh_retry_count = 0

        return None
      else:
        # Node process is not running
        self.calc_node_status_label.configure(
          text="Node Status: Not Running [OK]-", foreground="red"
        )
        self.log(
          "Block calculator: Could not get current block height - node not running"
        )
        self.calc_refresh_in_progress = False
        self.calc_refresh_retry_count = 0

        # Only show popup if this is a manual refresh (not auto-retry)
        if not auto_retry:
          response = messagebox.askyesno(
            "Node Not Running",
            "The FBD node is not running. Would you like to start it now?\n\n"
            "(You can still use Manual Block Entry mode without the node running)",
          )
          if response:
            # Double-check node isn't running before starting
            # (user might have started it while dialog was open)
            if not (self.fbd_process and self.fbd_process.poll() is None):
              self.start_node()
              # Update status and begin auto-retry cycle
              self.calc_node_status_label.configure(
                text="Node Status: Starting... [ ]", foreground="orange"
              )
              self.calc_refresh_in_progress = True
              self.calc_refresh_retry_count = 0
              # Wait 5 seconds for node to start, then begin auto-retry
              self.root.after(
                5000,
                lambda: self.refresh_calc_current_block(
                  auto_retry=True
                ),
              )
            else:
              # Node was started while dialog was open
              self.log(
                "Block calculator: Node already started, beginning refresh..."
              )
              self.calc_refresh_in_progress = True
              self.calc_refresh_retry_count = 0
              self.root.after(
                2000,
                lambda: self.refresh_calc_current_block(
                  auto_retry=True
                ),
              )

        return None

  def lookup_name_for_calc(self):
    """Look up name and populate calculator"""
    name = self.calc_name_var.get().strip()
    if not name:
      messagebox.showwarning("Input Required", "Please enter a name to lookup")
      return

    # Get name info
    name_info = self.get_name_info_silent(name)
    if not name_info:
      # Check if node process is actually running
      node_process_running = self.fbd_process and self.fbd_process.poll() is None

      if node_process_running:
        # Node is running but RPC not ready or name doesn't exist
        messagebox.showinfo(
          "Lookup Failed",
          f"Could not retrieve information for name: {name}\n\n"
          "The node is starting up. Please wait a moment and try again.",
        )
        # Update current block display status and start auto-retry
        self.calc_node_status_label.configure(
          text="Node Status: Starting... [ ]", foreground="orange"
        )
        if not self.calc_refresh_in_progress:
          self.calc_refresh_in_progress = True
          self.calc_refresh_retry_count = 0
          self.root.after(
            5000, lambda: self.refresh_calc_current_block(auto_retry=True)
          )
        return

      # Node is not running - offer to start it
      response = messagebox.askyesno(
        "Node Not Running",
        f"Could not retrieve information for name: {name}\n\n"
        "The node may not be running. Would you like to start it?",
      )
      if response:
        # Double-check before starting
        if not (self.fbd_process and self.fbd_process.poll() is None):
          self.start_node()
          # Update status labels and start auto-retry cycle
          self.calc_node_status_label.configure(
            text="Node Status: Starting... [ ]", foreground="orange"
          )
          messagebox.showinfo(
            "Node Starting",
            "Node is starting. Please wait a moment and try the lookup again.",
          )
          # Start auto-retry for current block
          if not self.calc_refresh_in_progress:
            self.calc_refresh_in_progress = True
            self.calc_refresh_retry_count = 0
            self.root.after(
              5000,
              lambda: self.refresh_calc_current_block(auto_retry=True),
            )
        else:
          # Already running
          messagebox.showinfo(
            "Node Running",
            "Node is already running. Please wait a moment and try the lookup again.",
          )
      return

    # Debug: Log what we got
    self.log(f"Block calculator: Got name info for '{name}': {name_info}")

    # Get current block (silently - don't prompt to start node again)
    current_height = self._get_current_height_silent()
    if current_height is None:
      # Still allow lookup even if node not running, but without current height
      self.log(
        "Block calculator: No current height available (node may not be running)"
      )

    # Extract auction info
    state = name_info.get("state", "UNKNOWN")
    info = name_info.get("info", {})

    # Parse block heights based on state
    # FBD Auction Timeline:
    # OPEN: ~1 hour (37 blocks)
    # BIDDING: 3 days (2160 blocks)
    # REVEAL: 1 day (720 blocks)
    # CLOSED: Can REGISTER or REDEEM (10 days / 7200 blocks)

    open_block = None
    bid_start = None
    reveal_start = None
    closed_block = None
    redeem_deadline = None
    renewal_block = None

    OPENING_PERIOD = 37 # ~1 hour
    BIDDING_PERIOD = 2160 # 3 days
    REVEAL_PERIOD = 720 # 1 day
    REDEEM_PERIOD = 7200 # 10 days for losers to reclaim funds

    if state == "AVAILABLE":
      # Name is available - not in auction yet
      self.log(f"Block calculator: '{name}' is AVAILABLE (not in auction)")
      messagebox.showinfo(
        "Name Available",
        f"The name '{name}' is currently AVAILABLE.\n\n"
        "No auction is active for this name.",
      )
      # Clear any previous results
      for item in self.calc_results_tree.get_children():
        self.calc_results_tree.delete(item)
      return

    # Try to extract all available block information
    # For auction states: height is when OPEN was mined
    # For REGISTERED: height might be registration block, need to check stats/history

    # Try multiple possible field locations for better compatibility
    open_block = None
    registered_block = None
    renewal_block = info.get("renewal") or name_info.get("renewal")

    # For REGISTERED names, try to get both auction start AND registration blocks
    if state == "REGISTERED":
      # The actual registration block - try multiple field names
      registered_block = (
        info.get("registered")
        or info.get("height")
        or name_info.get("registered")
        or name_info.get("height")
        or info.get("claimed")
        or info.get("claimedAt")
      )

      # Try to find when the auction originally started (if available)
      # This might be in stats, history, or auction fields
      stats = info.get("stats") or name_info.get("stats") or {}
      history = info.get("history") or name_info.get("history") or {}

      open_block = (
        stats.get("openedAt")
        or stats.get("auctionStart")
        or history.get("opened")
        or info.get("auctionStart")
        or name_info.get("auctionStart")
      )

      self.log(
        f"Block calculator: '{name}' is REGISTERED - "
        f"Registration block: {registered_block}, "
        f"Original auction opened at: {open_block if open_block else 'unknown'}, "
        f"Renewal due: {renewal_block}"
      )
    else:
      # For active auction states
      open_block = info.get("height") or name_info.get("height")

      # For some states, try alternative field names
      if open_block is None and state in ["BIDDING", "REVEAL", "CLOSED"]:
        # Try other possible field names
        open_block = (
          info.get("openBlock")
          or info.get("start")
          or name_info.get("start")
          or name_info.get("openBlock")
        )

    # If we have auction start block, calculate auction phases
    if open_block is not None and state in [
      "OPENING",
      "BIDDING",
      "REVEAL",
      "CLOSED",
      "REGISTERED",
    ]:
      # Calculate all auction phases from OPEN block
      bid_start = open_block + OPENING_PERIOD
      reveal_start = bid_start + BIDDING_PERIOD
      closed_block = reveal_start + REVEAL_PERIOD
      redeem_deadline = closed_block + REDEEM_PERIOD

      if state == "REGISTERED":
        self.log(
          f"Block calculator: Auction timeline reconstructed from OPEN at {open_block}"
        )
      else:
        self.log(
          f"Block calculator: Auction phases calculated from OPEN at {open_block}"
        )

    # Fallback: if we didn't get height but got renewal, at least show that
    if (
      open_block is None
      and registered_block is None
      and renewal_block is not None
    ):
      self.log(
        f"Block calculator: Only have renewal info for '{name}': {renewal_block}"
      )

    # Check if we got any useful data
    if open_block is None and registered_block is None and renewal_block is None:
      self.log(
        f"Block calculator: WARNING - No block data found for '{name}' (state: {state})"
      )
      self.log(f"Block calculator: Debug - Full nameinfo structure:")
      self.log(f" name_info keys: {list(name_info.keys())}")
      self.log(f" info keys: {list(info.keys()) if info else 'info is empty'}")
      self.log(f" Full data: {json.dumps(name_info, indent=2)}")

      # Create context-aware error message
      if state in ["BIDDING", "REVEAL", "CLOSED", "OPENING"]:
        error_msg = (
          f"Could not extract block data for '{name}', but the name is in {state} state.\n\n"
          f"This suggests the auction IS active, but the node may not have complete \n"
          f"auction index data.\n\n"
          f"Possible causes:\n"
          f"* Node started with --index-auctions flag missing\n"
          f"* Node still syncing auction data\n"
          f"* Incomplete blockchain data\n\n"
          f"Check the log for full name data structure."
        )
      else:
        error_msg = (
          f"Could not extract block information for '{name}'.\n\n"
          f"State: {state}\n\n"
          f"The name may have incomplete data in the blockchain.\n"
          f"Check the log for full structure details."
        )

      messagebox.showwarning("Missing Block Data", error_msg)
      # Still try to display with what we have

    self.log(
      f"Block calculator: Looked up '{name}' - State: {state}, Open: {open_block}, "
      f"Registered: {registered_block}, Bid: {bid_start}, Reveal: {reveal_start}, "
      f"Closed: {closed_block}, Redeem: {redeem_deadline}, Renewal: {renewal_block}"
    )

    # Calculate and display
    self._display_calc_results(
      current_height,
      open_block,
      bid_start,
      reveal_start,
      closed_block,
      state,
      name,
      renewal_block,
      redeem_deadline,
      registered_block, # Pass the actual registration block
    )

  def calculate_manual_times(self):
    """Calculate times from manually entered block heights"""
    try:
      # Get manual inputs
      open_block = (
        int(self.calc_open_block_var.get())
        if self.calc_open_block_var.get()
        else None
      )
      bid_start = (
        int(self.calc_bid_start_var.get())
        if self.calc_bid_start_var.get()
        else None
      )
      reveal_start = (
        int(self.calc_reveal_start_var.get())
        if self.calc_reveal_start_var.get()
        else None
      )
      closed_block = (
        int(self.calc_closed_block_var.get())
        if self.calc_closed_block_var.get()
        else None
      )

      if not any([open_block, bid_start, reveal_start, closed_block]):
        messagebox.showwarning(
          "Input Required", "Please enter at least one block height"
        )
        return

      # FBD Auction periods
      OPENING_PERIOD = 37 # ~1 hour
      BIDDING_PERIOD = 2160 # 3 days
      REVEAL_PERIOD = 720 # 1 day
      REDEEM_PERIOD = 7200 # 10 days

      # Auto-calculate missing phases from provided block
      redeem_deadline = None

      # If user provides OPEN, calculate the rest
      if open_block and not (bid_start or reveal_start or closed_block):
        bid_start = open_block + OPENING_PERIOD
        reveal_start = bid_start + BIDDING_PERIOD
        closed_block = reveal_start + REVEAL_PERIOD
        redeem_deadline = closed_block + REDEEM_PERIOD
        self.log(
          f"Block calculator: Auto-calculated auction phases from OPEN block {open_block}"
        )
      # If user provides BID START, calculate the rest
      elif bid_start and not (open_block or reveal_start or closed_block):
        open_block = bid_start - OPENING_PERIOD
        reveal_start = bid_start + BIDDING_PERIOD
        closed_block = reveal_start + REVEAL_PERIOD
        redeem_deadline = closed_block + REDEEM_PERIOD
        self.log(
          f"Block calculator: Auto-calculated auction phases from BID START block {bid_start}"
        )
      # If user provides REVEAL, backtrack and forward-calculate
      elif reveal_start and not (open_block or bid_start or closed_block):
        bid_start = reveal_start - BIDDING_PERIOD
        open_block = bid_start - OPENING_PERIOD
        closed_block = reveal_start + REVEAL_PERIOD
        redeem_deadline = closed_block + REDEEM_PERIOD
        self.log(
          f"Block calculator: Auto-calculated auction phases from REVEAL block {reveal_start}"
        )
      # If user provides CLOSED, backtrack
      elif closed_block and not (open_block or bid_start or reveal_start):
        reveal_start = closed_block - REVEAL_PERIOD
        bid_start = reveal_start - BIDDING_PERIOD
        open_block = bid_start - OPENING_PERIOD
        redeem_deadline = closed_block + REDEEM_PERIOD
        self.log(
          f"Block calculator: Auto-calculated auction phases from CLOSED block {closed_block}"
        )
      else:
        # User provided multiple values, just calculate redeem deadline if closed is known
        if closed_block:
          redeem_deadline = closed_block + REDEEM_PERIOD

      # Try to get current block (optional for manual mode)
      current_height = None
      try:
        result = self.rpc_call("getblockchaininfo")
        if result:
          current_height = result.get("blocks", 0)
      except:
        pass # It's okay if node is not running in manual mode

      self.log(
        f"Block calculator: Manual calculation - Current: {current_height}, Open: {open_block}, Bid: {bid_start}, Reveal: {reveal_start}, Closed: {closed_block}, Redeem: {redeem_deadline}"
      )

      # Calculate and display
      self._display_calc_results(
        current_height,
        open_block,
        bid_start,
        reveal_start,
        closed_block,
        None,
        None,
        None,
        redeem_deadline,
        None, # No registered_block for manual entry
      )

    except ValueError:
      messagebox.showerror(
        "Invalid Input", "Please enter valid block height numbers"
      )

  def _display_calc_results(
    self,
    current_height,
    open_block,
    bid_start,
    reveal_start,
    closed_block,
    state=None,
    name=None,
    renewal_block=None,
    redeem_deadline=None,
    registered_block=None, # New parameter for actual registration block
  ):
    """Display calculated results in treeview"""
    # Clear existing results
    for item in self.calc_results_tree.get_children():
      self.calc_results_tree.delete(item)

    # Block time constant (2 minutes average for FBD)
    block_time_seconds = 120 # 2 minutes per block

    now = datetime.now()

    # Helper to calculate datetime and status
    def calc_row(phase_name, block_height):
      """Calc row."""
      if block_height is None:
        return (phase_name, "-", "-", "-", "Not specified")

      if current_height is None:
        # No current height - just show the block number without time estimate
        return (
          phase_name,
          f"{block_height:,}",
          "-",
          "(Start node for time estimate)",
          "Unknown (offline)",
        )

      blocks_until = block_height - current_height

      if blocks_until > 0:
        # Future event
        seconds_until = blocks_until * block_time_seconds
        estimated_time = now + timedelta(seconds=seconds_until)
        time_str = estimated_time.strftime("%Y-%m-%d %H:%M:%S")
        status = "Upcoming"
        blocks_str = f"+{blocks_until:,}"
      elif blocks_until == 0:
        # Happening now
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        status = "NOW"
        blocks_str = "0"
      else:
        # Past event
        seconds_ago = abs(blocks_until) * block_time_seconds
        estimated_time = now - timedelta(seconds=seconds_ago)
        time_str = estimated_time.strftime("%Y-%m-%d %H:%M:%S")
        status = "Past"
        blocks_str = f"{blocks_until:,}"

      return (phase_name, f"{block_height:,}", blocks_str, time_str, status)

    # For REGISTERED names, show complete auction history plus registration
    if state == "REGISTERED":
      # If we have auction timeline, show the full auction that led to registration
      if open_block is not None:
        row = calc_row("[+] Auction OPENED", open_block)
        self.calc_results_tree.insert("", "end", values=row)

      if bid_start is not None:
        row = calc_row("[*]o BIDDING Started", bid_start)
        self.calc_results_tree.insert("", "end", values=row)

      if reveal_start is not None:
        row = calc_row("[*] REVEAL Started", reveal_start)
        self.calc_results_tree.insert("", "end", values=row)

      if closed_block is not None:
        row = calc_row("[OK] Auction CLOSED", closed_block)
        self.calc_results_tree.insert("", "end", values=row)

      # Show the actual REGISTER transaction block
      if registered_block is not None:
        row = calc_row("[*] REGISTERED (Winner Claimed)", registered_block)
        self.calc_results_tree.insert("", "end", values=row)
      elif open_block is not None and registered_block is None:
        # Fallback: if we don't have separate registered_block, show it as unknown
        self.calc_results_tree.insert(
          "",
          "end",
          values=(
            "[*] REGISTERED (Winner Claimed)",
            "Unknown",
            "-",
            "-",
            "Data unavailable",
          ),
        )

      # Show renewal deadline
      if renewal_block is not None:
        row = calc_row("[*] RENEWAL Due", renewal_block)
        self.calc_results_tree.insert("", "end", values=row)

      # For recently registered names (still in REDEEM period), also show REDEEM deadline
      if closed_block is not None and redeem_deadline is not None:
        row = calc_row("[*] REDEEM Deadline", redeem_deadline)
        self.calc_results_tree.insert("", "end", values=row)

      # Enhanced status message
      if registered_block and renewal_block:
        status_msg = (
          f"Name '{name}' was REGISTERED at block {registered_block:,} "
          f"(renewal due at block {renewal_block:,})"
        )
      elif renewal_block:
        status_msg = f"Name '{name}' is REGISTERED (renewal due at block {renewal_block:,})"
      else:
        status_msg = f"Name '{name}' is REGISTERED"
      self.log(f"Block calculator: {status_msg}")

    # For auction phases
    else:
      if open_block is not None:
        row = calc_row("[+] OPEN (~1 hour)", open_block)
        self.calc_results_tree.insert("", "end", values=row)

      if bid_start is not None:
        row = calc_row("[*]o BIDDING (3 days)", bid_start)
        self.calc_results_tree.insert("", "end", values=row)

      if reveal_start is not None:
        row = calc_row("[*] REVEAL (1 day)", reveal_start)
        self.calc_results_tree.insert("", "end", values=row)

      if closed_block is not None:
        row = calc_row("[OK] CLOSED (Register)", closed_block)
        self.calc_results_tree.insert("", "end", values=row)

      if redeem_deadline is not None:
        row = calc_row("[*] REDEEM Deadline", redeem_deadline)
        self.calc_results_tree.insert("", "end", values=row)

      # Add current state info if available
      if state and name:
        status_msg = f"Name '{name}' is currently in {state} state"
        self.log(f"Block calculator: {status_msg}")

    # If no rows were added, only log - don't show another popup (already shown in lookup_name_for_calc)
    if len(self.calc_results_tree.get_children()) == 0:
      self.log(
        f"Block calculator: WARNING - No results to display for '{name}' (state: {state})"
      )
      self.log(
        f"Block calculator: No timeline rows could be calculated. "
        f"This was already reported to the user."
      )

  def clear_calc_results(self):
    """Clear calculator results"""
    self.calc_name_var.set("")
    self.calc_open_block_var.set("")
    self.calc_bid_start_var.set("")
    self.calc_reveal_start_var.set("")
    self.calc_closed_block_var.set("")
    for item in self.calc_results_tree.get_children():
      self.calc_results_tree.delete(item)
    self.log("Block calculator: Results cleared")

  def create_settings_tab(self):
    """Create settings tab"""
    tab = self._add_notebook_tab("Settings")

    # Create canvas and scrollbar for scrollable content
    canvas = tk.Canvas(tab, highlightthickness=0)
    scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
    scrollable_frame = self._create_scrollable_frame(canvas)

    scrollable_frame.bind(
      "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window(
      (0, 0), window=scrollable_frame, anchor="nw"
    )
    canvas.bind(
      "<Configure>",
      lambda e: canvas.itemconfigure(canvas_window, width=e.width),
    )
    canvas.configure(yscrollcommand=scrollbar.set)

    # Pack canvas and scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Enable mousewheel scrolling while cursor is over this tab
    self._bind_canvas_mousewheel(canvas, tab)

    # Now use scrollable_frame instead of tab for all content
    # Configuration Profiles
    profile_outer, profile_frame = self._create_section_frame(
      scrollable_frame, "Configuration Profiles", padding=10
    )
    profile_outer.pack(fill="x", padx=10, pady=5)

    profile_row1 = ttk.Frame(profile_frame)
    profile_row1.pack(fill="x", pady=2)

    ttk.Label(profile_row1, text="Profile:").pack(side="left", padx=5)
    self.profile_var = tk.StringVar(value="default")
    self.profile_combo = ttk.Combobox(
      profile_row1,
      textvariable=self.profile_var,
      values=self.list_profiles(),
      width=30,
    )
    self.profile_combo.pack(side="left", padx=5)

    profile_row2 = self._create_inline_frame(profile_frame)
    profile_row2.pack(fill="x", pady=2)

    self._create_button(profile_row2, text="Load Profile", command=self.load_profile).pack(
      side="left", padx=5
    )
    self._create_button(
      profile_row2, text="Save as New", command=self.save_new_profile
    ).pack(side="left", padx=5)
    self._create_button(
      profile_row2, text="Update Current", command=self.update_profile
    ).pack(side="left", padx=5)
    self._create_button(
      profile_row2, text="Delete Profile", command=self.delete_profile
    ).pack(side="left", padx=5)

    appearance_outer, appearance_frame = self._create_section_frame(
      scrollable_frame, "Appearance", padding=10
    )
    appearance_outer.pack(fill="x", padx=10, pady=5)

    ttk.Label(appearance_frame, text="Theme mode:").grid(
      row=0, column=0, sticky="w", pady=2
    )
    self.theme_combo = ttk.Combobox(
      appearance_frame,
      textvariable=self.theme_choice_var,
      values=list(self.theme_mode_labels.values()),
      state="readonly",
      width=24,
    )
    self.theme_combo.grid(row=0, column=1, sticky="w", pady=2)
    self.theme_combo.bind("<<ComboboxSelected>>", self.on_theme_mode_changed)

    ttk.Label(
      appearance_frame,
      text="Dark mode colors are applied when Dark or system-dark is active.",
      font=("Arial", 8),
      foreground="gray",
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

    ttk.Label(appearance_frame, text="UI toolkit (test):").grid(
      row=2, column=0, sticky="w", pady=(8, 2)
    )
    self.ui_toolkit_combo = ttk.Combobox(
      appearance_frame,
      textvariable=self.ui_toolkit_choice_var,
      values=list(self.ui_toolkit_labels.values()),
      state="readonly",
      width=30,
    )
    self.ui_toolkit_combo.grid(row=2, column=1, sticky="w", pady=(8, 2))
    self.ui_toolkit_combo.bind("<<ComboboxSelected>>", self.on_ui_toolkit_changed)

    ttk.Label(
      appearance_frame,
      text=f"Env override: {UI_TOOLKIT_ENV_VAR}=ttk|customtkinter",
      font=("Arial", 8),
      foreground="gray",
    ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 0))

    # FBD executable path
    path_outer, path_frame = self._create_section_frame(
      scrollable_frame, "FBD Path Configuration", padding=10
    )
    path_outer.pack(fill="x", padx=10, pady=5)

    ttk.Label(path_frame, text="FBD Executable:").grid(
      row=0, column=0, sticky="w", pady=2
    )
    self.fbd_path_var = tk.StringVar(value="./fbd")
    self._create_entry(path_frame, textvariable=self.fbd_path_var, width=50).grid(
      row=0, column=1, sticky="ew", pady=2
    )
    self._create_button(path_frame, text="Browse", command=self.browse_fbd).grid(
      row=0, column=2, padx=5
    )

    ttk.Label(
      path_frame,
      text="Note: fbdctl must exist in the same directory as fbd",
      font=("Arial", 8),
      foreground="blue",
    ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 5))

    path_frame.columnconfigure(1, weight=1)

    # RPC settings
    rpc_outer, rpc_frame = self._create_section_frame(
      scrollable_frame, "RPC Configuration", padding=10
    )
    rpc_outer.pack(fill="x", padx=10, pady=5)

    ttk.Label(rpc_frame, text="RPC Host:").grid(row=0, column=0, sticky="w", pady=2)
    self.rpc_host_var = tk.StringVar(value="127.0.0.1")
    self._create_entry(rpc_frame, textvariable=self.rpc_host_var, width=30).grid(
      row=0, column=1, sticky="ew", pady=2
    )

    ttk.Label(rpc_frame, text="RPC Port:").grid(row=1, column=0, sticky="w", pady=2)
    self.rpc_port_var = tk.StringVar(value="32869")
    self._create_entry(rpc_frame, textvariable=self.rpc_port_var, width=30).grid(
      row=1, column=1, sticky="ew", pady=2
    )
    ttk.Label(
      rpc_frame,
      text="Change from 32869 if running multiple instances [!]",
      font=("Arial", 8),
      foreground="red",
    ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 2))
    ttk.Label(
      rpc_frame,
      text="Note: Wallet and auction operations use these RPC settings",
      font=("Arial", 8),
      foreground="blue",
    ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 5))

    rpc_frame.columnconfigure(1, weight=1)

    # Advanced options
    advanced_outer, advanced_frame = self._create_section_frame(
      scrollable_frame, "Advanced Options", padding=10
    )
    advanced_outer.pack(fill="x", padx=10, pady=5)

    # Custom datadir
    ttk.Label(advanced_frame, text="Custom Data Directory (optional):").grid(
      row=0, column=0, sticky="w", pady=2
    )
    self.custom_datadir_var = tk.StringVar(value="")
    self._create_entry(advanced_frame, textvariable=self.custom_datadir_var, width=40).grid(
      row=0, column=1, sticky="ew", pady=2
    )
    ttk.Label(
      advanced_frame,
      text="For multi-instance: set custom datadir + change RPC port above!",
      font=("Arial", 8),
      foreground="red",
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 5))

    # Custom DNS/NS port only (P2P port is not configurable)
    ttk.Label(advanced_frame, text="NS Port (default 32870, for auctions):").grid(
      row=2, column=0, sticky="w", pady=2
    )
    self.custom_dns_port_var = tk.StringVar(value="")
    self._create_entry(advanced_frame, textvariable=self.custom_dns_port_var, width=40).grid(
      row=2, column=1, sticky="ew", pady=2
    )

    ttk.Label(
      advanced_frame,
      text="NS port for auctions only; P2P (32867) not configurable",
      font=("Arial", 8),
      foreground="blue",
    ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 5))

    # Utility button
    self._create_button(
      advanced_frame,
      text="Check for Running FBD Instances",
      command=self.check_running_instances,
    ).grid(row=4, column=0, columnspan=2, pady=10)

    advanced_frame.columnconfigure(1, weight=1)

    # Miner binary management
    miner_outer, miner_frame = self._create_section_frame(
      scrollable_frame, "Miner Binary Management", padding=10
    )
    miner_outer.pack(fill="x", padx=10, pady=5)

    ttk.Label(miner_frame, text="Miner Download URL:").grid(
      row=0, column=0, sticky="w", pady=2
    )
    self.miner_download_url_var = tk.StringVar(value="https://l.woodburn.au/miner")
    self._create_entry(miner_frame, textvariable=self.miner_download_url_var, width=50).grid(
      row=0, column=1, sticky="ew", pady=2
    )

    button_row = self._create_inline_frame(miner_frame)
    button_row.grid(row=0, column=2, padx=5, sticky="n")

    self._create_button(
      button_row,
      text="Check Miner Version",
      command=self.check_miner_version,
    ).pack(fill="x", pady=(0, 3))

    self._create_button(
      button_row,
      text="Check & Auto-Update Miner",
      command=self.download_or_update_miner,
    ).pack(fill="x")

    self.miner_path_label = ttk.Label(
      miner_frame,
      text=f"Target: {self.script_dir / 'miner'}",
      font=("Arial", 8),
      foreground="gray",
    )
    self.miner_path_label.grid(
      row=1, column=0, columnspan=3, sticky="w", pady=(2, 0)
    )

    ttk.Label(
      miner_frame,
      text="Tip: Check compares local and latest binary by SHA256 before replacing.",
      font=("Arial", 8),
      foreground="blue",
    ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 2))

    ttk.Separator(miner_frame, orient="horizontal").grid(
      row=3, column=0, columnspan=3, sticky="ew", pady=6
    )

    ttk.Label(miner_frame, text="FBD Package URL (zip):").grid(
      row=4, column=0, sticky="w", pady=2
    )
    self.fbd_download_url_var = tk.StringVar(
      value="https://fbd.dev/download/fbd-latest-linux-x86_64.zip"
    )
    self._create_entry(
      miner_frame, textvariable=self.fbd_download_url_var, width=50
    ).grid(row=4, column=1, sticky="ew", pady=2)

    fbd_button_row = self._create_inline_frame(miner_frame)
    fbd_button_row.grid(row=4, column=2, padx=5, sticky="n")
    self._create_button(
      fbd_button_row,
      text="Check FBD Version",
      command=self.check_fbd_version,
    ).pack(fill="x", pady=(0, 3))
    self._create_button(
      fbd_button_row,
      text="Check & Auto-Update FBD",
      command=self.download_or_update_fbd,
    ).pack(fill="x")

    self.fbd_target_label = ttk.Label(
      miner_frame,
      text="Target: configured fbd path + adjacent fbdctl",
      font=("Arial", 8),
      foreground="gray",
    )
    self.fbd_target_label.grid(
      row=5, column=0, columnspan=3, sticky="w", pady=(2, 0)
    )

    miner_frame.columnconfigure(1, weight=1)

    # Auto-restart
    restart_outer, restart_frame = self._create_section_frame(
      scrollable_frame, "Auto-Restart", padding=10
    )
    restart_outer.pack(fill="x", padx=10, pady=5)

    self.auto_restart_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
      restart_frame,
      text="Enable auto-restart on crash",
      variable=self.auto_restart_var,
    ).pack(anchor="w")

    ttk.Label(
      restart_frame,
      text="[*]! Recommended for unattended operation and mining",
      font=("Arial", 8),
      foreground="#006600",
    ).pack(anchor="w", padx=(20, 0))

    ttk.Label(restart_frame, text="Restart delay (seconds):").pack(
      anchor="w", pady=2
    )
    self.restart_delay_var = tk.StringVar(value="3")
    self._create_entry(restart_frame, textvariable=self.restart_delay_var, width=10).pack(
      anchor="w"
    )

    # Email Notifications (moved from Node tab)
    email_outer, email_frame = self._create_section_frame(
      scrollable_frame, "Email Notifications (Optional)", padding=10
    )
    email_outer.pack(fill="x", padx=10, pady=5)

    # Enable checkbox
    self.email_enabled_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
      email_frame,
      text="Enable email notifications for critical events",
      variable=self.email_enabled_var,
    ).grid(row=0, column=0, columnspan=3, sticky="w", pady=5)

    # SMTP Server
    ttk.Label(email_frame, text="SMTP Server:").grid(
      row=1, column=0, sticky="w", pady=2
    )
    self.email_smtp_server_var = tk.StringVar(value="smtp.gmail.com")
    self._create_entry(email_frame, textvariable=self.email_smtp_server_var, width=30).grid(
      row=1, column=1, sticky="ew", pady=2
    )

    # SMTP Port
    ttk.Label(email_frame, text="SMTP Port:").grid(
      row=2, column=0, sticky="w", pady=2
    )
    self.email_smtp_port_var = tk.StringVar(value="587")
    self._create_entry(email_frame, textvariable=self.email_smtp_port_var, width=30).grid(
      row=2, column=1, sticky="ew", pady=2
    )

    # From Email
    ttk.Label(email_frame, text="From Email:").grid(
      row=3, column=0, sticky="w", pady=2
    )
    self.email_from_var = tk.StringVar(value="")
    self._create_entry(email_frame, textvariable=self.email_from_var, width=30).grid(
      row=3, column=1, sticky="ew", pady=2
    )

    # Password with show/hide toggle
    ttk.Label(email_frame, text="Password:").grid(
      row=4, column=0, sticky="w", pady=2
    )
    self.email_password_var = tk.StringVar(value="")
    self.email_password_entry = self._create_entry(
      email_frame, textvariable=self.email_password_var, width=25, show="*"
    )
    self.email_password_entry.grid(row=4, column=1, sticky="ew", pady=2)

    # Show/Hide password button
    self.email_password_visible = False
    self._create_button(
      email_frame, text="Show", width=90, command=self.toggle_email_password
    ).grid(row=4, column=2, padx=5)

    # To Email
    ttk.Label(email_frame, text="To Email:").grid(
      row=5, column=0, sticky="w", pady=2
    )
    self.email_to_var = tk.StringVar(value="")
    self._create_entry(email_frame, textvariable=self.email_to_var, width=30).grid(
      row=5, column=1, sticky="ew", pady=2
    )

    # Gmail note
    ttk.Label(
      email_frame,
      text="For Gmail: Use an App Password from https://myaccount.google.com/apppasswords",
      font=("Arial", 8),
      foreground="blue",
    ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(5, 2))

    # Buttons
    email_buttons = self._create_inline_frame(email_frame)
    email_buttons.grid(row=7, column=0, columnspan=3, pady=10)

    self._create_button(
      email_buttons, text="Save Email Settings", command=self.save_email_settings
    ).pack(side="left", padx=5)
    self._create_button(
      email_buttons, text="Send Test Email", command=self.send_test_email
    ).pack(side="left", padx=5)

    # Critical events note
    ttk.Label(
      email_frame,
      text="Emails sent only for: Won Auction, Lost Auction, Automation Failed, High Competing Bid",
      font=("Arial", 8),
      foreground="gray",
    ).grid(row=8, column=0, columnspan=3, sticky="w")

    email_frame.columnconfigure(1, weight=1)

    # Save/Load buttons
    button_frame = self._create_inline_frame(scrollable_frame)
    button_frame.pack(fill="x", padx=10, pady=20)

    self._create_button(
      button_frame, text="Save All Settings", command=self.save_settings
    ).pack(side="left", padx=5)
    self._create_button(
      button_frame, text="Load Settings", command=self.load_settings_file
    ).pack(side="left", padx=5)
    self._create_button(
      button_frame, text="Reset to Defaults", command=self.reset_defaults
    ).pack(side="left", padx=5)

  def toggle_mining_options(self):
    """Enable/disable mining options based on checkbox"""
    if (
      self.mining_enabled.get()
      and self.pool_miner_process
      and self.pool_miner_process.poll() is None
    ):
      self.mining_enabled.set(False)
      messagebox.showwarning(
        "Mining Mode Conflict",
        "Pool miner is running. Stop it before enabling internal miner.",
      )
    state = "normal" if self.mining_enabled.get() else "disabled"
    self.miner_address_entry.configure(state=state)
    self.miner_threads_entry.configure(state=state)

  def build_pool_miner_command(self):
    """Build pool miner command line from settings"""
    wallet_address = self.pool_miner_address_var.get().strip()
    if not wallet_address:
      raise ValueError("Please enter a wallet address for the pool miner")

    host = self.pool_miner_host_var.get().strip() or "pool.woodburn.au"
    threads = self.pool_miner_threads_var.get().strip() or "0"

    miner_path = str((self.script_dir / "miner").resolve())
    cmd = [
      miner_path,
      "--host",
      host,
      "--user",
      f"{wallet_address}.wslgui",
      "--threads",
      threads,
    ]

    if sys.platform == "win32":
      cmd[0] = self._convert_to_wsl_path(cmd[0])
      cmd = ["wsl"] + cmd

    return cmd

  def browse_fbd(self):
    """Browse for FBD executable"""
    filename = filedialog.askopenfilename(
      title="Select FBD executable",
      filetypes=[("Executable", "fbd*"), ("All files", "*")],
    )
    if filename:
      self.fbd_path_var.set(filename)

  def build_command(self):
    """Build FBD command line from settings"""
    cmd = [self.fbd_path_var.get()]

    # Network
    cmd.extend(["--network", self.network_var.get()])

    # Host
    cmd.extend(["--host", self.host_var.get()])

    # Log level
    cmd.extend(["--log-level", self.loglevel_var.get()])

    # Agent
    if self.agent_var.get():
      cmd.extend(["--agent", self.agent_var.get()])

    # Custom datadir (if specified)
    if (
      hasattr(self, "custom_datadir_var")
      and self.custom_datadir_var.get().strip()
    ):
      cmd.extend(["--datadir", self.custom_datadir_var.get().strip()])

    # Custom RPC port (if different from default 32869)
    if (
      self.rpc_port_var.get().strip()
      and self.rpc_port_var.get().strip() != "32869"
    ):
      cmd.extend(["--rpc-port", self.rpc_port_var.get().strip()])

    # Custom DNS port (if specified) - Note: P2P port is not configurable in fbd
    if (
      hasattr(self, "custom_dns_port_var")
      and self.custom_dns_port_var.get().strip()
    ):
      cmd.extend(["--ns-port", self.custom_dns_port_var.get().strip()])

    # Index options
    if self.index_tx_var.get():
      cmd.append("--index-tx")

    if self.index_address_var.get():
      cmd.append("--index-address")

    if self.index_auctions_var.get():
      cmd.append("--index-auctions")

    # Mining
    if self.mining_enabled.get():
      if self.miner_address_var.get():
        cmd.extend(["--miner-address", self.miner_address_var.get()])

      if self.miner_threads_var.get():
        cmd.extend(["--miner-threads", self.miner_threads_var.get()])

    return cmd

  def start_node(self, is_restart=False):
    """Start the FBD node"""
    if self.fbd_process and self.fbd_process.poll() is None:
      if not is_restart:
        messagebox.showwarning("Warning", "Node is already running!")
      return

    if (
      self.mining_enabled.get()
      and self.pool_miner_process
      and self.pool_miner_process.poll() is None
    ):
      messagebox.showwarning(
        "Mining Mode Conflict",
        "Stop pool miner before starting the node with internal mining enabled.",
      )
      return

    cmd = self.build_command()

    # If running on Windows, wrap command with WSL to execute Linux binary
    if sys.platform == "win32":
      # Convert fbd path to WSL format
      wsl_fbd_path = self._convert_to_wsl_path(cmd[0])
      cmd[0] = wsl_fbd_path
      # Prepend wsl to run the command inside WSL
      cmd = ["wsl"] + cmd

    try:
      if is_restart:
        self.log(f"Auto-restarting node (Restart #{self.restart_count})...")
      else:
        self.log("Starting FBD node...")
        self.restart_count = 0 # Reset counter on manual start
        self.restart_label.configure(text="Restarts: 0")
        self.blocks_mined_session = 0 # Reset session block counter
        self.blocks_won_label.configure(text="Blocks Won (Session): 0")

      self.log(f"Command: {' '.join(cmd)}")

      # Start process
      self.fbd_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
      )

      # Start output monitoring thread
      threading.Thread(target=self.monitor_output, daemon=True).start()

      # Update UI
      self.start_btn.configure(state="disabled")
      self.stop_btn.configure(state="normal")
      self.mining_checkbox.configure(state="disabled") # Disable while running
      self.status_label.configure(text="Status: Starting...", foreground="orange")

      # Update block calc tab status
      self.update_block_calc_status(starting=True)

      # Wait a moment then check RPC
      self.root.after(3000, self.read_api_key)

    except Exception as e:
      self.log(f"Error starting node: {e}")
      if not is_restart:
        messagebox.showerror("Error", f"Failed to start node: {e}")

  def stop_node(self):
    """Stop the FBD node"""
    if not self.fbd_process or self.fbd_process.poll() is not None:
      messagebox.showwarning("Warning", "Node is not running!")
      return

    # Disable auto-restart for manual stop
    self.restart_in_progress = False

    try:
      # Try graceful shutdown via RPC
      self.rpc_call("stop")
      self.log("Sent stop command to node...")

      # Wait for process to end
      try:
        self.fbd_process.wait(timeout=10)
      except subprocess.TimeoutExpired:
        self.log("Force terminating...")
        self.fbd_process.terminate()
        self.fbd_process.wait()

      self.fbd_process = None

      # Update UI
      self.start_btn.configure(state="normal")
      self.stop_btn.configure(state="disabled")
      self.mining_checkbox.configure(state="normal") # Re-enable after stop
      self.status_label.configure(text="Status: Stopped")

      # Update block calc tab status
      self.update_block_calc_status(stopped=True)

      self.log("Node stopped.")

    except Exception as e:
      self.log(f"Error stopping node: {e}")

  def start_pool_miner(self):
    """Start the pool miner"""
    if self.pool_miner_process and self.pool_miner_process.poll() is None:
      messagebox.showwarning("Warning", "Pool miner is already running!")
      return

    if self.mining_enabled.get():
      messagebox.showwarning(
        "Mining Mode Conflict",
        "Disable internal mining before starting pool miner.",
      )
      return

    miner_path = self.script_dir / "miner"
    if not miner_path.exists():
      messagebox.showerror(
        "Miner Not Found",
        f"Could not find miner binary at {miner_path}\n\n"
        "Download it and place it in the same directory as fbd_wslgui.py.",
      )
      return

    try:
      cmd = self.build_pool_miner_command()
    except ValueError as e:
      messagebox.showwarning("Warning", str(e))
      return

    try:
      self.log("Starting pool miner...")
      self.log(f"Command: {' '.join(cmd)}")

      self.pool_miner_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
      )

      threading.Thread(target=self.monitor_pool_miner_output, daemon=True).start()
      self.start_pool_miner_btn.configure(state="disabled")
      self.stop_pool_miner_btn.configure(state="normal")
      self.mining_checkbox.configure(state="disabled")
      self.miner_address_entry.configure(state="disabled")
      self.miner_threads_entry.configure(state="disabled")

    except Exception as e:
      self.log(f"Error starting pool miner: {e}")
      messagebox.showerror("Error", f"Failed to start pool miner: {e}")

  def stop_pool_miner(self):
    """Stop the pool miner"""
    if not self.pool_miner_process or self.pool_miner_process.poll() is not None:
      messagebox.showwarning("Warning", "Pool miner is not running!")
      return

    try:
      self.log("Stopping pool miner...")
      self.pool_miner_process.terminate()

      try:
        self.pool_miner_process.wait(timeout=10)
      except subprocess.TimeoutExpired:
        self.log("Force terminating pool miner...")
        self.pool_miner_process.kill()
        self.pool_miner_process.wait()

      self.pool_miner_process = None
      self.update_pool_miner_ui_stopped()
      self.log("Pool miner stopped.")

    except Exception as e:
      self.log(f"Error stopping pool miner: {e}")

  def update_pool_miner_ui_stopped(self):
    """Update pool miner controls when the miner stops"""
    self.start_pool_miner_btn.configure(state="normal")
    self.stop_pool_miner_btn.configure(state="disabled")
    if not self.fbd_process or self.fbd_process.poll() is not None:
      self.mining_checkbox.configure(state="normal")
    self.toggle_mining_options()

  def monitor_pool_miner_output(self):
    """Monitor pool miner output in background thread"""
    process = self.pool_miner_process

    try:
      if not process:
        return

      for line in iter(process.stdout.readline, ""):
        if line:
          self.log(f"[POOL] {line.strip()}")

      if process and process.stdout:
        process.stdout.close()

      exit_code = process.wait() if process else None
      if exit_code is None:
        return

      if exit_code != 0:
        self.log(
          f"[!] Pool miner exited with exit code: {format_process_exit_code(exit_code)}"
        )
        hint = get_process_exit_hint(exit_code)
        if hint:
          self.log(f"[HINT] {hint}")
      else:
        self.log("Pool miner exited cleanly (exit code 0)")

      if self.pool_miner_process is process:
        self.root.after(0, self.update_pool_miner_ui_stopped)

    except Exception as e:
      self.log(f"Error in monitor_pool_miner_output: {e}")
      self.root.after(0, self.update_pool_miner_ui_stopped)

  def monitor_output(self):
    """Monitor node output in background thread"""
    # Store local reference to avoid race condition with stop_node
    process = self.fbd_process

    try:
      if not process:
        return

      for line in iter(process.stdout.readline, ""):
        if line:
          # Check for block win patterns
          self.check_block_win(line)
          self.log(line.strip())

          # Detect LevelDB lock error (another instance running)
          if "lock" in line.lower() and (
            "resource temporarily unavailable" in line.lower()
            or "levelDBError" in line
          ):
            self.log(
              "[!] [!] [!] CRITICAL: Database locked - another fbd instance is running!"
            )
            self.root.after(0, self.show_database_lock_error)

          # Detect index-address on existing chain error
          if "--index-address enabled but no existing index" in line:
            self.log(
              "\u26a0\u26a0\u26a0 CRITICAL: Index-address enabled on existing chain!"
            )
            self.root.after(0, self.show_index_address_chain_error)

      if process and process.stdout:
        process.stdout.close()

      # Wait for process to fully exit (check if still valid)
      exit_code = process.wait() if process else None
      if exit_code is None:
        return

      # Detect crash
      if exit_code != 0:
        self.log(
          f"[!] Node crashed with exit code: {format_process_exit_code(exit_code)}"
        )
        hint = get_process_exit_hint(exit_code)
        if hint:
          self.log(f"[HINT] {hint}")
      else:
        self.log("Node exited cleanly (exit code 0)")

      # Check if auto-restart is enabled (and process wasn't manually stopped)
      if (
        self.auto_restart_var.get()
        and not self.restart_in_progress
        and self.fbd_process is process
      ):
        self.handle_node_crash(exit_code)
      else:
        # Update UI for manual stop
        self.root.after(0, self.update_ui_stopped)

    except Exception as e:
      self.log(f"Error in monitor_output: {e}")
      # Update UI on error
      self.root.after(0, self.update_ui_stopped)

  def handle_node_crash(self, exit_code):
    """Handle node crash with auto-restart"""
    self.restart_count += 1

    try:
      delay = int(self.restart_delay_var.get())
    except ValueError:
      delay = 3

    self.log(f"[*] Auto-restart enabled. Waiting {delay} seconds before restart...")
    self.log(f"Total restarts this session: {self.restart_count}")

    # Update restart counter in UI
    self.root.after(
      0, lambda: self.restart_label.configure(text=f"Restarts: {self.restart_count}")
    )

    # Schedule restart after delay
    self.root.after(delay * 1000, self.do_auto_restart)

  def do_auto_restart(self):
    """Execute auto-restart"""
    self.restart_in_progress = True
    self.start_node(is_restart=True)
    self.restart_in_progress = False

  def check_block_win(self, line):
    """Check log line for block win and update counter"""
    # Common patterns for block mining success
    block_win_patterns = [
      "block mined",
      "found block",
      "new block found",
      "mined block",
      "successfully mined",
      "block hash:", # Often follows mining success
      "solved block",
    ]

    line_lower = line.lower()
    for pattern in block_win_patterns:
      if pattern in line_lower:
        self.blocks_mined_session += 1
        self.root.after(0, self.update_block_win_ui, line)
        break

  def update_block_win_ui(self, line):
    """Update UI to show block win (runs in main thread)"""
    # Update counter
    self.blocks_won_label.configure(
      text=f"Blocks Won (Session): {self.blocks_mined_session}"
    )

    # Log with highlighting
    self.log("" + "=" * 60)
    self.log(f"[*] BLOCK WIN #{self.blocks_mined_session}! [*]")
    self.log(line.strip())
    self.log("=" * 60)

    # Show popup notification
    messagebox.showinfo(
      "Block Mined!",
      f"Congratulations! Block #{self.blocks_mined_session} mined this session!\n\n{line.strip()}",
      parent=self.root,
    )

  def update_ui_stopped(self):
    """Update UI when node stops without restart"""
    self.start_btn.configure(state="normal")
    self.stop_btn.configure(state="disabled")
    self.mining_checkbox.configure(state="normal") # Re-enable after stop
    self.status_label.configure(text="Status: Stopped", foreground="red")
    self.block_label.configure(text="Block Height: -")
    self.peers_label.configure(text="Peers: -")

    # Update block calc tab status
    self.update_block_calc_status(stopped=True)

  def show_index_address_chain_error(self):
    """Show error dialog for index-address on existing chain with action button"""
    # Disable auto-restart to prevent restart loop
    self.auto_restart_var.set(False)

    self.log("[!] Auto-restart disabled due to index-address chain error")
    self.log("[!] Fix the issue before re-enabling auto-restart")

    # Create custom dialog with action button
    dialog = self._create_toplevel()
    dialog.title("Index-Address Error - Chain Reset Required")
    dialog.geometry("600x400")
    dialog.transient(self.root)
    dialog.grab_set()

    # Error message
    message_frame = ttk.Frame(dialog, padding=20)
    message_frame.pack(fill="both", expand=True)

    ttk.Label(
      message_frame,
      text="[!] Node Crashed - Chain Reset Required",
      font=("Arial", 14, "bold"),
      foreground="#cc0000",
    ).pack(pady=(0, 10))

    error_text = self._create_log_widget(
      message_frame, height=10, wrap=tk.WORD, font=("Arial", 10)
    )
    error_text.pack(fill="both", expand=True)

    error_text.insert(
      "1.0",
      "Node crashed because --index-address was enabled on an existing chain.\n\n"
      "Current chain has blocks but no address index exists.\n"
      "Auto-restart has been DISABLED to prevent crash loop.\n\n"
      "*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]\n\n"
      "SOLUTION OPTIONS:\n\n"
      "Option A) Delete chain and resync (keeps index-address enabled)\n"
      "  * Click 'Delete Chain & Restart' button below\n"
      "  * This will delete ~/.fbd/chain and ~/.fbd/blocks directories\n"
      "  * Prevents index-tx confusion during resync\n"
      "  * Node will resync from scratch with indexing enabled\n\n"
      "Option B) Disable indexing and restart\n"
      "  * Uncheck 'Index Addresses' in Node & Mining tab\n"
      "  * Restart the node manually\n"
      "  * Note: Wallet operations will NOT work without indexing\n\n"
      "*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]*[~]\n\n"
      "[!] IMPORTANT: Wallet address operations require --index-address!",
    )
    error_text.configure(state="disabled")

    # Button frame
    button_frame = ttk.Frame(dialog, padding=10)
    button_frame.pack(fill="x")

    def delete_and_close():
      """Delete and close."""
      dialog.destroy()
      self.delete_chain_data(auto_restart=True, from_error=True)

    self._create_button(
      button_frame, text="[!] Delete Chain & Restart", command=delete_and_close
    ).pack(side="left", padx=5)

    self._create_button(button_frame, text="Close", command=dialog.destroy).pack(
      side="right", padx=5
    )

  def delete_chain_data(self, auto_restart=False, from_error=False):
    """Delete blockchain chain data with safety checks and confirmation"""
    # Step 1: Check if node is running
    if self.fbd_process is not None and self.fbd_process.poll() is None:
      stop_node = messagebox.askyesno(
        "Node Running",
        "The FBD node is currently running and must be stopped before deleting chain data.\n\n"
        "Stop the node now?",
        icon="warning",
      )
      if stop_node:
        self.log("[*]> Stopping node for chain data deletion...")
        self.stop_node()
        # Wait a moment for shutdown
        time.sleep(2)
      else:
        self.log("[!] Chain deletion cancelled - node still running")
        return

    # Step 2: Determine chain directory paths
    # Check for custom datadir
    if (
      hasattr(self, "custom_datadir_var")
      and self.custom_datadir_var.get().strip()
    ):
      datadir = Path(self.custom_datadir_var.get().strip()).expanduser()
    else:
      datadir = Path.home() / ".fbd"

    chain_dir = datadir / "chain"
    blocks_dir = datadir / "blocks"

    # Step 3: Check if any chain data exists
    dirs_to_delete = []
    if chain_dir.exists():
      dirs_to_delete.append(("chain", chain_dir))
    if blocks_dir.exists():
      dirs_to_delete.append(("blocks", blocks_dir))

    if not dirs_to_delete:
      messagebox.showinfo(
        "No Chain Data",
        f"No chain data directories exist in:\n{datadir}\n\n"
        "Nothing to delete.",
      )
      return

    # Step 4: Safety confirmation (unless called from error dialog)
    if not from_error:
      dirs_list = "\n".join(
        [f"[*] {name}: {path}" for name, path in dirs_to_delete]
      )
      confirm = messagebox.askyesno(
        "[!] Confirm Chain Deletion",
        f"You are about to DELETE all blockchain data:\n\n"
        f"{dirs_list}\n\n"
        f"This will:\n"
        f" * Delete all synced blockchain data\n"
        f" * Delete block index data (prevents index-tx confusion)\n"
        f" * Require complete resync (may take hours)\n"
        f" * NOT affect your wallets or keys\n\n"
        f"This action CANNOT be undone!\n\n"
        f"Are you absolutely sure?",
        icon="warning",
      )
      if not confirm:
        self.log("[!] Chain deletion cancelled by user")
        return

    # Step 5: Perform deletion
    try:
      self.log(f"[!] Deleting blockchain data from: {datadir}")

      # Show progress
      progress_dialog = self._create_toplevel()
      progress_dialog.title("Deleting Chain Data")
      progress_dialog.geometry("450x180")
      progress_dialog.transient(self.root)
      progress_dialog.grab_set()

      ttk.Label(
        progress_dialog,
        text="[!] Deleting blockchain data...",
        font=("Arial", 11, "bold"),
      ).pack(pady=20)

      progress_label = ttk.Label(progress_dialog, text="", font=("Arial", 9))
      progress_label.pack(pady=10)

      # Delete each directory
      for name, dir_path in dirs_to_delete:
        progress_label.configure(text=f"Deleting {name}: {dir_path}")
        progress_dialog.update()

        if sys.platform == "win32":
          # On Windows/WSL
          if dir_path.exists():
            shutil.rmtree(dir_path)
        else:
          # Native Linux
          shutil.rmtree(dir_path)

        self.log(f" [OK] Deleted {name} directory")

      progress_dialog.destroy()

      self.log("[OK] All chain data deleted successfully")

      # Step 6: Success confirmation with restart option
      if auto_restart or messagebox.askyesno(
        "[OK] Chain Data Deleted",
        f"Chain data has been successfully deleted!\n\n"
        f"The node will need to resync from scratch when started.\n\n"
        f"Would you like to restart the node now?",
        icon="info",
      ):
        self.log("[*] Restarting node after chain deletion...")
        time.sleep(1)
        self.start_node(is_restart=True)
      else:
        messagebox.showinfo(
          "Ready to Resync",
          "Chain data deleted.\n\n"
          "Start the node manually when ready to begin resyncing.",
        )

    except PermissionError as e:
      self.log(f"[X] Permission denied deleting chain: {e}")
      messagebox.showerror(
        "Permission Denied",
        f"Could not delete chain data due to permissions.\n\n"
        f"Error: {e}\n\n"
        f"Try running with appropriate permissions or delete manually:\n"
        f"rm -rf {datadir}/chain {datadir}/blocks",
      )
    except Exception as e:
      self.log(f"[X] Error deleting chain: {e}")
      messagebox.showerror(
        "Deletion Failed",
        f"Failed to delete chain data.\n\n"
        f"Error: {e}\n\n"
        f"You may need to delete manually:\n"
        f"rm -rf {datadir}/chain {datadir}/blocks",
      )

  def show_database_lock_error(self):
    """Show error dialog for database lock (another instance running)"""
    # Disable auto-restart to prevent restart loop
    self.auto_restart_var.set(False)

    messagebox.showerror(
      "Database Lock Error - Another Instance Running",
      "Node crashed because another fbd instance is already using the database.\n\n"
      "Error: Resource temporarily unavailable (LevelDB LOCK)\n"
      "Auto-restart has been DISABLED to prevent crash loop.\n\n"
      "SOLUTIONS:\n\n"
      "Option 1 (Simple): Stop the other fbd instance\n"
      "  * Check if fbd is running in terminal/background\n"
      "  * Use: ps aux | grep fbd\n"
      "  * Kill it: pkill fbd\n\n"
      "Option 2 (Advanced): Run multiple instances with different datadirs\n"
      "  * Add --datadir flag to fbd command\n"
      "  * Use different RPC and NS ports in GUI settings\n"
      "  * Example: Change RPC Port to 32879, NS Port to 32880\n"
      "  * Note: P2P port (32867) is not configurable\n\n"
      "You CANNOT run two instances with the same datadir (~/.fbd).",
      icon="error",
    )

    self.log("[!] Auto-restart disabled due to database lock error")
    self.log("[!] Another fbd instance is running - check with: ps aux | grep fbd")
    self.log("[!] Fix the issue before re-enabling auto-restart")

  def read_api_key(self):
    """Read API key from .cookie file"""
    # Determine the datadir (custom or default)
    if (
      hasattr(self, "custom_datadir_var")
      and self.custom_datadir_var.get().strip()
    ):
      datadir = Path(self.custom_datadir_var.get().strip()).expanduser()
    else:
      datadir = Path.home() / ".fbd"

    cookie_path = datadir / ".cookie"
    try:
      if cookie_path.exists():
        with open(cookie_path, "r") as f:
          self.rpc_password = f.read().strip()
        self.log(f"RPC API key loaded from {cookie_path}")
        self.refresh_status()
      else:
        self.root.after(2000, self.read_api_key) # Retry
    except Exception as e:
      self.log(f"Error reading API key: {e}")

  def rpc_call(self, method, params=None):
    """Make RPC call to FBD node"""
    if params is None:
      params = []

    url = f"http://{self.rpc_host_var.get()}:{self.rpc_port_var.get()}/"

    payload = {"method": method, "params": params, "id": 1}

    try:
      response = requests.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(self.rpc_user, self.rpc_password or ""),
        timeout=5,
      )
      response.raise_for_status()
      data = response.json()

      if data.get("error"):
        raise Exception(data["error"])

      return data.get("result")

    except requests.exceptions.ConnectionError:
      return None
    except Exception as e:
      self.log(f"RPC Error ({method}): {e}")
      return None

  def check_index_address_error(self, error_message):
    """Check if error is due to missing --index-address and notify user"""
    error_str = str(error_message).lower()
    index_keywords = [
      "index",
      "address",
      "txindex",
      "not indexed",
      "requires indexing",
    ]

    if any(keyword in error_str for keyword in index_keywords):
      self.log("[!] Operation requires --index-address to be enabled")

      if not self.index_address_var.get():
        messagebox.showwarning(
          "Index Required",
          "This operation requires the node to run with --index-address enabled.\n\n"
          "To enable:\n"
          "1. Stop the node\n"
          "2. Check 'Index Addresses (--index-address)' in Node & Mining tab\n"
          "3. If the chain already has blocks, you may need to delete ~/.fbd/chain and resync\n"
          "4. Restart the node",
        )
        return True
      else:
        messagebox.showwarning(
          "Index Incomplete",
          "Address indexing is enabled but may be incomplete.\n\n"
          "If you enabled --index-address after the chain had blocks:\n"
          "1. Stop the node\n"
          "2. Delete ~/.fbd/chain directory\n"
          "3. Restart to resync with indexing",
        )
        return True
    return False

  def start_monitoring(self):
    """Start periodic status monitoring"""
    self.monitoring = True
    self.monitor_status()

  def monitor_status(self):
    """Periodically check node status"""
    if self.monitoring:
      self.refresh_status()
      self.check_rollout_reminders()
      self.check_watchlist_auction_start()
      self.root.after(5000, self.monitor_status) # Every 5 seconds

  def refresh_status(self):
    """Refresh node status"""
    # Check if process exists and is running
    process_running = (
      self.fbd_process is not None and self.fbd_process.poll() is None
    )

    if not process_running:
      # Node is not running - update UI to reflect stopped state
      if self.status_label.cget("text") != "Status: Stopped":
        self.status_label.configure(text="Status: Stopped", foreground="red")
        self.block_label.configure(text="Block Height: -")
        self.peers_label.configure(text="Peers: -")
        # Update block calc tab
        self.update_block_calc_status(stopped=True)
      return

    # Try RPC first
    info = self.rpc_call("getblockchaininfo")

    if info:
      blocks = info.get("blocks", "-")
      self.status_label.configure(text="Status: Running", foreground="green")
      self.block_label.configure(text=f"Block Height: {blocks}")

      # Update block calc tab with current height
      self.update_block_calc_status(current_height=blocks)

      # Get network info
      net_info = self.rpc_call("getnetworkinfo")
      if net_info:
        connections = net_info.get("connections", "-")
        self.peers_label.configure(text=f"Peers: {connections}")
    else:
      # If RPC fails, try fbdctl
      try:
        cmd, fbdctl_path = self.get_fbdctl_command("getblockchaininfo")
        result = subprocess.run(
          cmd,
          capture_output=True,
          text=True,
          timeout=5,
          cwd=Path(self.fbd_path_var.get()).parent,
        )

        if result.returncode == 0:
          response = json.loads(result.stdout)
          info = (
            response.get("result", {})
            if isinstance(response, dict)
            else response
          )
          blocks = info.get("blocks", "-")
          self.status_label.configure(text="Status: Running", foreground="green")
          self.block_label.configure(text=f"Block Height: {blocks}")

          # Update block calc tab with current height
          self.update_block_calc_status(current_height=blocks)

          # Get peer count
          peer_cmd, _ = self.get_fbdctl_command("getpeerinfo")
          peer_result = subprocess.run(
            peer_cmd,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(self.fbd_path_var.get()).parent,
          )
          if peer_result.returncode == 0:
            response = json.loads(peer_result.stdout)
            peers = (
              response.get("result", [])
              if isinstance(response, dict)
              else response
            )
            peer_count = len(peers) if isinstance(peers, list) else "-"
            self.peers_label.configure(text=f"Peers: {peer_count}")
        else:
          # fbdctl failed, check if node is still starting
          if process_running:
            self.status_label.configure(
              text="Status: Starting...", foreground="orange"
            )
            # Update block calc as starting
            self.update_block_calc_status(starting=True)
          else:
            self.status_label.configure(
              text="Status: Stopped", foreground="red"
            )
            self.block_label.configure(text="Block Height: -")
            self.peers_label.configure(text="Peers: -")
            # Update block calc as stopped
            self.update_block_calc_status(stopped=True)
      except Exception as e:
        self.log(f"Error refreshing status: {e}")
        # If error occurred, check if node is still starting
        if process_running:
          self.status_label.configure(
            text="Status: Starting...", foreground="orange"
          )
          # Update block calc as starting
          self.update_block_calc_status(starting=True)
        else:
          self.status_label.configure(text="Status: Stopped", foreground="red")
          self.block_label.configure(text="Block Height: -")
          self.peers_label.configure(text="Peers: -")
          # Update block calc as stopped
          self.update_block_calc_status(stopped=True)
          # Update block calc as stopped
          self.update_block_calc_status(stopped=True)

  def update_block_calc_status(
    self, current_height=None, stopped=False, starting=False
  ):
    """Update block calculator tab status automatically

    Args:
      current_height: Current block height (int or string)
      stopped: True if node is stopped
      starting: True if node is starting
    """
    # Check if block calc UI elements exist
    if not hasattr(self, "calc_node_status_label") or not hasattr(
      self, "calc_current_height_label"
    ):
      return

    try:
      if stopped:
        # Node stopped
        self.calc_node_status_label.configure(
          text="Node Status: Not Running [OK]-", foreground="red"
        )
        self.calc_current_height_label.configure(text="Current Block: -")
        # Reset refresh state
        self.calc_refresh_in_progress = False
        self.calc_refresh_retry_count = 0
      elif starting:
        # Node starting
        self.calc_node_status_label.configure(
          text="Node Status: Starting... [ ]", foreground="orange"
        )
        # Don't change current height while starting
      elif current_height is not None:
        # Node running with current height
        self.calc_node_status_label.configure(
          text="Node Status: Running [OK]", foreground="green"
        )
        # Format height with comma separator if it's a number
        try:
          height_int = int(current_height)
          self.calc_current_height_label.configure(
            text=f"Current Block: {height_int:,}"
          )
        except (ValueError, TypeError):
          self.calc_current_height_label.configure(
            text=f"Current Block: {current_height}"
          )
        # Reset refresh state on success
        self.calc_refresh_in_progress = False
        self.calc_refresh_retry_count = 0
    except Exception as e:
      # Silently ignore errors (UI elements might not be created yet)
      pass

  def get_mining_stats(self):
    """Get mining statistics for the configured mining address"""
    mining_address = self.miner_address_var.get()
    if not mining_address:
      messagebox.showwarning(
        "No Mining Address", "Please configure a mining address first"
      )
      return

    self.log(f"Fetching mining statistics for: {mining_address}")

    try:
      # Try to get address info via RPC (requires --index-address)
      addr_info = self.rpc_call("getaddressinfo", [mining_address])

      if addr_info:
        # Try to get balance to show mining rewards
        self.log(f"Address Info: {json.dumps(addr_info, indent=2)}")

        balance_info = self.rpc_call("getaddressbalance", [mining_address])
        if balance_info:
          self.log(f"Mining Rewards Balance: {balance_info}")
          messagebox.showinfo(
            "Mining Statistics",
            f"Mining Address: {mining_address}\\n\\n"
            f"Session Blocks Won: {self.blocks_mined_session}\\n"
            f"Balance: {balance_info}\\n\\n"
            f"See log for detailed info.",
          )
        else:
          messagebox.showinfo(
            "Mining Statistics",
            f"Mining Address: {mining_address}\\n\\n"
            f"Session Blocks Won: {self.blocks_mined_session}\\n\\n"
            f"Unable to query historical data.\\n"
            f"Enable --index-address for full statistics.",
          )
      else:
        # RPC failed, try fbdctl
        self.get_mining_stats_fbdctl(mining_address)

    except Exception as e:
      error_msg = str(e)
      self.log(f"Error getting mining stats: {error_msg}")

      if "index" in error_msg.lower():
        messagebox.showwarning(
          "Indexing Required",
          f"Session Blocks Won: {self.blocks_mined_session}\\n\\n"
          f"To view historical mining statistics, enable:\\n"
          f"--index-address in Node & Mining settings\\n\\n"
          f"Note: May require chain resync if enabled after blocks exist.",
        )
      else:
        messagebox.showerror(
          "Error", f"Failed to get mining stats: {error_msg}"
        )

  def get_mining_stats_fbdctl(self, mining_address):
    """Get mining stats using fbdctl as fallback"""
    try:
      cmd, fbdctl_path = self.get_fbdctl_command("getaddressinfo", mining_address)

      # Try getaddressinfo
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
      )

      if result.returncode == 0:
        self.log(f"Mining Address Info:\\n{result.stdout}")
        messagebox.showinfo(
          "Mining Statistics",
          f"Mining Address: {mining_address}\\n\\n"
          f"Session Blocks Won: {self.blocks_mined_session}\\n\\n"
          f"See log for address details.",
        )
      else:
        self.log(f"fbdctl error: {result.stderr}")
        messagebox.showinfo(
          "Mining Statistics",
          f"Mining Address: {mining_address}\\n\\n"
          f"Session Blocks Won: {self.blocks_mined_session}\\n\\n"
          f"Historical data unavailable.\\n"
          f"Ensure node is running with --index-address.",
        )
    except Exception as e:
      self.log(f"Error using fbdctl: {e}")

  # Wallet methods
  def check_node_running(self):
    """Check if the node is running, show warning if not"""
    if not self.fbd_process or self.fbd_process.poll() is not None:
      result = messagebox.askyesno(
        "Node Not Running",
        "The FBD node is not running!\n\n"
        "Most wallet operations require a running node.\n\n"
        "Would you like to start the node now?",
      )
      if result:
        # Switch to Node & Mining tab
        self._notebook_select(0)
      return False
    return True

  def update_wallet_dropdown(self, wallets):
    """Update active wallet dropdown values without changing selection unexpectedly."""
    if not hasattr(self, "wallet_combo"):
      return

    wallet_list = [w for w in wallets if w]
    if not wallet_list:
      wallet_list = ["main"]

    current_wallet = self.wallet_name_var.get().strip()
    if current_wallet and current_wallet not in wallet_list:
      wallet_list.append(current_wallet)

    self.wallet_combo["values"] = wallet_list

    if current_wallet:
      self.wallet_name_var.set(current_wallet)
    else:
      self.wallet_name_var.set(wallet_list[0])

  def on_active_wallet_selected(self, _event=None):
    """Handle active wallet changes from the dropdown."""
    selected_wallet = self.wallet_name_var.get().strip()
    if not selected_wallet:
      return

    self.log(f"Active wallet set to: {selected_wallet}")
    self.get_wallet_info()
    self.refresh_auction_balance()

  def get_wallet_address(self, wallet):
    """Get address for a specific wallet, returning None when unavailable."""
    cmd_info, _ = self.get_fbdctl_command("--wallet", wallet, "getwalletinfo")
    result_info = subprocess.run(
      cmd_info,
      capture_output=True,
      text=True,
      cwd=Path(self.fbd_path_var.get()).parent,
    )

    if result_info.returncode != 0:
      error_msg = (result_info.stderr or result_info.stdout or "").strip()
      raise RuntimeError(error_msg or "Unknown error retrieving wallet info")

    response_info = json.loads(result_info.stdout)
    data_info = (
      response_info.get("result", {})
      if isinstance(response_info, dict)
      else response_info
    )
    return data_info.get("address")

  def list_wallets(self, show_feedback=True):
    """Refresh wallet list and populate the active-wallet dropdown."""
    # Check if node is running
    if not self.check_node_running():
      return []

    try:
      cmd, fbdctl_path = self.get_fbdctl_command("listwallets")

      self.log(f"[DEBUG] Running: {' '.join(cmd)}")
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
      )

      self.log(f"[DEBUG] Return code: {result.returncode}")
      self.log(f"[DEBUG] stdout: {result.stdout}")
      self.log(f"[DEBUG] stderr: {result.stderr}")

      if result.returncode == 0:
        if not result.stdout.strip():
          self.log("No wallets found (empty response)")
          if show_feedback:
            messagebox.showinfo("Wallets", "No wallets found")
          return []

        try:
          response = json.loads(result.stdout)
          wallets = (
            response.get("result", [])
            if isinstance(response, dict)
            else response
          )
          if wallets:
            wallets = [str(w) for w in wallets if str(w).strip()]
            self.log(f"Wallets: {', '.join(wallets)}")
            self.update_wallet_dropdown(wallets)
            if show_feedback:
              messagebox.showinfo(
                "Wallets Refreshed",
                f"Loaded {len(wallets)} wallet(s) into Active Wallet dropdown.",
              )
            return wallets

          self.log("No wallets found")
          if show_feedback:
            messagebox.showinfo("Wallets", "No wallets found")
          return []
        except json.JSONDecodeError as je:
          self.log(f"Error parsing wallet list JSON: {je}")
          self.log(f"Raw output: {result.stdout}")
          if show_feedback:
            messagebox.showwarning(
              "Warning",
              f"Could not parse wallet list\nRaw output: {result.stdout}",
            )
          return []

      error_msg = result.stderr
      self.log(f"Error listing wallets (code {result.returncode}): {error_msg}")

      if "Connection failed" in error_msg or "Couldn't connect" in error_msg:
        if show_feedback:
          messagebox.showwarning(
            "Node Not Running",
            "The FBD node is not running!\n\n"
            "Wallet operations require a running node.\n\n"
            "Please start the node from the 'Node & Mining' tab first.",
          )
        return []

      if not self.check_index_address_error(error_msg) and show_feedback:
        messagebox.showwarning(
          "Warning", f"Could not retrieve wallet list\nError: {error_msg}"
        )
      return []
    except Exception as e:
      self.log(f"Exception listing wallets: {type(e).__name__}: {e}")
      if show_feedback:
        messagebox.showwarning(
          "Warning", f"Could not retrieve wallet list: {e}"
        )
      return []

  def copy_wallet_address_dialog(self):
    """Copy wallet address from any available wallet without changing active wallet."""
    if not self.check_node_running():
      return

    wallets = self.list_wallets(show_feedback=False)
    if not wallets:
      messagebox.showinfo(
        "No Wallets", "No wallets available. Create or import a wallet first."
      )
      return

    dialog = self._create_toplevel()
    dialog.title("Copy Wallet Address")
    dialog.geometry("620x260")
    dialog.transient(self.root)
    dialog.grab_set()

    ttk.Label(
      dialog,
      text="Select wallet to copy its address (does not change active wallet):",
      font=("Arial", 10, "bold"),
    ).pack(pady=(12, 8), padx=10, anchor="w")

    selected_wallet_var = tk.StringVar(
      value=self.wallet_name_var.get() or wallets[0]
    )
    wallet_picker = ttk.Combobox(
      dialog,
      textvariable=selected_wallet_var,
      values=wallets,
      state="readonly",
      width=50,
    )
    wallet_picker.pack(padx=10, fill="x")

    result_label = ttk.Label(dialog, text="")
    result_label.pack(pady=(8, 4), padx=10, anchor="w")

    # Keep picker on a valid wallet if active wallet isn't in the list.
    if selected_wallet_var.get() not in wallets:
      selected_wallet_var.set(wallets[0])

    def get_selected_wallet_address():
      """Get selected wallet address."""
      selected_wallet = selected_wallet_var.get().strip()
      if not selected_wallet:
        messagebox.showwarning(
          "Wallet Required", "Please select a wallet first."
        )
        return None, None

      try:
        address = self.get_wallet_address(selected_wallet)
        if not address:
          messagebox.showwarning(
            "Address Unavailable",
            f"Wallet '{selected_wallet}' did not return an address.",
          )
          return None, None
        return selected_wallet, address
      except Exception as e:
        self.log(
          f"Error copying wallet address for '{selected_wallet}': {type(e).__name__}: {e}",
          level="error",
        )
        if not self.check_index_address_error(str(e)):
          messagebox.showerror(
            "Copy Address Failed",
            f"Could not get address for wallet '{selected_wallet}'.\n\nError: {e}",
          )
        return None, None

    def copy_to_clipboard(address):
      """Copy to clipboard."""
      self.root.clipboard_clear()
      self.root.clipboard_append(address)
      self.root.update()

    def copy_selected_wallet_address():
      """Copy selected wallet address."""
      selected_wallet, address = get_selected_wallet_address()
      if not address:
        return

      copy_to_clipboard(address)
      result_label.configure(text=f"Copied address for wallet '{selected_wallet}'.")
      self.log(f"Copied address for wallet '{selected_wallet}': {address}")

    def copy_into_send_to():
      """Copy into send to."""
      selected_wallet, address = get_selected_wallet_address()
      if not address:
        return

      copy_to_clipboard(address)
      self.send_address_var.set(address)
      result_label.configure(
        text=f"Copied address and filled Send To for wallet '{selected_wallet}'."
      )
      self.log(
        f"Filled Send To address from wallet '{selected_wallet}': {address}"
      )

    def copy_into_pool_miner_address():
      """Copy into pool miner address."""
      selected_wallet, address = get_selected_wallet_address()
      if not address:
        return

      copy_to_clipboard(address)
      self.pool_miner_address_var.set(address)
      result_label.configure(
        text=f"Copied address and filled Pool Miner Address for wallet '{selected_wallet}'."
      )
      self.log(
        f"Filled Pool Miner Address from wallet '{selected_wallet}': {address}"
      )

    def copy_into_miner_address():
      """Copy into miner address."""
      selected_wallet, address = get_selected_wallet_address()
      if not address:
        return

      copy_to_clipboard(address)
      self.miner_address_var.set(address)
      result_label.configure(
        text=f"Copied address and filled Miner Address for wallet '{selected_wallet}'."
      )
      self.log(f"Filled Miner Address from wallet '{selected_wallet}': {address}")

    button_frame = ttk.Frame(dialog)
    button_frame.pack(pady=(0, 10))

    self._create_button(
      button_frame, text="Copy Address", command=copy_selected_wallet_address
    ).pack(side="left", padx=5)

    self._create_button(
      button_frame, text="Copy -> Send To", command=copy_into_send_to
    ).pack(side="left", padx=5)

    self._create_button(
      button_frame,
      text="Copy -> Pool Miner Address",
      command=copy_into_pool_miner_address,
    ).pack(side="left", padx=5)

    self._create_button(
      button_frame, text="Copy -> Miner Address", command=copy_into_miner_address
    ).pack(side="left", padx=5)

    self._create_button(button_frame, text="Close", command=dialog.destroy).pack(
      side="left", padx=5
    )

    # Center dialog on parent window
    dialog.update_idletasks()
    x = (
      self.root.winfo_x()
      + (self.root.winfo_width() // 2)
      - (dialog.winfo_width() // 2)
    )
    y = (
      self.root.winfo_y()
      + (self.root.winfo_height() // 2)
      - (dialog.winfo_height() // 2)
    )
    dialog.geometry(f"+{x}+{y}")

  def create_wallet(self):
    """Create a new wallet"""
    # Check if node is running
    if not self.check_node_running():
      return

    name = simpledialog.askstring("Create Wallet", "Enter wallet name:")
    if name:
      result = self.rpc_call("createwallet", [name])
      if result:
        self.log(f"Wallet created: {name}")
        if "mnemonic" in result:
          self.show_seed_dialog(name, result["mnemonic"])
        self.wallet_name_var.set(name)
        self.list_wallets(show_feedback=False)

  def import_wallet(self):
    """Import an existing wallet from seed phrase"""
    # Check if node is running
    if not self.check_node_running():
      return

    # Create dialog for wallet import
    dialog = self._create_toplevel()
    dialog.title("Import Wallet")
    dialog.geometry("500x250")
    dialog.transient(self.root)
    dialog.grab_set()

    ttk.Label(dialog, text="Wallet Name:", font=("Arial", 10)).pack(pady=(10, 5))
    name_entry = self._create_entry(dialog, width=40)
    name_entry.pack(pady=5)

    ttk.Label(dialog, text="Seed Phrase (Mnemonic):", font=("Arial", 10)).pack(
      pady=(10, 5)
    )
    seed_entry = self._create_entry(dialog, width=60)
    seed_entry.pack(pady=5)

    ttk.Label(
      dialog,
      text="Enter your 12 or 24-word seed phrase, separated by spaces",
      font=("Arial", 8),
      foreground="gray",
    ).pack(pady=5)

    def do_import():
      """Do import."""
      wallet_name = name_entry.get().strip()
      seed_phrase = seed_entry.get().strip()

      if not wallet_name or not seed_phrase:
        messagebox.showwarning(
          "Error", "Please provide both wallet name and seed phrase"
        )
        return

      try:
        cmd, fbdctl_path = self.get_fbdctl_command(
          "createwallet", wallet_name, seed_phrase
        )
        result = subprocess.run(
          cmd,
          capture_output=True,
          text=True,
          cwd=Path(self.fbd_path_var.get()).parent,
        )

        if result.returncode == 0:
          self.log(f"Wallet imported from mnemonic: {wallet_name}")
          messagebox.showinfo(
            "Success",
            f"Wallet '{wallet_name}' restored from mnemonic successfully!",
          )
          self.wallet_name_var.set(wallet_name)
          self.list_wallets(show_feedback=False)
          dialog.destroy()
        else:
          stderr_msg = (result.stderr or "").strip()
          stdout_msg = (result.stdout or "").strip()
          error_msg = (
            stderr_msg
            or stdout_msg
            or "No error details returned by fbdctl."
          )

          # Avoid logging sensitive seed phrase; only log wallet and tool output.
          self.log(
            "Error importing wallet "
            f"'{wallet_name}' (exit code {result.returncode}). "
            f"stderr: {stderr_msg or '<empty>'}; stdout: {stdout_msg or '<empty>'}",
            level="error",
          )
          messagebox.showerror(
            "Wallet Import Failed",
            "Failed to import wallet.\n\n"
            f"Wallet: {wallet_name}\n"
            f"Exit code: {result.returncode}\n\n"
            f"Details:\n{error_msg}",
          )
      except Exception as e:
        self.log(
          f"Exception importing wallet '{wallet_name}': {type(e).__name__}: {e}",
          level="error",
        )
        messagebox.showerror(
          "Wallet Import Failed",
          "Failed to import wallet due to an unexpected error.\n\n"
          f"Wallet: {wallet_name}\n"
          f"Error type: {type(e).__name__}\n"
          f"Details: {e}",
        )

    self._create_button(dialog, text="Import", command=do_import).pack(pady=10)
    self._create_button(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)

  def delete_wallet(self):
    """Delete a wallet"""
    wallet = self.wallet_name_var.get()
    if not wallet:
      messagebox.showwarning("Warning", "Please enter a wallet name to delete")
      return

    # Check if node is running
    if not self.check_node_running():
      return

    # Confirm deletion
    if not messagebox.askyesno(
      "Confirm Delete",
      f"Are you sure you want to delete wallet '{wallet}'?\\n\\n"
      "This action CANNOT be undone!\\n"
      "Make sure you have saved your seed phrase!",
    ):
      return

    try:
      cmd, fbdctl_path = self.get_fbdctl_command(
        "--wallet", wallet, "deletewallet"
      )
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
      )

      if result.returncode == 0:
        self.log(f"Wallet deleted: {wallet}")
        messagebox.showinfo(
          "Success", f"Wallet '{wallet}' deleted successfully"
        )
        self.wallet_name_var.set("")
        self.list_wallets(show_feedback=False)
      else:
        error_msg = result.stderr
        self.log(f"Error deleting wallet: {error_msg}")
        messagebox.showerror("Error", f"Failed to delete wallet:\\n{error_msg}")
    except Exception as e:
      self.log(f"Exception deleting wallet: {e}")
      messagebox.showerror("Error", f"Failed to delete wallet: {e}")

  def show_seed_dialog(self, wallet_name, seed_phrase):
    """Show seed phrase with copy-to-clipboard functionality"""
    dialog = self._create_toplevel()
    dialog.title("Wallet Created - SAVE YOUR SEED!")
    dialog.geometry("600x300")
    dialog.transient(self.root)
    dialog.grab_set()

    # Warning label
    ttk.Label(
      dialog,
      text="[!] SAVE THIS SEED PHRASE SECURELY [!]",
      font=("Arial", 14, "bold"),
      foreground="red",
    ).pack(pady=10)

    ttk.Label(
      dialog, text=f"Wallet: {wallet_name}", font=("Arial", 12, "bold")
    ).pack(pady=5)

    # Seed phrase text box
    seed_frame = ttk.Frame(dialog)
    seed_frame.pack(pady=10, padx=20, fill="both", expand=True)

    seed_text = tk.Text(seed_frame, height=4, wrap=tk.WORD, font=("Courier", 11))
    seed_text.pack(fill="both", expand=True)
    seed_text.insert("1.0", seed_phrase)
    seed_text.configure(state="disabled")

    # Copy button
    def copy_to_clipboard():
      """Copy to clipboard."""
      self.root.clipboard_clear()
      self.root.clipboard_append(seed_phrase)
      self.root.update()
      copy_btn.configure(text="[OK] Copied!")
      self.root.after(2000, lambda: copy_btn.configure(text="Copy to Clipboard"))

    copy_btn = self._create_button(
      dialog, text="Copy to Clipboard", command=copy_to_clipboard
    )
    copy_btn.pack(pady=10)

    # Warning message
    ttk.Label(
      dialog,
      text="Write this down on paper and store it safely!",
      font=("Arial", 10),
      foreground="red",
    ).pack(pady=5)
    ttk.Label(
      dialog,
      text="Anyone with this seed can access your funds!",
      font=("Arial", 10),
      foreground="red",
    ).pack(pady=5)

    self._create_button(dialog, text="I Have Saved My Seed", command=dialog.destroy).pack(
      pady=10
    )

  def get_wallet_info(self):
    """Get wallet information"""
    wallet = self.wallet_name_var.get()
    if not wallet:
      messagebox.showwarning("Warning", "Please enter a wallet name")
      return

    if not self.check_node_running():
      return

    # Use fbdctl for wallet commands
    try:
      # Get balance (includes spendable, confirmed, immature)
      cmd, fbdctl_path = self.get_fbdctl_command("--wallet", wallet, "getbalance")
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        # Extract the "result" field from the response
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )

        # Convert from satoshis to FBC (divide by 1,000,000)
        spendable = data.get("spendable", 0) / 1000000
        confirmed = data.get("confirmed", 0) / 1000000
        immature = data.get("immature", 0) / 1000000

        # Update balance display - show spendable (confirmed = spendable + immature)
        self.balance_label.configure(
          text=f"Balance: {spendable:.6f} FBC (Confirmed: {confirmed:.6f}, Immature: {immature:.6f})"
        )

        # Also update auction tab balance for consistency
        self.auction_balance_label.configure(
          text=f"Confirmed: {confirmed:.6f} FBC (Available for bids: {spendable:.6f} FBC, Immature: {immature:.6f} FBC)"
        )

        # Calculate mined blocks from immature balance
        # Block reward is 500 FBC, immature represents last 100 blocks
        block_reward = 500.0 # FBC per block
        immature_blocks = int(immature / block_reward) if immature > 0 else 0

        # Try to get total blocks mined from blockchain
        total_blocks_mined = self.get_total_blocks_mined(wallet)

        if total_blocks_mined is not None:
          self.total_blocks_label.configure(
            text=f"Total Blocks (Chain): {total_blocks_mined} total ({immature_blocks} immature)"
          )
          self.log(
            f"Total blocks mined: {total_blocks_mined}, Immature: {immature_blocks}"
          )
        elif immature_blocks > 0:
          self.total_blocks_label.configure(
            text=f"Total Blocks (Chain): ~{immature_blocks} immature"
          )
          self.log(
            f"Estimated immature blocks: {immature_blocks} (immature balance: {immature:.6f} FBC)"
          )
        else:
          self.total_blocks_label.configure(text="Total Blocks (Chain): 0")

        # Get wallet info for address
        cmd_info, _ = self.get_fbdctl_command(
          "--wallet", wallet, "getwalletinfo"
        )
        result_info = subprocess.run(
          cmd_info,
          capture_output=True,
          text=True,
          cwd=Path(self.fbd_path_var.get()).parent,
        )

        if result_info.returncode == 0:
          response_info = json.loads(result_info.stdout)
          data_info = (
            response_info.get("result", {})
            if isinstance(response_info, dict)
            else response_info
          )
          address = data_info.get("address", "N/A")
          self.address_label.configure(text=f"Address: {address}")

        self.log(f"Wallet balance loaded for: {wallet}")
        self.log(f"Spendable: {spendable:.6f} FBC")
        self.log(f"Confirmed: {confirmed:.6f} FBC")
        self.log(f"Immature: {immature:.6f} FBC")
      else:
        error_msg = result.stderr
        stdout_msg = result.stdout
        full_error = f"stderr: {error_msg} | stdout: {stdout_msg}"
        self.log(f"DEBUG - Full error output: {full_error}")

        # Check if wallet doesn't exist (check multiple possible error formats)
        # Check both stderr AND stdout for error messages
        combined_output = (error_msg + " " + stdout_msg).lower()
        if any(
          phrase in combined_output
          for phrase in [
            "wallet not found",
            "does not exist",
            "unknown wallet",
            "wallet does not",
            "no wallet",
            'wallet "',
            "no such wallet",
          ]
        ):
          self.balance_label.configure(text="Balance: Wallet not found")
          self.address_label.configure(text="Address: -")
          self.show_wallet_not_found_dialog(wallet)
          return

        # Check if it's an index-address issue
        if not self.check_index_address_error(error_msg):
          messagebox.showerror(
            "Wallet Error",
            f"Could not get wallet info.\n\nError: {error_msg or stdout_msg}",
          )

    except Exception as e:
      error_msg = str(e)
      self.log(f"Error getting wallet info: {error_msg}")
      if not self.check_index_address_error(error_msg):
        messagebox.showerror("Error", f"Failed to get wallet info: {error_msg}")

  def show_wallet_not_found_dialog(self, wallet_name):
    """Show custom dialog with actionable options when wallet not found"""
    dialog = self._create_toplevel()
    dialog.title("Wallet Not Found")
    dialog.geometry("450x200")
    dialog.transient(self.root)
    dialog.grab_set()

    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")

    # Message
    msg_frame = ttk.Frame(dialog)
    msg_frame.pack(pady=20, padx=20, fill="both", expand=True)

    ttk.Label(
      msg_frame,
      text=f"Wallet '{wallet_name}' does not exist.",
      font=("Arial", 11, "bold"),
    ).pack(pady=(0, 10))

    ttk.Label(
      msg_frame,
      text="Would you like to:",
      font=("Arial", 10),
    ).pack(pady=(0, 15))

    # Button frame
    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(0, 20))

    def on_list_wallets():
      """On list wallets."""
      dialog.destroy()
      self.list_wallets()

    def on_create_wallet():
      """On create wallet."""
      dialog.destroy()
      self.create_wallet()

    def on_cancel():
      """On cancel."""
      dialog.destroy()

    self._create_button(
      btn_frame,
      text="->>> Refresh Wallet Dropdown",
      command=on_list_wallets,
      width=25,
    ).grid(row=0, column=0, padx=5, pady=5)

    self._create_button(
      btn_frame,
      text="* Create New Wallet",
      command=on_create_wallet,
      width=25,
    ).grid(row=0, column=1, padx=5, pady=5)

    self._create_button(
      btn_frame,
      text="Cancel",
      command=on_cancel,
      width=15,
    ).grid(row=1, column=0, columnspan=2, pady=(10, 0))

  def get_total_blocks_mined(self, wallet):
    """Get total number of blocks mined to this wallet address"""
    try:
      # First get the wallet address
      cmd_info, _ = self.get_fbdctl_command("--wallet", wallet, "getwalletinfo")
      result_info = subprocess.run(
        cmd_info,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
      )

      if result_info.returncode != 0:
        return None

      response_info = json.loads(result_info.stdout)
      data_info = (
        response_info.get("result", {})
        if isinstance(response_info, dict)
        else response_info
      )
      address = data_info.get("address")

      if not address:
        return None

      # Try to get address info (requires --index-address)
      addr_info = self.rpc_call("getaddressinfo", [address])

      if addr_info and "blocks" in addr_info:
        # If the RPC returns blocks mined count
        return addr_info.get("blocks", 0)

      # Alternative: query address balance history
      balance_info = self.rpc_call("getaddressbalance", [address])
      if balance_info:
        # Calculate from total received (if available)
        total_received = (
          balance_info.get("received", 0) / 1000000
        ) # Convert to FBC
        if total_received > 0:
          block_reward = 500.0
          return int(total_received / block_reward)

      return None

    except Exception as e:
      self.log(f"Could not determine total blocks mined: {e}")
      return None

  def refresh_auction_balance(self):
    """Refresh wallet balance for auction page"""
    wallet = self.wallet_name_var.get()
    if not wallet:
      messagebox.showwarning(
        "No Wallet Selected",
        "Please select an active wallet in the Wallet tab first.\n\n"
        "Go to Wallet tab -> Select or create a wallet -> Set it as default",
      )
      return

    if not self.check_node_running():
      return

    try:
      cmd, _ = self.get_fbdctl_command("--wallet", wallet, "getbalance")
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )

        confirmed = data.get("confirmed", 0) / 1000000
        spendable = data.get("spendable", 0) / 1000000
        immature = data.get("immature", 0) / 1000000

        self.auction_balance_label.configure(
          text=f"Confirmed: {confirmed:.6f} FBC (Available for bids: {spendable:.6f} FBC, Immature: {immature:.6f} FBC)"
        )

        # Also update wallet tab display
        self.balance_label.configure(
          text=f"Balance: {spendable:.6f} FBC (Confirmed: {confirmed:.6f}, Immature: {immature:.6f})"
        )

        self.log(f"Auction balance refreshed for wallet: {wallet}")
      else:
        error_msg = result.stderr
        stdout_msg = result.stdout
        full_error = f"stderr: {error_msg} | stdout: {stdout_msg}"
        self.log(f"DEBUG - Full error output: {full_error}")

        # Check if wallet doesn't exist (check multiple possible error formats)
        # Check both stderr AND stdout for error messages
        combined_output = (error_msg + " " + stdout_msg).lower()
        if any(
          phrase in combined_output
          for phrase in [
            "wallet not found",
            "does not exist",
            "unknown wallet",
            "wallet does not",
            "no wallet",
            'wallet "',
            "no such wallet",
          ]
        ):
          self.auction_balance_label.configure(text="Wallet not found")
          self.log(f"Wallet not found: {wallet}")
          self.show_wallet_not_found_dialog(wallet)
          return
        # Generic error
        self.log(f"Error refreshing auction balance: {full_error}")
        messagebox.showerror(
          "Balance Error",
          f"Could not get wallet balance.\n\nError: {error_msg or stdout_msg}",
        )

    except Exception as e:
      error_str = str(e)
      if (
        "wallet not found" in error_str.lower()
        or "does not exist" in error_str.lower()
        or "wallet does not" in error_str.lower()
        or "no wallet" in error_str.lower()
      ):
        self.auction_balance_label.configure(text="Wallet not found")
        self.log(f"Wallet not found: {wallet}")
        self.show_wallet_not_found_dialog(wallet)
      else:
        self.log(f"Error refreshing auction balance: {e}")
        messagebox.showerror(
          "Balance Error", f"Could not get wallet balance.\n\nError: {e}"
        )

  def clear_all_notifications(self):
    """Clear all notifications with confirmation (Stage 4)"""
    if messagebox.askyesno(
      "Clear Notifications",
      "Are you sure you want to clear all notifications? This cannot be undone.",
    ):
      self.notification_manager.clear_notifications()
      self.log("All notifications cleared")

  # Stage 6: Job Manager UI Methods
  def show_jobs_context_menu(self, event):
    """Show the jobs context menu for the row under the pointer."""
    row_id = self.jobs_tree.identify_row(event.y)
    if not row_id:
      return

    self.jobs_tree.selection_set(row_id)
    self.jobs_tree.focus(row_id)

    try:
      self.jobs_context_menu.tk_popup(event.x_root, event.y_root)
    finally:
      self.jobs_context_menu.grab_release()

  def _get_selected_job_context(self, show_warning=True):
    """Return the jobs payload and selected job for the jobs tree selection."""
    selection = self.jobs_tree.selection()
    if not selection:
      if show_warning:
        messagebox.showwarning("No Selection", "Please select a job first.")
      return (None, None)

    selected_job_id = selection[0]
    jobs_data = self.load_auction_jobs()
    jobs = jobs_data.get("jobs", [])
    job = next((j for j in jobs if j.get("id") == selected_job_id), None)

    if job is None:
      item = self.jobs_tree.item(selected_job_id)
      job_name = item.get("values", [None])[0]
      job = next((j for j in jobs if j.get("name") == job_name), None)

    if job is None and show_warning:
      messagebox.showerror("Error", "Job not found in data file.")

    return (jobs_data, job)

  def _populate_block_calc_from_job(self, name):
    """Populate the main block calc tab for the selected job name."""
    self.calc_input_method.set("name")
    self.toggle_calc_input_method()
    self.clear_calc_results()
    self.calc_name_var.set(name)
    self.lookup_name_for_calc()
    return [
      self.calc_results_tree.item(item, "values")
      for item in self.calc_results_tree.get_children()
    ]

  def _open_block_calc_tab(self):
    """Switch to the block calc tab."""
    self._notebook_select(self.block_calc_tab)

  def _show_block_calc_popup(self, name, rows):
    """Show block calculator results for a job in a popup window."""
    popup = self._create_toplevel()
    popup.title(f"Block Calc - {name}")
    popup.geometry("860x360")
    popup.transient(self.root)
    popup.bind("<Escape>", lambda _event: popup.destroy())

    container = ttk.Frame(popup, padding=10)
    container.pack(fill="both", expand=True)

    ttk.Label(
      container,
      text=f"Auction timing for '{name}'",
      font=("Arial", 11, "bold"),
    ).pack(anchor="w")
    ttk.Label(
      container,
      text=f"{self.calc_current_height_label.cget('text')} | Esc closes this window",
      foreground="#666666",
      font=("Arial", 9),
    ).pack(anchor="w", pady=(2, 8))

    tree_frame = ttk.Frame(container)
    tree_frame.pack(fill="both", expand=True)

    columns = ("Phase", "Block Height", "Blocks Remaining", "Date/Time", "Status")
    popup_tree = ttk.Treeview(
      tree_frame, columns=columns, show="headings", height=8
    )
    popup_tree.heading("Phase", text="Auction Phase")
    popup_tree.heading("Block Height", text="Block Height")
    popup_tree.heading("Blocks Remaining", text="Blocks Until")
    popup_tree.heading("Date/Time", text="Approximate Date/Time")
    popup_tree.heading("Status", text="Status")
    popup_tree.column("Phase", width=180)
    popup_tree.column("Block Height", width=110)
    popup_tree.column("Blocks Remaining", width=110)
    popup_tree.column("Date/Time", width=210)
    popup_tree.column("Status", width=110)

    popup_scrollbar = ttk.Scrollbar(
      tree_frame, orient="vertical", command=popup_tree.yview
    )
    popup_tree.configure(yscrollcommand=popup_scrollbar.set)

    popup_tree.pack(side="left", fill="both", expand=True)
    popup_scrollbar.pack(side="right", fill="y")

    for row in rows:
      popup_tree.insert("", "end", values=row)

    button_frame = ttk.Frame(container)
    button_frame.pack(fill="x", pady=(8, 0))

    self._create_button(
      button_frame,
      text="Open Block Calc Tab",
      command=lambda: (self._open_block_calc_tab(), popup.destroy()),
    ).pack(side="left")
    self._create_button(button_frame, text="Close", command=popup.destroy).pack(side="right")

    popup.update_idletasks()
    x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (popup.winfo_width() // 2)
    y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (popup.winfo_height() // 2)
    popup.geometry(f"+{x}+{y}")
    popup.focus_force()

  def show_selected_job_block_calc(self):
    """Load block calc data for the selected job and show it in a popup."""
    _jobs_data, job = self._get_selected_job_context()
    if not job:
      return

    name = job.get("name", "").strip()
    if not name:
      messagebox.showerror("Error", "Selected job does not have a valid name.")
      return

    rows = self._populate_block_calc_from_job(name)
    if not rows:
      self.log(f"Block calculator: No popup shown for '{name}' because no rows were available")
      return

    self._show_block_calc_popup(name, rows)

  def refresh_jobs_list(self):
    """Refresh the jobs list in the TreeView"""
    try:
      # Clear existing items
      for item in self.jobs_tree.get_children():
        self.jobs_tree.delete(item)

      # Load jobs from file
      jobs_data = self.load_auction_jobs()
      jobs = jobs_data.get("jobs", []) # Extract jobs list from dict
      jobs_changed = False

      # Backfill missing fields for older/imported jobs.
      for job in jobs:
        if self._ensure_job_schema(job):
          jobs_changed = True

      # Sort by created time (most recent first)
      jobs.sort(
        key=lambda j: j.get("created", j.get("created_at", "")),
        reverse=True,
      )

      # Add jobs to tree
      for job in jobs:
        status = job.get("status", "unknown")

        # Skip very old completed jobs (older than 24 hours)
        if status in ["registered", "lost", "failed"]:
          try:
            created = datetime.fromisoformat(
              job.get("created", job.get("created_at", ""))
            )
            age_hours = (datetime.now() - created).total_seconds() / 3600
            if age_hours > 24:
              continue
          except:
            pass

        # Format values
        name = job.get("name", "N/A")
        wallet = job.get("wallet", "N/A")[:15] # Truncate long wallet names

        snapshot = self._build_job_snapshot(job)
        if self._sync_job_status_from_chain(job, snapshot):
          jobs_changed = True
          status = job.get("status", status)
          snapshot = self._build_job_snapshot(job)

        historical_bid = self._get_original_bid_amount(job, snapshot)
        bid_amount = f"{self._format_fbc(historical_bid)} FBC"
        lockup_amount = f"{self._format_fbc(job.get('lockup_amount', 0))} FBC"
        winning_cost = self._get_winning_cost_text(job, snapshot)

        # Get status emoji and text
        status_text = self._get_job_status_text(status)

        # Get progress text
        progress_text = self._get_job_progress_text(job, snapshot)

        # Get relative time
        created_text = self._get_relative_time(
          job.get("created", job.get("created_at", ""))
        )

        # Insert into tree
        self.jobs_tree.insert(
          "",
          "end",
          iid=job["id"],
          values=(
            name,
            status_text,
            wallet,
            bid_amount,
            lockup_amount,
            winning_cost,
            progress_text,
            created_text,
          ),
          tags=(status,),
        )

      if jobs_changed:
        self.save_auction_jobs(jobs_data)

      # Update tag colors
      self.jobs_tree.tag_configure("registered", foreground="green")
      self.jobs_tree.tag_configure("lost", foreground="orange")
      self.jobs_tree.tag_configure("failed", foreground="red")

      self.log(f"Jobs list refreshed ({len(jobs)} jobs)")

    except Exception as e:
      self.log(f"Error refreshing jobs list: {e}")

  def _get_job_status_text(self, status):
    """Get display text with emoji for job status"""
    status_map = {
      "pending_open": "[ ] Waiting to open",
      "opened": "[*] Opened (BIDDING)",
      "bid_placed": "Bid placed",
      "revealed": "Revealed",
      "registered": "[OK] SUCCESS - Registered!",
      "lost": "[X] Lost auction",
      "failed": "[!] Failed",
      "cancelled": "> Cancelled",
    }
    return status_map.get(status, f"[!] {status}")

  def _get_job_progress_text(self, job, snapshot=None):
    """Get progress description text"""
    status = job.get("status", "unknown")

    if status == "pending_open":
      return "Waiting for OPEN phase..."
    elif status == "opened":
      return "Waiting for BIDDING phase..."
    elif status == "bid_placed":
      return "Awaiting reveal"
    elif status == "revealed":
      if snapshot is None:
        snapshot = self._build_job_snapshot(job)
      outcome = snapshot.get("outcome", "unknown")
      if outcome == "won":
        return "Await REGISTER"
      elif outcome == "lost":
        return "Await REDEEM"
      return "Await REGISTER/REDEEM"
    elif status == "registered":
      txid = job.get("txid", "")
      return (
        f"Name registered! TX: {txid[:12]}..." if txid else "Name registered!"
      )
    elif status == "lost":
      return "Bid was not highest"
    elif status == "failed":
      error = job.get("error", "Unknown error")
      return error[:50] + ("..." if len(error) > 50 else "")
    elif status == "cancelled":
      return "Cancelled by user"
    else:
      return status

  def _to_float(self, value, default=0.0):
    """Safely convert values to float."""
    try:
      return float(value)
    except (TypeError, ValueError):
      return default

  def _format_fbc(self, value):
    """Format FBC amount without trailing zeros."""
    amount = self._to_float(value, 0.0)
    text = f"{amount:.6f}".rstrip("0").rstrip(".")
    return text if text else "0"

  def _ensure_job_schema(self, job):
    """Backfill missing fields for imported/legacy jobs."""
    changed = False

    if "id" not in job or not job.get("id"):
      job["id"] = str(uuid.uuid4())
      changed = True

    if "txids" not in job or not isinstance(job.get("txids"), dict):
      job["txids"] = {"open": None, "bid": None, "reveal": [], "register": None}
      changed = True
    else:
      defaults = {"open": None, "bid": None, "reveal": [], "register": None}
      for key, default in defaults.items():
        if key not in job["txids"]:
          job["txids"][key] = default
          changed = True
      if not isinstance(job["txids"].get("reveal"), list):
        reveal_val = job["txids"].get("reveal")
        job["txids"]["reveal"] = [reveal_val] if reveal_val else []
        changed = True

    if "block_heights" not in job or not isinstance(job.get("block_heights"), dict):
      job["block_heights"] = {
        "opened_at": None,
        "bid_placed_at": None,
        "revealed_at": None,
        "registered_at": None,
      }
      changed = True
    else:
      for key in ["opened_at", "bid_placed_at", "revealed_at", "registered_at"]:
        if key not in job["block_heights"]:
          job["block_heights"][key] = None
          changed = True

    if "error_log" not in job or not isinstance(job.get("error_log"), list):
      job["error_log"] = []
      changed = True

    if "retry_count" not in job:
      job["retry_count"] = 0
      changed = True

    if "original_bid_amount" not in job:
      job["original_bid_amount"] = str(job.get("bid_amount", 0))
      changed = True

    if "created" not in job:
      created_at = job.get("created_at")
      if isinstance(created_at, (int, float)):
        job["created"] = datetime.fromtimestamp(created_at).isoformat()
      elif isinstance(created_at, str):
        job["created"] = created_at
      else:
        job["created"] = datetime.now().isoformat()
      changed = True

    return changed

  def _get_auction_bids_silent(self, name):
    """Get all bids for a name. Returns [] when unavailable."""
    try:
      cmd, _ = self.get_fbdctl_command("getauctionbids", name)
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=10,
      )
      if result.returncode != 0:
        return []

      response = json.loads(result.stdout)
      data = response.get("result", {}) if isinstance(response, dict) else response
      bids = data.get("bids", []) if isinstance(data, dict) else []
      return bids if isinstance(bids, list) else []
    except Exception:
      return []

  def _build_job_snapshot(self, job):
    """Build live auction context used by progress and winning cost."""
    snapshot = {
      "state": "UNKNOWN",
      "outcome": "unknown", # won | lost | unknown
      "original_bid": self._to_float(
        job.get("original_bid_amount", job.get("bid_amount", 0))
      ),
      "has_higher_unrevealed_lockup": False,
      "has_revealed_rival_above": False,
      "next_highest_rival": 0.0,
      "can_compute_cost": False,
    }

    name = job.get("name")
    wallet = job.get("wallet")
    if not name or not wallet:
      return snapshot

    name_info = self.get_name_info_silent(name) or {}
    snapshot["state"] = name_info.get("state", "UNKNOWN")
    can_register = bool(name_info.get("canRegister", False))

    our_bids = self.get_wallet_bids_silent(wallet, name) or []
    revealed_ours = [b for b in our_bids if b.get("revealed", False)]
    if snapshot["original_bid"] <= 0 and revealed_ours:
      snapshot["original_bid"] = max(
        [self._to_float(b.get("value", 0)) for b in revealed_ours],
        default=0.0,
      )

    all_bids = self._get_auction_bids_silent(name)

    our_signatures = set()
    for b in our_bids:
      our_signatures.add(
        (
          round(self._to_float(b.get("value", 0)), 8),
          round(self._to_float(b.get("lockup", 0)), 8),
        )
      )

    rival_bids = []
    for b in all_bids:
      sig = (
        round(self._to_float(b.get("value", 0)), 8),
        round(self._to_float(b.get("lockup", 0)), 8),
      )
      if sig not in our_signatures:
        rival_bids.append(b)

    original_bid = snapshot["original_bid"]
    revealed_rival_values = []
    for b in rival_bids:
      lockup = self._to_float(b.get("lockup", 0))
      value = self._to_float(b.get("value", 0))
      revealed = bool(b.get("revealed", False))

      if (not revealed) and lockup > original_bid and snapshot["state"] == "REVEAL":
        snapshot["has_higher_unrevealed_lockup"] = True

      if revealed and value > original_bid:
        snapshot["has_revealed_rival_above"] = True

      if revealed:
        revealed_rival_values.append(value)

    revealed_not_above = [v for v in revealed_rival_values if v <= original_bid]
    snapshot["next_highest_rival"] = max(revealed_not_above, default=0.0)
    snapshot["can_compute_cost"] = (
      not snapshot["has_higher_unrevealed_lockup"]
      and not snapshot["has_revealed_rival_above"]
    )

    if can_register:
      snapshot["outcome"] = "won"
    elif snapshot["has_revealed_rival_above"]:
      snapshot["outcome"] = "lost"
    elif snapshot["state"] == "CLOSED" and snapshot["can_compute_cost"]:
      snapshot["outcome"] = "won"
    else:
      snapshot["outcome"] = "unknown"

    return snapshot

  def _sync_job_status_from_chain(self, job, snapshot):
    """Promote stale bid_placed jobs to revealed if chain data confirms reveal."""
    if job.get("status") != "bid_placed":
      return False

    if snapshot.get("state") not in ["REVEAL", "CLOSED"]:
      return False

    wallet = job.get("wallet")
    name = job.get("name")
    bids = self.get_wallet_bids_silent(wallet, name) if wallet and name else []
    if not any(b.get("revealed", False) for b in bids):
      return False

    job["status"] = "revealed"
    job["updated_at"] = datetime.now().isoformat()
    if "block_heights" in job and not job["block_heights"].get("revealed_at"):
      job["block_heights"]["revealed_at"] = self._get_current_height_silent()
    return True

  def _get_original_bid_amount(self, job, snapshot=None):
    """Return persisted original bid amount for historical display."""
    original_bid = self._to_float(
      job.get("original_bid_amount", job.get("bid_amount", 0))
    )
    if original_bid > 0:
      return original_bid

    if snapshot is None:
      snapshot = self._build_job_snapshot(job)

    candidate = snapshot.get("original_bid", 0.0)
    if candidate > 0:
      job["original_bid_amount"] = str(candidate)
      return candidate
    return 0.0

  def _get_winning_cost_text(self, job, snapshot=None):
    """Compute winning cost according to reveal/competition conditions."""
    if job.get("status") != "revealed":
      return "n/a"

    if snapshot is None:
      snapshot = self._build_job_snapshot(job)

    original_bid = self._get_original_bid_amount(job, snapshot)
    if original_bid <= 0:
      return "n/a"

    if snapshot.get("has_higher_unrevealed_lockup"):
      return "n/a"
    if snapshot.get("has_revealed_rival_above"):
      return "n/a"
    if not snapshot.get("can_compute_cost"):
      return "n/a"

    next_highest = snapshot.get("next_highest_rival", 0.0)
    if next_highest <= 0:
      return "0"

    cost = original_bid - next_highest
    if cost <= 0:
      return "n/a"
    return self._format_fbc(cost)

  def _get_relative_time(self, iso_timestamp):
    """Convert ISO timestamp to relative time (e.g., '2h ago')"""
    try:
      created = datetime.fromisoformat(iso_timestamp)
      now = datetime.now()
      diff = now - created

      seconds = diff.total_seconds()
      if seconds < 60:
        return f"{int(seconds)}s ago"
      elif seconds < 3600:
        return f"{int(seconds/60)}m ago"
      elif seconds < 86400:
        return f"{int(seconds/3600)}h ago"
      else:
        return f"{int(seconds/86400)}d ago"
    except:
      return "N/A"

  def view_job_details(self):
    """View full details of selected job"""
    try:
      _jobs_data, job = self._get_selected_job_context()
      if not job:
        return

      job_name = job.get("name", "Unknown")

      # Create details popup
      details_window = self._create_toplevel()
      details_window.title(f"Job Details - {job_name}")
      details_window.geometry("600x400")

      # JSON display
      details_text = self._create_log_widget(
        details_window, wrap=tk.WORD, font=("Courier", 10)
      )
      details_text.pack(fill="both", expand=True, padx=10, pady=10)

      # Format JSON nicely
      details_text.insert("1.0", json.dumps(job, indent=2, default=str))
      details_text.configure(state="disabled")

      # Close button
      self._create_button(
        details_window, text="Close", command=details_window.destroy
      ).pack(pady=5)

    except Exception as e:
      messagebox.showerror("Error", f"Failed to view job details: {e}")
      self.log(f"Error viewing job details: {e}")

  def cancel_selected_job(self):
    """Cancel the selected automation job"""
    try:
      jobs_data, job = self._get_selected_job_context()
      if not job:
        return

      job_name = job.get("name", "Unknown")

      # Confirm cancellation
      if not messagebox.askyesno(
        "Confirm Cancel",
        f"Cancel automation for '{job_name}'?\n\nThis will stop all automated actions for this auction.",
      ):
        return

      # Update job status to cancelled
      if job.get("status") in ["registered", "lost", "failed", "cancelled"]:
        messagebox.showinfo(
          "Already Complete",
          f"Job '{job_name}' is already complete (status: {job.get('status')}).",
        )
        return

      job["status"] = "cancelled"
      job["cancelled_at"] = datetime.now().isoformat()
      self.save_auction_jobs(jobs_data)
      self.log(f"Job cancelled: {job_name}")
      messagebox.showinfo("Success", f"Job '{job_name}' has been cancelled.")
      self.refresh_jobs_list()

    except Exception as e:
      messagebox.showerror("Error", f"Failed to cancel job: {e}")
      self.log(f"Error cancelling job: {e}")

  def clear_completed_jobs(self):
    """Remove completed jobs (registered/lost/failed) from the list"""
    try:
      jobs_data = self.load_auction_jobs()
      jobs = jobs_data.get("jobs", [])
      initial_count = len(jobs)

      # Keep only non-terminal jobs
      active_jobs = [
        j
        for j in jobs
        if j.get("status") not in ["registered", "lost", "failed", "cancelled"]
      ]

      removed_count = initial_count - len(active_jobs)

      if removed_count == 0:
        messagebox.showinfo(
          "No Completed Jobs", "There are no completed jobs to clear."
        )
        return

      if messagebox.askyesno(
        "Confirm Clear",
        f"Remove {removed_count} completed job(s)?\n\nThis cannot be undone.",
      ):
        jobs_data["jobs"] = active_jobs
        self.save_auction_jobs(jobs_data)
        self.log(f"Cleared {removed_count} completed job(s)")
        messagebox.showinfo(
          "Success", f"Removed {removed_count} completed job(s)."
        )
        self.refresh_jobs_list()

    except Exception as e:
      messagebox.showerror("Error", f"Failed to clear completed jobs: {e}")
      self.log(f"Error clearing completed jobs: {e}")

  def start_jobs_auto_refresh(self):
    """Start auto-refresh timer for jobs list (every 60 seconds)"""
    self.refresh_jobs_list()
    self.jobs_refresh_timer = self.root.after(60000, self.start_jobs_auto_refresh)

  def stop_jobs_auto_refresh(self):
    """Stop auto-refresh timer"""
    if self.jobs_refresh_timer:
      self.root.after_cancel(self.jobs_refresh_timer)
      self.jobs_refresh_timer = None

  def send_payment(self):
    """Send a payment"""
    wallet = self.wallet_name_var.get()
    address = self.send_address_var.get()
    amount = self.send_amount_var.get()

    if not all([wallet, address, amount]):
      messagebox.showwarning("Warning", "Please fill in all fields")
      return

    if not self.check_node_running():
      return

    if messagebox.askyesno("Confirm", f"Send {amount} FBC to {address}?"):
      try:
        cmd, fbdctl_path = self.get_fbdctl_command(
          "--wallet", wallet, "sendnone", address, amount
        )
        result = subprocess.run(
          cmd,
          capture_output=True,
          text=True,
          cwd=Path(self.fbd_path_var.get()).parent,
        )

        if result.returncode == 0:
          response = json.loads(result.stdout)
          data = (
            response.get("result", {})
            if isinstance(response, dict)
            else response
          )
          messagebox.showinfo(
            "Success", f"Transaction sent!\nTXID: {data.get('txid', 'N/A')}"
          )
          self.log(f"Payment sent: {amount} FBC to {address}")

          # Clear fields after successful transaction
          self.send_address_var.set("")
          self.send_amount_var.set("")
          self.log("[OK] Payment fields cleared to prevent accidental repeat")
        else:
          messagebox.showerror("Error", result.stderr)

      except Exception as e:
        messagebox.showerror("Error", f"Failed to send payment: {e}")

  def save_current_address(self):
    """Save the current address to the saved addresses list"""
    address = self.send_address_var.get().strip()
    if not address:
      messagebox.showwarning("No Address", "Please enter an address to save")
      return

    saved_addresses = self.config.get("saved_addresses", [])
    if address in saved_addresses:
      messagebox.showinfo(
        "Already Saved", "This address is already in your saved list"
      )
      return

    saved_addresses.append(address)
    self.config["saved_addresses"] = saved_addresses
    self.save_config()

    # Update the combobox values
    self.send_address_combo["values"] = saved_addresses

    messagebox.showinfo(
      "Saved", f"Address saved!\nTotal saved: {len(saved_addresses)}"
    )
    self.log(f"[*] Saved address: {address}")

  def load_transactions(self):
    """Load transaction history"""
    wallet = self.wallet_name_var.get()
    if not wallet:
      messagebox.showwarning("Warning", "Please enter a wallet name")
      return

    if not self.check_node_running():
      return

    try:
      cmd, fbdctl_path = self.get_fbdctl_command(
        "--wallet", wallet, "listtransactions", "20"
      )
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        txs = (
          response.get("result", [])
          if isinstance(response, dict)
          else response
        )
        self.tx_text.delete(1.0, tk.END)

        for tx in txs:
          self.tx_text.insert(tk.END, f"TXID: {tx.get('txid', 'N/A')}\n")
          self.tx_text.insert(tk.END, f"Type: {tx.get('type', 'N/A')}\n")
          self.tx_text.insert(
            tk.END, f"Net: {tx.get('net', 0) / 1000000:.6f} FBC\n"
          )
          self.tx_text.insert(
            tk.END, f"Confirmations: {tx.get('confirmations', 0)}\n"
          )

          # Add timestamp if available
          timestamp = tx.get("time", None)
          if timestamp:
            from datetime import datetime

            dt = datetime.fromtimestamp(timestamp)
            self.tx_text.insert(
              tk.END, f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

          self.tx_text.insert(tk.END, "-" * 50 + "\n")
      else:
        self.tx_text.delete(1.0, tk.END)
        self.tx_text.insert(tk.END, f"Error: {result.stderr}")

    except Exception as e:
      self.log(f"Error loading transactions: {e}")

  # Auction methods
  def get_name_info(self):
    """Get information about a name"""
    name = self.name_var.get()
    if not name:
      messagebox.showwarning("Warning", "Please enter a name")
      return

    if not self.check_node_running():
      return

    try:
      cmd, fbdctl_path = self.get_fbdctl_command("getnameinfo", name)
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )
        self.auction_info_text.delete(1.0, tk.END)
        self.auction_info_text.insert(tk.END, json.dumps(data, indent=2))
        # Ensure widget is visible by scrolling to top
        self.auction_info_text.see(1.0)
        self.log(
          f"[OK] Name info for '{name}' displayed in 'Name/Auction Details' text area"
        )

        # Calculate converted minimumBid
        min_bid_raw = data.get("minimumBid", 0)
        min_bid_fbc = (
          min_bid_raw / 1000000
          if isinstance(min_bid_raw, (int, float))
          else 0
        )
        if abs(min_bid_fbc - round(min_bid_fbc)) < 1e-9:
          min_bid_display = f"{int(round(min_bid_fbc)):,}"
        else:
          min_bid_display = f"{min_bid_fbc:,.6f}".rstrip("0").rstrip(".")
        min_bid_raw_display = (
          f"{int(min_bid_raw):,}"
          if isinstance(min_bid_raw, (int, float))
          else str(min_bid_raw)
        )

        # Also show in popup for better visibility
        messagebox.showinfo(
          f"Name Info: {name}",
          f"Details shown in 'Name/Auction Details' section below.\n\n"
          f"Minimum bid:\n"
          f"{min_bid_display} FBC\n"
          f"({min_bid_raw_display} Raw)\n"
          f"State: {data.get('state', 'N/A')}",
        )
        rollout_height = data.get("rolloutHeight")
        if isinstance(rollout_height, (int, float)) and int(rollout_height) > 0:
          self.offer_rollout_reminder(name, int(rollout_height))
        self.offer_add_to_watchlist(name)
      else:
        self.auction_info_text.delete(1.0, tk.END)
        self.auction_info_text.insert(tk.END, f"Error: {result.stderr}")
        self.log(f"[X] Error getting name info for '{name}'")

    except Exception as e:
      messagebox.showerror("Error", f"Failed to get name info: {e}")

  def send_open(self):
    """Open an auction for a name"""
    wallet = self.wallet_name_var.get()
    name = self.name_var.get()

    if not all([wallet, name]):
      messagebox.showwarning("Warning", "Please fill in wallet and name")
      return

    if not self.check_node_running():
      return

    if messagebox.askyesno("Confirm", f"Open auction for '{name}'?"):
      try:
        txid = self._run_send_open(name, wallet)
        messagebox.showinfo("Success", f"Auction opened!\nTXID: {txid}")

      except Exception as e:
        messagebox.showerror("Error", f"Failed to open auction: {e}")

  def _run_send_open(self, name, wallet):
    """Execute the raw OPEN transaction and return the txid."""
    cmd, _ = self.get_fbdctl_command("--wallet", wallet, "sendopen", name)
    result = subprocess.run(
      cmd,
      capture_output=True,
      text=True,
      cwd=Path(self.fbd_path_var.get()).parent,
      timeout=30,
    )

    if result.returncode != 0:
      error_msg = result.stderr.strip() or "Unknown error"
      raise RuntimeError(error_msg)

    response = json.loads(result.stdout)
    data = response.get("result", {}) if isinstance(response, dict) else response
    return data.get("txid", "N/A")

  def send_bid(self):
    """Place a bid - Stage 1: Smart bidding with auto-open"""
    wallet = self.wallet_name_var.get()
    name = self.name_var.get()
    bid = self.bid_amount_var.get()
    lockup = self.lockup_amount_var.get()

    if not all([wallet, name, bid, lockup]):
      messagebox.showwarning("Warning", "Please fill in all fields")
      return

    if not self.check_node_running():
      return

    # Stage 1: Check name state before bidding
    try:
      name_info = self.get_name_info_silent(name)
      state = name_info.get("state", "UNKNOWN")

      self.log(f"Name '{name}' current state: {state}")

      if state == "INACTIVE" or state == "UNKNOWN":
        # Name needs to be opened first
        if self.auto_continue_var.get():
          # Automation enabled - ask user if they want to auto-open
          response = messagebox.askyesno(
            "Name Inactive - Auto-Open?",
            f"'{name}' is {state} and needs to be opened first.\n\n"
            f"Open auction now and place bid automatically when bidding period starts?\n\n"
            f"[OK] Automation enabled: Will auto-bid, auto-reveal, and auto-register",
          )

          if response:
            # Create automation job first
            job_id = self.add_auction_job(
              name, wallet, bid, lockup, auto_enabled=True
            )

            if not job_id:
              messagebox.showerror(
                "Error", "Failed to create automation job"
              )
              return

            # Execute OPEN with job tracking
            if self.execute_send_open(name, wallet, job_id):
              messagebox.showinfo(
                "Auction Opened - Automation Active",
                f"[OK] Auction opened for '{name}'!\n\n"
                f"Automation will handle:\n"
                f" * Place bid when bidding opens\n"
                f" * Reveal bid at reveal phase\n"
                f" * Register name if you win\n\n"
                f"Job ID: {job_id[:8]}...\n"
                f"Check logs for progress updates.",
              )
            else:
              # OPEN failed, delete the job
              self.delete_job(job_id)
              # Error already shown by execute_send_open
          else:
            # User declined auto-open
            self.log("User declined auto-open for inactive name")
        else:
          # Automation disabled - just inform user
          messagebox.showwarning(
            "Cannot Bid - Name Inactive",
            f"'{name}' is {state}.\n\n"
            f"You must open the auction first using 'Open Auction' button.\n\n"
            f"Or enable 'Auto-continue' checkbox to automate the full process.",
          )

      elif state == "BIDDING":
        # Name is in bidding phase - proceed with normal bid
        if self.auto_continue_var.get():
          # Create job for automation
          job_id = self.add_auction_job(
            name, wallet, bid, lockup, auto_enabled=True
          )

          if not job_id:
            messagebox.showerror("Error", "Failed to create automation job")
            return

          # Update job to 'opened' status since we're starting from BID phase
          self.update_job_status(job_id, "opened")

          # Execute bid with job tracking
          if self.execute_send_bid(name, wallet, bid, lockup, job_id):
            messagebox.showinfo(
              "Bid Placed - Automation Active",
              f"[OK] Bid placed on '{name}'!\n\n"
              f"Automation will handle:\n"
              f" * Reveal bid at reveal phase\n"
              f" * Register name if you win\n\n"
              f"Job ID: {job_id[:8]}...",
            )
          else:
            # Bid failed, delete job
            self.delete_job(job_id)
        else:
          # Manual mode - just place bid
          self.execute_send_bid(name, wallet, bid, lockup, job_id=None)

      elif state == "REVEAL":
        messagebox.showwarning(
          "Cannot Bid - Reveal Phase",
          f"'{name}' is in REVEAL phase.\n\n"
          f"Bidding is closed. You can only reveal existing bids now.",
        )

      elif state == "CLOSED":
        messagebox.showwarning(
          "Cannot Bid - Auction Closed",
          f"'{name}' auction is CLOSED.\n\n"
          f"You can only register if you won the auction.",
        )

      elif state == "REGISTERED":
        messagebox.showinfo(
          "Name Already Registered",
          f"'{name}' is already REGISTERED.\n\n"
          f"This name is owned and cannot be bid on.",
        )

      else:
        messagebox.showwarning(
          "Cannot Bid",
          f"Name is in {state} state.\n\n" f"Cannot bid at this time.",
        )

    except Exception as e:
      self.log(f"Error in smart bid logic: {e}")
      messagebox.showerror("Error", f"Failed to process bid request: {e}")

  def send_reveal(self):
    """Reveal bids for a name"""
    wallet = self.wallet_name_var.get()
    name = self.name_var.get()

    if not all([wallet, name]):
      messagebox.showwarning("Warning", "Please fill in wallet and name")
      return

    if not self.check_node_running():
      return

    if messagebox.askyesno("Confirm", f"Reveal bids for '{name}'?"):
      try:
        cmd, fbdctl_path = self.get_fbdctl_command(
          "--wallet", wallet, "sendreveal", name
        )
        result = subprocess.run(
          cmd,
          capture_output=True,
          text=True,
          cwd=Path(self.fbd_path_var.get()).parent,
        )

        if result.returncode == 0:
          response = json.loads(result.stdout)
          data = (
            response.get("result", {})
            if isinstance(response, dict)
            else response
          )
          txids = data.get("txids", [])
          messagebox.showinfo(
            "Success", f"Bids revealed!\nCount: {len(txids)}"
          )
        else:
          messagebox.showerror("Error", result.stderr)

      except Exception as e:
        messagebox.showerror("Error", f"Failed to reveal bids: {e}")

  def send_register(self):
    """Register a won name"""
    wallet = self.wallet_name_var.get()
    name = self.name_var.get()

    if not all([wallet, name]):
      messagebox.showwarning("Warning", "Please fill in wallet and name")
      return

    if not self.check_node_running():
      return

    if messagebox.askyesno("Confirm", f"Register name '{name}'?"):
      try:
        cmd, fbdctl_path = self.get_fbdctl_command(
          "--wallet", wallet, "sendregister", name
        )
        result = subprocess.run(
          cmd,
          capture_output=True,
          text=True,
          cwd=Path(self.fbd_path_var.get()).parent,
        )

        if result.returncode == 0:
          response = json.loads(result.stdout)
          data = (
            response.get("result", {})
            if isinstance(response, dict)
            else response
          )
          messagebox.showinfo(
            "Success", f"Name registered!\nTXID: {data.get('txid', 'N/A')}"
          )
        else:
          messagebox.showerror("Error", result.stderr)

      except Exception as e:
        messagebox.showerror("Error", f"Failed to register name: {e}")

  def load_my_names(self):
    """Load names owned by wallet"""
    wallet = self.wallet_name_var.get()
    if not wallet:
      messagebox.showwarning("Warning", "Please enter a wallet name")
      return

    if not self.check_node_running():
      return

    try:
      cmd, fbdctl_path = self.get_fbdctl_command("--wallet", wallet, "getnames")
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        names = (
          response.get("result", [])
          if isinstance(response, dict)
          else response
        )
        self.names_text.delete(1.0, tk.END)

        if not names or len(names) == 0:
          self.names_text.insert(
            tk.END, f"No names found for wallet '{wallet}'.\n\n"
          )
          self.names_text.insert(
            tk.END, "This wallet has not registered any names yet.\n"
          )
          self.names_text.insert(
            tk.END,
            "Use the 'Open Auction' or 'Register' buttons above to acquire names.",
          )
          self.log(f"No names found for wallet: {wallet}")
        else:
          for name_data in names:
            name_info = name_data.get("name", {})
            self.names_text.insert(
              tk.END, f"Name: {name_info.get('string', 'N/A')}\n"
            )
            self.names_text.insert(
              tk.END, f"State: {name_info.get('state', 'N/A')}\n"
            )
            self.names_text.insert(
              tk.END,
              f"Value: {name_data.get('value', 0) / 1000000:.6f} FBC\n",
            )
            self.names_text.insert(tk.END, "-" * 40 + "\n")
          self.log(f"Loaded {len(names)} names for wallet: {wallet}")
      else:
        error_msg = result.stderr
        # Check if wallet doesn't exist
        if (
          "wallet not found" in error_msg.lower()
          or "does not exist" in error_msg.lower()
        ):
          self.names_text.delete(1.0, tk.END)
          self.names_text.insert(
            tk.END, f"[!] Wallet '{wallet}' not found in this node.\n\n"
          )
          self.names_text.insert(
            tk.END,
            "Open the Active Wallet dropdown in Wallet tab to see available wallets,\n",
          )
          self.names_text.insert(
            tk.END, "or 'Create Wallet' to create a new one."
          )
          self.log(f"Wallet not found: {wallet}")
        else:
          self.names_text.delete(1.0, tk.END)
          self.names_text.insert(tk.END, f"Error: {error_msg}")
          self.log(f"Error loading names: {error_msg}")

    except Exception as e:
      self.log(f"Error loading names: {e}")

  # Settings methods
  def load_config(self):
    """Load configuration from file"""
    default_miner_threads = str(max(1, (os.cpu_count() or 1) // 2))
    default_config = {
      "fbd_path": "./fbd",
      "ui_toolkit": UI_TOOLKIT_TTK,
      "theme_mode": "system",
      "network": "main",
      "host": "0.0.0.0",
      "log_level": "info",
      "agent": "tiMaxal",
      "mining_enabled": True,
      "miner_address": "fb1qp979k4ell5hvaktk5e3d6man66jrz2ucvkt748",
      "miner_threads": default_miner_threads,
      "pool_miner_address": "",
      "pool_miner_host": "pool.woodburn.au",
      "pool_miner_threads": "0",
      "miner_download_url": "https://l.woodburn.au/miner",
      "fbd_download_url": "https://fbd.dev/download/fbd-latest-linux-x86_64.zip",
      "index_tx": True,
      "index_address": False,
      "index_auctions": False,
      "wallet_name": "main",
      "rpc_host": "127.0.0.1",
      "rpc_port": "32869",
      "auto_restart": False,
      "restart_delay": "3",
      "custom_datadir": "",
      "custom_dns_port": "",
      "saved_addresses": [],
      "rollout_reminders": [],
      "watchlist": [],
    }

    try:
      if self.config_file.exists():
        with open(self.config_file, "r") as f:
          loaded_config = json.load(f)
          default_config.update(loaded_config)
    except Exception as e:
      print(f"Error loading config: {e}")

    return default_config

  def save_config(self):
    """Save configuration to file"""
    config = {
      "fbd_path": self.fbd_path_var.get(),
      "ui_toolkit": self.ui_toolkit_var.get(),
      "theme_mode": self.theme_mode_var.get(),
      "network": self.network_var.get(),
      "host": self.host_var.get(),
      "log_level": self.loglevel_var.get(),
      "agent": self.agent_var.get(),
      "mining_enabled": self.mining_enabled.get(),
      "miner_address": self.miner_address_var.get(),
      "miner_threads": self.miner_threads_var.get(),
      "pool_miner_address": self.pool_miner_address_var.get(),
      "pool_miner_host": self.pool_miner_host_var.get(),
      "pool_miner_threads": self.pool_miner_threads_var.get(),
      "miner_download_url": self.miner_download_url_var.get().strip(),
      "fbd_download_url": self.fbd_download_url_var.get().strip(),
      "index_tx": self.index_tx_var.get(),
      "index_address": self.index_address_var.get(),
      "index_auctions": self.index_auctions_var.get(),
      "wallet_name": self.wallet_name_var.get(),
      "rpc_host": self.rpc_host_var.get(),
      "rpc_port": self.rpc_port_var.get(),
      "auto_restart": self.auto_restart_var.get(),
      "restart_delay": self.restart_delay_var.get(),
      "rollout_reminders": self.rollout_reminders,
      "watchlist": self.watchlist,
    }

    # Add custom settings if they exist
    if hasattr(self, "custom_datadir_var"):
      config["custom_datadir"] = self.custom_datadir_var.get()
    if hasattr(self, "custom_dns_port_var"):
      config["custom_dns_port"] = self.custom_dns_port_var.get()

    try:
      self.config_file.parent.mkdir(parents=True, exist_ok=True)
      with open(self.config_file, "w") as f:
        json.dump(config, f, indent=2)
      return True
    except Exception as e:
      print(f"Error saving config: {e}")
      return False

  def load_saved_settings(self):
    """Load saved settings into UI"""
    default_miner_threads = str(max(1, (os.cpu_count() or 1) // 2))
    self.fbd_path_var.set(self.config.get("fbd_path", "./fbd"))
    toolkit_mode = _normalize_ui_toolkit(self.config.get("ui_toolkit", UI_TOOLKIT_TTK)) or UI_TOOLKIT_TTK
    if toolkit_mode == UI_TOOLKIT_CUSTOMTK and ctk is None:
      toolkit_mode = UI_TOOLKIT_TTK
    self.ui_toolkit_mode = toolkit_mode
    self.customtkinter_active = self.ui_toolkit_mode == UI_TOOLKIT_CUSTOMTK and ctk is not None
    self.ui_toolkit_var.set(toolkit_mode)
    self.ui_toolkit_choice_var.set(self.ui_toolkit_labels.get(toolkit_mode, self.ui_toolkit_labels[UI_TOOLKIT_TTK]))
    theme_mode = (self.config.get("theme_mode", "system") or "system").lower()
    if theme_mode not in ("system", "dark", "light"):
      theme_mode = "system"
    self.theme_mode_var.set(theme_mode)
    self.theme_choice_var.set(self.theme_mode_labels.get(theme_mode, "Same as system"))
    self.network_var.set(self.config.get("network", "main"))
    self.host_var.set(self.config.get("host", "0.0.0.0"))
    self.loglevel_var.set(self.config.get("log_level", "info"))
    self.agent_var.set(self.config.get("agent", "tiMaxal"))
    self.mining_enabled.set(self.config.get("mining_enabled", True))
    self.miner_address_var.set(self.config.get("miner_address", ""))
    self.miner_threads_var.set(
      self.config.get("miner_threads", default_miner_threads)
    )
    self.pool_miner_address_var.set(
      self.config.get("pool_miner_address", self.config.get("miner_address", ""))
    )
    self.pool_miner_host_var.set(
      self.config.get("pool_miner_host", "pool.woodburn.au")
    )
    self.pool_miner_threads_var.set(self.config.get("pool_miner_threads", "0"))
    self.miner_download_url_var.set(
      self.config.get("miner_download_url", "https://l.woodburn.au/miner")
    )
    self.fbd_download_url_var.set(
      self.config.get(
        "fbd_download_url",
        "https://fbd.dev/download/fbd-latest-linux-x86_64.zip",
      )
    )
    self.index_tx_var.set(self.config.get("index_tx", True))
    self.index_address_var.set(self.config.get("index_address", False))
    self.index_auctions_var.set(self.config.get("index_auctions", False))
    self.wallet_name_var.set(self.config.get("wallet_name", "main"))
    self.update_wallet_dropdown([self.wallet_name_var.get() or "main"])
    self.rpc_host_var.set(self.config.get("rpc_host", "127.0.0.1"))
    self.rpc_port_var.set(self.config.get("rpc_port", "32869"))
    self.auto_restart_var.set(self.config.get("auto_restart", False))
    self.restart_delay_var.set(self.config.get("restart_delay", "3"))
    reminders = self.config.get("rollout_reminders", [])
    self.rollout_reminders = reminders if isinstance(reminders, list) else []
    watchlist_data = self.config.get("watchlist", [])
    self.watchlist = watchlist_data if isinstance(watchlist_data, list) else []

    # Load custom settings if they exist
    if hasattr(self, "custom_datadir_var"):
      self.custom_datadir_var.set(self.config.get("custom_datadir", ""))
    if hasattr(self, "custom_dns_port_var"):
      self.custom_dns_port_var.set(self.config.get("custom_dns_port", ""))

    # Stage 5: Load email settings
    if hasattr(self, "email_manager"):
      self.load_email_settings()

    self.toggle_mining_options()
    self.apply_theme()

  def save_settings(self):
    """Save current settings"""
    if self.save_config():
      messagebox.showinfo("Success", "Settings saved successfully!")
      self.log("Settings saved")
    else:
      messagebox.showerror("Error", "Failed to save settings")

  def load_settings_file(self):
    """Load settings from file dialog"""
    filename = filedialog.askopenfilename(
      title="Load Settings",
      defaultextension=".json",
      filetypes=[("JSON files", "*.json"), ("All files", "*")],
    )

    if filename:
      try:
        with open(filename, "r") as f:
          self.config = json.load(f)
        self.load_saved_settings()
        messagebox.showinfo("Success", "Settings loaded successfully!")
      except Exception as e:
        messagebox.showerror("Error", f"Failed to load settings: {e}")

  def reset_defaults(self):
    """Reset settings to defaults"""
    if messagebox.askyesno("Confirm", "Reset all settings to defaults?"):
      default_miner_threads = str(max(1, (os.cpu_count() or 1) // 2))
      self.config = self.load_config()
      # Clear the config file by reloading defaults
      self.config = {
        "fbd_path": "./fbd",
        "ui_toolkit": UI_TOOLKIT_TTK,
        "theme_mode": "system",
        "network": "main",
        "host": "0.0.0.0",
        "log_level": "info",
        "agent": "tiMaxal",
        "mining_enabled": True,
        "miner_address": "fb1qp979k4ell5hvaktk5e3d6man66jrz2ucvkt748",
        "miner_threads": default_miner_threads,
        "pool_miner_address": "",
        "pool_miner_host": "pool.woodburn.au",
        "pool_miner_threads": "0",
        "miner_download_url": "https://l.woodburn.au/miner",
        "fbd_download_url": "https://fbd.dev/download/fbd-latest-linux-x86_64.zip",
        "index_tx": True,
        "index_address": False,
        "index_auctions": False,
        "wallet_name": "main",
        "rpc_host": "127.0.0.1",
        "rpc_port": "32869",
        "auto_restart": False,
        "restart_delay": "3",
        "custom_datadir": "",
        "custom_dns_port": "",
        "rollout_reminders": [],
        "watchlist": [],
      }
      self.load_saved_settings()
      messagebox.showinfo("Success", "Settings reset to defaults")

  def download_or_update_miner(self):
    """Check latest miner and auto-update only when a newer/different binary exists"""
    url = self.miner_download_url_var.get().strip()
    if not url:
      messagebox.showwarning("Missing URL", "Please enter a miner download URL.")
      return

    if not (url.startswith("http://") or url.startswith("https://")):
      messagebox.showwarning(
        "Invalid URL",
        "Miner download URL must start with http:// or https://",
      )
      return

    self.log(f"Checking miner version/update source: {url}")
    threading.Thread(
      target=self._download_or_update_miner_thread,
      args=(url,),
      daemon=True,
    ).start()

  def check_miner_version(self):
    """Check whether local miner matches the latest downloadable binary"""
    url = self.miner_download_url_var.get().strip()
    if not url:
      messagebox.showwarning("Missing URL", "Please enter a miner download URL.")
      return

    if not (url.startswith("http://") or url.startswith("https://")):
      messagebox.showwarning(
        "Invalid URL",
        "Miner download URL must start with http:// or https://",
      )
      return

    self.log(f"Checking miner version against: {url}")
    threading.Thread(
      target=self._check_miner_version_thread,
      args=(url,),
      daemon=True,
    ).start()

  def _get_file_sha256(self, path):
    """Return SHA256 for a file path"""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
      for chunk in iter(lambda: f.read(1024 * 1024), b""):
        hasher.update(chunk)
    return hasher.hexdigest()

  def _get_miner_version_string(self, miner_path):
    """Best-effort version string extraction from miner binary"""

    def _extract_version_line(output_text):
      """Return a stable version/banner line or None."""
      if not output_text:
        return None

      lines = [line.strip() for line in output_text.splitlines() if line.strip()]
      if not lines:
        return None

      # Prefer an explicit miner/version line and ignore obvious error text.
      for line in lines:
        lowered = line.lower()
        if "missing expected argument --user" in lowered:
          continue
        if "fistbump cpu miner" in lowered or " miner v" in lowered:
          return line[:200]
        if "version" in lowered and "error" not in lowered:
          return line[:200]

      return None

    try:
      if sys.platform != "win32":
        os.chmod(miner_path, 0o755)

      probe_args = [
        ["--version"],
        ["version"],
        ["-V"],
        ["--help"],
        ["-h"],
      ]

      saw_user_argument_error = False
      for args in probe_args:
        result = subprocess.run(
          [str(miner_path), *args],
          capture_output=True,
          text=True,
          timeout=10,
        )
        output = "\n".join(
          part for part in [result.stdout, result.stderr] if part
        ).strip()

        version_line = _extract_version_line(output)
        if version_line:
          return version_line

        if "missing expected argument --user" in output.lower():
          saw_user_argument_error = True

      if saw_user_argument_error:
        return "unknown (miner does not expose version via CLI flags)"
    except Exception:
      pass
    return "unknown"

  def _resolve_fbd_paths(self):
    """Resolve configured fbd path and sibling fbdctl path"""
    configured = self.fbd_path_var.get().strip() or "./fbd"
    fbd_path = Path(configured)
    if not fbd_path.is_absolute():
      fbd_path = (self.script_dir / fbd_path).resolve()
    fbdctl_path = fbd_path.parent / "fbdctl"
    return fbd_path, fbdctl_path

  def _extract_fbd_binaries_from_zip(self, zip_path, out_dir):
    """Extract fbd and fbdctl binaries from downloaded zip into out_dir"""
    out_dir.mkdir(parents=True, exist_ok=True)
    remote_fbd = out_dir / "fbd"
    remote_fbdctl = out_dir / "fbdctl"

    with zipfile.ZipFile(zip_path, "r") as zf:
      fbd_member = None
      fbdctl_member = None
      for member in zf.namelist():
        clean = member.rstrip("/")
        if clean.endswith("/fbd") or clean == "fbd":
          fbd_member = member
        elif clean.endswith("/fbdctl") or clean == "fbdctl":
          fbdctl_member = member

      if not fbd_member or not fbdctl_member:
        raise RuntimeError("Zip does not contain both fbd and fbdctl binaries.")

      with zf.open(fbd_member) as src, open(remote_fbd, "wb") as dst:
        shutil.copyfileobj(src, dst)
      with zf.open(fbdctl_member) as src, open(remote_fbdctl, "wb") as dst:
        shutil.copyfileobj(src, dst)

    if sys.platform != "win32":
      os.chmod(remote_fbd, 0o755)
      os.chmod(remote_fbdctl, 0o755)

    return remote_fbd, remote_fbdctl

  def check_fbd_version(self):
    """Check whether local fbd binary matches latest downloadable package"""
    url = self.fbd_download_url_var.get().strip()
    if not url:
      messagebox.showwarning("Missing URL", "Please enter an FBD package URL.")
      return
    if not (url.startswith("http://") or url.startswith("https://")):
      messagebox.showwarning(
        "Invalid URL", "FBD package URL must start with http:// or https://"
      )
      return

    self.log(f"Checking FBD package version against: {url}")
    threading.Thread(target=self._check_fbd_version_thread, args=(url,), daemon=True).start()

  def _check_fbd_version_thread(self, url):
    """Background thread: compare local fbd hash against latest packaged fbd"""
    fbd_path, _ = self._resolve_fbd_paths()
    zip_path = self.script_dir / "fbd.package.check.zip"
    extract_dir = self.script_dir / "fbd.package.check"

    try:
      response = requests.get(url, stream=True, timeout=40)
      response.raise_for_status()
      with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
          if chunk:
            f.write(chunk)

      remote_fbd, _ = self._extract_fbd_binaries_from_zip(zip_path, extract_dir)
      remote_hash = self._get_file_sha256(remote_fbd)
      remote_ver = self._get_miner_version_string(remote_fbd)

      if not fbd_path.exists():
        self.root.after(
          0,
          lambda: messagebox.showinfo(
            "FBD Version Check",
            "Configured fbd binary not found.\n\n"
            f"Latest version: {remote_ver}\n"
            "Use 'Check & Auto-Update FBD' to install.",
          ),
        )
        return

      local_hash = self._get_file_sha256(fbd_path)
      local_ver = self._get_miner_version_string(fbd_path)
      if local_hash == remote_hash:
        self.root.after(
          0,
          lambda: messagebox.showinfo(
            "FBD Version Check",
            "FBD is already up to date.\n\n"
            f"Local version: {local_ver}\n"
            f"Latest version: {remote_ver}",
          ),
        )
      else:
        self.root.after(
          0,
          lambda: messagebox.showinfo(
            "FBD Version Check",
            "FBD update available.\n\n"
            f"Local version: {local_ver}\n"
            f"Latest version: {remote_ver}\n\n"
            "Use 'Check & Auto-Update FBD' to apply.",
          ),
        )
    except Exception as e:
      self.log(f"FBD version check failed: {e}", level="error")
      self.root.after(
        0,
        lambda: messagebox.showerror(
          "FBD Version Check Failed", f"Failed to check FBD version:\n{e}"
        ),
      )
    finally:
      try:
        if zip_path.exists():
          zip_path.unlink()
        if extract_dir.exists():
          shutil.rmtree(extract_dir, ignore_errors=True)
      except Exception:
        pass

  def download_or_update_fbd(self):
    """Check latest FBD package and auto-update only when binaries differ"""
    url = self.fbd_download_url_var.get().strip()
    if not url:
      messagebox.showwarning("Missing URL", "Please enter an FBD package URL.")
      return
    if not (url.startswith("http://") or url.startswith("https://")):
      messagebox.showwarning(
        "Invalid URL", "FBD package URL must start with http:// or https://"
      )
      return

    self.log(f"Checking FBD package/update source: {url}")
    threading.Thread(target=self._download_or_update_fbd_thread, args=(url,), daemon=True).start()

  def _download_or_update_fbd_thread(self, url):
    """Background thread: update configured fbd + sibling fbdctl from latest zip"""
    fbd_path, fbdctl_path = self._resolve_fbd_paths()
    zip_path = self.script_dir / "fbd.package.update.zip"
    extract_dir = self.script_dir / "fbd.package.update"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
      response = requests.get(url, stream=True, timeout=40)
      response.raise_for_status()
      with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
          if chunk:
            f.write(chunk)

      remote_fbd, remote_fbdctl = self._extract_fbd_binaries_from_zip(zip_path, extract_dir)
      remote_hash = self._get_file_sha256(remote_fbd)
      remote_ver = self._get_miner_version_string(remote_fbd)

      if fbd_path.exists() and self._get_file_sha256(fbd_path) == remote_hash:
        self.root.after(
          0,
          lambda: messagebox.showinfo(
            "FBD Up To Date",
            "No update needed. Configured fbd matches latest package.",
          ),
        )
        return

      fbd_path.parent.mkdir(parents=True, exist_ok=True)

      if fbd_path.exists():
        fbd_path.replace(fbd_path.parent / f"fbd.backup.{ts}")
      if fbdctl_path.exists():
        fbdctl_path.replace(fbdctl_path.parent / f"fbdctl.backup.{ts}")

      remote_fbd.replace(fbd_path)
      remote_fbdctl.replace(fbdctl_path)

      if sys.platform != "win32":
        os.chmod(fbd_path, 0o755)
        os.chmod(fbdctl_path, 0o755)

      self.root.after(
        0,
        lambda: messagebox.showinfo(
          "FBD Updated",
          "FBD and fbdctl updated successfully.\n\n"
          f"Version: {remote_ver}\n"
          f"Path: {fbd_path}",
        ),
      )
    except Exception as e:
      self.log(f"FBD update failed: {e}", level="error")
      self.root.after(
        0,
        lambda: messagebox.showerror(
          "FBD Update Failed", f"Failed to update FBD binaries:\n{e}"
        ),
      )
    finally:
      try:
        if zip_path.exists():
          zip_path.unlink()
        if extract_dir.exists():
          shutil.rmtree(extract_dir, ignore_errors=True)
      except Exception:
        pass

  def startup_binary_update_check(self):
    """Check for newer miner/FBD binaries on startup and offer update-now or later"""
    threading.Thread(target=self._startup_binary_update_check_thread, daemon=True).start()

  def _startup_binary_update_check_thread(self):
    """Background thread: gather update availability and prompt once"""
    updates = []

    # Miner check
    try:
      miner_url = self.miner_download_url_var.get().strip()
      miner_path = self.script_dir / "miner"
      miner_temp = self.script_dir / "miner.startup.check"
      if miner_url.startswith("http"):
        r = requests.get(miner_url, stream=True, timeout=30)
        r.raise_for_status()
        with open(miner_temp, "wb") as f:
          for chunk in r.iter_content(chunk_size=8192):
            if chunk:
              f.write(chunk)
        if miner_temp.exists() and miner_temp.stat().st_size > 0:
          remote_hash = self._get_file_sha256(miner_temp)
          local_hash = self._get_file_sha256(miner_path) if miner_path.exists() else ""
          if remote_hash != local_hash:
            updates.append("miner")
      if miner_temp.exists():
        miner_temp.unlink()
    except Exception as e:
      self.log(f"Startup miner update check skipped: {e}", level="warning")

    # FBD check
    try:
      fbd_url = self.fbd_download_url_var.get().strip()
      fbd_path, _ = self._resolve_fbd_paths()
      zip_path = self.script_dir / "fbd.startup.check.zip"
      extract_dir = self.script_dir / "fbd.startup.check"
      if fbd_url.startswith("http"):
        r = requests.get(fbd_url, stream=True, timeout=40)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
          for chunk in r.iter_content(chunk_size=8192):
            if chunk:
              f.write(chunk)
        remote_fbd, _ = self._extract_fbd_binaries_from_zip(zip_path, extract_dir)
        remote_hash = self._get_file_sha256(remote_fbd)
        local_hash = self._get_file_sha256(fbd_path) if fbd_path.exists() else ""
        if remote_hash != local_hash:
          updates.append("fbd")
      if zip_path.exists():
        zip_path.unlink()
      if extract_dir.exists():
        shutil.rmtree(extract_dir, ignore_errors=True)
    except Exception as e:
      self.log(f"Startup FBD update check skipped: {e}", level="warning")

    if not updates:
      self.log("Startup binary check: binaries are up to date")
      return

    def _prompt():
      """ prompt."""
      parts = []
      if "miner" in updates:
        parts.append("miner")
      if "fbd" in updates:
        parts.append("fbd/fbdctl")
      item_text = " and ".join(parts)
      do_update = messagebox.askyesno(
        "Binary Updates Available",
        f"Newer {item_text} binaries were detected.\n\n"
        "Update now?\n\n"
        "Yes = check & auto-update now\n"
        "No = do later",
      )
      if do_update:
        if "miner" in updates:
          self.download_or_update_miner()
        if "fbd" in updates:
          self.download_or_update_fbd()
      else:
        self.log("Startup update prompt deferred by user (do later)")

    self.root.after(0, _prompt)

  def _check_miner_version_thread(self, url):
    """Background thread: compare local and latest miner hashes/versions"""
    miner_path = self.script_dir / "miner"
    temp_path = self.script_dir / "miner.check"

    try:
      response = requests.get(url, stream=True, timeout=30)
      response.raise_for_status()

      with open(temp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
          if chunk:
            f.write(chunk)

      if not temp_path.exists() or temp_path.stat().st_size == 0:
        raise RuntimeError("Downloaded check file is empty.")

      remote_hash = self._get_file_sha256(temp_path)

      if not miner_path.exists():
        self.log("Local miner not found. Update required.")
        self.root.after(
          0,
          lambda: messagebox.showinfo(
            "Miner Version Check",
            "Local miner not found.\n\n"
            f"SHA256: {remote_hash[:16]}...\n\n"
            "Use 'Check & Auto-Update Miner' to install.",
          ),
        )
        return

      local_hash = self._get_file_sha256(miner_path)

      if local_hash == remote_hash:
        self.log("Miner version check: already up to date.")
        self.root.after(
          0,
          lambda: messagebox.showinfo(
            "Miner Version Check",
            "Miner is already up to date.",
          ),
        )
      else:
        self.log("Miner version check: update available.")
        self.root.after(
          0,
          lambda: messagebox.showinfo(
            "Miner Version Check",
            "Update available for miner.\n\n"
            f"Local SHA256: {local_hash[:16]}...\n"
            f"Latest SHA256: {remote_hash[:16]}...\n\n"
            "Use 'Check & Auto-Update Miner' to apply.",
          ),
        )
    except Exception as e:
      self.log(f"Miner version check failed: {e}", level="error")
      self.root.after(
        0,
        lambda: messagebox.showerror(
          "Version Check Failed",
          f"Failed to check miner version:\n{e}",
        ),
      )
    finally:
      try:
        if temp_path.exists():
          temp_path.unlink()
      except Exception:
        pass

  def _download_or_update_miner_thread(self, url):
    """Background thread: download latest miner and replace only when hash differs"""
    miner_path = self.script_dir / "miner"
    temp_path = self.script_dir / "miner.download"
    backup_path = self.script_dir / (
      f"miner.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

    try:
      response = requests.get(url, stream=True, timeout=30)
      response.raise_for_status()

      with open(temp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
          if chunk:
            f.write(chunk)

      if not temp_path.exists() or temp_path.stat().st_size == 0:
        raise RuntimeError("Downloaded miner file is empty.")

      remote_hash = self._get_file_sha256(temp_path)
      remote_ver = self._get_miner_version_string(temp_path)

      if miner_path.exists():
        local_hash = self._get_file_sha256(miner_path)
        local_ver = self._get_miner_version_string(miner_path)
        if local_hash == remote_hash:
          self.log("Miner already up to date (hash match).")
          self.root.after(
            0,
            lambda: messagebox.showinfo(
              "Miner Up To Date",
              "No update needed. Local miner matches latest.\n\n"
              f"Version: {local_ver}\n"
              f"SHA256: {local_hash[:16]}...",
            ),
          )
          return

      if miner_path.exists():
        miner_path.replace(backup_path)
        self.log(f"Backed up existing miner to: {backup_path.name}")

      temp_path.replace(miner_path)

      if sys.platform != "win32":
        os.chmod(miner_path, 0o755)

      new_ver = self._get_miner_version_string(miner_path)
      self.log(f"Miner updated successfully: {miner_path}")
      self.root.after(
        0,
        lambda: messagebox.showinfo(
          "Miner Updated",
          "Miner downloaded/updated successfully.\n\n"
          f"Version: {new_ver}\n"
          f"SHA256: {remote_hash[:16]}...\n"
          f"Path: {miner_path}",
        ),
      )
    except Exception as e:
      self.log(f"Miner update failed: {e}", level="error")
      self.root.after(
        0,
        lambda: messagebox.showerror(
          "Miner Update Failed", f"Failed to download/update miner:\n{e}"
        ),
      )
    finally:
      try:
        if temp_path.exists():
          temp_path.unlink()
      except Exception:
        pass

  def check_running_instances(self):
    """Check for running fbd instances"""
    try:
      # Run ps command to find fbd processes
      result = subprocess.run(
        ["ps", "aux"], capture_output=True, text=True, timeout=5
      )

      if result.returncode == 0:
        # Filter for fbd processes (exclude grep and this GUI)
        lines = result.stdout.split("\n")
        fbd_processes = []

        for line in lines:
          if (
            "fbd" in line.lower()
            and "grep" not in line
            and "fbd_gui" not in line
          ):
            fbd_processes.append(line.strip())

        if fbd_processes:
          process_list = "\n".join(fbd_processes)
          messagebox.showwarning(
            f"Found {len(fbd_processes)} FBD Process(es)",
            f"The following fbd processes are running:\n\n{process_list}\n\n"
            f"If you see multiple instances, they may conflict if using the same datadir.\n\n"
            f"To kill a process:\n"
            f"1. Note the PID (second column)\n"
            f"2. Run: kill <PID>\n"
            f"Or kill all: pkill fbd",
          )
          self.log(f"Found {len(fbd_processes)} fbd process(es) running")
        else:
          messagebox.showinfo(
            "No FBD Processes", "No fbd processes found running."
          )
          self.log("No fbd processes found")
      else:
        messagebox.showerror(
          "Error", f"Failed to check processes: {result.stderr}"
        )

    except Exception as e:
      self.log(f"Error checking instances: {e}")
      messagebox.showerror("Error", f"Failed to check for running instances: {e}")

  # Stage 5: Email Notification Methods
  def toggle_email_password(self):
    """Toggle email password visibility"""
    self.email_password_visible = not self.email_password_visible
    if self.email_password_visible:
      self.email_password_entry.configure(show="")
      # Find and update button text
      for child in self.email_password_entry.master.winfo_children():
        if isinstance(child, ttk.Button) and child.cget("text") in [
          "Show",
          "Hide",
        ]:
          child.configure(text="Hide")
    else:
      self.email_password_entry.configure(show="*")
      for child in self.email_password_entry.master.winfo_children():
        if isinstance(child, ttk.Button) and child.cget("text") in [
          "Show",
          "Hide",
        ]:
          child.configure(text="Show")

  def save_email_settings(self):
    """Save email notification settings"""
    try:
      # Get values from UI
      enabled = self.email_enabled_var.get()
      smtp_server = self.email_smtp_server_var.get().strip()
      smtp_port = int(self.email_smtp_port_var.get().strip())
      from_email = self.email_from_var.get().strip()
      password = self.email_password_var.get()
      to_email = self.email_to_var.get().strip()

      # Validate
      if enabled and not all(
        [smtp_server, smtp_port, from_email, password, to_email]
      ):
        messagebox.showwarning(
          "Incomplete Settings",
          "Please fill all fields to enable email notifications.",
        )
        return

      # Update email manager config
      self.email_manager.update_config(
        enabled, smtp_server, smtp_port, from_email, password, to_email
      )

      messagebox.showinfo("Success", "Email settings saved successfully!")
      self.log("Email notification settings updated")

    except ValueError:
      messagebox.showerror(
        "Invalid Port", "SMTP port must be a number (usually 587 or 465)"
      )
    except Exception as e:
      messagebox.showerror("Error", f"Failed to save email settings: {e}")
      self.log(f"Error saving email settings: {e}")

  def send_test_email(self):
    """Send a test email"""
    try:
      # First save settings
      self.save_email_settings()

      # Send test
      self.log("Sending test email...")
      success, message = self.email_manager.send_test_email()

      if success:
        messagebox.showinfo("Test Email Sent", message)
        self.log("Test email sent successfully")
      else:
        messagebox.showerror("Test Email Failed", message)
        self.log(f"Test email failed: {message}")

    except Exception as e:
      messagebox.showerror("Error", f"Failed to send test email: {e}")
      self.log(f"Error sending test email: {e}")

  def load_email_settings(self):
    """Load email settings into UI"""
    try:
      config = self.email_manager.config

      self.email_enabled_var.set(config.get("enabled", False))
      self.email_smtp_server_var.set(config.get("smtp_server", "smtp.gmail.com"))
      self.email_smtp_port_var.set(str(config.get("smtp_port", 587)))
      self.email_from_var.set(config.get("from_email", ""))
      self.email_to_var.set(config.get("to_email", ""))

      # Load password (decoded)
      password = self.email_manager.get_password()
      self.email_password_var.set(password)

    except Exception as e:
      self.log(f"Error loading email settings: {e}")

  # Configuration Profile Management
  def get_profiles_dir(self):
    """Get directory for storing configuration profiles"""
    profiles_dir = Path.home() / ".fbdgui" / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    return profiles_dir

  def list_profiles(self):
    """List all available configuration profiles"""
    profiles_dir = self.get_profiles_dir()
    profiles = ["default"]

    if profiles_dir.exists():
      for profile_file in profiles_dir.glob("*.json"):
        profiles.append(profile_file.stem)

    return sorted(set(profiles))

  def save_new_profile(self):
    """Save current configuration as a new profile"""
    from tkinter import simpledialog

    profile_name = simpledialog.askstring(
      "New Profile", "Enter name for new profile:", initialvalue="my_config"
    )

    if profile_name:
      # Remove any path separators for security
      profile_name = profile_name.replace("/", "_").replace("\\", "_")

      if profile_name == "default":
        messagebox.showwarning(
          "Invalid Name", "Cannot use 'default' as profile name"
        )
        return

      profiles_dir = self.get_profiles_dir()
      profile_file = profiles_dir / f"{profile_name}.json"

      # Get current configuration
      config = {
        "fbd_path": self.fbd_path_var.get(),
        "network": self.network_var.get(),
        "host": self.host_var.get(),
        "log_level": self.loglevel_var.get(),
        "agent": self.agent_var.get(),
        "mining_enabled": self.mining_enabled.get(),
        "miner_address": self.miner_address_var.get(),
        "miner_threads": self.miner_threads_var.get(),
        "pool_miner_address": self.pool_miner_address_var.get(),
        "pool_miner_host": self.pool_miner_host_var.get(),
        "pool_miner_threads": self.pool_miner_threads_var.get(),
        "miner_download_url": self.miner_download_url_var.get().strip(),
        "fbd_download_url": self.fbd_download_url_var.get().strip(),
        "index_tx": self.index_tx_var.get(),
        "index_address": self.index_address_var.get(),
        "index_auctions": self.index_auctions_var.get(),
        "wallet_name": self.wallet_name_var.get(),
        "rpc_host": self.rpc_host_var.get(),
        "rpc_port": self.rpc_port_var.get(),
        "auto_restart": self.auto_restart_var.get(),
        "restart_delay": self.restart_delay_var.get(),
      }

      # Add custom settings if they exist
      if hasattr(self, "custom_datadir_var"):
        config["custom_datadir"] = self.custom_datadir_var.get()
      if hasattr(self, "custom_dns_port_var"):
        config["custom_dns_port"] = self.custom_dns_port_var.get()

      try:
        with open(profile_file, "w") as f:
          json.dump(config, f, indent=2)

        # Update profile list in UI
        self.profile_combo["values"] = self.list_profiles()
        self.profile_var.set(profile_name)

        messagebox.showinfo(
          "Success", f"Profile '{profile_name}' saved successfully!"
        )
        self.log(f"Profile '{profile_name}' saved")
      except Exception as e:
        messagebox.showerror("Error", f"Failed to save profile: {e}")

  def update_profile(self):
    """Update the currently selected profile with current settings"""
    profile_name = self.profile_var.get()

    if profile_name == "default":
      # Update default config file
      if self.save_config():
        messagebox.showinfo("Success", "Default configuration updated!")
        self.log("Default configuration updated")
      else:
        messagebox.showerror("Error", "Failed to update default configuration")
      return

    if messagebox.askyesno(
      "Confirm", f"Overwrite profile '{profile_name}' with current settings?"
    ):
      profiles_dir = self.get_profiles_dir()
      profile_file = profiles_dir / f"{profile_name}.json"

      config = {
        "fbd_path": self.fbd_path_var.get(),
        "network": self.network_var.get(),
        "host": self.host_var.get(),
        "log_level": self.loglevel_var.get(),
        "agent": self.agent_var.get(),
        "mining_enabled": self.mining_enabled.get(),
        "miner_address": self.miner_address_var.get(),
        "miner_threads": self.miner_threads_var.get(),
        "pool_miner_address": self.pool_miner_address_var.get(),
        "pool_miner_host": self.pool_miner_host_var.get(),
        "pool_miner_threads": self.pool_miner_threads_var.get(),
        "miner_download_url": self.miner_download_url_var.get().strip(),
        "fbd_download_url": self.fbd_download_url_var.get().strip(),
        "index_tx": self.index_tx_var.get(),
        "index_address": self.index_address_var.get(),
        "index_auctions": self.index_auctions_var.get(),
        "wallet_name": self.wallet_name_var.get(),
        "rpc_host": self.rpc_host_var.get(),
        "rpc_port": self.rpc_port_var.get(),
        "auto_restart": self.auto_restart_var.get(),
        "restart_delay": self.restart_delay_var.get(),
      }

      # Add custom settings if they exist
      if hasattr(self, "custom_datadir_var"):
        config["custom_datadir"] = self.custom_datadir_var.get()
      if hasattr(self, "custom_dns_port_var"):
        config["custom_dns_port"] = self.custom_dns_port_var.get()

      try:
        with open(profile_file, "w") as f:
          json.dump(config, f, indent=2)
        messagebox.showinfo("Success", f"Profile '{profile_name}' updated!")
        self.log(f"Profile '{profile_name}' updated")
      except Exception as e:
        messagebox.showerror("Error", f"Failed to update profile: {e}")

  def load_profile(self):
    """Load selected configuration profile"""
    profile_name = self.profile_var.get()

    if profile_name == "default":
      # Load default config
      self.config = self.load_config()
      self.load_saved_settings()
      messagebox.showinfo("Success", "Default configuration loaded!")
      self.log("Default configuration loaded")
      return

    profiles_dir = self.get_profiles_dir()
    profile_file = profiles_dir / f"{profile_name}.json"

    if not profile_file.exists():
      messagebox.showerror("Error", f"Profile '{profile_name}' not found")
      return

    try:
      with open(profile_file, "r") as f:
        self.config = json.load(f)
      self.load_saved_settings()
      messagebox.showinfo(
        "Success", f"Profile '{profile_name}' loaded successfully!"
      )
      self.log(f"Profile '{profile_name}' loaded")
    except Exception as e:
      messagebox.showerror("Error", f"Failed to load profile: {e}")

  def delete_profile(self):
    """Delete selected configuration profile"""
    profile_name = self.profile_var.get()

    if profile_name == "default":
      messagebox.showwarning("Cannot Delete", "Cannot delete the default profile")
      return

    if messagebox.askyesno("Confirm Delete", f"Delete profile '{profile_name}'?"):
      profiles_dir = self.get_profiles_dir()
      profile_file = profiles_dir / f"{profile_name}.json"

      try:
        if profile_file.exists():
          profile_file.unlink()

          # Update profile list in UI
          self.profile_combo["values"] = self.list_profiles()
          self.profile_var.set("default")

          messagebox.showinfo("Success", f"Profile '{profile_name}' deleted")
          self.log(f"Profile '{profile_name}' deleted")
        else:
          messagebox.showwarning(
            "Not Found", f"Profile '{profile_name}' not found"
          )
      except Exception as e:
        messagebox.showerror("Error", f"Failed to delete profile: {e}")

  # ========================================================================
  # STAGE 7: EDGE CASES & POLISH
  # ========================================================================

  def check_wallet_unlocked_before_automation(self, job):
    """
    Verify wallet is unlocked before automated action (Stage 7)

    Args:
      job: Job data dict with wallet

    Returns:
      bool: True if wallet is unlocked or not encrypted, False if locked
    """
    wallet = job["wallet"]
    info = self.get_wallet_info_silent(wallet)

    if not info:
      # Could not get wallet info - assume problem
      self.log(f"[!] Could not get wallet info for '{wallet}'", "warning")
      return False

    encrypted = info.get("encrypted", False)
    unlocked = info.get("unlocked", True) # Default to true if not encrypted

    if encrypted and not unlocked:
      self.log(
        f"[!] Wallet '{wallet}' is locked, cannot perform automated action",
        "warning",
      )
      self.notification_manager.add_notification(
        "wallet_locked",
        f"Wallet '{wallet}' locked - automation paused",
        f"Job: {job['name']} - Unlock wallet to continue",
        job_id=job["id"],
        level="warning",
      )
      self.update_job_status(
        job["id"], "paused_wallet_locked", error=f"Wallet '{wallet}' is locked"
      )
      return False

    return True

  def check_sufficient_funds(self, job, action):
    """
    Verify balance before transaction (Stage 7)

    Args:
      job: Job data dict
      action: Action type ('bid', 'reveal', 'register')

    Returns:
      bool: True if sufficient funds, False otherwise
    """
    wallet = job["wallet"]
    balance = self.get_balance_silent(wallet)

    if not balance:
      self.log(f"[!] Could not get balance for wallet '{wallet}'", "warning")
      return False

    spendable = balance.get("spendable", 0)

    # Calculate required amount (in base units - satoshis)
    if action == "bid":
      lockup = float(job["lockup_amount"]) * 1_000_000
      required = lockup + 10000 # + fee buffer
    elif action == "register":
      required = 50000 # Typical register fee + buffer
    elif action == "open":
      required = 10000 # Small fee for open
    else:
      # Reveal doesn't require funds (just unlocks)
      return True

    if spendable < required:
      error_msg = f"Insufficient funds: need {required/1_000_000:.6f} FBC, have {spendable/1_000_000:.6f} FBC"
      self.log(f"[X] {error_msg}", "error")
      self.update_job_status(job["id"], "failed", error=error_msg)
      self.notification_manager.add_notification(
        "insufficient_funds",
        f"Cannot {action}: {job['name']}",
        error_msg,
        job_id=job["id"],
        level="error",
      )
      return False

    return True

  def verify_transaction_confirmed(self, txid, min_confirmations=1):
    """
    Verify transaction is still valid (reorg protection) (Stage 7)

    Args:
      txid: Transaction ID to verify
      min_confirmations: Minimum confirmations required

    Returns:
      bool: True if confirmed, False otherwise
    """
    try:
      tx = self.get_transaction_silent(txid)

      if not tx:
        self.log(
          f"[!] Transaction {txid[:12]}... not found (possible reorg)",
          "warning",
        )
        return False

      confirmations = tx.get("confirmations", 0)

      if confirmations >= min_confirmations:
        return True
      else:
        self.log(
          f"[!] Transaction {txid[:12]}... has {confirmations} confirmations (need {min_confirmations})",
          "warning",
        )
        return False

    except Exception as e:
      self.log(f"[!] Error verifying transaction {txid[:12]}...: {e}", "warning")
      return False

  def execute_with_timeout(self, func, timeout=30, *args, **kwargs):
    """
    Execute function with timeout to prevent UI blocking (Stage 7)

    Args:
      func: Function to execute
      timeout: Timeout in seconds
      *args, **kwargs: Arguments to pass to function

    Returns:
      Result from function or error dict
    """
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor() as executor:
      future = executor.submit(func, *args, **kwargs)
      try:
        return future.result(timeout=timeout)
      except concurrent.futures.TimeoutError:
        self.log(f"[!] Operation timed out after {timeout}s", "error")
        return {"success": False, "error": "Operation timeout"}
      except Exception as e:
        self.log(f"[X] Error: {e}", "error")
        return {"success": False, "error": str(e)}

  def _write_log_with_rotation(self, log_line):
    """
    Write to log file with 10MB rotation (Stage 7)

    Args:
      log_line: Line to write to log
    """
    log_file = self.log_file # Use the instance log file path

    try:
      # Check size and rotate if needed
      if log_file.exists() and log_file.stat().st_size > 10 * 1024 * 1024: # 10MB
        # Rotate: .log -> .log.1, .log.1 -> .log.2, etc. (keep last 3)
        for i in range(2, 0, -1):
          old_file = Path(f"{log_file}.{i}")
          new_file = Path(f"{log_file}.{i+1}")
          if old_file.exists():
            old_file.rename(new_file)

        # Rename current log to .log.1
        log_file.rename(f"{log_file}.1")

      # Write to log file
      with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

    except Exception as e:
      # Don't crash if rotation fails
      try:
        with open(log_file, "a", encoding="utf-8") as f:
          f.write(log_line)
      except:
        pass # Fail silently

  def restore_auction_jobs_on_startup(self):
    """
    Restore and verify jobs after app restart (Stage 7)
    Called from __init__ to recover state
    """
    jobs_data = self.load_auction_jobs()
    active_jobs = [
      j
      for j in jobs_data["jobs"]
      if j["status"] not in ["registered", "lost", "failed", "cancelled"]
    ]

    if active_jobs:
      self.log(f"[i] Restored {len(active_jobs)} active auction job(s)", "info")

      # Verify each job's state
      for job in active_jobs:
        self._verify_and_sync_job_state(job)

  def _verify_and_sync_job_state(self, job):
    """
    Verify job state matches blockchain state (Stage 7)

    Args:
      job: Job data to verify
    """
    try:
      # Check if transactions are still confirmed
      txids = job.get("txids", {})

      for tx_type, txid in txids.items():
        if txid and isinstance(txid, str): # Single txid
          if not self.verify_transaction_confirmed(txid):
            self.log(
              f"[!] Job {job['name']}: {tx_type} transaction {txid[:12]}... needs verification",
              "warning",
            )
        elif txid and isinstance(txid, list): # Multiple txids (reveals)
          for t in txid:
            if not self.verify_transaction_confirmed(t):
              self.log(
                f"[!] Job {job['name']}: {tx_type} transaction {t[:12]}... needs verification",
                "warning",
              )

      # Verify wallet still exists and is accessible
      wallet = job["wallet"]
      wallet_info = self.get_wallet_info_silent(wallet)
      if not wallet_info:
        self.log(
          f"[!] Job {job['name']}: wallet '{wallet}' not accessible", "warning"
        )

    except Exception as e:
      self.log(
        f"[!] Error verifying job {job.get('id', 'unknown')[:8]}...: {e}",
        "warning",
      )

  # ========================================================================
  # END STAGE 7
  # ========================================================================

  def log(self, message, level="info"):
    """
    Log message to output and file with level support (Stage 7 enhanced)

    Args:
      message: Message to log
      level: Log level ('debug', 'info', 'warning', 'error')
    """
    from datetime import datetime

    # Emoji map for levels
    emoji_map = {"debug": "[*][*]", "info": "[i]", "warning": "[!]", "error": "[X]"}

    # Get emoji prefix (if not already in message)
    emoji = emoji_map.get(level, "")
    if not any(e in message for e in emoji_map.values()):
      display_message = f"{emoji} {message}" if emoji else message
    else:
      display_message = message

    # Show debug lines in UI when log level is debug/trace.
    configured_level = (
      self.loglevel_var.get().lower()
      if hasattr(self, "loglevel_var") and self.loglevel_var.get()
      else "info"
    )
    show_debug = configured_level in ["debug", "trace"]
    if level in ["info", "warning", "error"] or (level == "debug" and show_debug):
      self.log_text.insert(tk.END, f"{display_message}\n")
      self.log_text.see(tk.END)

    # Write to log file with timestamp and rotation
    try:
      timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      log_line = f"[{timestamp}] [{level.upper()}] {message}\n"
      self._write_log_with_rotation(log_line)
    except Exception as e:
      # Don't crash if logging fails, just show in GUI
      self.log_text.insert(tk.END, f"(Log file error: {e})\n")

  def clear_log_display(self):
    """Clear the log display (doesn't delete log file)"""
    if messagebox.askyesno(
      "Clear Log", "Clear the log display?\n\n(Log file will be preserved)"
    ):
      self.log_text.delete("1.0", tk.END)
      self.log("=" * 60)
      self.log("Log display cleared (previous logs still in file)")
      self.log("=" * 60)

  def open_log_file(self):
    """Open the GUI log file in default text editor"""
    try:
      if self.log_file.exists():
        log_path_str = str(self.log_file)
        # Use platform-appropriate command
        if sys.platform == "win32":
          # On Windows, use subprocess.Popen to avoid blocking
          subprocess.Popen(["notepad.exe", log_path_str])
        else:
          # On Linux/WSL, convert path to Windows format using wslpath
          try:
            # Use wslpath to convert WSL path to Windows path
            result = subprocess.run(
              ["wslpath", "-w", log_path_str],
              capture_output=True,
              text=True,
              check=True,
            )
            win_path = result.stdout.strip()
            subprocess.Popen(["notepad.exe", win_path])
            self.log(f"[*][!] Opening log file: {win_path}")
          except subprocess.CalledProcessError:
            # wslpath failed, try xdg-open
            try:
              subprocess.Popen(["xdg-open", log_path_str])
            except:
              messagebox.showinfo(
                "Log File Location",
                f"Log file:\n{self.log_file}\n\nOpen it manually in your text editor.",
              )
          except FileNotFoundError:
            # wslpath not available, fall back to xdg-open
            try:
              subprocess.Popen(["xdg-open", log_path_str])
            except:
              messagebox.showinfo(
                "Log File Location",
                f"Log file:\n{self.log_file}\n\nOpen it manually in your text editor.",
              )
      else:
        messagebox.showinfo(
          "Log File",
          f"Log file not yet created.\nWill be created at:\n{self.log_file}",
        )
    except Exception as e:
      messagebox.showinfo(
        "Log File Location",
        f"Log file:\n{self.log_file}\n\n(Could not auto-open: {e})",
      )

  def open_config_dir(self):
    """Open the GUI configuration directory in file manager"""
    try:
      config_dir = self.config_file.parent
      config_dir.mkdir(parents=True, exist_ok=True)

      # Use platform-appropriate command
      if sys.platform == "win32":
        os.startfile(config_dir)
      else:
        subprocess.run(["xdg-open", str(config_dir)])
    except Exception as e:
      messagebox.showerror("Error", f"Could not open config directory:\n{e}")

  def show_help(self):
    """Display help dialog with quick reference"""
    help_text = """
FBD Node Manager v4.1.0 - Quick Help

PLATFORM:
* Linux-native Python app (runs on native Linux, WSL, or Windows via WSL)
* "wslgui" name reflects original WSL development environment
* Core app is standard cross-platform Python/Tkinter

DEPENDENCIES:
* Python 3.6+ with tkinter (python3-tk)
* python3-requests library
* Auto-checked on startup with install offers

[!] REQUIRED BINARIES:
* fbd & fbdctl NOT included in repo (file size)
* Download: https://fbd.dev/download/fbd-latest-linux-x86_64.zip
* Extract and place in same directory as this app
* chmod +x fbd fbdctl
* Keep updated by re-downloading latest zip

DOCUMENTATION:
* README.md - Complete usage guide
* QUICKSTART.txt - Quick start reference
* ai-hist_fbd-wslgui/ - Archived docs & older versions

GETTING STARTED:
1. Download fbd & fbdctl binaries (see above)
2. Settings Tab -> Set FBD path (e.g., ./fbd or ./fbd-latest-linux-x86_64/fbd)
3. Node & Mining Tab -> Configure network & miner address
4. Click "Start Node"

MINING (Two Modes - Choose One):

  SOLO MINING:
  * Enable Mining checkbox: CHECKED
  * Set miner address & threads
  * Click "Start Node"
  * Keep 100% of block rewards
  -> For dedicated miners

  POOL MINING (Recommended):
  * Enable Mining checkbox: UNCHECKED
  * Set pool wallet address & host
  * Click "Start Pool Miner" button
  * Consistent payouts, no full node needed
  * Settings -> Check Miner Version (compare local vs latest)
  * Settings -> Check & Auto-Update Miner (updates only when needed)
  -> For casual miners

  [!] Cannot run BOTH simultaneously!


WALLET:
* List/Create wallets in Wallet tab
* Get balance, send payments, view transactions
* Remember to save your wallet mnemonic!

AUCTIONS:
* Get name info -> Open -> Bid -> Reveal -> Register
* View owned names with "Load My Names"
* Automation available in Auction Automation tab

[!] SETTINGS:
* Save/load configurations
* Export/import for backup
* Configure auto-restart & indexing
* Manage miner URL and safe version-checked auto-update
* Manage FBD package URL and safe fbd/fbdctl auto-update
* Startup checks for both miner and fbd/fbdctl with Update Now or Do Later

FILES LOCATION:
* Config: ~/.fbdgui/fbdgui_config.json
* Profiles: ~/.fbdgui/profiles/
* Logs: ~/.fbdgui/fbdgui.log

RESOURCES:
* FBD Docs: https://fbd.dev
* Explorer: https://explorer.fistbump.org/
* Whitepaper: https://fistbump.org/fistbump.txt

[*]! TIP: Use File -> Open GUI Config Directory
to access config and log files!
"""

    # Create custom dialog
    help_window = self._create_toplevel()
    help_window.title("FBD Node Manager - Help")
    help_window.geometry("650x600")

    # Help text display
    text_frame = ttk.Frame(help_window, padding=10)
    text_frame.pack(fill="both", expand=True)

    help_display = self._create_log_widget(
      text_frame, wrap=tk.WORD, font=("Courier", 10)
    )
    help_display.pack(fill="both", expand=True)
    help_display.insert("1.0", help_text)
    help_display.configure(state="disabled")

    # Buttons
    button_frame = ttk.Frame(help_window, padding=10)
    button_frame.pack(fill="x")

    self._create_button(
      button_frame,
      text="Open README.md",
      command=lambda: self.open_doc_file("README.md"),
    ).pack(side="left", padx=5)
    self._create_button(
      button_frame,
      text="Open QUICKSTART.txt",
      command=lambda: self.open_doc_file("QUICKSTART.txt"),
    ).pack(side="left", padx=5)
    self._create_button(button_frame, text="Close", command=help_window.destroy).pack(
      side="right", padx=5
    )

    # Make window stay on top but don't grab (allows interaction with docs)
    help_window.transient(self.root)

  def open_doc_file(self, filename):
    """Open a documentation file in the default text editor (non-blocking)"""
    # Run in background thread to avoid blocking GUI
    threading.Thread(
      target=self._open_doc_file_thread, args=(filename,), daemon=True
    ).start()

  def _open_doc_file_thread(self, filename):
    """Background thread for opening documentation files"""
    doc_path = self.script_dir / filename
    if not doc_path.exists():
      self.root.after(
        0,
        lambda: messagebox.showwarning(
          "Not Found", f"{filename} not found at {doc_path}"
        ),
      )
      return

    try:
      if sys.platform == "win32":
        # Windows: use os.startfile (non-blocking)
        os.startfile(str(doc_path))
        self.log(f"Opened {filename}")
      else:
        # For Linux/WSL, try multiple approaches (all non-blocking)
        opened = False

        # First, try Windows notepad via WSL with path conversion
        try:
          # Convert WSL path to Windows path for notepad.exe (with timeout)
          result = subprocess.run(
            ["wslpath", "-w", str(doc_path)],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
          )
          if result.returncode == 0:
            windows_path = result.stdout.strip()
            # Use Popen for non-blocking execution
            subprocess.Popen(["notepad.exe", windows_path])
            opened = True
            self.log(f"Opened {filename} in Windows Notepad")
        except (FileNotFoundError, subprocess.TimeoutExpired):
          pass

        if not opened:
          # Try xdg-open (native Linux, non-blocking)
          try:
            subprocess.Popen(["xdg-open", str(doc_path)])
            opened = True
            self.log(f"Opened {filename} with xdg-open")
          except FileNotFoundError:
            pass

        if not opened:
          # Try common text editors (non-blocking)
          for editor in ["gedit", "kate", "mousepad", "leafpad"]:
            try:
              subprocess.Popen([editor, str(doc_path)])
              opened = True
              self.log(f"Opened {filename} with {editor}")
              break
            except FileNotFoundError:
              continue

        if not opened:
          # Last resort: display content in GUI window (runs in main thread)
          self.root.after(
            0, lambda: self._show_doc_in_window(filename, doc_path)
          )

    except Exception as e:
      self.log(f"Error opening {filename}: {e}")
      self.root.after(
        0,
        lambda: messagebox.showerror(
          "Error", f"Could not open {filename}: {e}"
        ),
      )

  def _show_doc_in_window(self, filename, doc_path):
    """Display file content in a GUI window"""
    try:
      with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

      # Create a window to display the file
      view_window = self._create_toplevel()
      view_window.title(f"View: {filename}")
      view_window.geometry("800x600")

      text_frame = ttk.Frame(view_window, padding=10)
      text_frame.pack(fill="both", expand=True)

      text_display = self._create_log_widget(
        text_frame, wrap=tk.WORD, font=("Courier", 9)
      )
      text_display.pack(fill="both", expand=True)
      text_display.insert("1.0", content)
      text_display.configure(state="disabled")

      self._create_button(view_window, text="Close", command=view_window.destroy).pack(
        pady=10
      )

      self.log(f"Displaying {filename} in GUI (no external editor found)")
    except Exception as e:
      messagebox.showerror("Error", f"Could not display {filename}: {e}")

  def on_ctrl_q(self, event=None):
    """Handle Ctrl+Q keyboard shortcut"""
    # Only ask for confirmation if node is stopped
    if not self.fbd_process or self.fbd_process.poll() is not None:
      if messagebox.askyesno("Confirm Exit", "Exit FBD Node Manager?"):
        self.on_closing()
    else:
      # Node is running, use standard closing
      self.on_closing()

  def on_closing(self):
    """Handle window closing"""
    self.monitoring = False
    self.restart_in_progress = False # Prevent restart on closing

    # Stage 2: Stop auction monitor
    if hasattr(self, "auction_monitor") and self.auction_monitor:
      self.auction_monitor.stop()

    # Stage 6: Stop jobs auto-refresh
    if hasattr(self, "stop_jobs_auto_refresh"):
      self.stop_jobs_auto_refresh()

    node_running = self.fbd_process and self.fbd_process.poll() is None
    pool_running = (
      self.pool_miner_process and self.pool_miner_process.poll() is None
    )

    if node_running or pool_running:
      if messagebox.askyesno(
        "Confirm Exit", "Node or pool miner is still running. Stop it and exit?"
      ):
        if node_running:
          self.stop_node()
        if pool_running:
          self.stop_pool_miner()
        self.root.destroy()
    else:
      self.root.destroy()

  # ========================================================================
  # AUCTION AUTOMATION - STAGE 0: FOUNDATION SETUP
  # ========================================================================

  def _ensure_auction_jobs_file(self):
    """Ensure auction jobs JSON file exists with proper structure"""
    if not self.auction_jobs_file.exists():
      initial_data = {"version": "1.0", "jobs": []}
      try:
        with open(self.auction_jobs_file, "w") as f:
          json.dump(initial_data, f, indent=2)
        self.log(f"Created auction jobs file: {self.auction_jobs_file}")
      except Exception as e:
        self.log(f"Error creating auction jobs file: {e}")

  # ========================================================================
  # AUCTION AUTOMATION - STAGE 1: SMART OPEN INTEGRATION
  # ========================================================================

  def get_name_info_silent(self, name):
    """
    Get name information without updating UI

    Args:
      name: Name to query

    Returns:
      dict: Name info data, or empty dict on error
    """
    try:
      cmd, _ = self.get_fbdctl_command("getnameinfo", name)
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=10,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )
        return data
      else:
        self.log(f"Error getting name info for '{name}': {result.stderr}")
        return {}

    except Exception as e:
      self.log(f"Exception in get_name_info_silent: {e}")
      return {}

  def _get_current_height_silent(self):
    """
    Get current block height without prompting user or updating UI

    Returns:
      int: Current block height, or None if node not running
    """
    try:
      result = self.rpc_call("getblockchaininfo")
      if result:
        return result.get("blocks", None)
      return None
    except Exception:
      return None

  def offer_rollout_reminder(self, name, rollout_height):
    """Offer rollout reminder options when rolloutHeight is available."""
    if self.has_rollout_reminder(name, rollout_height):
      existing = [
        r for r in self.rollout_reminders
        if r.get("name") == name
        and int(r.get("rollout_height", 0)) == int(rollout_height)
        and not r.get("fired", False)
      ]
      reminder_lines = "\n".join(
        f"  \u2022 {r.get('label', r.get('mode', 'unknown'))}" for r in existing
      )
      messagebox.showinfo(
        "Reminder Already Set",
        f"Rollout reminders already set for '{name}' (release block {rollout_height:,}):\n\n{reminder_lines}\n\nUse 'Rollout Reminders' to manage them.",
      )
      return

    if not messagebox.askyesno(
      "Rollout Reminder",
      f"Name '{name}' has rolloutHeight {rollout_height:,}.\n\n"
      "Would you like a reminder before or when it becomes available?",
    ):
      return

    self.show_rollout_reminder_dialog(name, rollout_height)

  def show_rollout_reminder_dialog(self, name, rollout_height):
    """Prompt for one or more rollout reminder triggers."""
    dialog = self._create_toplevel()
    dialog.title(f"Rollout Reminder: {name}")
    dialog.geometry("520x250")
    dialog.resizable(False, False)
    dialog.transient(self.root)
    dialog.grab_set()

    current_height = self._get_current_height_silent()

    frame = ttk.Frame(dialog, padding=15)
    frame.pack(fill="both", expand=True)

    status_text = (
      f"Release block: {rollout_height:,}\nCurrent block: {current_height:,}"
      if current_height is not None
      else f"Release block: {rollout_height:,}\nCurrent block: unavailable"
    )
    ttk.Label(frame, text=status_text, justify="left").pack(
      anchor="w", pady=(0, 10)
    )

    notify_at_release_var = tk.BooleanVar(value=True)
    notify_blocks_var = tk.BooleanVar(value=False)
    notify_hours_var = tk.BooleanVar(value=False)
    blocks_before_var = tk.StringVar(value="10")
    hours_before_var = tk.StringVar(value="48")

    ttk.Checkbutton(
      frame,
      text="Notify at release block",
      variable=notify_at_release_var,
    ).pack(anchor="w", pady=2)

    blocks_row = ttk.Frame(frame)
    blocks_row.pack(fill="x", pady=2)
    ttk.Checkbutton(
      blocks_row,
      text="Notify blocks before:",
      variable=notify_blocks_var,
    ).pack(side="left")
    self._create_entry(blocks_row, textvariable=blocks_before_var, width=8).pack(
      side="left", padx=(8, 4)
    )
    ttk.Label(blocks_row, text="blocks").pack(side="left")

    minutes_row = ttk.Frame(frame)
    minutes_row.pack(fill="x", pady=2)
    ttk.Checkbutton(
      minutes_row,
      text="Notify hours before:",
      variable=notify_hours_var,
    ).pack(side="left")
    self._create_entry(minutes_row, textvariable=hours_before_var, width=8).pack(
      side="left", padx=(19, 4)
    )
    ttk.Label(minutes_row, text="hours (approx, 30 blocks/hour)").pack(side="left")

    def save_reminders():
      added = 0

      if not any(
        [
          notify_at_release_var.get(),
          notify_blocks_var.get(),
          notify_hours_var.get(),
        ]
      ):
        messagebox.showwarning(
          "No Reminder Selected",
          "Select at least one rollout reminder option.",
          parent=dialog,
        )
        return

      if notify_at_release_var.get():
        added += self.add_rollout_reminder(
          name,
          rollout_height,
          rollout_height,
          "at release block",
          lead_blocks=0,
          mode="release",
        )

      if notify_blocks_var.get():
        try:
          blocks_before = int(blocks_before_var.get().strip())
          if blocks_before <= 0:
            raise ValueError()
        except ValueError:
          messagebox.showwarning(
            "Invalid Blocks",
            "Enter a positive whole number for blocks before release.",
            parent=dialog,
          )
          return

        added += self.add_rollout_reminder(
          name,
          rollout_height,
          rollout_height - blocks_before,
          f"{blocks_before:,} blocks before release",
          lead_blocks=blocks_before,
          mode="blocks",
        )

      if notify_hours_var.get():
        try:
          hours_before = int(hours_before_var.get().strip())
          if hours_before <= 0:
            raise ValueError()
        except ValueError:
          messagebox.showwarning(
            "Invalid Hours",
            "Enter a positive whole number for hours before release.",
            parent=dialog,
          )
          return

        lead_blocks = max(1, hours_before * 30)
        added += self.add_rollout_reminder(
          name,
          rollout_height,
          rollout_height - lead_blocks,
          f"about {hours_before:,} hours before release (~{lead_blocks:,} blocks)",
          lead_blocks=lead_blocks,
          mode="hours",
        )

      if added > 0:
        dialog.destroy()
        messagebox.showinfo(
          "Rollout Reminder",
          f"Saved {added} rollout reminder(s) for '{name}'.",
        )
      else:
        messagebox.showinfo(
          "Rollout Reminder",
          f"No new reminders were added for '{name}'.",
          parent=dialog,
        )

    button_row = ttk.Frame(frame)
    button_row.pack(fill="x", pady=(15, 0))
    self._create_button(button_row, text="Save", command=save_reminders).pack(
      side="right", padx=(8, 0)
    )
    self._create_button(button_row, text="Cancel", command=dialog.destroy).pack(
      side="right"
    )

  def has_rollout_reminder(self, name, rollout_height):
    """Return True when a pending reminder already exists for this rollout."""
    rollout_height = int(rollout_height)
    return any(
      reminder.get("name") == name
      and int(reminder.get("rollout_height", 0)) == rollout_height
      and not reminder.get("fired", False)
      for reminder in self.rollout_reminders
    )

  def show_rollout_reminders_manager(self):
    """Show a small UI for viewing and removing pending rollout reminders."""
    dialog = self._create_toplevel()
    dialog.title("Pending Rollout Reminders")
    dialog.geometry("760x320")
    dialog.transient(self.root)

    frame = ttk.Frame(dialog, padding=10)
    frame.pack(fill="both", expand=True)

    current_height = self._get_current_height_silent()
    current_text = (
      f"Current block: {current_height:,}"
      if current_height is not None
      else "Current block: unavailable"
    )
    ttk.Label(frame, text=current_text).pack(anchor="w", pady=(0, 8))

    columns = ("name", "release", "trigger", "lead")
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=10)
    tree.heading("name", text="Name")
    tree.heading("release", text="Release Block")
    tree.heading("trigger", text="Trigger Block")
    tree.heading("lead", text="Reminder")
    tree.column("name", width=180)
    tree.column("release", width=110, anchor="center")
    tree.column("trigger", width=110, anchor="center")
    tree.column("lead", width=320)
    tree.pack(fill="both", expand=True)

    empty_label = ttk.Label(frame, text="No pending rollout reminders.")

    def refresh_tree():
      for item in tree.get_children():
        tree.delete(item)

      reminders = sorted(
        [r for r in self.rollout_reminders if not r.get("fired", False)],
        key=lambda reminder: (
          int(reminder.get("trigger_block", 0)),
          str(reminder.get("name", "")),
        ),
      )

      if reminders:
        empty_label.pack_forget()
        for reminder in reminders:
          reminder_id = reminder.get("id") or f"row-{len(tree.get_children())}"
          tree.insert(
            "",
            tk.END,
            iid=reminder_id,
            values=(
              reminder.get("name", ""),
              f"{int(reminder.get('rollout_height', 0)):,}",
              f"{int(reminder.get('trigger_block', 0)):,}",
              reminder.get("label", ""),
            ),
          )
      else:
        empty_label.pack(anchor="w", pady=(8, 0))

    def remove_selected():
      selected = tree.selection()
      if not selected:
        messagebox.showwarning(
          "No Selection",
          "Please select at least one rollout reminder to remove.",
          parent=dialog,
        )
        return

      selected_ids = set(selected)
      before_count = len(self.rollout_reminders)
      self.rollout_reminders = [
        reminder
        for reminder in self.rollout_reminders
        if reminder.get("id") not in selected_ids
      ]
      removed = before_count - len(self.rollout_reminders)
      if removed > 0:
        self.save_config()
        self.log(f"Removed {removed} rollout reminder(s)")
      refresh_tree()

    button_row = ttk.Frame(frame)
    button_row.pack(fill="x", pady=(10, 0))
    self._create_button(
      button_row,
      text="Remove Selected",
      command=remove_selected,
    ).pack(side="left")
    self._create_button(button_row, text="Refresh", command=refresh_tree).pack(
      side="left", padx=(8, 0)
    )
    self._create_button(button_row, text="Close", command=dialog.destroy).pack(side="right")

    refresh_tree()

  # â”€â”€ Watchlist methods â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  def is_on_watchlist(self, name):
    """Return True if name is already on the watchlist."""
    return any(w.get("name") == name for w in self.watchlist)

  def add_to_watchlist(self, name, notes=""):
    """Add a name to the watchlist if not already present. Returns True if added."""
    if self.is_on_watchlist(name):
      return False
    entry = {
      "name": name,
      "added": datetime.now().isoformat(),
      "notes": notes,
      "last_state": None,
      "notified_states": [],
    }
    self.watchlist.append(entry)
    self.save_config()
    self.log(f"Added '{name}' to watchlist")
    return True

  def remove_from_watchlist(self, name):
    """Remove a name from the watchlist. Returns True if removed."""
    before = len(self.watchlist)
    self.watchlist = [w for w in self.watchlist if w.get("name") != name]
    if len(self.watchlist) < before:
      self.save_config()
      return True
    return False

  def offer_add_to_watchlist(self, name):
    """Offer to add a name to the watchlist after a name lookup."""
    if self.is_on_watchlist(name):
      return
    if messagebox.askyesno(
      "Add to Watchlist",
      f"Add '{name}' to your watchlist?\n\n"
      "You'll be notified if an auction starts for this name.",
    ):
      self.add_to_watchlist(name)
      messagebox.showinfo("Watchlist", f"'{name}' added to watchlist.")

  def show_watchlist_manager(self):
    """Show the watchlist manager dialog."""
    dialog = self._create_toplevel()
    dialog.title("Watchlist")
    dialog.geometry("760x400")
    dialog.transient(self.root)

    frame = ttk.Frame(dialog, padding=10)
    frame.pack(fill="both", expand=True)

    # Filter row
    filter_row = ttk.Frame(frame)
    filter_row.pack(fill="x", pady=(0, 8))
    ttk.Label(filter_row, text="Filter:").pack(side="left")
    search_var = tk.StringVar()
    self._create_entry(filter_row, textvariable=search_var, width=30).pack(
      side="left", padx=(6, 0)
    )

    columns = ("name", "state", "added", "notes")
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
    tree.heading("name", text="Name")
    tree.heading("state", text="State")
    tree.heading("added", text="Added")
    tree.heading("notes", text="Notes")
    tree.column("name", width=180)
    tree.column("state", width=100, anchor="center")
    tree.column("added", width=170, anchor="center")
    tree.column("notes", width=270)
    tree.pack(fill="both", expand=True)

    empty_label = ttk.Label(frame, text="Watchlist is empty.")

    def refresh_tree(filter_text=""):
      for item in tree.get_children():
        tree.delete(item)
      items = list(self.watchlist)
      if filter_text:
        ft = filter_text.lower()
        items = [w for w in items if ft in w.get("name", "").lower()]
      items = sorted(items, key=lambda w: w.get("name", ""))
      if items:
        empty_label.pack_forget()
        for entry in items:
          wname = entry.get("name", "")
          state = entry.get("last_state") or "\u2014"
          added_raw = entry.get("added", "")
          try:
            added_dt = datetime.fromisoformat(added_raw)
            added_str = added_dt.strftime("%Y-%m-%d %H:%M")
          except Exception:
            added_str = added_raw[:16] if added_raw else "\u2014"
          notes = entry.get("notes", "")
          tree.insert(
            "", tk.END, iid=wname, values=(wname, state, added_str, notes)
          )
      else:
        empty_label.pack(anchor="w", pady=(8, 0))

    search_var.trace_add("write", lambda *_: refresh_tree(search_var.get()))

    def use_name():
      selected = tree.selection()
      if not selected:
        messagebox.showwarning(
          "No Selection", "Select a name first.", parent=dialog
        )
        return
      self.name_var.set(selected[0])
      dialog.destroy()

    def open_auction():
      selected = tree.selection()
      if not selected:
        messagebox.showwarning(
          "No Selection", "Select a name first.", parent=dialog
        )
        return
      wname = selected[0]
      dialog.destroy()
      self.start_watchlist_auction(wname)

    def remove_selected():
      selected = tree.selection()
      if not selected:
        messagebox.showwarning(
          "No Selection",
          "Select at least one name to remove.",
          parent=dialog,
        )
        return
      for wname in selected:
        self.remove_from_watchlist(wname)
      refresh_tree(search_var.get())

    button_row = ttk.Frame(frame)
    button_row.pack(fill="x", pady=(10, 0))
    self._create_button(button_row, text="Use Name", command=use_name).pack(side="left")
    self._create_button(button_row, text="Open Auction", command=open_auction).pack(
      side="left", padx=(8, 0)
    )
    self._create_button(
      button_row, text="Remove Selected", command=remove_selected
    ).pack(side="left", padx=(8, 0))
    self._create_button(
      button_row,
      text="Refresh",
      command=lambda: refresh_tree(search_var.get()),
    ).pack(side="left", padx=(8, 0))
    self._create_button(button_row, text="Close", command=dialog.destroy).pack(
      side="right"
    )

    refresh_tree()

  def _emit_watchlist_auction_alert(self, name, state):
    """Emit a watchlist auction-start alert on the main thread."""
    state_label = {
      "OPENING": "auction is opening (bidding starts soon)",
      "BIDDING": "auction is open for bidding",
      "REVEAL": "bidding closed \u2014 reveal phase active",
    }.get(state, f"state changed to {state}")
    message = f"Watchlist: '{name}' \u2014 {state_label}."
    self.log(f"[!] {message}")
    self.notification_manager.add_notification(
      "watchlist_alert", name, message, level="info"
    )
    messagebox.showinfo("Watchlist Alert", message)

  def _validate_bid_lockup_values(self, bid_amount, lockup_amount):
    """Validate bid/lockup values used for queued watchlist bids."""
    bid_text = str(bid_amount).strip()
    lockup_text = str(lockup_amount).strip()

    if not bid_text or not lockup_text:
      return None, None, "Bid and lockup amounts are required."

    try:
      bid_value = float(bid_text)
      lockup_value = float(lockup_text)
    except ValueError:
      return None, None, "Bid and lockup amounts must be numeric."

    if bid_value <= 0 or lockup_value <= 0:
      return None, None, "Bid and lockup amounts must be greater than zero."

    if lockup_value < bid_value:
      return None, None, "Lockup amount must be at least the bid amount."

    return bid_text, lockup_text, None

  def _prompt_watchlist_open_bid_options(self, name, parent=None):
    """Prompt for optional BID/LOCKUP scheduling when opening from watchlist."""
    parent_window = parent or self.root
    response = messagebox.askyesnocancel(
      "Start Auction from Watchlist",
      f"Start auction for '{name}'?\n\n"
      "Yes = OPEN and queue a BID/LOCKUP action when BIDDING starts\n"
      "No = OPEN only\n"
      "Cancel = Do nothing",
      parent=parent_window,
      icon="question",
    )

    if response is None:
      return None

    if response is False:
      return {"queue_bid": False}

    default_bid = self.bid_amount_var.get().strip()
    default_lockup = self.lockup_amount_var.get().strip()

    while True:
      bid_amount = simpledialog.askstring(
        "Queued Bid Amount",
        f"Bid amount to place for '{name}' when BIDDING begins (FBC):",
        initialvalue=default_bid,
        parent=parent_window,
      )
      if bid_amount is None:
        return None

      lockup_amount = simpledialog.askstring(
        "Queued Lockup Amount",
        f"Lockup amount for '{name}' when BIDDING begins (FBC):",
        initialvalue=default_lockup,
        parent=parent_window,
      )
      if lockup_amount is None:
        return None

      bid_text, lockup_text, error = self._validate_bid_lockup_values(
        bid_amount, lockup_amount
      )
      if not error:
        break

      messagebox.showwarning("Invalid Bid Setup", error, parent=parent_window)
      default_bid = str(bid_amount).strip()
      default_lockup = str(lockup_amount).strip()

    add_to_automation = messagebox.askyesno(
      "Add to Automation Cycle?",
      f"After the queued BID is placed for '{name}', add it to the automation cycle\n"
      "for REVEAL and REGISTER as well?",
      parent=parent_window,
      icon="question",
    )

    return {
      "queue_bid": True,
      "bid_amount": bid_text,
      "lockup_amount": lockup_text,
      "auto_enabled": add_to_automation,
    }

  def start_watchlist_auction(self, name):
    """Start an auction from watchlist with optional queued BID/LOCKUP."""
    wallet = self.wallet_name_var.get().strip()

    if not wallet:
      messagebox.showwarning(
        "No Wallet Selected", "Select a wallet before starting an auction."
      )
      return

    self.name_var.set(name)

    if not self.check_node_running():
      return

    plan = self._prompt_watchlist_open_bid_options(name)
    if plan is None:
      return

    if not plan.get("queue_bid"):
      try:
        txid = self._run_send_open(name, wallet)
        messagebox.showinfo(
          "Auction Opened", f"Auction opened for '{name}'!\nTXID: {txid}"
        )
      except Exception as e:
        messagebox.showerror("Error", f"Failed to open auction: {e}")
      return

    bid_amount = str(plan["bid_amount"])
    lockup_amount = str(plan["lockup_amount"])
    auto_enabled = bool(plan["auto_enabled"])

    self.bid_amount_var.set(bid_amount)
    self.lockup_amount_var.set(lockup_amount)

    job_id = self.add_auction_job(
      name,
      wallet,
      bid_amount,
      lockup_amount,
      auto_enabled=auto_enabled,
      auto_bid_enabled=True,
    )

    if not job_id:
      messagebox.showerror("Error", "Failed to create queued auction job")
      return

    if self.execute_send_open(name, wallet, job_id):
      cycle_text = (
        "The auction remains in the automation cycle for REVEAL and REGISTER."
        if auto_enabled
        else "The queued job will stop after placing the BID unless you later enable automation."
      )
      messagebox.showinfo(
        "Auction Opened - Bid Queued",
        f"Auction opened for '{name}'.\n\n"
        f"Queued BID: {bid_amount} FBC\n"
        f"Queued LOCKUP: {lockup_amount} FBC\n\n"
        "The BID will be sent automatically when the name enters BIDDING.\n"
        f"{cycle_text}\n\n"
        f"Job ID: {job_id[:8]}...",
      )
    else:
      self.delete_job(job_id)

  def add_rollout_reminder(
    self, name, rollout_height, trigger_block, label, lead_blocks=0, mode="release"
  ):
    """Add a rollout reminder if an equivalent reminder does not already exist."""
    trigger_block = int(trigger_block)
    rollout_height = int(rollout_height)
    lead_blocks = int(lead_blocks)

    reminder_id = f"{name}:{rollout_height}:{mode}:{lead_blocks}:{trigger_block}"
    if any(r.get("id") == reminder_id for r in self.rollout_reminders):
      return 0

    reminder = {
      "id": reminder_id,
      "name": name,
      "rollout_height": rollout_height,
      "trigger_block": trigger_block,
      "label": label,
      "lead_blocks": lead_blocks,
      "mode": mode,
      "created": datetime.now().isoformat(),
      "fired": False,
    }

    current_height = self._get_current_height_silent()
    if current_height is not None and trigger_block <= current_height:
      self.emit_rollout_reminder(reminder, current_height)
      return 1

    self.rollout_reminders.append(reminder)
    self.save_config()
    self.log(
      f"Saved rollout reminder for '{name}' at block {trigger_block:,} ({label})"
    )
    return 1

  def emit_rollout_reminder(self, reminder, current_height):
    """Emit a one-time reminder notification for a rollout trigger."""
    name = reminder.get("name", "")
    rollout_height = int(reminder.get("rollout_height", 0))
    trigger_block = int(reminder.get("trigger_block", rollout_height))
    label = reminder.get("label", "rollout reminder")

    if trigger_block >= rollout_height:
      message = (
        f"Name '{name}' is available now at rollout block {rollout_height:,}."
      )
    else:
      message = (
        f"Name '{name}' release is approaching: {label}. "
        f"Release block {rollout_height:,}, current block {current_height:,}."
      )

    self.notification_manager.add_notification(
      "rollout_reminder",
      name,
      message,
      level="info",
    )
    self.log(message)
    messagebox.showinfo("Rollout Reminder", message)

  def check_rollout_reminders(self):
    """Fire pending rollout reminders when the current block reaches them."""
    if not self.rollout_reminders:
      return

    current_height = self._get_current_height_silent()
    if current_height is None:
      return

    changed = False
    remaining = []
    for reminder in self.rollout_reminders:
      trigger_block = int(reminder.get("trigger_block", 0))
      if reminder.get("fired", False) or current_height < trigger_block:
        remaining.append(reminder)
        continue

      reminder["fired"] = True
      self.emit_rollout_reminder(reminder, current_height)
      changed = True

    if changed:
      self.rollout_reminders = [
        reminder for reminder in remaining if not reminder.get("fired", False)
      ]
      self.save_config()

  def check_watchlist_auction_start(self):
    """Check watchlist names for auction-state changes every ~60 seconds."""
    if not self.watchlist:
      return
    self._watchlist_check_tick += 1
    if self._watchlist_check_tick < 12:
      return
    self._watchlist_check_tick = 0
    threading.Thread(
      target=self._check_watchlist_states_thread, daemon=True
    ).start()

  def _check_watchlist_states_thread(self):
    """Background: query getnameinfo state for all watchlist names."""
    ACTIVE_STATES = {"OPENING", "BIDDING", "REVEAL"}
    changed = False
    for entry in list(self.watchlist):
      name = entry.get("name", "")
      if not name:
        continue
      try:
        result = self.rpc_call("getnameinfo", [name])
        if not isinstance(result, dict):
          continue
        state = result.get("state")
        if state is None:
          continue
        old_state = entry.get("last_state")
        if state != old_state:
          entry["last_state"] = state
          changed = True
          notified = entry.get("notified_states") or []
          if state in ACTIVE_STATES and state not in notified:
            notified = list(notified) + [state]
            entry["notified_states"] = notified
            self.root.after(
              0, self._emit_watchlist_auction_alert, name, state
            )
      except Exception:
        pass
    if changed:
      self.save_config()

  def get_wallet_info_silent(self, wallet):
    """
    Get wallet info without updating UI (Stage 7)
    Used by automation validation

    Args:
      wallet: Wallet name to query

    Returns:
      dict: Wallet info data (address, encrypted, unlocked, etc.), or None on error
    """
    try:
      cmd, _ = self.get_fbdctl_command("--wallet", wallet, "getwalletinfo")
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=10,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )
        return data
      else:
        return None

    except Exception as e:
      return None

  def get_balance_silent(self, wallet):
    """
    Get wallet balance without updating UI (Stage 7)
    Used by automation validation

    Args:
      wallet: Wallet name to query

    Returns:
      dict: Balance info (spendable, confirmed, immature in satoshis), or None on error
    """
    try:
      cmd, _ = self.get_fbdctl_command("--wallet", wallet, "getbalance")
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=10,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )
        return data if isinstance(data, dict) else None
      else:
        return None

    except Exception as e:
      return None

  def execute_send_open(self, name, wallet, job_id):
    """
    Execute OPEN transaction with job tracking (Stage 1 + Stage 4 notifications)

    Args:
      name: Name to open
      wallet: Wallet to use
      job_id: Job ID for tracking

    Returns:
      bool: True if successful, False otherwise
    """
    try:
      self.log(f"Opening auction for '{name}' (Job: {job_id[:8]}...)")

      txid = self._run_send_open(name, wallet)

      # Update job status
      self.update_job_status(job_id, "opened", txid=txid)

      self.log(f"[OK] Auction opened for '{name}': {txid[:12]}...")
      # Stage 4: Notify opened
      self.notification_manager.notify_opened(name, job_id, txid)
      return True

    except Exception as e:
      error_msg = str(e)
      self.log(f"Exception opening auction for '{name}': {error_msg}")
      self.update_job_status(job_id, "failed", error=error_msg)
      messagebox.showerror("Error", f"Failed to open auction: {error_msg}")
      return False

  def execute_send_bid(self, name, wallet, bid, lockup, job_id=None):
    """
    Execute BID transaction with optional job tracking

    Args:
      name: Name to bid on
      wallet: Wallet to use
      bid: Bid amount in FBC
      lockup: Lockup amount in FBC
      job_id: Optional job ID for tracking

    Returns:
      bool: True if successful, False otherwise
    """
    try:
      # Confirmation dialog for manual mode only
      if job_id is None:
        if not messagebox.askyesno(
          "Confirm Bid", f"Bid {bid} FBC (lockup {lockup} FBC) on '{name}'?"
        ):
          return False

      self.log(
        f"Placing bid on '{name}': {bid} FBC (lockup: {lockup} FBC)"
        + (f" (Job: {job_id[:8]}...)" if job_id else "")
      )

      cmd, _ = self.get_fbdctl_command(
        "--wallet", wallet, "sendbid", name, bid, lockup
      )
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=30,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )
        txid = data.get("txid", "N/A")

        # Update job status if tracking
        if job_id:
          self.update_job_status(job_id, "bid_placed", txid=txid)
          self.log(f"[OK] Bid placed on '{name}': {txid[:12]}...")
        else:
          messagebox.showinfo("Success", f"Bid placed!\nTXID: {txid}")

        return True
      else:
        error_msg = result.stderr
        self.log(f"[OK]- Failed to place bid on '{name}': {error_msg}")

        if job_id:
          self.update_job_status(job_id, "failed", error=error_msg)

        messagebox.showerror("Bid Failed", f"Failed to place bid:\n{error_msg}")
        return False

    except Exception as e:
      error_msg = str(e)
      self.log(f"Exception placing bid on '{name}': {error_msg}")

      if job_id:
        self.update_job_status(job_id, "failed", error=error_msg)

      messagebox.showerror("Error", f"Failed to place bid: {error_msg}")
      return False

  # ========================================================================
  # AUCTION AUTOMATION - STAGE 3: AUTOMATIC PHASE TRANSITIONS
  # ========================================================================

  def execute_send_bid_silent(self, name, wallet, bid, lockup):
    """
    Execute BID silently (no UI dialogs) for automation

    Returns:
      dict: {'success': bool, 'txid': str, 'error': str}
    """
    try:
      cmd, _ = self.get_fbdctl_command(
        "--wallet", wallet, "sendbid", name, bid, lockup
      )
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=30,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )
        txid = data.get("txid", "N/A")
        return {"success": True, "txid": txid}
      else:
        return {"success": False, "error": result.stderr}

    except Exception as e:
      return {"success": False, "error": str(e)}

  def execute_send_reveal_silent(self, name, wallet):
    """
    Execute REVEAL silently (no UI dialogs) for automation

    Returns:
      dict: {'success': bool, 'txids': list, 'error': str}
    """
    try:
      cmd, _ = self.get_fbdctl_command("--wallet", wallet, "sendreveal", name)
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=30,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )
        txids = data.get("txids", [])
        return {"success": True, "txids": txids}
      else:
        return {"success": False, "error": result.stderr}

    except Exception as e:
      return {"success": False, "error": str(e)}

  def execute_send_register_silent(self, name, wallet):
    """
    Execute REGISTER silently (no UI dialogs) for automation

    Returns:
      dict: {'success': bool, 'txid': str, 'error': str}
    """
    try:
      cmd, _ = self.get_fbdctl_command("--wallet", wallet, "sendregister", name)
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=30,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )
        txid = data.get("txid", "N/A")
        return {"success": True, "txid": txid}
      else:
        return {"success": False, "error": result.stderr}

    except Exception as e:
      return {"success": False, "error": str(e)}

  def execute_send_redeem_silent(self, name, wallet):
    """
    Execute REDEEM silently (no UI dialogs) for automation
    Redeems locked funds from lost auctions

    Returns:
      dict: {'success': bool, 'txid': str, 'error': str}
    """
    try:
      cmd, _ = self.get_fbdctl_command("--wallet", wallet, "sendredeem", name)
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=30,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", {})
          if isinstance(response, dict)
          else response
        )
        txid = data.get("txid", "N/A")
        return {"success": True, "txid": txid}
      else:
        return {"success": False, "error": result.stderr}

    except Exception as e:
      return {"success": False, "error": str(e)}

  def get_wallet_bids_silent(self, wallet, name):
    """
    Get wallet's bids for a name (silent, for automation)

    Returns:
      list: List of bid dicts, empty list on error
    """
    try:
      # Try to get bids from wallet for this name
      # This requires --index-auctions to be enabled
      cmd, _ = self.get_fbdctl_command("--wallet", wallet, "getbids", name)
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=10,
      )

      if result.returncode == 0:
        response = json.loads(result.stdout)
        data = (
          response.get("result", [])
          if isinstance(response, dict)
          else response
        )
        return data if isinstance(data, list) else []
      else:
        # Command failed - may not be implemented yet
        return []

    except Exception as e:
      self.log(f"Could not get wallet bids: {e}")
      return []

  # ========================================================================
  # AUCTION IMPORT: SCAN & ADD EXISTING AUCTIONS TO AUTOMATION
  # ========================================================================

  def scan_wallet_auctions(self, wallet):
    """
    Scan wallet for active/pending auctions
    Returns list of auction dicts with name, state, and bid info

    Enhanced to find:
    1. Names already registered to wallet (from getnames)
    2. Names wallet has bid on (from wallet transactions)
    """
    auctions = []
    found_names = set()

    try:
      self.log(f"[*][*] Scanning wallet '{wallet}' for auction activity...")

      # STEP 1: Get registered names from wallet (existing logic)
      self.log(" -> Checking registered names...")
      try:
        cmd, _ = self.get_fbdctl_command("--wallet", wallet, "getnames")
        result = subprocess.run(
          cmd,
          capture_output=True,
          text=True,
          cwd=Path(self.fbd_path_var.get()).parent,
          timeout=15,
        )

        if result.returncode == 0:
          response = json.loads(result.stdout)
          names_data = (
            response.get("result", [])
            if isinstance(response, dict)
            else response
          )

          if names_data:
            for name_entry in names_data:
              name_info = name_entry.get("name", {})
              name = name_info.get("string", "")
              if name:
                found_names.add(name)
            self.log(f"  Found {len(found_names)} registered name(s)")
      except Exception as e:
        self.log(f"  Could not get registered names: {e}")

      # STEP 2: Get wallet address for debugging
      self.log(" -> Getting wallet address...")
      try:
        cmd, _ = self.get_fbdctl_command("--wallet", wallet, "getwalletinfo")
        result = subprocess.run(
          cmd,
          capture_output=True,
          text=True,
          cwd=Path(self.fbd_path_var.get()).parent,
          timeout=15,
        )
        if result.returncode == 0:
          response = json.loads(result.stdout)
          wallet_info = (
            response.get("result", {})
            if isinstance(response, dict)
            else response
          )
          wallet_address = wallet_info.get("address", "N/A")
          self.log(f"  Wallet '{wallet}' address: {wallet_address}")
      except Exception as e:
        self.log(f"  Could not get wallet address: {e}")

      # STEP 3: Scan wallet transactions for auction activity (OPEN, BID)
      self.log(" -> Scanning wallet transactions for auction activity...")
      try:
        cmd, _ = self.get_fbdctl_command("--wallet", wallet, "listtransactions")
        result = subprocess.run(
          cmd,
          capture_output=True,
          text=True,
          cwd=Path(self.fbd_path_var.get()).parent,
          timeout=20,
        )

        if result.returncode == 0:
          response = json.loads(result.stdout)
          txs = (
            response.get("result", [])
            if isinstance(response, dict)
            else response
          )

          auction_tx_types = ["OPEN", "BID", "REVEAL", "REGISTER", "REDEEM"]
          tx_count = 0

          self.log(f"  Scanning {len(txs)} transaction(s)...")

          # Debug: Show first few transaction structures
          if len(txs) > 0 and len(found_names) == 0:
            for i, tx in enumerate(txs[:3]):
              self.log(
                f"  DEBUG: Sample tx {i+1} structure: {json.dumps(tx, indent=2)[:400]}..."
              )

          for tx in txs:
            tx_type = tx.get("type", "")

            # Check if this is a covenant transaction (type="covenant")
            # or if the type directly matches an auction action
            is_covenant = (tx_type == "covenant") or (
              tx_type in auction_tx_types
            )

            if is_covenant:
              # Try multiple methods to extract name
              name = None

              # Method 1: Parse covenants array (e.g., ["BID fb.d"])
              covenants_array = tx.get("covenants", [])
              if covenants_array and isinstance(covenants_array, list):
                for covenant_str in covenants_array:
                  if isinstance(covenant_str, str):
                    # Format: "ACTION name" (e.g., "BID fb.d")
                    parts = covenant_str.split(
                      None, 1
                    ) # Split on first whitespace
                    if len(parts) >= 2:
                      action = parts[0].upper()
                      if action in auction_tx_types:
                        name = parts[1]
                        break

              # Method 2: covenant.items[0]
              if not name:
                covenant = tx.get("covenant", {})
                if covenant and isinstance(covenant, dict):
                  items = covenant.get("items", [])
                  if items and len(items) > 0:
                    # Items might be hex-encoded
                    name = items[0]

              # Method 3: Check 'name' field directly in tx
              if not name:
                name = tx.get("name")

              # Method 4: Check covenant.action or covenant.name
              if not name:
                covenant = tx.get("covenant", {})
                if covenant:
                  name = covenant.get("name") or covenant.get(
                    "action"
                  )

              # Method 5: Try outputs[].covenant.items[]
              if not name:
                outputs = tx.get("outputs", [])
                for output in outputs:
                  if isinstance(output, dict):
                    out_covenant = output.get("covenant", {})
                    if out_covenant:
                      out_items = out_covenant.get("items", [])
                      if out_items and len(out_items) > 0:
                        name = out_items[0]
                        break

              # Decode hex if needed
              if name and isinstance(name, str):
                # Try hex decode if it looks like hex
                if len(name) > 0 and all(
                  c in "0123456789abcdefABCDEF" for c in name
                ):
                  try:
                    decoded = bytes.fromhex(name).decode("utf-8")
                    name = decoded
                  except:
                    pass # Keep original if decode fails

              # Add name to found set if valid
              if name and isinstance(name, str) and len(name) > 0:
                if name not in found_names:
                  found_names.add(name)
                  tx_count += 1
                  self.log(
                    f"   Found name '{name}' from transaction"
                  )

          self.log(
            f"  Found {tx_count} additional name(s) from transactions"
          )
        else:
          self.log(f"  Could not list transactions: {result.stderr}")
      except Exception as e:
        self.log(f"  Could not scan transactions: {e}")
        import traceback

        self.log(f"  Stack trace: {traceback.format_exc()}")

      # STEP 4: Try RPC method to get wallet bids (if index-auctions enabled)
      self.log(" -> Trying RPC method to find wallet auction activity...")
      try:
        # Try to get all wallet bids using RPC
        result = self.rpc_call("getwalletbids", [wallet])
        if result and not result.get("error"):
          wallet_bids = result.get("result", [])
          if wallet_bids:
            for bid_entry in wallet_bids:
              name = bid_entry.get("name")
              if name and name not in found_names:
                found_names.add(name)
                self.log(
                  f"   Found name '{name}' from wallet bids RPC"
                )
            self.log(f"  Found {len(wallet_bids)} bid(s) via RPC")
          else:
            self.log(
              "  No bids found via RPC (this is normal if --index-auctions not enabled)"
            )
        else:
          self.log("  RPC getwalletbids not available (this is normal)")
      except Exception as e:
        self.log(f"  RPC method not available: {e}")

      if not found_names:
        self.log(" [OK]- No names found in wallet")
        return []

      self.log(f" -> Analyzing {len(found_names)} name(s) for auction state...")

      # STEP 3: Check each found name's auction state
      for name in found_names:
        try:
          # Skip if already in automation (unless completed/failed/lost)
          existing_job = self.get_job_by_name(name)
          if existing_job and existing_job.get("status") not in [
            "completed",
            "failed",
            "lost",
          ]:
            self.log(f"  Skipping '{name}' - already in automation")
            continue

          # Get detailed name info from blockchain
          full_info = self.get_name_info_silent(name)
          if not full_info:
            self.log(f"  Skipping '{name}' - could not get name info")
            continue

          state = full_info.get("state", "UNKNOWN")

          # Only interested in auction-related states
          if state not in ["BIDDING", "REVEAL", "CLOSED"]:
            self.log(f"  Skipping '{name}' - state is {state}")
            continue

          # Get wallet's bids for this name
          bids = self.get_wallet_bids_silent(wallet, name)

          auction_data = {
            "name": name,
            "state": state,
            "wallet": wallet,
            "bids": bids,
            "name_info": full_info,
          }

          auctions.append(auction_data)
          self.log(
            f"  [OK] Found auction: {name} (state: {state}, bids: {len(bids)})"
          )

        except Exception as e:
          self.log(f"  Error checking name '{name}': {e}")
          continue

      self.log(f" [OK] Scan complete: {len(auctions)} active auction(s) found")
      return auctions

    except Exception as e:
      self.log(f"Error scanning wallet auctions: {e}")
      return []

  def import_wallet_auctions(self):
    """
    Agentic import of wallet auctions to automation list
    Scans active wallet and intelligently adds auctions based on state
    """
    wallet = self.wallet_name_var.get()
    if not wallet:
      messagebox.showwarning("Warning", "Please set Active Wallet in Wallet tab")
      return

    # Check if node is running, offer to start if not
    if not self.check_node_running():
      response = messagebox.askyesno(
        "Node Not Running",
        "The FBD node is not running.\n\n"
        "Would you like to start the node now?",
        icon="question",
      )
      if response:
        self.start_node()
        # Wait a moment for node to start
        self.log("Waiting for node to start...")
        import time

        time.sleep(3)
        # Check again
        if not self.check_node_running():
          messagebox.showerror(
            "Node Start Failed",
            "Node failed to start. Please start it manually from the Node & Mining tab.",
          )
          return
      else:
        return

    # Scan wallet for auctions
    self.log(f"Scanning wallet '{wallet}' for active auctions...")
    auctions = self.scan_wallet_auctions(wallet)

    if not auctions:
      # Offer three options: manual input, check other wallets, or view log
      response = messagebox.askyesnocancel(
        "No Auctions Found",
        f"No active auctions found in wallet '{wallet}'.\n\n"
        "Check the log (Node & Mining tab) for scan details.\n\n"
        "What would you like to do?\n\n"
        "* Yes = Check ALL wallets\n"
        "* No = Enter name manually\n"
        "* Cancel = View log & close",
        icon="question",
      )

      if response is True: # Yes - check all wallets
        self.scan_all_wallets_dialog()
      elif response is False: # No - manual input
        self.manual_import_name_dialog(wallet)
      else: # Cancel - show log
        # Switch to Node & Mining tab to show log
        self._notebook_select(0)
        self.log("=== SCAN RESULTS ===")
        self.log(f"No auctions found in wallet '{wallet}'.")
        self.log("Check the scan details above.")
        self.log("Possible reasons:")
        self.log(" 1. No auction transactions in wallet history")
        self.log(" 2. Names already in automation list")
        self.log(" 3. Names not in BIDDING/REVEAL/CLOSED state")
        self.log(" 4. Bid might be in a different wallet")
        self.log("===================")
      return

    # Show import dialog with found auctions
    self.show_import_auctions_dialog(auctions)

  def scan_all_wallets_dialog(self):
    """
    Scan all wallets for auctions and show combined results
    """
    if not self.check_node_running():
      return

    self.log("Scanning ALL wallets for auctions...")

    # Get list of all wallets
    try:
      cmd, _ = self.get_fbdctl_command("listwallets")
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(self.fbd_path_var.get()).parent,
        timeout=10,
      )

      if result.returncode != 0:
        messagebox.showerror(
          "Error", f"Could not list wallets:\n{result.stderr}"
        )
        return

      response = json.loads(result.stdout)
      wallets = (
        response.get("result", []) if isinstance(response, dict) else response
      )

      if not wallets:
        messagebox.showinfo("No Wallets", "No wallets found in this node.")
        return

      self.log(f"Found {len(wallets)} wallet(s), scanning each...")

      # Scan each wallet
      all_auctions = []
      for wallet_name in wallets:
        self.log(f"")
        self.log(f"Scanning wallet: {wallet_name}")
        auctions = self.scan_wallet_auctions(wallet_name)
        if auctions:
          all_auctions.extend(auctions)
          self.log(f" Found {len(auctions)} auction(s) in '{wallet_name}'")

      if not all_auctions:
        messagebox.showinfo(
          "No Auctions",
          f"No active auctions found in any of the {len(wallets)} wallet(s).\n\n"
          "Check the log for details about each wallet.",
        )
        self._notebook_select(0) # Switch to log tab
        return

      # Show all found auctions
      self.log(f"")
      self.log(f"Total: Found {len(all_auctions)} auction(s) across all wallets")
      self.show_import_auctions_dialog(all_auctions)

    except Exception as e:
      self.log(f"Error scanning all wallets: {e}")
      messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

  def manual_import_name_dialog(self, wallet):
    """
    Dialog to manually specify a name to import (when scan fails to find it)
    """
    dialog = self._create_toplevel()
    dialog.title("Manual Import - Enter Name")
    dialog.geometry("500x250")
    dialog.transient(self.root)
    dialog.grab_set()

    # Header
    header = ttk.Label(
      dialog,
      text="[*][!] Manually Import Auction",
      font=("Arial", 12, "bold"),
    )
    header.pack(pady=10)

    # Instructions
    instructions = ttk.Label(
      dialog,
      text="Enter the name you want to import.\n"
      "The system will check its state and import if possible.",
      foreground="#666",
    )
    instructions.pack(pady=(0, 10))

    # Name entry
    entry_frame = ttk.Frame(dialog)
    entry_frame.pack(pady=10, padx=20, fill="x")

    ttk.Label(entry_frame, text="Name:", font=("Arial", 10)).pack(
      side="left", padx=(0, 10)
    )
    name_var = tk.StringVar()
    name_entry = self._create_entry(
      entry_frame, textvariable=name_var, width=30, font=("Arial", 10)
    )
    name_entry.pack(side="left", fill="x", expand=True)
    name_entry.focus()

    # Status label
    status_label = ttk.Label(dialog, text="", foreground="blue")
    status_label.pack(pady=5)

    def import_name():
      """Import name."""
      name = name_var.get().strip()
      if not name:
        status_label.configure(text="[!] Please enter a name", foreground="red")
        return

      status_label.configure(text=f"[ ] Checking '{name}'...", foreground="blue")
      dialog.update()

      try:
        # Check if already in automation
        existing_job = self.get_job_by_name(name)
        if existing_job and existing_job.get("status") not in [
          "completed",
          "failed",
          "lost",
        ]:
          messagebox.showwarning(
            "Already in Automation",
            f"'{name}' is already in the automation list.\n\n"
            f"Status: {existing_job.get('status')}",
          )
          dialog.destroy()
          return

        # Get name info
        name_info = self.get_name_info_silent(name)
        if not name_info:
          messagebox.showerror(
            "Name Not Found",
            f"Could not find name '{name}' on the blockchain.\n\n"
            "Please check the spelling and try again.",
          )
          status_label.configure(text="", foreground="blue")
          return

        state = name_info.get("state", "UNKNOWN")

        if state not in ["BIDDING", "REVEAL", "CLOSED"]:
          messagebox.showwarning(
            "Invalid State",
            f"Name '{name}' is in state '{state}'.\n\n"
            "Only BIDDING, REVEAL, or CLOSED auctions can be imported.",
          )
          status_label.configure(text="", foreground="blue")
          return

        # Get bids
        bids = self.get_wallet_bids_silent(wallet, name)

        # Create auction data
        auction_data = {
          "name": name,
          "state": state,
          "wallet": wallet,
          "bids": bids,
          "name_info": name_info,
        }

        # Get recommendation
        recommendation = self._get_import_recommendation(auction_data)

        # Show confirmation
        confirm = messagebox.askyesno(
          "Import Confirmation",
          f"Name: {name}\n"
          f"State: {state}\n"
          f"Bids: {len(bids)}\n\n"
          f"Action: {recommendation['action']}\n"
          f"Details: {recommendation['details']}\n\n"
          "Proceed with import?",
          icon="question",
        )

        if confirm:
          success = self._execute_import(auction_data, recommendation)
          if success:
            messagebox.showinfo(
              "Success", f"Successfully imported '{name}'!"
            )
            self.refresh_jobs_list()
            dialog.destroy()
          else:
            messagebox.showerror(
              "Import Failed",
              f"Failed to import '{name}'. Check logs for details.",
            )
            status_label.configure(text="", foreground="blue")
        else:
          dialog.destroy()

      except Exception as e:
        self.log(f"Error in manual import: {e}")
        messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        status_label.configure(text="", foreground="blue")

    # Buttons
    button_frame = ttk.Frame(dialog)
    button_frame.pack(pady=15)

    self._create_button(button_frame, text="Import", command=import_name).pack(
      side="left", padx=5
    )
    self._create_button(button_frame, text="Cancel", command=dialog.destroy).pack(
      side="left", padx=5
    )

    # Bind Enter key
    name_entry.bind("<Return>", lambda e: import_name())

  def show_import_auctions_dialog(self, auctions):
    """
    Display dialog to select which auctions to import
    Provides agentic recommendations based on state
    """
    dialog = self._create_toplevel()
    dialog.title(f"Import Auctions - Found {len(auctions)}")
    dialog.geometry("900x600")
    dialog.transient(self.root)
    dialog.grab_set()

    # Header
    header = ttk.Label(
      dialog,
      text=f"[OK] Found {len(auctions)} active auction(s) in wallet",
      font=("Arial", 12, "bold"),
    )
    header.pack(pady=10)

    # Instructions
    instructions = ttk.Label(
      dialog,
      text="Select auctions to import. The system will automatically determine the best action.",
      foreground="#666",
    )
    instructions.pack(pady=(0, 10))

    # Auctions list frame
    list_frame = ttk.Frame(dialog)
    list_frame.pack(fill="both", expand=True, padx=10, pady=5)

    # TreeView for auctions
    columns = ("Name", "State", "Bids", "Recommendation", "Details")
    tree = ttk.Treeview(
      list_frame, columns=columns, show="tree headings", selectmode="extended"
    )

    tree.heading("#0", text="Import")
    tree.heading("Name", text="Name")
    tree.heading("State", text="State")
    tree.heading("Bids", text="# Bids")
    tree.heading("Recommendation", text="Action")
    tree.heading("Details", text="Details")

    tree.column("#0", width=60)
    tree.column("Name", width=150)
    tree.column("State", width=80)
    tree.column("Bids", width=60)
    tree.column("Recommendation", width=150)
    tree.column("Details", width=400)

    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Populate tree with auctions and recommendations
    auction_items = {}
    for auction in auctions:
      recommendation = self._get_import_recommendation(auction)

      item_id = tree.insert(
        "",
        "end",
        text="",
        values=(
          auction["name"],
          auction["state"],
          len(auction["bids"]),
          recommendation["action"],
          recommendation["details"],
        ),
      )
      auction_items[item_id] = {
        "auction": auction,
        "recommendation": recommendation,
      }

    # Select all by default
    tree.selection_set(tree.get_children())

    # Buttons
    button_frame = ttk.Frame(dialog)
    button_frame.pack(fill="x", padx=10, pady=10)

    def select_all():
      """Select all."""
      tree.selection_set(tree.get_children())

    def deselect_all():
      """Deselect all."""
      tree.selection_set()

    def import_selected():
      """Import selected."""
      selected = tree.selection()
      if not selected:
        messagebox.showwarning(
          "No Selection", "Please select at least one auction to import"
        )
        return

      imported_count = 0
      failed_count = 0

      for item_id in selected:
        data = auction_items[item_id]
        success = self._execute_import(data["auction"], data["recommendation"])
        if success:
          imported_count += 1
        else:
          failed_count += 1

      # Show results
      result_msg = f"Import complete!\n\nSuccessfully imported: {imported_count}"
      if failed_count > 0:
        result_msg += f"\nFailed: {failed_count}"

      messagebox.showinfo("Import Complete", result_msg)

      # Refresh jobs list
      self.refresh_jobs_list()

      dialog.destroy()

    self._create_button(button_frame, text="Select All", command=select_all).pack(
      side="left", padx=5
    )
    self._create_button(button_frame, text="Deselect All", command=deselect_all).pack(
      side="left", padx=5
    )
    self._create_button(button_frame, text="Import Selected", command=import_selected).pack(
      side="right", padx=5
    )
    self._create_button(button_frame, text="Cancel", command=dialog.destroy).pack(
      side="right", padx=5
    )

  def _get_import_recommendation(self, auction):
    """
    Agentic decision-making: determine best action for auction based on state

    Returns dict with 'action' and 'details' keys
    """
    name = auction["name"]
    state = auction["state"]
    bids = auction["bids"]
    name_info = auction["name_info"]

    # Get current blockchain height
    try:
      current_height = self._get_current_height_silent()
    except:
      current_height = None

    if state == "BIDDING":
      if len(bids) > 0:
        # Already placed bid, add to automation for reveal
        return {
          "action": "Add to automation (REVEAL pending)",
          "details": f"Bid already placed. Will auto-reveal when REVEAL phase starts.",
        }
      else:
        # No bid yet - can't auto-add without bid amount
        return {
          "action": "[!] Cannot import",
          "details": "No bids placed yet. Place bid manually first.",
        }

    elif state == "REVEAL":
      if len(bids) > 0:
        # Need to reveal
        unrevealed = [b for b in bids if not b.get("revealed", False)]
        if unrevealed:
          return {
            "action": "Execute REVEAL immediately",
            "details": f"{len(unrevealed)} bid(s) need revealing. Will reveal now.",
          }
        else:
          # Already revealed, add to automation for register
          return {
            "action": "Add to automation (REGISTER pending)",
            "details": "Bids revealed. Will auto-register if won.",
          }
      else:
        # No bids in REVEAL? Auction lost or error
        return {
          "action": "[!] Skip",
          "details": "No bids found. May have been revealed already or auction lost.",
        }

    elif state == "CLOSED":
      # Check if we won or lost
      owner = name_info.get("owner", {})
      can_register = name_info.get("canRegister", False)

      if owner:
        # Already registered by someone - check if it was us
        # If we have revealed bids, we might need to redeem
        if len(bids) > 0:
          revealed_bids = [b for b in bids if b.get("revealed", False)]
          if revealed_bids:
            return {
              "action": "Execute REDEEM immediately",
              "details": "Auction lost. Will redeem locked funds now.",
            }
        return {
          "action": "[!] Skip",
          "details": "Auction closed. Name already registered.",
        }
      else:
        # Not registered yet - check if we can register
        if can_register:
          return {
            "action": "Execute REGISTER immediately",
            "details": "Auction won! Will register name now.",
          }
        elif len(bids) > 0:
          # We have bids but can't register - we lost
          revealed_bids = [b for b in bids if b.get("revealed", False)]
          if revealed_bids:
            return {
              "action": "Execute REDEEM immediately",
              "details": "Auction lost. Will redeem locked funds now.",
            }
          else:
            return {
              "action": "[!] Skip",
              "details": "Auction closed but bids not revealed. Cannot redeem.",
            }
        else:
          return {
            "action": "[!] Skip",
            "details": "Auction closed. No action needed.",
          }

    return {
      "action": "[!] Unknown state",
      "details": f"State '{state}' not recognized.",
    }

  def _execute_import(self, auction, recommendation):
    """
    Execute the import action for an auction
    Returns True on success, False on failure
    """
    name = auction["name"]
    wallet = auction["wallet"]
    state = auction["state"]
    bids = auction["bids"]
    action = recommendation["action"]

    try:
      # Check if already in automation
      existing_job = self.get_job_by_name(name)
      if existing_job and existing_job.get("status") not in [
        "completed",
        "failed",
        "lost",
      ]:
        self.log(f"[!] Auction '{name}' already in automation, skipping")
        return False

      if "Cannot import" in action or "Skip" in action:
        self.log(f"[!] Skipping '{name}': {recommendation['details']}")
        return False

      if "Execute REVEAL immediately" in action:
        # Execute reveal right now
        self.log(f"[*][*] Executing REVEAL for '{name}'...")
        result = self.execute_send_reveal_silent(name, wallet)
        if result:
          # Add to automation for register phase
          self._add_imported_job(name, wallet, bids, "revealed")
          self.log(f"[OK] REVEAL executed and added to automation: {name}")
          return True
        else:
          self.log(f"[X] REVEAL failed for '{name}'")
          return False

      elif "Execute REGISTER immediately" in action:
        # Execute register right now
        self.log(f"[*][!] Executing REGISTER for '{name}'...")
        result = self.execute_send_register_silent(name, wallet)
        if result and result.get("success"):
          self.log(
            f"[OK] REGISTER executed: {name} (TXID: {result.get('txid', 'N/A')[:12]}...)"
          )
          return True
        else:
          error = (
            result.get("error", "Unknown error")
            if result
            else "No response"
          )
          self.log(f"[X] REGISTER failed for '{name}': {error}")
          return False

      elif "Execute REDEEM immediately" in action:
        # Execute redeem right now
        self.log(f"[*]o Executing REDEEM for '{name}'...")
        result = self.execute_send_redeem_silent(name, wallet)
        if result and result.get("success"):
          self.log(
            f"[OK] REDEEM executed: {name} (TXID: {result.get('txid', 'N/A')[:12]}...)"
          )
          return True
        else:
          error = (
            result.get("error", "Unknown error")
            if result
            else "No response"
          )
          self.log(f"[X] REDEEM failed for '{name}': {error}")
          return False

      elif "Add to automation" in action:
        # Add to automation jobs
        if "REVEAL pending" in action:
          status = "bid_placed"
        elif "REGISTER pending" in action:
          status = "revealed"
        else:
          status = "opened"

        self._add_imported_job(name, wallet, bids, status)
        self.log(f"[OK] Added to automation: {name} (status: {status})")
        return True

      return False

    except Exception as e:
      self.log(f"[X] Error importing '{name}': {e}")
      return False

  def _add_imported_job(self, name, wallet, bids, status):
    """
    Add imported auction to automation jobs
    Extracts bid/lockup amounts from existing bids
    """
    # Preserve historical bid and lockup using the strongest values from wallet bids.
    bid_amount = 0.0
    lockup_amount = 0.0

    if bids and len(bids) > 0:
      for bid in bids:
        value = self._to_float(bid.get("value", 0))
        lockup = self._to_float(bid.get("lockup", 0))

        # Some RPC shapes report atoms; convert only when value is atom-like.
        if value > 1000000:
          value = value / 1000000
        if lockup > 1000000:
          lockup = lockup / 1000000

        if value > bid_amount:
          bid_amount = value
        if lockup > lockup_amount:
          lockup_amount = lockup

    # Create job
    job_id = str(uuid.uuid4())

    jobs_data = self.load_auction_jobs()

    new_job = {
      "id": job_id,
      "name": name,
      "wallet": wallet,
      "bid_amount": bid_amount,
      "original_bid_amount": bid_amount,
      "lockup_amount": lockup_amount,
      "status": status,
      "auto_enabled": True,
      "created": datetime.now().isoformat(),
      "created_at": datetime.now().isoformat(),
      "updated_at": datetime.now().isoformat(),
      "txids": {"open": None, "bid": None, "reveal": [], "register": None},
      "block_heights": {
        "opened_at": None,
        "bid_placed_at": None,
        "revealed_at": None,
        "registered_at": None,
      },
      "error_log": [],
      "retry_count": 0,
      "imported": True, # Flag to indicate this was imported
    }

    jobs_data["jobs"].append(new_job)
    self.save_auction_jobs(jobs_data)

    self.log(f"[*][YEN] Imported job: {name} (ID: {job_id[:8]}..., Status: {status})")

  # ========================================================================
  # AUCTION AUTOMATION - STAGE 0: FOUNDATION (CRUD METHODS)
  # ========================================================================

  def load_auction_jobs(self):
    """Load auction jobs from JSON file"""
    try:
      if self.auction_jobs_file.exists():
        with open(self.auction_jobs_file, "r") as f:
          data = json.load(f)
          # Validate structure
          if "jobs" not in data:
            data["jobs"] = []
          if "version" not in data:
            data["version"] = "1.0"
          return data
      else:
        return {"version": "1.0", "jobs": []}
    except Exception as e:
      self.log(f"Error loading auction jobs: {e}")
      return {"version": "1.0", "jobs": []}

  def save_auction_jobs(self, jobs_data):
    """Save auction jobs to JSON file"""
    try:
      with open(self.auction_jobs_file, "w") as f:
        json.dump(jobs_data, f, indent=2)
      return True
    except Exception as e:
      self.log(f"Error saving auction jobs: {e}")
      return False

  def add_auction_job(
    self,
    name,
    wallet,
    bid_amount,
    lockup_amount,
    auto_enabled=True,
    auto_bid_enabled=None,
  ):
    """
    Create a new auction automation job

    Args:
      name: Name to auction
      wallet: Wallet to use
      bid_amount: Bid amount in FBC
      lockup_amount: Lockup amount in FBC
      auto_enabled: Whether automation is enabled
      auto_bid_enabled: Whether BID should be placed automatically when BIDDING starts

    Returns:
      str: Job ID if successful, None otherwise
    """
    try:
      jobs_data = self.load_auction_jobs()

      if auto_bid_enabled is None:
        auto_bid_enabled = auto_enabled

      # Generate unique job ID
      job_id = str(uuid.uuid4())

      # Create job structure
      new_job = {
        "id": job_id,
        "name": name,
        "wallet": wallet,
        "bid_amount": str(bid_amount),
        "original_bid_amount": str(bid_amount),
        "lockup_amount": str(lockup_amount),
        "status": "pending_open", # pending_open, opened, bid_placed, revealed, registered, lost, failed
        "auto_enabled": auto_enabled,
        "auto_bid_enabled": auto_bid_enabled,
        "created": datetime.now().isoformat(),
        "created_at": int(time.time()),
        "txids": {"open": None, "bid": None, "reveal": [], "register": None},
        "block_heights": {
          "opened_at": None,
          "bid_placed_at": None,
          "revealed_at": None,
          "registered_at": None,
        },
        "error_log": [],
        "retry_count": 0,
      }

      # Add to jobs list
      jobs_data["jobs"].append(new_job)

      # Save
      if self.save_auction_jobs(jobs_data):
        self.log(f"[OK] Created auction job for '{name}' (ID: {job_id[:8]}...)")
        return job_id
      else:
        return None

    except Exception as e:
      self.log(f"Error adding auction job: {e}")
      return None

  def update_job_status(self, job_id, new_status, **kwargs):
    """
    Update job status and related fields

    Args:
      job_id: Job ID to update
      new_status: New status value
      **kwargs: Additional fields to update (txid, block_height, error, message, etc.)
    """
    try:
      jobs_data = self.load_auction_jobs()

      # Find job
      job = None
      for j in jobs_data["jobs"]:
        if j["id"] == job_id:
          job = j
          break

      if not job:
        self.log(f"[!] Job not found: {job_id[:8]}...")
        return False

      # Imported/older jobs can miss nested fields used below.
      self._ensure_job_schema(job)

      # Update status
      old_status = job["status"]
      job["status"] = new_status

      # Update optional fields
      if "txid" in kwargs:
        # Determine which txid field to update based on old status
        if old_status == "pending_open":
          job["txids"]["open"] = kwargs["txid"]
        elif old_status == "opened":
          job["txids"]["bid"] = kwargs["txid"]
        elif old_status == "bid_placed":
          # Reveal can have multiple txids
          if isinstance(kwargs["txid"], list):
            job["txids"]["reveal"] = kwargs["txid"]
          else:
            job["txids"]["reveal"].append(kwargs["txid"])
        elif old_status == "revealed":
          job["txids"]["register"] = kwargs["txid"]

      if "block_height" in kwargs:
        # Update block height based on new status
        if new_status == "opened":
          job["block_heights"]["opened_at"] = kwargs["block_height"]
        elif new_status == "bid_placed":
          job["block_heights"]["bid_placed_at"] = kwargs["block_height"]
        elif new_status == "revealed":
          job["block_heights"]["revealed_at"] = kwargs["block_height"]
        elif new_status == "registered":
          job["block_heights"]["registered_at"] = kwargs["block_height"]

      if "error" in kwargs:
        error_entry = {"timestamp": int(time.time()), "error": kwargs["error"]}
        job["error_log"].append(error_entry)

      if "message" in kwargs:
        # Add informational message to error log (not an error, just info)
        info_entry = {"timestamp": int(time.time()), "info": kwargs["message"]}
        job["error_log"].append(info_entry)

      # Save updated jobs
      if self.save_auction_jobs(jobs_data):
        self.log(
          f"[OK] Updated job {job_id[:8]}... status: {old_status} -> {new_status}"
        )
        return True
      else:
        return False

    except Exception as e:
      self.log(f"Error updating job status: {e}")
      return False

  def get_job_by_name(self, name):
    """
    Find an active job by name

    Returns:
      dict: Job data if found, None otherwise
    """
    try:
      jobs_data = self.load_auction_jobs()

      # Look for non-terminal status jobs with this name
      for job in jobs_data["jobs"]:
        if job["name"] == name and job["status"] not in [
          "registered",
          "lost",
          "failed",
        ]:
          return job

      return None

    except Exception as e:
      self.log(f"Error getting job by name: {e}")
      return None

  def delete_job(self, job_id):
    """
    Delete a job from the jobs list

    Args:
      job_id: Job ID to delete

    Returns:
      bool: True if successful, False otherwise
    """
    try:
      jobs_data = self.load_auction_jobs()

      # Find and remove job
      initial_count = len(jobs_data["jobs"])
      jobs_data["jobs"] = [j for j in jobs_data["jobs"] if j["id"] != job_id]

      if len(jobs_data["jobs"]) < initial_count:
        if self.save_auction_jobs(jobs_data):
          self.log(f"[OK] Deleted job {job_id[:8]}...")
          return True
      else:
        self.log(f"[!] Job not found for deletion: {job_id[:8]}...")
        return False

    except Exception as e:
      self.log(f"Error deleting job: {e}")
      return False


def main():
  """Main."""
  toolkit_mode = _resolve_startup_ui_toolkit()
  if toolkit_mode == UI_TOOLKIT_CUSTOMTK and ctk is not None:
    root = ctk.CTk()
  else:
    root = tk.Tk()
    if toolkit_mode == UI_TOOLKIT_CUSTOMTK and ctk is None:
      print(
        "[!] CustomTkinter mode requested, but customtkinter is not installed. "
        "Falling back to Legacy ttk."
      )

  root._ui_toolkit_mode = toolkit_mode if toolkit_mode in SUPPORTED_UI_TOOLKITS else UI_TOOLKIT_TTK
  app = FBDManager(root)
  root.protocol("WM_DELETE_WINDOW", app.on_closing)
  root.mainloop()


if __name__ == "__main__":
  main()








