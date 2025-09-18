"""
Non-interactive admin fix script.
Backs up the DB, demotes other admins, creates/updates target admin, and verifies login.
"""

import os
import shutil
import sys
import time
import traceback

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "hr_management_app", "src")
)
try:
    from database import database as db
except Exception:
    # fallback if package path differs
    sys.path.insert(0, os.path.join("hr_management_app", "src"))
    from database import database as db

TARGET_EMAIL = "datnhism@gmail.com"
TARGET_PW = "1234@Bc"


def resolve_db_path():
    pkg_dir = os.path.dirname(db.__file__)
    name = os.getenv("HR_MANAGEMENT_TEST_DB", "hr_management.db")
    return name if os.path.isabs(name) else os.path.join(pkg_dir, name)


def backup_db(path):
    try:
        bak = path + ".bak." + time.strftime("%Y%m%d%H%M%S")
        shutil.copy2(path, bak)
        print("backup: OK ->", bak)
        return True
    except Exception as e:
        print("backup: FAILED", e)
        traceback.print_exc()
        return False


def main():
    dbpath = resolve_db_path()
    print("DB path=", dbpath)
    if not os.path.exists(dbpath):
        print("ERROR: DB file not found:", dbpath)
        return 2

    backup_db(dbpath)

    users = db.get_all_users()
    other_admins = [
        u for u in users if u[2] == "admin" and u[1].lower() != TARGET_EMAIL.lower()
    ]
    print("other admins:", other_admins)
    for a in other_admins:
        try:
            db.update_user_role(a[0], "engineer")
            print("demoted", a[1])
        except Exception as e:
            print("failed to demote", a, e)

    # Remove existing target if present (to ensure clean password set)
    u = db.get_user_by_email(TARGET_EMAIL)
    if u:
        print("target exists, deleting", u)
        try:
            db.delete_user(u[0])
            print("deleted existing target")
        except Exception as e:
            print("failed to delete existing target", e)

    # Create target admin
    try:
        nid = db.create_user(TARGET_EMAIL, TARGET_PW, "admin")
        print("created user id", nid)
    except Exception as e:
        print("create failed", e)
        traceback.print_exc()
        # try to update existing user instead
        u2 = db.get_user_by_email(TARGET_EMAIL)
        if u2:
            try:
                db.update_user_role(u2[0], "admin")
                print("updated existing user role to admin", u2[0])
            except Exception as e2:
                print("failed to promote existing user", e2)

    verified = db.verify_user(TARGET_EMAIL, TARGET_PW)
    print("verify:", verified)
    print("user row:", db.get_user_by_email(TARGET_EMAIL))
    return 0


if __name__ == "__main__":
    sys.exit(main())
