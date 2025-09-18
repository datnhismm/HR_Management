#!/usr/bin/env python3
"""Verify admin (moved)."""
try:
    from database import database as db
except Exception:
    from hr_management_app.src.database import database as db

email = "datnhism@gmail.com"
password = "1234@Bc"
print("Verifying", email)
ok = db.verify_user(email, password)
print("authentication_ok =", ok)
if not ok:
    row = db.get_user_by_email(email)
    print("stored_row=", row)
