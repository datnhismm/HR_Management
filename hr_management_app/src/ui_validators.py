from datetime import datetime
from typing import Tuple


def validate_contract_fields(
    cid_text: str, eid_text: str, start: str, end: str
) -> Tuple[int, int, str, str]:
    """Validate and parse contract input strings.

    Returns (cid, eid, start_iso, end_iso) or raises ValueError with a message.
    """
    if not cid_text or not eid_text:
        raise ValueError("Contract ID and Employee ID are required.")
    try:
        cid = int(cid_text)
        eid = int(eid_text)
    except ValueError:
        raise ValueError("Contract ID and Employee ID must be integers.")

    try:
        s_dt = datetime.fromisoformat(start)
        e_dt = datetime.fromisoformat(end)
    except Exception:
        raise ValueError("Start and End must be in ISO format YYYY-MM-DD.")
    if s_dt > e_dt:
        raise ValueError("Start date must be before or equal to End date.")
    return cid, eid, s_dt.date().isoformat(), e_dt.date().isoformat()
