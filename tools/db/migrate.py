"""Simple migration helper: imports DB module and ensures schema exists."""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "hr_management_app", "src")
)
from database import database as db

if __name__ == "__main__":
    print("Initializing/ensuring DB schema...")
    try:
        db.init_db()
        print("DB init complete")
    except Exception as e:
        print("DB init failed:", e)
        raise
