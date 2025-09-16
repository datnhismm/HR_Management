from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from hr_management_app.src.database.database import _conn

DB_NAME = "hr_management.db"


@dataclass
class Contract:
    id: int
    employee_id: int
    start_date: str
    end_date: str
    terms: str

    def __repr__(self) -> str:
        return f"Contract(id={self.id}, employee_id={self.employee_id}, start={self.start_date}, end={self.end_date})"

    def save(self) -> None:
        """Insert or update this contract into the DB."""
        # ensure employee exists before saving the contract
        from hr_management_app.src.database.database import get_employee_by_id

        if get_employee_by_id(int(self.employee_id)) is None:
            raise ValueError(
                f"Employee id {self.employee_id} does not exist; cannot save contract."
            )
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO contracts (id, employee_id, start_date, end_date, terms) VALUES (?, ?, ?, ?, ?)",
                (
                    self.id,
                    int(self.employee_id),
                    self.start_date,
                    self.end_date,
                    self.terms,
                ),
            )

    # backward-compatible alias
    def create_contract(self) -> None:
        self.save()

    def update_contract(self, new_terms: str) -> None:
        """Update contract terms both in object and DB."""
        self.terms = new_terms
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE contracts SET terms = ? WHERE id = ?", (new_terms, self.id)
            )

    def delete(self) -> None:
        """Delete this contract from DB."""
        with _conn() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM contracts WHERE id = ?", (self.id,))

    def get_details(self) -> Dict:
        """Return contract data as a dict (used by UI)."""
        return asdict(self)

    @classmethod
    def from_row(cls, row) -> "Contract":
        return cls(*row)

    @classmethod
    def retrieve_contract(cls, id: int) -> Optional["Contract"]:
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, employee_id, start_date, end_date, terms FROM contracts WHERE id = ?",
                (id,),
            )
            row = c.fetchone()
        return cls.from_row(row) if row else None

    @classmethod
    def all_contracts(cls) -> List["Contract"]:
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, employee_id, start_date, end_date, terms FROM contracts"
            )
            rows = c.fetchall()
        return [cls.from_row(r) for r in rows]


@dataclass
class Subset:
    id: int
    contract_id: int
    title: str
    description: Optional[str]
    status: str
    order_index: int = 0

    def __repr__(self) -> str:
        return f"Subset(id={self.id}, contract_id={self.contract_id}, title={self.title}, status={self.status})"

    @classmethod
    def from_row(cls, row):
        return cls(*row)

    def save(self):
        # persisted via database helper
        from hr_management_app.src.database.database import update_subset_status

        if not self.id:
            raise ValueError(
                "Subset must have id to be saved via this object; use create_contract_subset to create new subsets"
            )
        # allow status update
        update_subset_status(self.id, self.status)


def get_subsets(contract_id: int) -> List[Subset]:
    from hr_management_app.src.database.database import get_subsets_for_contract

    rows = get_subsets_for_contract(contract_id)
    return [Subset.from_row(r) for r in rows]


def contract_progress(contract_id: int) -> Dict:
    """Return a small progress report for a contract based on subset statuses.

    - percent_complete: fraction of subsets in COMPLETED_STATUSES
    - total: number of subsets
    - completed: number completed
    - details: list of subset dicts
    """
    from hr_management_app.src.database.database import (
        COMPLETED_STATUSES,
        get_status_color,
        get_subsets_for_contract,
    )

    rows = get_subsets_for_contract(contract_id)
    total = len(rows)
    completed = sum(1 for r in rows if r[4] in COMPLETED_STATUSES)
    percent = int((completed / total) * 100) if total > 0 else 0
    details = []
    for r in rows:
        sid, cid, title, description, status, order_index = r
        details.append(
            {
                "id": sid,
                "title": title,
                "description": description,
                "status": status,
                "color": get_status_color(status),
                "order_index": order_index,
            }
        )
    return {
        "percent_complete": percent,
        "total": total,
        "completed": completed,
        "details": details,
    }
