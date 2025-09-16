"""Train the ML imputer model from DB records and save artifact.

Usage: run from repo root with virtualenv activated:

    python hr_management_app/tools/train_imputer.py

This script will read employees (and users) from the DB, build a training set,
train models and save them under src/models/imputer_model.joblib
"""

import os
import sys
from pprint import pprint

# ensure local src on path
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

try:
    from hr_management_app.src.ml.imputer_ml import fit_imputer_from_records
except Exception:
    from ml.imputer_ml import fit_imputer_from_records  # type: ignore
try:
    from hr_management_app.src.database.database import _conn
except Exception:
    from hr_management_app.src.database.database import _conn  # type: ignore


def fetch_records(limit=None):
    # join users and employees to get name, email, job_title, role, year_start
    q = """
    SELECT u.email, e.name, e.job_title, e.role, e.year_start
    FROM users u
    LEFT JOIN employees e ON e.user_id = u.id
    WHERE e.name IS NOT NULL
    """
    out = []
    # Use context manager to ensure DB connection is closed promptly to avoid ResourceWarning
    with _conn() as conn:
        c = conn.cursor()
        if limit:
            c.execute(q, (limit,))
        else:
            c.execute(q)
        rows = c.fetchall()

    for email, name, job_title, role, year_start in rows:
        out.append(
            {
                "email": email,
                "name": name,
                "job_title": job_title,
                "role": role,
                "year_start": year_start,
            }
        )
    return out


if __name__ == "__main__":
    print("Fetching records from DB...")
    records = fetch_records()
    print(f"Got {len(records)} records for training")
    if len(records) < 50:
        print("Warning: fewer than 50 records; model may be weak.")
    print("Training model...")
    model = fit_imputer_from_records(records)
    print("Model training complete. Saved model artifact.")
    pprint(model.keys())
