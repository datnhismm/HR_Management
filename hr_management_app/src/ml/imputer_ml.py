"""
ML-backed imputer for missing job_title and year_start.

This file provides:
- fit_imputer_from_db(conn_or_records): trains simple sklearn models (RandomForest)
  to predict job_title (categorical) and year_start (regression) from available fields.
- load_model(path): loads saved models (job and year models) using joblib.
- predict_batch(records, model): predicts missing fields for a batch and returns filled records + confidences.

Design choices:
- Feature extraction is intentionally simple: name token counts, role one-hot (mapped), and simple length features.
- Categorical job_title prediction uses a RandomForestClassifier with label encoding.
- Year_start prediction uses RandomForestRegressor.
- Model artifacts are saved together in a directory with joblib.

Note: This is a lightweight approach suited for medium-sized datasets (thousands of rows). For 20k+ rows
it will work better; tune hyperparameters if needed.
"""

import json
import os
import re
from collections import Counter
from typing import Any
from typing import Any as _Any
from typing import Dict, List, Optional, Tuple, cast

# Try to import sklearn and joblib; if unavailable, use a lightweight fallback
HAS_SKLEARN = True
# declare as Any so the static/type checker won't treat these as None
joblib: _Any = None
np: _Any = None
RandomForestClassifier: _Any = None
RandomForestRegressor: _Any = None
LabelEncoder: _Any = None
try:
    import joblib
except Exception:
    HAS_SKLEARN = False

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR, exist_ok=True)


def _name_tokens(name: str) -> List[str]:
    if not name:
        return []
    s = re.sub(r"[^a-z0-9]+", " ", name.strip().lower())
    return [t for t in s.split() if t]


def _extract_features(
    records: List[Dict[str, Any]], le_role: Optional[Any] = None
) -> Tuple[Any, Dict]:
    # simple features: name token counts, name length, role encoded
    role_vals = [r.get("role") or "" for r in records]
    all_roles = list(set(role_vals))
    if le_role is None:
        # If sklearn is available, import LabelEncoder locally to avoid static
        # analyzers confusing the module-level symbol. Otherwise, create a
        # simple dummy encoder with classes_.
        if HAS_SKLEARN:
            try:
                from sklearn.preprocessing import LabelEncoder as _LabelEncoder_local

                le_role = _LabelEncoder_local()
                try:
                    le_role.fit(all_roles)
                except Exception:
                    # fallback to setting classes_ directly
                    try:
                        le_role.classes_ = list(all_roles)
                    except Exception:
                        pass
            except Exception:
                # treat as unavailable below
                le_role = None
        if le_role is None:

            class _DummyLE:
                def __init__(self, classes):
                    self.classes_ = list(classes)

            le_role = _DummyLE(all_roles)
    # Safely encode roles: LabelEncoder.transform will raise on unseen labels,
    # so build a mapping from known classes to indices and fall back to 0.
    try:
        classes = list(le_role.classes_)
    except Exception:
        classes = list(set(role_vals))
        try:
            le_role.classes_ = classes
        except Exception:
            pass

    mapping = {c: i for i, c in enumerate(classes)}

    X = []
    meta = {"le_role": le_role}
    for idx, r in enumerate(records):
        name = r.get("name") or ""
        toks = _name_tokens(name)
        tok_count = len(toks)
        name_len = len(name)
        rv = role_vals[idx]
        role_val = mapping.get(rv, 0)
        X.append([tok_count, name_len, role_val])

    try:
        import numpy as _np

        return _np.array(X), meta
    except Exception:
        return X, meta


