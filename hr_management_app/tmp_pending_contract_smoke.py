"""Smoke test: submit pending contract as low-role user, approve it as manager, assert live contract exists.
Run with PYTHONPATH set to the repository root. For example, set PYTHONPATH to your repo root and run this script.
"""
import time
import sys

from hr_management_app.src.database.database import (
    submit_pending_contract,
    list_pending_contracts,
    approve_pending_contract,
    get_all_contracts_filtered,
    delete_contract_and_descendants,
)

print("Starting pending-contract end-to-end smoke test")

# Choose a high-ish, likely-unused contract id using timestamp
test_cid = int(time.time()) % 1000000 + 900000
print("Using test contract id:", test_cid)

try:
    pending_id = submit_pending_contract(
        contract_id=test_cid,
        employee_id=None,
        construction_id=None,
        parent_contract_id=None,
        area="smoke-test",
        incharge="smoke-runner",
        start_date="2025-09-30",
        end_date="2026-09-30",
        terms="This is an automated smoke test.",
        file_path=None,
        submitted_by=999999,
    )
    print("Submitted pending_id:", pending_id)
    if not pending_id:
        print("Failed to create pending contract (no id returned)")
        sys.exit(2)

    # verify pending exists
    pendings = list_pending_contracts(status="pending")
    if not any((int(r[0]) == int(pending_id)) for r in pendings):
        print("Pending contract not found in list_pending_contracts output")
        sys.exit(3)
    print("Pending visible in DB")

    # approve as manager (user id 1 simulated)
    approve_pending_contract(int(pending_id), approved_by=1)
    print("Approved pending_id", pending_id)

    # verify live contract exists
    rows = get_all_contracts_filtered()
    found = any((int(r[0]) == int(test_cid)) for r in rows)
    print("Live contract found:", found)
    if not found:
        print("FAIL: live contract not found after approval")
        sys.exit(4)

    print("SUCCESS: pending -> approved -> live contract path works")

finally:
    # Best-effort cleanup: remove the live contract and descendants if created
    try:
        delete_contract_and_descendants(test_cid)
        print("Cleaned up test contract and descendants")
    except Exception as e:
        print("Warning: cleanup failed:", e)

print("Smoke test completed")
