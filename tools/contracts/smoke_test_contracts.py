"""Smoke test for contract subsets."""

from hr_management_app.src.contracts.models import Contract, contract_progress
from hr_management_app.src.database import database as db
from hr_management_app.src.contracts.views import view_contract
from hr_management_app.src.database.database import (
    add_contract_to_db,
    create_contract_subset,
    update_subset_status,
)

# defensive: guard when no admin exists
admin = db.get_admin_user()
if not admin:
    raise RuntimeError("No admin user found; create one before running this smoke test")
emp = db.get_employee_by_user(admin[0])
if not emp:
    raise RuntimeError(
        "No employee record for admin; create one before running this smoke test"
    )
print("admin", admin)
print("employee", emp)
# create contract object
c = Contract(
    id=9998,
    employee_id=emp[0],
    start_date="2025-09-01",
    end_date="2026-09-01",
    terms="Test contract",
)
add_contract_to_db(c)
# add subsets
s1 = create_contract_subset(
    9998, "Phase 1 planning", "Planning tasks", status="to do", order_index=1
)
s2 = create_contract_subset(
    9998, "Phase 1 execution", "Exec tasks", status="starting", order_index=2
)
s3 = create_contract_subset(
    9998, "Phase 1 audit", "Audit tasks", status="starting", order_index=3
)
print("created subsets", s1, s2, s3)
# update s2 to in progress then to final settlement
update_subset_status(s2, "in progress", actor_user_id=admin[0])
update_subset_status(s2, "final settlement of phase 1", actor_user_id=admin[0])
# print progress
print(contract_progress(9998))

view_contract(c)
