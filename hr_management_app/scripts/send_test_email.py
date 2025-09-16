"""Utility to send a test email using the app's send_email helper.

Usage (PowerShell):
  $env:SMTP_SERVER='smtp.example.com'; $env:SMTP_PORT='587'; $env:SMTP_USER='you@example.com'; $env:SMTP_PASSWORD='app-pass'; $env:FROM_EMAIL='you@example.com'
    python ./scripts/send_test_email.py datnhism@gmail.com

This script adds the package `src` to sys.path so it can be executed from the repo root.
It logs full exceptions to the log and prints a friendly message to the console.
"""

import logging
import os
import sys

# Ensure `src` is on sys.path so imports like `from database.database import send_email`
# work when running the script from the repository root.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from hr_management_app.src.database.database import send_email
except Exception:
    print(
        "Failed to import application modules. Make sure you run this from the repository root and that src/ is present."
    )
    raise

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/send_test_email.py <target-email>")
        return 2
    to_addr = sys.argv[1]
    subject = "HR Management - test email"
    body = "This is a test email sent from the HR Management app. If you received this, SMTP is configured."
    try:
        send_email(to_addr, subject, body)
        print(
            f"Sent test email to {to_addr} (or skipped because SMTP not configured). Check the inbox."
        )
        return 0
    except Exception:
        logger.exception("Test email send failed")
        print(
            "Failed to send email. See log for details. Common causes: wrong SMTP settings, blocked port, auth failure."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
