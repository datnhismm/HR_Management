#!/usr/bin/env python3
"""Set admin password using project's PBKDF2 hashing so verify_user succeeds.

Run: set the PYTHONPATH to 'hr_management_app/src' and run the script with the project's Python.
For example (PowerShell):
    $env:PYTHONPATH='hr_management_app/src'; ./.venv/Scripts/python.exe tools/fix_admin_password.py
"""
import datetime
import os
import shutil

try:
    from database import database as db
except Exception:
    from hr_management_app.src.database import database as db

DB = (
    os.path.join(os.path.dirname(os.path.dirname(db.__file__)), "database.db")
    if hasattr(db, "__file__")
    else "hr_management_app/src/database/hr_management.db"
)
# backup
ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join("hr_management_app", "src", "db_backups", f"pre_fix_pwd_{ts}")
os.makedirs(backup_dir, exist_ok=True)
shutil.copy2(
    os.path.join(os.path.dirname(db.__file__), "hr_management.db"),
    os.path.join(backup_dir, "hr_management.db"),
)
print("DB backed up to", backup_dir)

EMAIL = "datnhism@gmail.com"
NEW_PWD = "1234@Bc"

row = db.get_user_by_email(EMAIL)
if not row:
    raise SystemExit("User not found: " + EMAIL)
user_id = row[0]
# generate salt and hash using project's function
salt = os.urandom(16)
pwd_hash = db._hash_password(NEW_PWD, salt)
# store hex salt
with db._conn() as conn:
    c = conn.cursor()
    c.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
        (pwd_hash, salt.hex(), user_id),
    )
    conn.commit()
print("Password updated for user", user_id)
