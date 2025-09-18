#!/usr/bin/env python3
"""Delete user data (moved)."""
import csv
from pathlib import Path

from database import database as db

EMAIL = "datnhism@gmail.com"
BACKUP_DIR = Path("backup") / EMAIL.replace("@", "_at_")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def dump_query_to_csv(conn, query, params, out_path):
    c = conn.cursor()
    c.execute(query, params)
    cols = [d[0] for d in c.description] if c.description else []
    rows = c.fetchall()
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if cols:
            writer.writerow(cols)
        for r in rows:
            writer.writerow(r)
    return len(rows)


def main():
    print("Searching for user:", EMAIL)
    user = db.get_user_by_email(EMAIL)
    if not user:
        print("No user found for email:", EMAIL)
        return
    user_id = user[0]
    print("Found user id:", user_id)
    with db._conn() as conn:
        print("Backing up user row...")
        dump_query_to_csv(
            conn,
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
            BACKUP_DIR / "users.csv",
        )
        print("Backing up employees...")
        dump_query_to_csv(
            conn,
            "SELECT * FROM employees WHERE user_id = ?",
            (user_id,),
            BACKUP_DIR / "employees.csv",
        )
        c = conn.cursor()
        c.execute("SELECT id FROM employees WHERE user_id = ?", (user_id,))
        emp_rows = c.fetchall()
        emp_ids = [r[0] for r in emp_rows]
        for eid in emp_ids:
            print("Backing up attendance for employee", eid)
            dump_query_to_csv(
                conn,
                "SELECT * FROM attendance WHERE employee_id = ?",
                (eid,),
                BACKUP_DIR / f"attendance_emp_{eid}.csv",
            )
            print("Backing up contracts for employee", eid)
            dump_query_to_csv(
                conn,
                "SELECT * FROM contracts WHERE employee_id = ?",
                (eid,),
                BACKUP_DIR / f"contracts_emp_{eid}.csv",
            )
        print("Backing up role_audit...")
        dump_query_to_csv(
            conn,
            "SELECT * FROM role_audit WHERE changed_user_id = ? OR actor_user_id = ?",
            (user_id, user_id),
            BACKUP_DIR / "role_audit.csv",
        )
        print("Backing up imputation_audit...")
        dump_query_to_csv(
            conn,
            "SELECT * FROM imputation_audit WHERE actor_user_id = ?",
            (user_id,),
            BACKUP_DIR / "imputation_audit.csv",
        )
        print("Deleting attendance...")
        for eid in emp_ids:
            c.execute("DELETE FROM attendance WHERE employee_id = ?", (eid,))
        print("Deleting contracts...")
        for eid in emp_ids:
            c.execute("DELETE FROM contracts WHERE employee_id = ?", (eid,))
        print("Deleting role_audit entries...")
        c.execute(
            "DELETE FROM role_audit WHERE changed_user_id = ? OR actor_user_id = ?",
            (user_id, user_id),
        )
        print("Deleting imputation_audit entries...")
        c.execute("DELETE FROM imputation_audit WHERE actor_user_id = ?", (user_id,))
        print("Deleting employee rows...")
        c.execute("DELETE FROM employees WHERE user_id = ?", (user_id,))
        print("Deleting user row...")
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    print("Deletion complete. Backups written to:", BACKUP_DIR)


if __name__ == "__main__":
    main()
