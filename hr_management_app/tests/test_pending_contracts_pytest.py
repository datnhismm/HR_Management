import importlib
import os
import tempfile


def _load_database_with_temp_db(tmp_path):
    # create a clean temp DB file and point the module to it via env var
    dbfile = tmp_path / "pending_test.db"
    # ensure the file exists
    dbfile.write_text("")
    os.environ["HR_MANAGEMENT_TEST_DB"] = str(dbfile)
    db = importlib.import_module("hr_management_app.src.database.database")
    # If module was previously imported in the test session, reload to pick up env var
    importlib.reload(db)
    db.init_db()
    return db


def test_submit_and_approve_pending_contract_non_gui(tmp_path):
    db = _load_database_with_temp_db(tmp_path)

    # baseline contract count
    before = db.get_all_contracts_filtered()

    # submit a pending contract (use None/0 for contract_id to let DB assign)
    pending_id = db.submit_pending_contract(
        contract_id=None,
        employee_id=42,
        construction_id=None,
        parent_contract_id=None,
        area="Test Area",
        incharge="Tester",
        start_date="2025-01-01",
        end_date="2025-12-31",
        terms="Unit test pending contract",
        file_path=None,
        submitted_by=1,
    )

    assert int(pending_id) > 0

    pendings = db.list_pending_contracts(status="pending")
    assert any(int(r[0]) == int(pending_id) for r in pendings)

    # approve the pending contract
    db.approve_pending_contract(int(pending_id), approved_by=1)

    approved = db.list_pending_contracts(status="approved")
    assert any(int(r[0]) == int(pending_id) for r in approved)

    after = db.get_all_contracts_filtered()
    # approving a pending should have created a live contract (count increased by 1)
    assert len(after) == len(before) + 1


def test_pending_selection_indexing(tmp_path):
    db = _load_database_with_temp_db(tmp_path)

    # create multiple pendings and ensure order/indexing is deterministic
    ids = []
    for i in range(3):
        pid = db.submit_pending_contract(
            contract_id=None,
            employee_id=100 + i,
            construction_id=None,
            parent_contract_id=None,
            area=f"Area {i}",
            incharge=f"Person {i}",
            start_date="2025-01-01",
            end_date="2025-12-31",
            terms=f"Pending {i}",
            file_path=None,
            submitted_by=None,
        )
        ids.append(int(pid))

    pendings = db.list_pending_contracts()
    # Ensure all ids we created are present in the returned list
    returned_ids = [int(r[0]) for r in pendings]
    for pid in ids:
        assert pid in returned_ids

    # Simulate selection: find index for the middle pending id
    target = ids[1]
    index = next((i for i, r in enumerate(pendings) if int(r[0]) == target), None)
    assert index is not None
    # Verify the id at that index matches
    assert int(pendings[index][0]) == target
