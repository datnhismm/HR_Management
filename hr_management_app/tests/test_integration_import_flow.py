import os
import unittest
import csv
import secrets
from hr_management_app.src.parsers.file_parser import parse_csv
from hr_management_app.src.parsers.normalizer import map_columns, validate_and_clean
from hr_management_app.src.ml.imputer import infer_missing_fields
from hr_management_app.src.database import database as db

try:
    from hr_management_app.src.ml.imputer_ml import load_model, predict_batch, fit_imputer_from_records
    ML_AVAILABLE = True
except Exception:
    ML_AVAILABLE = False

class IntegrationImportFlowTests(unittest.TestCase):
    def setUp(self):
        # create a small CSV with some missing fields
        self.csv_path = os.path.join(os.getcwd(), "tmp_integration.csv")
        rows = [
            {"name": "Test User A", "email": "test.user.a+%s@example.com" % secrets.token_hex(4), "job_title": "Engineer", "role": "engineer", "year_start": "2010"},
            {"name": "Test User B", "email": "", "job_title": "", "role": "manager", "year_start": ""},
            {"name": "Test User C", "email": "test.user.c+%s@example.com" % secrets.token_hex(4), "job_title": "", "role": "", "year_start": "2008"},
        ]
        with open(self.csv_path, "w", newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=["name", "email", "job_title", "role", "year_start"])
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        self.addCleanup(lambda: os.path.exists(self.csv_path) and os.remove(self.csv_path))

    def test_end_to_end_import_flow(self):
        raws = parse_csv(self.csv_path)
        self.assertGreaterEqual(len(raws), 3)

        cfg = {}
        cleaned_batch = []
        records = []
        for r in raws:
            mapped = map_columns(r, fuzzy_threshold=cfg.get("threshold", 80))
            cleaned, problems = validate_and_clean(mapped)
            cleaned_batch.append(cleaned)
            records.append({"raw": r, "mapped": mapped, "cleaned": cleaned, "problems": problems})

        # try ML predictions if available
        try:
            if ML_AVAILABLE:
                model = load_model()
                if model:
                    preds = predict_batch(cleaned_batch, model)
                    for rec, pr in zip(records, preds):
                        for k, v in pr.items():
                            if k and not k.startswith("_") and v is not None and rec['cleaned'].get(k) in (None, ""):
                                rec['cleaned'][k] = v
        except Exception:
            pass

        # heuristics
        heur = infer_missing_fields([r['cleaned'] for r in records], db_stats=db.get_all_users and {"emails": [u[1] for u in db.get_all_users()]})
        for rec, h in zip(records, heur):
            for k, v in h.items():
                if rec['cleaned'].get(k) in (None, "") and v is not None:
                    rec['cleaned'][k] = v

        # apply and create users/employees
        created_users = []
        created_employee_ids = []
        try:
            for rec in records:
                cleaned = rec['cleaned']
                email = cleaned.get('email')
                if email:
                    try:
                        existing = db.get_user_by_email(email)
                        if not existing:
                            uid = db.create_user(email, 'Pwd12345!')
                        else:
                            uid = existing[0]
                        created_users.append(email)
                    except Exception:
                        # skip create on failure
                        uid = None
                else:
                    uid = None
                # create employee
                try:
                    emp_id = db.create_employee(user_id=uid, name=cleaned.get('name') or '', dob=cleaned.get('dob'), job_title=cleaned.get('job_title'), role=cleaned.get('role'), year_start=int(cleaned.get('year_start')) if cleaned.get('year_start') else None, profile_pic=None, contract_type=cleaned.get('contract_type'), year_end=None)
                    created_employee_ids.append(emp_id)
                except Exception:
                    pass

            # assertions: at least one employee created
            self.assertGreaterEqual(len(created_employee_ids), 1)

            # export audit CSV to ensure exporter runs
            csvp = os.path.join(os.getcwd(), "tmp_audit_export.csv")
            try:
                n = db.export_imputation_audit_csv(csvp)
                # n is integer; file exists
                self.assertIsInstance(n, int)
            finally:
                if os.path.exists(csvp):
                    os.remove(csvp)
        finally:
            # cleanup created users
            for email in created_users:
                try:
                    u = db.get_user_by_email(email)
                    if u:
                        db.delete_user(u[0])
                except Exception:
                    pass
            # cleanup audit rows created by the test: we leave audit cleanup to DB helper
            try:
                with db._conn() as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM imputation_audit WHERE source = ?", ("preview",))
                    conn.commit()
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
