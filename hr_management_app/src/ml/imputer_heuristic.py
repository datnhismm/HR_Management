"""Heuristic imputer for missing fields.
Provides:
- fit_from_records(records): build frequency maps and medians
- predict_batch(records, model): fill missing fields using heuristics

Heuristics:
- job_title: most common job_title for the same role, else global most common
- year_start: median year for the job_title, else global median, else 2008
- email: if missing and name present -> name-based email with domain example.com
- name: if missing and email present -> infer from local-part
"""

import re
import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional


def _normalize_role(r):
    return (r or "").strip().lower()


def fit_from_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    job_by_role = defaultdict(Counter)
    years_by_job = defaultdict(list)
    global_jobs = Counter()
    global_years = []

    for r in records:
        job = r.get("job_title")
        role = _normalize_role(r.get("role"))
        ys = r.get("year_start")
        if job:
            job_by_role[role][job] += 1
            global_jobs[job] += 1
        if ys:
            try:
                y = int(ys)
                years_by_job[job].append(y)
                global_years.append(y)
            except Exception:
                pass

    # build maps
    job_by_role_top = {k: v.most_common(1)[0][0] for k, v in job_by_role.items() if v}
    job_global_top = global_jobs.most_common(1)[0][0] if global_jobs else None

    year_median_by_job = {
        j: int(statistics.median(v)) for j, v in years_by_job.items() if v
    }
    global_year_median = int(statistics.median(global_years)) if global_years else None

    return {
        "job_by_role_top": job_by_role_top,
        "job_global_top": job_global_top,
        "year_median_by_job": year_median_by_job,
        "global_year_median": global_year_median,
    }


def _email_from_name(name: Optional[str], idx: Optional[int] = None) -> str:
    if not name:
        return ""
    s = re.sub(r"[^a-z0-9]+", ".", str(name).strip().lower())
    if idx:
        return f"{s}.{idx}@example.com"
    return f"{s}@example.com"


def _name_from_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    local = str(email).split("@")[0]
    parts = local.replace(".", " ").replace("_", " ").split()
    parts = [p.capitalize() for p in parts if p]
    if parts:
        return " ".join(parts)
    return None


def predict_batch(
    records: List[Dict[str, Any]], model: Dict[str, Any]
) -> List[Dict[str, Any]]:
    out = []
    job_map = model.get("job_by_role_top", {})
    job_global = model.get("job_global_top")
    year_map = model.get("year_median_by_job", {})
    global_year = model.get("global_year_median")

    for idx, r in enumerate(records, start=1):
        rec = dict(r)
        # email
        if not rec.get("email") or str(rec.get("email")).strip() == "":
            if rec.get("name"):
                rec["email"] = _email_from_name(rec.get("name"), idx)
                rec["_imputed_email"] = True
        # name
        if (not rec.get("name") or str(rec.get("name")).strip() == "") and rec.get(
            "email"
        ):
            nm = _name_from_email(rec.get("email"))
            if nm:
                rec["name"] = nm
                rec["_imputed_name"] = True
        # job_title
        if not rec.get("job_title") or str(rec.get("job_title")).strip() == "":
            role = _normalize_role(rec.get("role"))
            jt = job_map.get(role) or job_global
            if jt:
                rec["job_title"] = jt
                rec["_imputed_job"] = True
        # year_start
        if not rec.get("year_start"):
            job = rec.get("job_title")
            ys = year_map.get(job) or global_year or 2008
            rec["year_start"] = int(ys)
            rec["_imputed_year"] = True

        out.append(rec)
    return out