def fit_imputer_from_records(
    records: List[Dict[str, Any]], save_to: Optional[str] = None
) -> Dict[str, Any]:
    """Train models from provided records. Returns a dict with models and label encoders."""
    # If sklearn available, train RandomForest models
    if HAS_SKLEARN:
        # prepare classification dataset for job_title
        job_records = [r for r in records if r.get("job_title")]
        if not job_records:
            raise ValueError("No job_title records found for training")

        # do local imports to keep static analyzers happy
        try:
            import joblib as _joblib
            import numpy as _np
            from sklearn.ensemble import RandomForestClassifier as _RFC
            from sklearn.ensemble import RandomForestRegressor as _RFR
            from sklearn.preprocessing import LabelEncoder as _LabelEncoder
        except Exception:
            raise RuntimeError("SKLearn environment expected but missing")

        X_job, meta = _extract_features(job_records)
        # r.get may be typed as Any|None; cast to str because we filtered job_records
        y_job = [cast(str, r.get("job_title")) for r in job_records]
        le_job = _LabelEncoder()
        y_enc = le_job.fit_transform(y_job)

        clf = _RFC(n_estimators=100, random_state=42)
        clf.fit(X_job, y_enc)

        # prepare regression for year_start
        year_records = [r for r in records if r.get("year_start")]
        X_year, meta_y = _extract_features(year_records, le_role=meta["le_role"])
        # Ensure year values are present and valid before casting
        # Filter out missing values before building numpy array
        y_year = _np.array(
            [
                int(cast(int, r.get("year_start")))
                for r in year_records
                if r.get("year_start") is not None
            ]
        )
        reg = _RFR(n_estimators=100, random_state=42)
        reg.fit(X_year, y_year)

        model = {
            "type": "sklearn",
            "clf": clf,
            "reg": reg,
            "le_job": le_job,
            "le_role": meta["le_role"],
        }

        if save_to is None:
            save_to = os.path.join(MODEL_DIR, "imputer_model.joblib")
        _joblib.dump(model, save_to)
        return model

    # Fallback: build simple frequency-based model and medians
    # job_title by role frequency, and year_start median per job_title
    job_by_role = {}
    job_counts = Counter()
    years_by_job = {}
    for r in records:
        job = r.get("job_title")
        role = r.get("role") or ""
        ys = r.get("year_start")
        if job:
            job_counts[job] += 1
            job_by_role.setdefault(role, Counter())[job] += 1
            if ys:
                years_by_job.setdefault(job, []).append(int(ys))

    job_most_common = job_counts.most_common(1)[0][0] if job_counts else None
    year_median_by_job = {
        j: int(sorted(v)[len(v) // 2]) for j, v in years_by_job.items()
    }
    global_years = [
        int(cast(int, r.get("year_start"))) for r in records if r.get("year_start")
    ]
    global_year_median = (
        int(sorted(global_years)[len(global_years) // 2]) if global_years else None
    )

    model = {
        "type": "fallback",
        "job_by_role": {k: v.most_common(1)[0][0] for k, v in job_by_role.items()},
        "job_most_common": job_most_common,
        "year_median_by_job": year_median_by_job,
        "global_year_median": global_year_median,
    }
    if save_to is None:
        save_to = os.path.join(MODEL_DIR, "imputer_model.json")
    with open(save_to, "w", encoding="utf-8") as fh:
        json.dump(model, fh)
    return model


def load_model(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    # try sklearn artifact
    if HAS_SKLEARN:
        if path is None:
            path = os.path.join(MODEL_DIR, "imputer_model.joblib")
        if not os.path.exists(path):
            return None
        return joblib.load(path)
    # fallback: load JSON model
    if path is None:
        path = os.path.join(MODEL_DIR, "imputer_model.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def predict_batch(
    records: List[Dict[str, Any]], model: Dict[str, Any]
) -> List[Dict[str, Any]]:
    if model is None:
        return records
    if isinstance(model, dict) and model.get("type") == "sklearn" and HAS_SKLEARN:
        clf = model["clf"]
        reg = model["reg"]
        le_job = model["le_job"]
        le_role = model["le_role"]

        X, _ = _extract_features(records, le_role=le_role)
        # predict job where missing
        probs = clf.predict_proba(X)
        # numpy required for array ops; import locally so static checker knows it's present
        try:
            import numpy as _np

            job_pred_idx = _np.argmax(probs, axis=1)
            job_pred_conf = _np.max(probs, axis=1)
        except Exception:
            return records
        job_labels = le_job.inverse_transform(job_pred_idx)

        year_pred = reg.predict(X)

        out = []
        for i, r in enumerate(records):
            rec = dict(r)
            if not rec.get("job_title") and job_pred_conf[i] > 0.45:
                rec["job_title"] = str(job_labels[i])
                rec["_imputed_job_conf"] = float(job_pred_conf[i])
            if not rec.get("year_start"):
                try:
                    rec["year_start"] = int(round(float(year_pred[i])))
                    rec["_imputed_year_pred"] = float(year_pred[i])
                except Exception:
                    # fallback to a sensible default if prediction malformed
                    rec["year_start"] = 2005
                    rec["_imputed_year_pred"] = float(rec["year_start"])
            out.append(rec)
        return out

    # fallback model: frequency/median based
    if isinstance(model, dict) and model.get("type") == "fallback":
        job_by_role = model.get("job_by_role", {})
        job_most_common = model.get("job_most_common")
        year_median_by_job = model.get("year_median_by_job", {})
        global_year_median = model.get("global_year_median")
        out = []
        for r in records:
            rec = dict(r)
            if not rec.get("job_title"):
                role = rec.get("role") or ""
                rec["job_title"] = job_by_role.get(role) or job_most_common
                rec["_imputed_job_conf"] = 0.5
            if not rec.get("year_start"):
                job = rec.get("job_title")
                rec["year_start"] = int(
                    year_median_by_job.get(job) or global_year_median or 2005
                )
                rec["_imputed_year_pred"] = float(rec["year_start"])
            out.append(rec)
        return out

    return records
