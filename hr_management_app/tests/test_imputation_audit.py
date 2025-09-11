import os
import unittest
from hr_management_app.src.database import database as db

class ImputationAuditTests(unittest.TestCase):
    def setUp(self):
        # ensure DB is initialized and add a marker audit row
        self.test_csv = os.path.join(os.getcwd(), "test_imputation_audit_export.csv")
        # insert a deterministic test row
        db.record_imputation_audit(row_index=999999, field="job_title", old_value=None, new_value="__UNIT_TEST_JOB__", source="unit_test", actor_user_id=None)

    def tearDown(self):
        # remove CSV if created
        try:
            if os.path.exists(self.test_csv):
                os.remove(self.test_csv)
        except Exception:
            pass
        # remove test audit rows from DB
        try:
            with db._conn() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM imputation_audit WHERE source = ? AND row_index = ?", ("unit_test", 999999))
                conn.commit()
        except Exception:
            pass

    def test_export_contains_test_row(self):
        # export audit CSV
        n = db.export_imputation_audit_csv(self.test_csv)
        self.assertIsInstance(n, int)
        self.assertGreaterEqual(n, 1)
        # verify CSV contains our marker
        with open(self.test_csv, "r", encoding="utf-8") as fh:
            data = fh.read()
        self.assertIn("unit_test", data)
        self.assertIn("__UNIT_TEST_JOB__", data)

if __name__ == "__main__":
    unittest.main()
