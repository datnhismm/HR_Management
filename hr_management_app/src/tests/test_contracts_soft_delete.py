import os
import tempfile

# Use a temporary DB for isolation: set env var before importing package modules
os.environ["HR_MANAGEMENT_TEST_DB"] = os.path.join(
    tempfile.gettempdir(), "hr_mgmt_test.db"
)
from hr_management_app.src.contracts.models import Contract
from hr_management_app.src.database import database as db


def setup_module():
    # ensure fresh DB
    try:
        if os.path.exists(os.environ["HR_MANAGEMENT_TEST_DB"]):
            os.remove(os.environ["HR_MANAGEMENT_TEST_DB"])
    except Exception:
        pass
    db.init_db()


def test_soft_delete_and_restore_cycle():
    # create a contract
    cid = 7777
    c = Contract(
        id=cid,
        employee_id=None,
        start_date="2025-01-01",
        end_date="2025-12-31",
        terms="soft-delete test",
    )
    db.add_contract_to_db(c)

    # verify present in all_contracts
    rows = db.get_all_contracts_filtered(include_deleted=False)
    assert any(r[0] == cid for r in rows)

    # soft-delete it
    db.soft_delete_contract(cid, cascade=False)

    rows_after = db.get_all_contracts_filtered(include_deleted=False)
    assert not any(r[0] == cid for r in rows_after)

    # ensure it's in trashed list
    trashed = db.list_trashed_contracts()
    assert any(r[0] == cid for r in trashed)

    # restore
    db.restore_contract(cid, cascade=False)
    rows_restored = db.get_all_contracts_filtered(include_deleted=False)
    assert any(r[0] == cid for r in rows_restored)


# cleanup test DB
def teardown_module():
    try:
        os.remove(os.environ["HR_MANAGEMENT_TEST_DB"])
    except Exception:
        pass
