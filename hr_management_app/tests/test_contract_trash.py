import importlib
import os
import tempfile
import time
import unittest

database = importlib.import_module("hr_management_app.src.database.database")


class ContractTrashTests(unittest.TestCase):
    def setUp(self):
        # use a temporary DB file for isolation
        fd, self.dbpath = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.environ["HR_MANAGEMENT_TEST_DB"] = self.dbpath
        # ensure fresh DB
        database.init_db()

    def tearDown(self):
        try:
            os.remove(self.dbpath)
        except Exception:
            pass
        os.environ.pop("HR_MANAGEMENT_TEST_DB", None)

    def _create_sample_contract(self, cid: int = None):
        class C:
            def __init__(self, id=None):
                self.id = id
                self.employee_id = None
                self.construction_id = None
                self.parent_contract_id = None
                self.start_date = "2025-01-01"
                self.end_date = "2025-12-31"
                self.area = "Area X"
                self.incharge = "Alice"
                self.terms = "Terms"
                self.file_path = None

        c = C(cid)
        database.add_contract_to_db(c)
        # fetch the inserted id from DB
        rows = database.get_all_contracts_filtered(include_deleted=True)
        if not rows:
            return None
        return int(rows[-1][0])

    def test_soft_delete_and_restore(self):
        cid = self._create_sample_contract()
        self.assertIsNotNone(cid)

        # soft-delete
        database.soft_delete_contract(cid)
        trashed = database.list_trashed_contracts()
        self.assertTrue(any(int(r[0]) == cid for r in trashed))

        # restore
        database.restore_contract(cid)
        trashed = database.list_trashed_contracts()
        self.assertFalse(any(int(r[0]) == cid for r in trashed))

    def test_purge_deleted_older_than(self):
        cid = self._create_sample_contract()
        self.assertIsNotNone(cid)
        # soft-delete but set deleted_at to older timestamp
        database.soft_delete_contract(cid)
        # manually backdate deleted_at for the test
        with database._conn() as conn:
            cur = conn.cursor()
            old_ts = time.time() - (10 * 24 * 3600)
            old_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(old_ts))
            cur.execute(
                "UPDATE contracts SET deleted_at = ? WHERE id = ?", (old_iso, cid)
            )
            conn.commit()

        purged = database.purge_deleted_older_than(5)
        self.assertGreaterEqual(purged, 1)
        # ensure the contract is gone
        row = database.get_contract_by_id(cid, include_deleted=True)
        self.assertIsNone(row)

    def test_delete_contract_and_descendants(self):
        parent_id = self._create_sample_contract()
        child_id = self._create_sample_contract()
        self.assertIsNotNone(parent_id)
        self.assertIsNotNone(child_id)
        # link child to parent in DB
        with database._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE contracts SET parent_contract_id = ? WHERE id = ?",
                (parent_id, child_id),
            )
            conn.commit()
        # hard delete
        database.delete_contract_and_descendants(parent_id)
        # ensure none remain
        all_rows = database.get_all_contracts_filtered(include_deleted=True)
        ids = [r[0] for r in all_rows]
        self.assertNotIn(parent_id, ids)


if __name__ == "__main__":
    unittest.main()
