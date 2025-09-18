#!/usr/bin/env python3
"""Wipe DB data (moved)."""
import sqlite3
from pathlib import Path

DB_PATH = Path("hr_management_app/src/database/hr_management.db")
if not DB_PATH.exists():
    raise SystemExit("DB not found at: " + str(DB_PATH))

TABLE_ORDER = [
    "attendance",
    "contracts",
    "imputation_audit",
    "role_audit",
    "employees",
    "users",
    "some_other_table",
]


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    deleted = {}
    try:
        for t in TABLE_ORDER:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)
            )
            if not cur.fetchone():
                continue
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cur.fetchone()[0]
            cur.execute(f"DELETE FROM {t}")
            deleted[t] = cnt
        conn.commit()
    finally:
        conn.close()
    print("Deleted rows:")
    for t, c in deleted.items():
        print(f" - {t}: {c}")


if __name__ == "__main__":
    main()
