"""Quick smoke test: instantiate DB helpers and run simple operations without GUI or network.

This script will:
- import database helpers
- create a temporary user and employee (using a random email)
- record a check-in and check-out
- calculate month work seconds for current month
- print results

Run inside the project's venv Python as provided by the environment.
"""
import os
import time
from datetime import datetime
from database.database import (
    create_user,
    create_employee,
    record_check_in,
    record_check_out,
    get_month_work_seconds,
    get_employee_by_user,
    get_user_by_email,
)

# Use a unique email to avoid conflicts
email = f"smoke_test_{int(time.time())}@example.com"
try:
    uid = create_user(email, "testpass123", role="engineer")
    print("create_user ->", uid)
    eid = create_employee(uid, "Smoke Tester", None, "Tester", "engineer", 2025, None, "contract")
    print("create_employee ->", eid)
    user_row = get_user_by_email(email)
    emp_row = get_employee_by_user(uid)
    print("user_row:", user_row)
    print("emp_row:", emp_row)

    # record check-in then check-out
    ci = record_check_in(eid)
    print("checkin:", ci)
    co = record_check_out(eid)
    print("checkout:", co)

    # month work seconds for current month
    now = datetime.now()
    seconds = get_month_work_seconds(eid, now.year, now.month)
    print("month seconds:", seconds)

    print("SMOKE TEST SUCCESS")
except Exception as e:
    print("SMOKE TEST FAILED:", e)
    raise
