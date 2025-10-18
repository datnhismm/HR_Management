#!/usr/bin/env python3
"""Update admin (moved)."""
import datetime
import hashlib
import secrets
import shutil
import sqlite3
from pathlib import Path

DB_PATH = Path("hr_management_app/src/database/hr_management.db")
if not DB_PATH.exists():
    raise SystemExit("DB not found at: " + str(DB_PATH))

# Backup DB
ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_dir = Path("hr_management_app/src/db_backups") / f"pre_update_admin_{ts}"
backup_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(DB_PATH, backup_dir / "hr_management.db")
print("DB backed up to", backup_dir)

TARGET_EMAIL = "datnhism@gmail.com"
TARGET_PWD = "1234@Bc"

con = sqlite3.connect(str(DB_PATH))
cur = con.cursor()
cur.execute("SELECT id,email FROM users WHERE id=?", (2118,))
row = cur.fetchone()
if not row:
    cur.execute("SELECT id,email FROM users WHERE lower(email)=?", ("y",))
    row = cur.fetchone()
if not row:
    print("No matching user (id 2118 or email y) found. Aborting.")
    con.close()
    raise SystemExit(1)
user_id, current_email = row[0], row[1]
print("Found user id", user_id, "current email", current_email)

salt = secrets.token_hex(16)
hash_val = hashlib.sha256((salt + TARGET_PWD).encode("utf-8")).hexdigest()
cur.execute(
    "UPDATE users SET email=?, password_hash=?, salt=? WHERE id=?",
    (TARGET_EMAIL, hash_val, salt, user_id),
)
con.commit()
print("Updated user", user_id, "-> email:", TARGET_EMAIL)
cur.execute("SELECT id FROM employees WHERE user_id=?", (user_id,))
emps = cur.fetchall()
print("Employee rows linked:", len(emps))
con.close()
print("Done.")
