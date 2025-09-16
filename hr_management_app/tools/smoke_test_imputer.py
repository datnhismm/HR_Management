"""Smoke test for imputer model: load model and run predict_batch on sample records."""

import os
import sys
from pprint import pprint

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

try:
    from hr_management_app.src.ml import imputer_ml
except Exception:
    from ml import imputer_ml  # type: ignore


def main():
    print("HAS_SKLEARN=", imputer_ml.HAS_SKLEARN)
    model = imputer_ml.load_model()
    print(
        "Loaded model type=",
        model.get("type") if isinstance(model, dict) else type(model),
    )
    samples = [
        {
            "email": "alice@example.com",
            "name": "Alice Johnson",
            "role": "engineering",
            "job_title": None,
            "year_start": None,
        },
        {
            "email": "bob@example.com",
            "name": "Bob K. Lee",
            "role": "sales",
            "job_title": None,
            "year_start": 2018,
        },
        {
            "email": "carol@example.com",
            "name": "Carol",
            "role": None,
            "job_title": None,
            "year_start": None,
        },
    ]
    if model is None:
        print("No model loaded; skipping predict_batch")
        out = []
    else:
        out = imputer_ml.predict_batch(samples, model)
    pprint(out)


if __name__ == "__main__":
    main()
