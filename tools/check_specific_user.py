#!/usr/bin/env python3
import sqlite3

p = "hr_management_app/src/database/hr_management.db"
con = sqlite3.connect(p)
cur = con.cursor()
cur.execute(
    "SELECT id,email,role FROM users WHERE id=? OR email=? OR email=?",
    (2118, "Y", "datnhism@gmail.com"),
)
rows = cur.fetchall()
print("matches=", len(rows))
for r in rows:
    print(r)
con.close()
