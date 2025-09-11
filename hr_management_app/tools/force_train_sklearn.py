"""Force a sklearn-based training run and save joblib artifact.
Run from repo root: python hr_management_app/tools/force_train_sklearn.py
"""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from ml import imputer_ml
from database.database import _conn


def fetch_records(limit=None):
    q = '''
    SELECT u.email, e.name, e.job_title, e.role, e.year_start
    FROM users u
    LEFT JOIN employees e ON e.user_id = u.id
    WHERE e.name IS NOT NULL
    '''
    out = []
    with _conn() as conn:
        c = conn.cursor()
        if limit:
            c.execute(q, (limit,))
        else:
            c.execute(q)
        rows = c.fetchall()

    for email, name, job_title, role, year_start in rows:
        out.append({
            "email": email,
            "name": name,
            "job_title": job_title,
            "role": role,
            "year_start": year_start,
        })
    return out


if __name__ == '__main__':
    print('HAS_SKLEARN=', imputer_ml.HAS_SKLEARN)
    records = fetch_records()
    print(f'Got {len(records)} records')
    if not imputer_ml.HAS_SKLEARN:
        print('skipping sklearn training because sklearn not available')
        sys.exit(0)
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'models', 'imputer_model.joblib')
    model = imputer_ml.fit_imputer_from_records(records, save_to=out_path)
    print('Saved sklearn model to', out_path)
    try:
        print('Model type:', model.get('type'))
    except Exception:
        print('Model returned')
