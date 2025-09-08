from dataclasses import dataclass, asdict
import sqlite3
from typing import Optional, List, Dict

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
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO contracts (id, employee_id, start_date, end_date, terms) VALUES (?, ?, ?, ?, ?)",
                (self.id, self.employee_id, self.start_date, self.end_date, self.terms),
            )

    # backward-compatible alias
    def create_contract(self) -> None:
        self.save()

    def update_contract(self, new_terms: str) -> None:
        """Update contract terms both in object and DB."""
        self.terms = new_terms
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("UPDATE contracts SET terms = ? WHERE id = ?", (new_terms, self.id))

    def delete(self) -> None:
        """Delete this contract from DB."""
        with sqlite3.connect(DB_NAME) as conn:
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
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT id, employee_id, start_date, end_date, terms FROM contracts WHERE id = ?", (id,))
            row = c.fetchone()
        return cls.from_row(row) if row else None

    @classmethod
    def all_contracts(cls) -> List["Contract"]:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT id, employee_id, start_date, end_date, terms FROM contracts")
            rows = c.fetchall()
        return [cls.from_row(r) for r in rows]