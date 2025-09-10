"""
Simple missing-data imputation utilities used by the import pipeline.

Strategy:
- Build light statistics from existing DB and/or the current batch.
- For categorical fields (job_title, role, contract_type): use most common value.
- For numeric fields (year_start): use median or mode depending on distribution.
- For email: if missing but name exists, synthesize using a safe pattern (name + unique suffix) when allowed; otherwise leave None.
- For dob: attempt to infer year from year_start - typical career start age (e.g., 22-30) or leave None.

This module is intentionally small and deterministic so it works without heavy ML libs.
"""
from collections import Counter
from typing import List, Dict, Any, Optional
import re

# heuristic age at start distribution used for DOB inference
DEFAULT_START_AGE = 24


def most_common(values: List[Any], default: Optional[Any] = None) -> Optional[Any]:
    vals = [v for v in values if v is not None]
    if not vals:
        return default
    c = Counter(vals)
    return c.most_common(1)[0][0]


def median_int(values: List[int], default: Optional[int] = None) -> Optional[int]:
    vals = sorted([int(v) for v in values if v is not None])
    if not vals:
        return default
    n = len(vals)
    mid = n // 2
    if n % 2 == 1:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) // 2


def synthesize_email_from_name(name: str, existing_emails: List[str]) -> str:
    """Create a safe synthesized email using name and a numeric suffix if needed."""
    base = re.sub(r"[^a-z0-9]+", ".", name.strip().lower())
    base = re.sub(r"\.+", ".", base).strip(".")
    if not base:
        base = "user"
    candidate = f"{base}@example.com"
    if candidate not in existing_emails:
        return candidate
    # add numeric suffixes until unique
    i = 1
    while True:
        cand = f"{base}{i}@example.com"
        if cand not in existing_emails:
            return cand
        i += 1


def infer_missing_fields(batch: List[Dict[str, Any]], db_stats: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Take a batch of cleaned records and return a new list with imputed values.

    db_stats: optional precomputed stats such as {"job_title_common": ..., "year_start_median": ..., "emails": [...]}
    """
    db_stats = db_stats or {}
    # collect existing values in this batch
    job_vals = [r.get("job_title") for r in batch]
    role_vals = [r.get("role") for r in batch]
    contract_vals = [r.get("contract_type") for r in batch]
    year_vals = [r.get("year_start") for r in batch if r.get("year_start") is not None]
    emails = [r.get("email") for r in batch if r.get("email")]

    job_common = db_stats.get("job_title_common") or most_common(job_vals)
    role_common = db_stats.get("role_common") or most_common(role_vals, default="engineer")
    contract_common = db_stats.get("contract_common") or most_common(contract_vals)
    year_median = db_stats.get("year_start_median") or median_int(year_vals)
    existing_emails = set(db_stats.get("emails", []) + emails)

    out = []
    for r in batch:
        rec = dict(r)  # shallow copy
        # job title
        if not rec.get("job_title") and job_common:
            rec["job_title"] = job_common
        # role
        if not rec.get("role"):
            rec["role"] = role_common or "engineer"
        # contract type
        if not rec.get("contract_type") and contract_common:
            rec["contract_type"] = contract_common
        # year start
        if not rec.get("year_start") and year_median is not None:
            rec["year_start"] = year_median
        # email: synthesize if missing and name exists
        if not rec.get("email") and rec.get("name"):
            rec["email"] = synthesize_email_from_name(rec.get("name"), list(existing_emails))
            existing_emails.add(rec["email"])
        # dob: if missing but year_start exists, infer approximate dob by subtracting DEFAULT_START_AGE
        if not rec.get("dob") and rec.get("year_start"):
            try:
                y = int(rec.get("year_start")) - DEFAULT_START_AGE
                rec["dob"] = f"{y}-01-01"
            except Exception:
                pass
        out.append(rec)
    return out
