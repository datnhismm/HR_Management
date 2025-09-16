import os
import sys
import time
from datetime import datetime

# ensure src/ is on sys.path for pytest collection
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hr_management_app.src.database.database import (
    create_employee,
    create_user,
    get_employee_by_user,
    get_month_work_seconds,
    get_user_by_email,
    record_check_in,
    record_check_out,
)


def test_create_user_and_employee():
    email = f"unit_test_{int(time.time())}@example.com"
    uid = create_user(email, "unitpass", role="engineer")
    assert isinstance(uid, int)
    user_row = get_user_by_email(email)
    assert user_row and user_row[0] == uid

    eid = create_employee(
        uid, "Unit Tester", None, "Dev", "engineer", 2025, None, "contract"
    )
    assert isinstance(eid, int)
    emp_row = get_employee_by_user(uid)
    assert emp_row and emp_row[0] == eid


def test_checkin_checkout_and_month_seconds():
    email = f"unit_test_ci_{int(time.time())}@example.com"
    uid = create_user(email, "unitpass", role="engineer")
    eid = create_employee(
        uid, "Unit Tester CI", None, "Dev", "engineer", 2025, None, "contract"
    )

    ci = record_check_in(eid)
    assert ci is not None
    # small sleep to ensure delta
    import time as _t

    _t.sleep(1)
    co = record_check_out(eid)
    assert co is not None

    now = datetime.now()
    secs = get_month_work_seconds(eid, now.year, now.month)
    assert isinstance(secs, int) and secs >= 0


def test_contract_requires_existing_employee():
    # attempt to save a contract for a non-existent employee -> should raise ValueError
    from contracts.models import Contract

    bogus = 9999999
    c = Contract(
        id=1,
        employee_id=bogus,
        start_date="2025-01-01",
        end_date="2025-12-31",
        terms="T",
    )
    try:
        c.save()
        raised = False
    except ValueError:
        raised = True
    assert raised, "Expected ValueError when saving contract for non-existent employee"


def test_create_employee_invalid_year():
    email = f"unit_test_year_{int(time.time())}@example.com"
    uid = create_user(email, "unitpass", role="engineer")
    # year too small
    try:
        create_employee(
            uid, "Bad Year", None, "Job", "engineer", 1900, None, "contract"
        )
        raised = False
    except ValueError:
        raised = True
    assert raised
