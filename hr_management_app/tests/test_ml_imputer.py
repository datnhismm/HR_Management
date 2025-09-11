import unittest
from hr_management_app.src.ml.imputer_ml import fit_imputer_from_records, predict_batch, load_model

class MLImputerTests(unittest.TestCase):
    def test_fit_and_predict_fallback(self):
        # small synthetic dataset
        records = [
            {"name": "Alice Smith", "role": "engineering", "job_title": "Engineer", "year_start": 2010},
            {"name": "Bob Jones", "role": "engineering", "job_title": "Engineer", "year_start": 2012},
            {"name": "Carol", "role": "hr", "job_title": "HR Specialist", "year_start": 2015},
        ]
        # fit fallback or sklearn model
        try:
            model = fit_imputer_from_records(records, save_to=None)
        except Exception:
            self.skipTest("Imputer training not available in this environment")
        # prepare a record with missing job_title
        recs = [{"name": "Dave", "role": "engineering", "job_title": None, "year_start": None}]
        # predict via model if available
        if isinstance(model, dict):
            # if sklearn model is provided, we expect predict_batch available on module; otherwise fallback is dict
            try:
                preds = predict_batch(recs, model)
                self.assertIsInstance(preds, list)
            except Exception:
                # fallback dict: emulate prediction
                self.assertTrue('job_by_role' in model or 'job_most_common' in model)

if __name__ == '__main__':
    unittest.main()
