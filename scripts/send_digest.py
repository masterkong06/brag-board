#!/usr/bin/env python3
"""
Standalone script for the weekly digest cron job.
Run via crontab:
  0 9 * * 0  cd /var/www/brag-board && ./venv/bin/python scripts/send_digest.py

Environment variables required (set in crontab or systemd):
  SMTP_USER, SMTP_PASSWORD, SECRET_KEY
"""
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mailer

if __name__ == "__main__":
    print("Sending weekly digest…")
    ok = mailer.send_digest()
    sys.exit(0 if ok else 1)
