#!/usr/bin/env python3
import sqlite3

p = "hr_management_app/src/database/hr_management.db"
con = sqlite3.connect(p)
cur = con.cursor()
cur.execute("SELECT COUNT(*) FROM users")
cnt = cur.fetchone()[0]
cur.execute("SELECT id,email,role FROM users WHERE lower(role) LIKE '%admin%'")
admins = cur.fetchall()
print(f"users_count={cnt}")
print(f"admin_like_count={len(admins)}")
for r in admins:
    print(r)
con.close()
