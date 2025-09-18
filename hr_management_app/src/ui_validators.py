from datetime import datetime
from typing import Optional

from hr_management_app.src.database.database import _conn


def _contract_exists(contract_id: int) -> bool:
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM contracts WHERE id = ? LIMIT 1", (contract_id,))
        return c.fetchone() is not None


def _detect_cycle(start_id: int, parent_id: int) -> bool:
    """Detect whether assigning parent_id as parent of start_id would create a cycle.

    Walk up the parent chain from parent_id and see if we encounter start_id.
    """
    visited = set()
    cur = parent_id
    with _conn() as conn:
        c = conn.cursor()
        while cur is not None and cur not in visited:
            if cur == start_id:
                return True
            visited.add(cur)
            c.execute("SELECT parent_contract_id FROM contracts WHERE id = ?", (cur,))
            row = c.fetchone()
            cur = row[0] if row else None
    return False


def validate_contract_fields(
    cid_text: str,
    eid_text: str,
    start: str,
    end: str,
    parent_text: Optional[str] = None,
) -> tuple:
    """Validate and parse contract input strings.

    Returns (cid, eid, start_iso, end_iso, parent_id) or raises ValueError.
    parent_text may be None or empty; when provided, parent existence and cycles are checked.
    """
    if not cid_text or not eid_text:
        raise ValueError("Contract ID and Employee (or Construction) ID are required.")
    try:
        cid = int(cid_text)
        eid = int(eid_text)
    except ValueError:
        raise ValueError("Contract ID and Employee/Construction ID must be integers.")

    try:
        s_dt = datetime.fromisoformat(start)
        e_dt = datetime.fromisoformat(end)
    except Exception:
        raise ValueError("Start and End must be in ISO format YYYY-MM-DD.")
    if s_dt > e_dt:
        raise ValueError("Start date must be before or equal to End date.")

    parent_id = None
    if parent_text and parent_text.strip():
        try:
            parent_id = int(parent_text.strip())
        except ValueError:
            raise ValueError("Parent Contract ID must be an integer if provided.")
        if not _contract_exists(parent_id):
            raise ValueError(f"Parent contract id {parent_id} does not exist.")
        # detect cycle: assigning parent_id as parent of cid must not create cycle
        if _detect_cycle(cid, parent_id):
            raise ValueError(
                "Assigning this parent would create a contract hierarchy cycle."
            )

    # Maintain backward-compatible 4-tuple return when caller did not pass parent_text
    if parent_text is None:
        return cid, eid, s_dt.date().isoformat(), e_dt.date().isoformat()
    return cid, eid, s_dt.date().isoformat(), e_dt.date().isoformat(), parent_id
