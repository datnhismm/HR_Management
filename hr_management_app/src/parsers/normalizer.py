import re
from typing import Dict, Any, List, Tuple
from dateutil import parser as dateparser
try:
    from rapidfuzz import process as rf_process
    RAPIDFUZZ_AVAILABLE = True
except Exception:
    RAPIDFUZZ_AVAILABLE = False
    rf_process = None
import difflib

FIELD_ALIASES = {
    "name": ["name", "full name", "fullname", "full_name"],
    "email": ["email", "e-mail", "mail"],
    "dob": ["dob", "date of birth", "birthdate", "birthday"],
    "job_title": ["job", "job title", "title", "position"],
    "role": ["role", "user role", "position type"],
    "year_start": ["year start", "start year", "joined"],
    "year_end": ["year end", "end year", "left"],
    "contract_type": ["contract", "contract type"],
}

# Configurable fuzzy threshold (0-100). Can be adjusted by caller.
FUZZY_THRESHOLD = 80

def _normalize_key(k: str) -> str:
    k = k.strip().lower()
    k = re.sub(r"[_\s]+", " ", k)
    return k

def map_columns(row: Dict[str, Any], fuzzy_threshold: int = FUZZY_THRESHOLD) -> Dict[str, Any]:
    """Map input row keys to canonical field names. fuzzy_threshold controls minimum score for fuzzy matches.
    """
    out = {}
    for k, v in row.items():
        nk = _normalize_key(str(k))
        mapped = None
        # exact match first
        for canonical, aliases in FIELD_ALIASES.items():
            if nk == canonical or nk in aliases:
                mapped = canonical
                break
        # fuzzy match fallback: build choices/key_map first
        if mapped is None and fuzzy_threshold is not None and fuzzy_threshold >= 0:
            choices = []
            key_map = {}
            for canonical, aliases in FIELD_ALIASES.items():
                choices.append(canonical)
                key_map[canonical] = canonical
                for a in aliases:
                    choices.append(a)
                    key_map[a] = canonical
            # try rapidfuzz first (if available)
            if RAPIDFUZZ_AVAILABLE:
                try:
                    fn = getattr(rf_process, 'extractOne', None)
                    if callable(fn):
                        res = fn(nk, choices)
                        if res and res[1] >= fuzzy_threshold:
                            match = res[0]
                            mapped = key_map.get(match)
                except Exception:
                    mapped = None
            # fallback to stdlib difflib for small typos or when rapidfuzz isn't available
            if mapped is None:
                best = None
                best_score = -1
                for choice in choices:
                    score = int(round(difflib.SequenceMatcher(None, nk, choice).ratio() * 100))
                    if score > best_score:
                        best_score = score
                        best = choice
                if best is not None and best_score >= fuzzy_threshold:
                    mapped = key_map.get(best)
        if mapped:
            out[mapped] = v
    return out


def map_columns_debug(row: Dict[str, Any], fuzzy_threshold: int = FUZZY_THRESHOLD) -> Tuple[Dict[str, Any], Dict[str, Tuple[str, int]]]:
    """Like map_columns but also return a debug map of original_key -> (canonical, score).
    Score is an int 0-100 when fuzzy matching was used, or None for exact matches.
    """
    out = {}
    debug = {}
    for k, v in row.items():
        nk = _normalize_key(str(k))
        mapped = None
        score = None
        # exact match first
        for canonical, aliases in FIELD_ALIASES.items():
            if nk == canonical or nk in aliases:
                mapped = canonical
                score = None
                break
        # fuzzy match fallback: build choices/key_map first
        if mapped is None and fuzzy_threshold is not None and fuzzy_threshold >= 0:
            choices = []
            key_map = {}
            for canonical, aliases in FIELD_ALIASES.items():
                choices.append(canonical)
                key_map[canonical] = canonical
                for a in aliases:
                    choices.append(a)
                    key_map[a] = canonical
            if RAPIDFUZZ_AVAILABLE:
                try:
                    fn = getattr(rf_process, 'extractOne', None)
                    if callable(fn):
                        res = fn(nk, choices)
                        if res:
                            match = res[0]
                            sc = int(round(res[1]))
                            if sc >= fuzzy_threshold:
                                mapped = key_map.get(match)
                                score = sc
                except Exception:
                    mapped = None
            # difflib fallback when rapidfuzz not present or score low
            if mapped is None:
                best = None
                best_score = -1
                for choice in choices:
                    sc = int(round(difflib.SequenceMatcher(None, nk, choice).ratio() * 100))
                    if sc > best_score:
                        best_score = sc
                        best = choice
                if best is not None and best_score >= fuzzy_threshold:
                    mapped = key_map.get(best)
                    score = best_score
        if mapped:
            out[mapped] = v
            debug[str(k)] = (mapped, score)
        else:
            debug[str(k)] = (None, None)
    return out, debug

def validate_and_clean(record: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Return cleaned record and list of validation problems (empty if ok)."""
    problems = []
    out = {}
    # name
    name = record.get("name")
    if not name:
        problems.append("Missing name")
    else:
        out["name"] = str(name).strip()

    # email
    email = record.get("email")
    if email:
        email = str(email).strip()
        if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            out["email"] = email
        else:
            problems.append("Invalid email")
    else:
        out["email"] = None

    # dob
    dob = record.get("dob")
    if dob:
        try:
            d = dateparser.parse(str(dob), dayfirst=False)
            out["dob"] = d.date().isoformat()
        except Exception:
            problems.append("Invalid dob")
            out["dob"] = None
    else:
        out["dob"] = None

    # job
    out["job_title"] = record.get("job_title") or record.get("job") or None

    # role
    out["role"] = (record.get("role") or "engineer").strip() if record.get("role") else "engineer"

    # years
    for key in ("year_start", "year_end"):
        val = record.get(key)
        if val:
            try:
                out[key] = int(str(val).strip())
            except Exception:
                problems.append(f"Invalid {key}")
                out[key] = None
        else:
            out[key] = None

    out["contract_type"] = record.get("contract_type") or None

    return out, problems
