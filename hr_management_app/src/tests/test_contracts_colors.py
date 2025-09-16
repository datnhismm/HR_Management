import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from contracts.models import Contract
from database import database as db
from hr_management_app.src.database.database import (
    STATUS_COLORS,
    add_contract_to_db,
    create_contract_subset,
    get_subset_status_history,
    update_subset_status,
)


def test_status_colors_and_history(tmp_path):
    cid = 9999
    # ensure admin exists
    admin = db.get_admin_user()
    if not admin:
        admin_id = db.create_user(
            "test_auto_admin2@example.com", "pw_admin", role="admin"
        )
        admin = db.get_user_by_id(admin_id)
    # safe guard: admin may still be None if creation failed
    assert admin is not None
    emp = db.get_employee_by_user(admin[0])
    if not emp:
        current_year = __import__("datetime").datetime.now().year
        db.create_employee(
            user_id=admin[0],
            name="Auto Admin 2",
            dob="1970-01-01",
            job_title="Admin",
            role="admin",
            year_start=current_year,
            profile_pic=None,
            contract_type="full-time",
        )
        emp = db.get_employee_by_user(admin[0])

    assert emp is not None
    c = Contract(
        id=cid,
        employee_id=emp[0],
        start_date="2025-09-01",
        end_date="2026-09-01",
        terms="test",
    )
    add_contract_to_db(c)
    s = create_contract_subset(cid, "ColorTest", status="to do", order_index=1)

    # validate STATUS_CHOICES colors
    for status, color in STATUS_COLORS.items():
        assert isinstance(status, str)
        assert isinstance(color, str)
        assert color.startswith("#")

    # update status and check history
    admin_id = admin[0]
    update_subset_status(s, "in progress", actor_user_id=admin_id)
    update_subset_status(s, "final settlement of phase 1", actor_user_id=admin_id)

    history = get_subset_status_history(s)
    assert len(history) >= 2
    # history tuple: (id, subset_id, old_status, new_status, actor_user_id, changed_at)
    assert history[-1][3] == "final settlement of phase 1"
