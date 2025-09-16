"""Permission smoke test: ensure only allowed roles can update subset status."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hr_management_app', 'src'))
try:
    from hr_management_app.src.database import database as db
    from hr_management_app.src.database.database import create_contract_subset, update_subset_status, add_contract_to_db
    from hr_management_app.src.contracts.models import Contract
except Exception:
    # fallback to ensure script can run in different execution contexts
    from hr_management_app.src.database import database as db  # type: ignore
    from hr_management_app.src.database.database import create_contract_subset, update_subset_status, add_contract_to_db  # type: ignore
    from hr_management_app.src.contracts.models import Contract  # type: ignore

admin = db.get_admin_user()
if not admin:
    raise RuntimeError('No admin user present; create one before running this permission_test')
# create a contract and subset
c = Contract(id=9997, employee_id=admin[0], start_date='2025-09-01', end_date='2026-09-01', terms='perm test')
add_contract_to_db(c)
subs_id = create_contract_subset(9997, 'Perm Test', 'Testing permissions', status='to do')
print('subset id', subs_id)
# create an engineer user and accountant user
eng_id = db.create_user('eng_perm_test@example.com', 'password', role='engineer')
acc_id = db.create_user('acc_perm_test@example.com', 'password', role='accountant')
print('eng id', eng_id, 'acc id', acc_id)
# engineer should fail
try:
    update_subset_status(subs_id, 'in progress', actor_user_id=eng_id)
    print('ENGINEER: unexpectedly allowed')
except PermissionError as e:
    print('ENGINEER: blocked as expected ->', e)
# accountant should succeed
try:
    update_subset_status(subs_id, 'in progress', actor_user_id=acc_id)
    print('ACCOUNTANT: allowed')
except Exception as e:
    print('ACCOUNTANT: failed ->', e)
