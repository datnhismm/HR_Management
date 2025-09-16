from dataclasses import asdict, dataclass
from typing import Dict, List, Optional
import os
import shutil
import time

from hr_management_app.src.database.database import _conn

DB_NAME = "hr_management.db"


# storage directory for uploaded contract files (pdf/docx)
def _contract_storage_dir() -> str:
    # hr_management_app/storage/contracts
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    storage = os.path.join(base, "storage", "contracts")
    os.makedirs(storage, exist_ok=True)
    return storage


def store_contract_file(src_path: str, construction_id: Optional[int] = None) -> str:
    """Copy the given file into the project's contract storage and return the relative path.

    The returned path is absolute. Filenames are sanitized by prefixing employee id and a timestamp.
    """
    if not src_path:
        raise ValueError("src_path is required")
    if not os.path.isfile(src_path):
        raise FileNotFoundError(f"Contract file not found: {src_path}")
    storage = _contract_storage_dir()
    name = os.path.basename(src_path)
    ts = int(time.time())
    prefix = f"cons{construction_id}_" if construction_id else ""
    dest_name = f"{prefix}{ts}_{name}"
    dest_path = os.path.join(storage, dest_name)
    shutil.copy2(src_path, dest_path)
    return dest_path


@dataclass
class Contract:
    id: int
    # retain employee_id for backward compatibility
    employee_id: Optional[int] = None
    # construction-specific identifier (separate from employee)
    construction_id: Optional[int] = None
    start_date: str = ""
    end_date: str = ""
    terms: str = ""
    file_path: Optional[str] = None

    def __repr__(self) -> str:
        return f"Contract(id={self.id}, employee_id={self.employee_id}, start={self.start_date}, end={self.end_date})"

    def save(self) -> None:
        """Insert or update this contract into the DB."""
        # This contract is construction-specific; ensure construction target exists if provided.
        # For backward compatibility, if only employee_id provided, allow saving.
        try:
            from hr_management_app.src.database.database import get_employee_by_id

            if self.construction_id is None and self.employee_id is not None:
                # allow legacy behavior (employee-based contract)
                if get_employee_by_id(int(self.employee_id)) is None:
                    raise ValueError(
                        f"Employee id {self.employee_id} does not exist; cannot save contract."
                    )
        except ImportError:
            # If the DB helper cannot be imported (very early init), skip validation.
            pass
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO contracts (id, employee_id, construction_id, start_date, end_date, terms, contract_file_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    self.id,
                    int(self.employee_id) if self.employee_id is not None else None,
                    int(self.construction_id) if self.construction_id is not None else None,
                    self.start_date,
                    self.end_date,
                    self.terms,
                    self.file_path,
                ),
            )
            conn.commit()

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
        # Support multiple row shapes for backward compatibility.
        # New shape: (id, employee_id, construction_id, start_date, end_date, terms, contract_file_path)
        # Older shapes may be (id, employee_id, start_date, end_date, terms[, contract_file_path])
        if not row:
            raise ValueError("Empty row provided to Contract.from_row")
        if len(row) == 7:
            # id, employee_id, construction_id, start_date, end_date, terms, file
            return cls(
                id=row[0],
                construction_id=row[2],
                employee_id=row[1],
                start_date=row[3],
                end_date=row[4],
                terms=row[5],
                file_path=row[6],
            )
        # legacy 6-column where last is file path
        if len(row) == 6:
            # id, employee_id, start_date, end_date, terms, file
            return cls(
                id=row[0],
                construction_id=None,
                employee_id=row[1],
                start_date=row[2],
                end_date=row[3],
                terms=row[4],
                file_path=row[5],
            )
        if len(row) == 5:
            # id, employee_id, start_date, end_date, terms
            return cls(
                id=row[0],
                construction_id=None,
                employee_id=row[1],
                start_date=row[2],
                end_date=row[3],
                terms=row[4],
                file_path=None,
            )
        # fallback: attempt best-effort mapping
        return cls(id=row[0], construction_id=None, employee_id=row[1], start_date=row[2], end_date=row[3], terms=str(row[4]), file_path=(row[5] if len(row) > 5 else None))

    @classmethod
    def retrieve_contract(cls, id: int) -> Optional["Contract"]:
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, employee_id, construction_id, start_date, end_date, terms, contract_file_path FROM contracts WHERE id = ?",
                (id,),
            )
            row = c.fetchone()
        return cls.from_row(row) if row else None

    @classmethod
    def all_contracts(cls) -> List["Contract"]:
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, employee_id, construction_id, start_date, end_date, terms, contract_file_path FROM contracts"
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
