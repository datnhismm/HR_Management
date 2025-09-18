"""Create an employee row for the current admin user (non-interactive)."""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "hr_management_app", "src")
)
from datetime import datetime

from database import database as db


def main():
    admin = db.get_admin_user()
    if not admin:
        print("no admin found")
        return 2
    admin_id = admin[0]
    print("admin id:", admin_id, "email:", admin[1])
    emp = db.get_employee_by_user(admin_id)
    if emp:
        print("employee already exists:", emp)
        return 0
    current_year = datetime.now().year
    try:
        eid = db.create_employee(
            user_id=admin_id,
            name="Admin User",
            dob="1970-01-01",
            job_title="Administrator",
            role="admin",
            year_start=current_year,
            profile_pic=None,
            contract_type="full-time",
        )
        print("created employee id", eid)
        print("row:", db.get_employee_by_user(admin_id))
        return 0
    except Exception as e:
        print("failed to create employee", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
