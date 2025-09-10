"""Train the ML imputer model from DB records and save artifact.

Usage: run from repo root with virtualenv activated:

    python hr_management_app/tools/train_imputer.py

This script will read employees (and users) from the DB, build a training set,
train models and save them under src/models/imputer_model.joblib
"""
import os
import sys
import sqlite3
from pprint import pprint

# ensure local src on path
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from ml.imputer_ml import fit_imputer_from_records
from database.database import _conn


def fetch_records(limit=None):
    conn = _conn()
    c = conn.cursor()
    # join users and employees to get name, email, job_title, role, year_start
    q = '''
    SELECT u.email, e.name, e.job_title, e.role, e.year_start
    FROM users u
    LEFT JOIN employees e ON e.user_id = u.id
    WHERE e.name IS NOT NULL
    '''
    if limit:
        q += " LIMIT ?"
        c.execute(q, (limit,))
    else:
        c.execute(q)
    rows = c.fetchall()
    out = []
    for email, name, job_title, role, year_start in rows:
        out.append({
            "email": email,
            "name": name,
            "job_title": job_title,
            "role": role,
            "year_start": year_start,
        })
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
