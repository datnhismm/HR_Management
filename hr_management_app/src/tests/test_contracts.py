import os
import tempfile

# ensure tests use an isolated DB file
os.environ["HR_MANAGEMENT_TEST_DB"] = os.path.join(
    tempfile.gettempdir(), "hr_mgmt_test.db"
)

from hr_management_app.src.contracts.models import Contract, contract_progress
from hr_management_app.src.database import database as db
from hr_management_app.src.database.database import (
    add_contract_to_db,
    create_contract_subset,
    update_subset_status,
)


def setup_module():
    # ensure fresh test DB for this module
    try:
        path = os.environ.get("HR_MANAGEMENT_TEST_DB")
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    db.init_db()


def test_contract_progress_and_permissions(tmp_path):
    # create a fresh contract id using timestamp to avoid collisions
    cid = 8888
    admin = db.get_admin_user()
    # ensure an admin exists for the test
    if not admin:
        admin_id = db.create_user(
            "test_auto_admin@example.com", "pw_admin", role="admin"
        )
        admin = db.get_user_by_id(admin_id)
    assert admin is not None
    admin_id = admin[0]
    emp = db.get_employee_by_user(admin_id)
    if not emp:
        # create a minimal employee record for the admin
        year_now = __import__("datetime").datetime.now().year
        db.create_employee(
            user_id=admin[0],
            name="Auto Admin",
            dob="1970-01-01",
            job_title="Admin",
            role="admin",
            year_start=year_now,
            profile_pic=None,
            contract_type="full-time",
        )
        emp = db.get_employee_by_user(admin_id)
    assert emp is not None
    # create contract
    c = Contract(
        id=cid,
        employee_id=emp[0],
        start_date="2025-09-01",
        end_date="2026-09-01",
        terms="test",
    )
    add_contract_to_db(c)
    # add subsets
    s1 = create_contract_subset(cid, "S1", status="to do", order_index=1)
    _s2 = create_contract_subset(cid, "S2", status="starting", order_index=2)
    # progress should be 0
    p = contract_progress(cid)
    assert p["total"] == 2
    assert p["completed"] == 0

    # create an engineer and accountant
    eng_id = db.create_user("test_eng@example.com", "pw", role="engineer")
    acc_id = db.create_user("test_acc@example.com", "pw", role="accountant")

    # engineer cannot update
    try:
        update_subset_status(s1, "in progress", actor_user_id=eng_id)
        assert False, "Engineer should not be allowed to update subset status"
    except PermissionError:
        pass

    # accountant can update
    update_subset_status(s1, "in progress", actor_user_id=acc_id)
    # mark as final settlement
    update_subset_status(s1, "final settlement of phase 1", actor_user_id=acc_id)
    p2 = contract_progress(cid)
    assert p2["completed"] == 1
