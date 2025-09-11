"""Train imputer models from an XLSX file and save sklearn joblib artifact.
Usage: .\.venv\Scripts\python.exe hr_management_app\tools\train_imputer_from_xlsx.py
"""
import os
import sys
from pprint import pprint
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from ml.imputer_ml import fit_imputer_from_records, load_model
from openpyxl import load_workbook

IN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'dummy_import_20k.xlsx')
OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'models', 'imputer_model.joblib')


def read_xlsx(path):
    wb = load_workbook(path, read_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    headers = list(next(it))
    records = []
    for row in it:
        r = dict(zip(headers, row))
        # normalize keys to expected names (lowercase)
        rec = {k.lower(): v for k, v in r.items()}
        records.append(rec)
    return records


if __name__ == '__main__':
    print('Reading', IN_FILE)
    recs = read_xlsx(IN_FILE)
    print('Loaded', len(recs), 'rows')

    # filter rows with at least some fields
    print('Training sklearn models (if sklearn available)...')
    model = fit_imputer_from_records(recs, save_to=OUT_PATH)
    print('Saved model to', OUT_PATH)
    try:
        print('Model type:', model.get('type'))
        if model.get('type') == 'sklearn':
            le_job = model.get('le_job')
            print('Job classes:', len(getattr(le_job, 'classes_', [])))
    except Exception:
        pass

    # quick smoke predictions on a few rows with missing fields
    samples = [r for r in recs if not r.get('job_title') or not r.get('year_start')][:10]
    if samples:
        print('Running sample predictions on first', len(samples), 'rows with missing values')
        from ml.imputer_ml import predict_batch, load_model
        m2 = load_model(OUT_PATH)
        out = predict_batch(samples, m2)
        pprint(out[:5])
    else:
        print('No sample rows with missing values found for smoke test')
