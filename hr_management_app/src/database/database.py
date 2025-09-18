import csv
import hashlib
import logging
import os
import random
import secrets
import smtplib
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from typing import List, Optional, Tuple

DB_NAME = os.getenv("HR_MANAGEMENT_TEST_DB", "hr_management.db")

# module logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    # basic configuration (can be overridden by application)
    logging.basicConfig(level=logging.INFO)


@contextmanager
def _conn():
    """Context manager that yields a sqlite3.Connection and ensures it is closed.

    Use like: with _conn() as conn: ...
    This prevents ResourceWarnings when callers forget to close connections.
    """
    # Resolve DB path at call time so tests can override via HR_MANAGEMENT_TEST_DB env var.
    env_db = os.getenv("HR_MANAGEMENT_TEST_DB")
    if env_db:
        # if absolute path provided, use it; otherwise treat as relative to package dir
        if os.path.isabs(env_db):
            path = env_db
        else:
            path = os.path.join(os.path.dirname(__file__), env_db)
    else:
        path = os.path.join(os.path.dirname(__file__), DB_NAME)
    conn = sqlite3.connect(path)
    # ensure core schema exists for this connection (helps tests that change the env var)
    try:
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not c.fetchone():
            # create tables on this connection
            _create_tables(conn)
    except Exception:
        # best-effort; if something goes wrong, let callers handle errors
        pass
    try:
        yield conn
        # commit is usually explicit in callers; do not auto-commit here
    finally:
        try:
            conn.close()
        except Exception:
            pass


def init_db() -> None:
    """Create required tables if missing."""
    with _conn() as conn:
        _create_tables(conn)


def _create_tables(conn) -> None:
    """Create core tables on the given sqlite3 connection object."""
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER,
            construction_id INTEGER,
            parent_contract_id INTEGER,
            area TEXT,
            incharge TEXT,
            start_date TEXT,
            end_date TEXT,
            terms TEXT,
            contract_file_path TEXT
        )
    """
    )
    # Contract subsets (each contract can have many subsets/phases/tasks)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS contract_subsets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER,
            title TEXT,
            description TEXT,
            status TEXT,
            order_index INTEGER DEFAULT 0
        )
    """
    )
    # History of status changes for contract subsets
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS subset_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subset_id INTEGER,
            old_status TEXT,
            new_status TEXT,
            actor_user_id INTEGER,
            changed_at TEXT
        )
    """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            check_in TEXT,
            check_out TEXT
        )
    """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            reset_token TEXT,
            reset_expiry TEXT,
            totp_secret TEXT,
            role TEXT DEFAULT 'engineer'
        )
    """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            employee_number INTEGER UNIQUE,
            name TEXT,
            dob TEXT,
            job_title TEXT,
            role TEXT,
            year_start INTEGER,
            year_end INTEGER,
            profile_pic TEXT,
            contract_type TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """
    )
    # Create useful indices for search performance
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_employees_employee_number ON employees(employee_number)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_contracts_construction_id ON contracts(construction_id)")
    except Exception:
        # ignore if index creation unsupported
        pass
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS role_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            changed_user_id INTEGER,
            old_role TEXT,
            new_role TEXT,
            actor_user_id INTEGER,
            changed_at TEXT
        )
    """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS imputation_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_index INTEGER,
            field TEXT,
            old_value TEXT,
            new_value TEXT,
            source TEXT,
            actor_user_id INTEGER,
            applied_at TEXT
        )
    """
    )
    conn.commit()

    # Create FTS5 virtual table for contracts text search (terms, area, incharge)
    try:
        # Create a shadow FTS table and triggers if not present
        c.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS contracts_fts USING fts5(terms, area, incharge, content='contracts', content_rowid='id')"
        )
        # Triggers to keep FTS in sync
        c.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS contracts_ai AFTER INSERT ON contracts BEGIN
                INSERT INTO contracts_fts(rowid, terms, area, incharge) VALUES (new.id, new.terms, new.area, new.incharge);
            END;
            CREATE TRIGGER IF NOT EXISTS contracts_ad AFTER DELETE ON contracts BEGIN
                INSERT INTO contracts_fts(contracts_fts, rowid, terms, area, incharge) VALUES('delete', old.id, old.terms, old.area, old.incharge);
            END;
            CREATE TRIGGER IF NOT EXISTS contracts_au AFTER UPDATE ON contracts BEGIN
                INSERT INTO contracts_fts(contracts_fts, rowid, terms, area, incharge) VALUES('delete', old.id, old.terms, old.area, old.incharge);
                INSERT INTO contracts_fts(rowid, terms, area, incharge) VALUES (new.id, new.terms, new.area, new.incharge);
            END;
            """
        )
        conn.commit()
    except Exception:
        # FTS may not be available in the SQLite build; that's fine — fall back to LIKE queries
        pass

    # Migration: ensure contract_file_path column exists on older DBs
    def _ensure_column(table: str, column: str, column_type: str = "TEXT") -> None:
        try:
            with _conn() as conn:
                c = conn.cursor()
                c.execute(f"PRAGMA table_info({table})")
                cols = [r[1] for r in c.fetchall()]
                if column not in cols:
                    # ALTER TABLE add column is supported by SQLite and is idempotent here
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                    conn.commit()
        except Exception:
            logger.exception("Failed to ensure column %s on table %s", column, table)

    _ensure_column("contracts", "contract_file_path", "TEXT")
    # ensure new columns for hierarchical contracts exist
    _ensure_column("contracts", "parent_contract_id", "INTEGER")
    _ensure_column("contracts", "area", "TEXT")
    _ensure_column("contracts", "incharge", "TEXT")
    # soft-delete support
    _ensure_column("contracts", "deleted", "INTEGER DEFAULT 0")
    _ensure_column("contracts", "deleted_at", "TEXT")
    # ensure new construction_id column exists and migrate values from old employee_id if present
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("PRAGMA table_info(contracts)")
            cols = [r[1] for r in c.fetchall()]
            if "construction_id" not in cols:
                c.execute("ALTER TABLE contracts ADD COLUMN construction_id INTEGER")
                conn.commit()
                # if employee_id exists, copy values into construction_id for backward compatibility
                if "employee_id" in cols:
                    try:
                        c.execute(
                            "UPDATE contracts SET construction_id = employee_id WHERE construction_id IS NULL AND employee_id IS NOT NULL"
                        )
                        conn.commit()
                    except Exception:
                        logger.exception(
                            "Failed to copy employee_id -> construction_id during migration"
                        )
    except Exception:
        logger.exception("Failed to ensure construction_id column on contracts table")

    def _safe_lastrowid(cursor) -> int:
        """Return an int lastrowid or 0 if None/invalid."""
        try:
            lid = getattr(cursor, "lastrowid", None)
            if lid is None:
                return 0
            return int(lid)
        except Exception:
            return 0


def record_imputation_audit(
    row_index: int,
    field: str,
    old_value: Optional[str],
    new_value: Optional[str],
    source: str = "import_preview",
    actor_user_id: Optional[int] = None,
) -> None:
    """Record an imputation decision into the imputation_audit table.

    row_index: the index in the imported batch (0-based) for traceability.
    field: the field name that was imputed (e.g., 'job_title').
    old_value/new_value: textual values prior to and after imputation.
    source: where the imputation originated (preview, ml, heuristic, etc.).
    actor_user_id: optional user id who accepted the imputation.
    """
    try:
        from datetime import datetime

        applied_at = datetime.now(timezone.utc).isoformat()
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO imputation_audit (row_index, field, old_value, new_value, source, actor_user_id, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    row_index,
                    field,
                    old_value,
                    new_value,
                    source,
                    actor_user_id,
                    applied_at,
                ),
            )
            conn.commit()
    except Exception:
        logger.exception(
            "Failed to write imputation_audit for row %s field %s", row_index, field
        )


def export_imputation_audit_csv(path: str) -> int:
    """Export imputation_audit table to CSV. Returns number of rows exported."""
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT row_index, field, old_value, new_value, source, actor_user_id, applied_at FROM imputation_audit ORDER BY id"
            )
            rows = c.fetchall()
        # write CSV
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "row_index",
                    "field",
                    "old_value",
                    "new_value",
                    "source",
                    "actor_user_id",
                    "applied_at",
                ]
            )
            for r in rows:
                writer.writerow(r)
        return len(rows)
    except Exception as exc:
        logger.exception("Failed to export imputation_audit to %s: %s", path, exc)
        raise


# ---------- Contracts ----------
def add_contract_to_db(contract) -> None:
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT OR REPLACE INTO contracts (id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                contract.id,
                contract.employee_id,
                getattr(contract, "construction_id", None),
                getattr(contract, "parent_contract_id", None),
                contract.start_date,
                contract.end_date,
                getattr(contract, "area", None),
                getattr(contract, "incharge", None),
                contract.terms,
                getattr(contract, "file_path", None),
            ),
        )
        conn.commit()


def get_all_contracts() -> List[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        # prefer shape with deleted columns when present; fall back if older DB
        try:
            c.execute(
                "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path, deleted, deleted_at FROM contracts"
            )
            return c.fetchall()
        except Exception:
            # older DB without deleted columns
            c.execute(
                "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path FROM contracts"
            )
            return c.fetchall()


def get_all_contracts_filtered(include_deleted: bool = False) -> List[Tuple]:
    """Return contracts rows; by default exclude soft-deleted rows.

    If include_deleted is True, return all rows including deleted ones.
    The returned row shape prefers the full set of columns (including deleted/deleted_at) when available.
    """
    with _conn() as conn:
        c = conn.cursor()
        # attempt to use deleted column in WHERE; if missing, fall back to simple select
        try:
            if include_deleted:
                c.execute(
                    "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path, deleted, deleted_at FROM contracts"
                )
            else:
                c.execute(
                    "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path, deleted, deleted_at FROM contracts WHERE deleted = 0"
                )
            return c.fetchall()
        except Exception:
            # older DB without deleted column
            c.execute(
                "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path FROM contracts"
            )
            return c.fetchall()


def search_contracts(term: str, include_deleted: bool = False, limit: Optional[int] = None) -> List[Tuple]:
    """Search contracts by id, area, incharge, terms, or construction_id.

    term: search string; numeric strings will be matched against id and construction_id.
    include_deleted: include soft-deleted rows when True.
    limit: optional cap on returned rows.
    Returns list of rows in the same shape as get_all_contracts_filtered.
    """
    term = (term or "").strip()
    term = (term or "").strip()
    with _conn() as conn:
        c = conn.cursor()
        # Prefer FTS5 when available for text search
        try:
            # check if FTS table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contracts_fts'")
            if c.fetchone() and term:
                # Use MATCH for fts5; numeric terms should match id/construction_id OR the FTS match
                params: List[object] = []
                search_or: List[str] = []
                if term.isdigit():
                    search_or.append("(id = ? OR construction_id = ?)")
                    params.extend([int(term), int(term)])
                # FTS MATCH query (match against terms, area, incharge)
                search_or.append("id IN (SELECT rowid FROM contracts_fts WHERE contracts_fts MATCH ?)")
                params.append(term)
                where = []
                where.append("(" + " OR ".join(search_or) + ")")
                if not include_deleted:
                    where.append("(deleted IS NULL OR deleted = 0)")
                sql = "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path, deleted, deleted_at FROM contracts WHERE " + " AND ".join(where) + " ORDER BY id DESC"
                if limit and int(limit) > 0:
                    sql += f" LIMIT {int(limit)}"
                c.execute(sql, tuple(params))
                return c.fetchall()
        except Exception:
            # if anything goes wrong with FTS, fall back
            pass

        # Fallback to LIKE-based search (older SQLite)
        params: List[object] = []
        search_parts: List[str] = []
        if term:
            like = f"%{term}%"
            search_parts.append("(area LIKE ? OR incharge LIKE ? OR terms LIKE ?)")
            params.extend([like, like, like])
            if term.isdigit():
                search_parts.append("(id = ? OR construction_id = ?)")
                params.extend([int(term), int(term)])
        where_clauses: List[str] = []
        if search_parts:
            where_clauses.append("(" + " OR ".join(search_parts) + ")")
        if not include_deleted:
            where_clauses.append("(deleted IS NULL OR deleted = 0)")
        where_sql = ""
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)
        limit_sql = f" LIMIT {int(limit)}" if limit and int(limit) > 0 else ""
        base = "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path, deleted, deleted_at FROM contracts"
        sql = base + where_sql + " ORDER BY id DESC" + limit_sql
        c.execute(sql, tuple(params))
        return c.fetchall()


# ---------- Contract subsets & status tracking ----------
STATUS_CHOICES = [
    "starting",
    "to do",
    "in progress",
    "final settlement of phase 1",
    "final settlement of phase 2",
    "audit phase 1",
    "audit phase 2",
    "complete",
    "fail",
    "closing",
    "done",
]

COMPLETED_STATUSES = set(
    [
        "final settlement of phase 1",
        "final settlement of phase 2",
        "audit phase 1",
        "audit phase 2",
        "complete",
        "done",
        "closing",
    ]
)

STATUS_COLORS = {
    "starting": "#E0E0E0",
    "to do": "#FFEB3B",
    "in progress": "#2196F3",
    "final settlement of phase 1": "#4CAF50",
    "final settlement of phase 2": "#43A047",
    "audit phase 1": "#FF9800",
    "audit phase 2": "#FB8C00",
    "complete": "#2E7D32",
    "fail": "#B71C1C",
    "closing": "#6A1B9A",
    "done": "#1B5E20",
}


def create_contract_subset(
    contract_id: int,
    title: str,
    description: str = "",
    status: str = "starting",
    order_index: int = 0,
) -> int:
    if status not in STATUS_CHOICES:
        raise ValueError(
            f"Invalid status '{status}'. Allowed: {', '.join(STATUS_CHOICES)}"
        )
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO contract_subsets (contract_id, title, description, status, order_index)
            VALUES (?, ?, ?, ?, ?)
        """,
            (contract_id, title, description, status, order_index),
        )
        conn.commit()
        lid = getattr(c, "lastrowid", None)
        return int(lid) if lid is not None else 0


def get_subsets_for_contract(contract_id: int) -> List[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT id, contract_id, title, description, status, order_index
            FROM contract_subsets WHERE contract_id = ? ORDER BY order_index, id
        """,
            (contract_id,),
        )
        return c.fetchall()


def get_child_contracts(contract_id: int) -> List[Tuple]:
    """Return list of contracts that have parent_contract_id == contract_id."""
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path FROM contracts WHERE parent_contract_id = ?",
            (contract_id,),
        )
        return c.fetchall()


def get_subsets_count(contract_id: int) -> int:
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(1) FROM contract_subsets WHERE contract_id = ?",
            (contract_id,),
        )
        row = c.fetchone()
        return int(row[0]) if row and row[0] else 0


def get_contract_by_id(
    contract_id: int, include_deleted: bool = False
) -> Optional[Tuple]:
    """Return a single contract row by id. If include_deleted is False, only returns non-deleted rows.

    Returns None if not found. The returned tuple follows the `get_all_contracts` shape when possible.
    """
    with _conn() as conn:
        c = conn.cursor()
        try:
            if include_deleted:
                c.execute(
                    "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path, deleted, deleted_at FROM contracts WHERE id = ?",
                    (contract_id,),
                )
            else:
                c.execute(
                    "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path, deleted, deleted_at FROM contracts WHERE id = ? AND (deleted IS NULL OR deleted = 0)",
                    (contract_id,),
                )
            row = c.fetchone()
            return row
        except Exception:
            # older DBs may not have deleted columns
            c.execute(
                "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path FROM contracts WHERE id = ?",
                (contract_id,),
            )
            return c.fetchone()


def soft_delete_contract(contract_id: int, cascade: bool = True) -> None:
    """Mark a contract (and optionally descendants) as deleted (soft delete).

    This sets contracts.deleted = 1 and deleted_at to now(). Subsets are not removed so they can be restored with the contract.
    """
    try:
        from datetime import datetime

        when = datetime.now().isoformat()
        with _conn() as conn:
            c = conn.cursor()
            # collect all descendant contract ids (DFS)
            to_mark = [int(contract_id)]
            if cascade:
                stack = [int(contract_id)]
                while stack:
                    cur = stack.pop()
                    c.execute(
                        "SELECT id FROM contracts WHERE parent_contract_id = ?", (cur,)
                    )
                    rows = c.fetchall()
                    for r in rows:
                        cid = int(r[0])
                        to_mark.append(cid)
                        stack.append(cid)

            for cid in set(to_mark):
                try:
                    c.execute(
                        "UPDATE contracts SET deleted = 1, deleted_at = ? WHERE id = ?",
                        (when, cid),
                    )
                except Exception:
                    # best-effort per-row update
                    logger.exception("Failed to soft-delete contract %s", cid)
            conn.commit()
    except Exception:
        logger.exception("Failed to soft-delete contract %s", contract_id)
        raise


def restore_contract(contract_id: int, cascade: bool = True) -> None:
    """Restore a soft-deleted contract (and optionally descendants).

    Clears deleted flag and deleted_at timestamp.
    """
    try:
        with _conn() as conn:
            c = conn.cursor()
            to_unmark = [int(contract_id)]
            if cascade:
                stack = [int(contract_id)]
                while stack:
                    cur = stack.pop()
                    c.execute(
                        "SELECT id FROM contracts WHERE parent_contract_id = ?", (cur,)
                    )
                    rows = c.fetchall()
                    for r in rows:
                        cid = int(r[0])
                        to_unmark.append(cid)
                        stack.append(cid)

            for cid in set(to_unmark):
                try:
                    c.execute(
                        "UPDATE contracts SET deleted = 0, deleted_at = NULL WHERE id = ?",
                        (cid,),
                    )
                except Exception:
                    logger.exception("Failed to restore contract %s", cid)
            conn.commit()
    except Exception:
        logger.exception("Failed to restore contract %s", contract_id)
        raise


def list_trashed_contracts() -> List[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "SELECT id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, contract_file_path, deleted, deleted_at FROM contracts WHERE deleted = 1"
            )
            return c.fetchall()
        except Exception:
            # older DB, no trashed items
            return []


def purge_deleted_older_than(days: int) -> int:
    """Permanently remove soft-deleted contracts older than `days` days.

    Returns number of contracts purged.
    """
    try:
        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        purged = 0
        with _conn() as conn:
            c = conn.cursor()
            # find ids to purge
            try:
                c.execute(
                    "SELECT id FROM contracts WHERE deleted = 1 AND deleted_at < ?",
                    (cutoff,),
                )
                rows = c.fetchall()
            except Exception:
                return 0
            ids = [r[0] for r in rows]
            if not ids:
                return 0
            # reuse existing hard-delete helper for each id
            for cid in ids:
                delete_contract_and_descendants(cid)
                purged += 1
        return purged
    except Exception:
        logger.exception("Failed to purge deleted contracts")
        raise


def delete_contract_and_descendants(contract_id: int) -> None:
    """Recursively delete a contract, its subsets, subset history, and all descendant contracts.

    This operates in a single transaction to ensure consistency.
    """
    try:
        with _conn() as conn:
            c = conn.cursor()
            # collect all descendant contract ids (DFS)
            to_delete = []
            stack = [int(contract_id)]
            while stack:
                cur = stack.pop()
                to_delete.append(cur)
                c.execute(
                    "SELECT id FROM contracts WHERE parent_contract_id = ?", (cur,)
                )
                rows = c.fetchall()
                for r in rows:
                    stack.append(r[0])

            # delete subsets and their history for each contract id
            for cid in to_delete:
                # delete history entries for subsets belonging to this contract
                c.execute(
                    "SELECT id FROM contract_subsets WHERE contract_id = ?",
                    (cid,),
                )
                subset_ids = [r[0] for r in c.fetchall()]
                if subset_ids:
                    # delete subset status history
                    c.executemany(
                        "DELETE FROM subset_status_history WHERE subset_id = ?",
                        [(sid,) for sid in subset_ids],
                    )
                    # delete subsets
                    c.executemany(
                        "DELETE FROM contract_subsets WHERE id = ?",
                        [(sid,) for sid in subset_ids],
                    )
            # finally delete contracts themselves
            c.executemany(
                "DELETE FROM contracts WHERE id = ?", [(cid,) for cid in to_delete]
            )
            conn.commit()
    except Exception:
        logger.exception("Failed to delete contract %s and descendants", contract_id)
        raise


def update_subset_status(
    subset_id: int, new_status: str, actor_user_id: Optional[int] = None
) -> None:
    """Update subset status and record history.

    actor_user_id is required (audit) and must be one of allowed roles.
    """
    if new_status not in STATUS_CHOICES:
        raise ValueError(f"Invalid status '{new_status}'")
    # actor must be provided for auditing
    if actor_user_id is None:
        raise PermissionError("actor_user_id is required to change subset status")
    # permission check: only certain roles may change subset status
    allowed_roles = ("accountant", "manager", "high_manager", "admin")
    actor = get_user_by_id(actor_user_id)
    actor_role = actor[-1] if actor else None
    if actor_role not in allowed_roles:
        raise PermissionError(
            f"Actor role '{actor_role}' is not permitted to change subset status"
        )
    from datetime import datetime

    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT status FROM contract_subsets WHERE id = ?", (subset_id,))
        row = c.fetchone()
        old_status = row[0] if row else None
        c.execute(
            "UPDATE contract_subsets SET status = ? WHERE id = ?",
            (new_status, subset_id),
        )
        changed_at = datetime.now().isoformat()
        c.execute(
            """
            INSERT INTO subset_status_history (subset_id, old_status, new_status, actor_user_id, changed_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (subset_id, old_status, new_status, actor_user_id, changed_at),
        )
        conn.commit()


def get_subset_status_history(subset_id: int) -> List[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT id, subset_id, old_status, new_status, actor_user_id, changed_at
            FROM subset_status_history WHERE subset_id = ? ORDER BY id
        """,
            (subset_id,),
        )
        return c.fetchall()


def get_status_color(status: str) -> str:
    return STATUS_COLORS.get(status, "#9E9E9E")


# ---------- Auth / Users ----------
def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex()


def get_admin_user() -> Optional[Tuple]:
    """Return the admin user row, or None if no admin exists."""
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, email, role FROM users WHERE role = 'admin' LIMIT 1")
        return c.fetchone()


def create_user(email: str, password: str, role: str = "engineer") -> int:
    email = email.strip().lower()
    salt = os.urandom(16)
    pwd_hash = _hash_password(password, salt)
    if role == "admin" and get_admin_user():
        raise PermissionError(
            "There is already an admin account. Only one admin is allowed."
        )
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (email, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                (email, pwd_hash, salt.hex(), role),
            )
            conn.commit()
            lid = getattr(c, "lastrowid", None)
            return int(lid) if lid is not None else 0
    except sqlite3.IntegrityError as ie:
        raise ValueError("Email already registered") from ie
    except Exception as exc:
        raise RuntimeError(f"Failed to create user: {exc}") from exc


def get_user_by_email(email: str) -> Optional[Tuple]:
    email = email.strip().lower()
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, email, password_hash, salt, reset_token, reset_expiry, totp_secret, role FROM users WHERE email = ?",
            (email,),
        )
        return c.fetchone()


def get_user_by_id(user_id: int) -> Optional[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, email, password_hash, salt, reset_token, reset_expiry, totp_secret, role FROM users WHERE id = ?",
            (user_id,),
        )
        return c.fetchone()


def verify_user(email: str, password: str) -> bool:
    row = get_user_by_email(email)
    if not row:
        return False
    _, _, stored_hash, salt_hex, _, _, _, _ = row
    salt = bytes.fromhex(salt_hex)
    return _hash_password(password, salt) == stored_hash


def create_reset_token(email: str, hours_valid: int = 1) -> str:
    token = secrets.token_urlsafe(32)
    expiry = (datetime.now(timezone.utc) + timedelta(hours=hours_valid)).isoformat()
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE users SET reset_token = ?, reset_expiry = ? WHERE email = ?",
            (token, expiry, email.strip().lower()),
        )
        conn.commit()
    return token


def reset_password_with_token(token: str, new_password: str) -> bool:
    now_dt = datetime.now(timezone.utc)
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, email, reset_expiry FROM users WHERE reset_token = ?", (token,)
        )
        row = c.fetchone()
        if not row:
            return False
        _, _, reset_expiry = row
        if reset_expiry is None:
            return False
        try:
            expiry_dt = datetime.fromisoformat(reset_expiry)
        except Exception:
            # malformed expiry value; deny reset
            logger.warning("Malformed reset_expiry for token: %s", token)
            return False
        if expiry_dt < now_dt:
            return False
        salt = os.urandom(16)
        pwd_hash = _hash_password(new_password, salt)
        c.execute(
            "UPDATE users SET password_hash = ?, salt = ?, reset_token = NULL, reset_expiry = NULL WHERE reset_token = ?",
            (pwd_hash, salt.hex(), token),
        )
        conn.commit()
    return True


# ---------- Email helpers (requires email_config.py) ----------
def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Send an email using settings in src/email_config.py.
    Raises RuntimeError with a helpful message on failure.
    """
    try:
        from email_config import (
            FROM_EMAIL,
            SMTP_CONFIGURED,
            SMTP_PASSWORD,
            SMTP_PORT,
            SMTP_SERVER,
            SMTP_USE_SSL,
            SMTP_USER,
        )
    except Exception as e:
        logger.exception("Failed to import email_config: %s", e)
        raise RuntimeError(
            "Missing or invalid email_config.py in src/ — create it with SMTP settings."
        ) from e

    # If SMTP isn't configured (development), skip sending and log.
    if not SMTP_CONFIGURED:
        logger.info("SMTP not configured; skipping send to %s", to_email)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(body)

    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15) as smtp:
                if SMTP_USER:
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                if SMTP_USER:
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as ex:
        logger.exception("SMTP auth failed: %s", ex)
        raise RuntimeError(
            "SMTP authentication failed: check SMTP_USER and SMTP_PASSWORD. "
            "For Gmail, enable 2-Step Verification and use an App Password."
        ) from ex
    except Exception as ex:
        logger.exception("Failed to send email: %s", ex)
        raise RuntimeError(f"Failed to send email: {ex}") from ex


def send_password_reset_email(email: str, token: str) -> None:
    reset_text = f"Use this token to reset your password (valid for one hour):\n\n{token}\n\nIf you did not request this, ignore."
    send_email(email, "Password reset for HR Management", reset_text)


def generate_verification_code() -> str:
    return f"{random.randint(100000, 999999):06d}"


def send_verification_code(email: str, code: str) -> None:
    subject = "Your HR Management Verification Code"
    body = f"Your verification code is: {code}\n\nEnter this code to complete your sign up."
    send_email(email, subject, body)


# ---------- Employees ----------
def create_employee(
    user_id: Optional[int],
    name: str,
    dob: Optional[str],
    job_title: Optional[str],
    role: Optional[str],
    year_start: Optional[int],
    profile_pic: Optional[str],
    contract_type: Optional[str],
    year_end: Optional[int] = None,
) -> int:
    """
    Creates an employee row. Accepts keyword args (used by GUI/signup).
    """
    # basic validation
    current_year = datetime.now(timezone.utc).year
    if year_start is not None:
        if not (1975 <= int(year_start) <= current_year):
            raise ValueError(f"year_start must be between 1975 and {current_year}")
    if role is not None and role not in ALLOWED_ROLES:
        raise ValueError(
            f"Invalid role '{role}'. Allowed roles: {', '.join(ALLOWED_ROLES)}"
        )

    try:
        with _conn() as conn:
            c = conn.cursor()
            # if user_id provided, ensure no existing employee for that user
            if user_id is not None:
                c.execute("SELECT id FROM employees WHERE user_id = ?", (user_id,))
                if c.fetchone():
                    raise ValueError("Employee already exists for this user_id")
            c.execute("SELECT MAX(employee_number) FROM employees")
            row = c.fetchone()
            max_num = row[0] if row and row[0] else 999
            employee_number = max_num + 1
            c.execute(
                """
                INSERT INTO employees (user_id, employee_number, name, dob, job_title, role, year_start, year_end, profile_pic, contract_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    employee_number,
                    name,
                    dob,
                    job_title,
                    role,
                    year_start,
                    year_end,
                    profile_pic,
                    contract_type,
                ),
            )
            conn.commit()
            lid = getattr(c, "lastrowid", None)
            return int(lid) if lid is not None else 0
    except sqlite3.IntegrityError as ie:
        raise ValueError(
            "Employee creation failed: unique constraint violation"
        ) from ie
    except Exception as exc:
        raise RuntimeError(f"Failed to create employee: {exc}") from exc


def get_employee_by_user(user_id: int) -> Optional[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, user_id, employee_number, name, dob, job_title, role, year_start, year_end, profile_pic, contract_type FROM employees WHERE user_id = ?",
            (user_id,),
        )
        return c.fetchone()


def get_employee_by_id(emp_id: int) -> Optional[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, user_id, employee_number, name, dob, job_title, role, year_start, year_end, profile_pic, contract_type FROM employees WHERE id = ?",
            (emp_id,),
        )
        return c.fetchone()


def search_employees(term: str, limit: Optional[int] = None) -> List[Tuple]:
    """Search employees by name, job_title, role, or employee_number.

    term: free-text; numeric strings will match employee_number and id.
    Returns list of rows: id, user_id, employee_number, name, dob, job_title, role, year_start, year_end, profile_pic, contract_type
    """
    term = (term or "").strip()
    with _conn() as conn:
        c = conn.cursor()
        params = []
        search_parts = []
        if term:
            like = f"%{term}%"
            search_parts.append("(name LIKE ? OR job_title LIKE ? OR role LIKE ?)")
            params.extend([like, like, like])
            if term.isdigit():
                search_parts.append("(employee_number = ? OR id = ?)")
                params.extend([int(term), int(term)])
        where_sql = ""
        if search_parts:
            where_sql = " WHERE (" + " OR ".join(search_parts) + ")"
        limit_sql = f" LIMIT {int(limit)}" if limit and int(limit) > 0 else ""
        sql = (
            "SELECT id, user_id, employee_number, name, dob, job_title, role, year_start, year_end, profile_pic, contract_type FROM employees"
            + where_sql
            + " ORDER BY id DESC"
            + limit_sql
        )
        c.execute(sql, tuple(params))
        return c.fetchall()


def update_employee(emp_id: int, **kwargs) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs.keys())
    vals = list(kwargs.values())
    vals.append(emp_id)
    with _conn() as conn:
        c = conn.cursor()
        c.execute(f"UPDATE employees SET {cols} WHERE id = ?", vals)
        conn.commit()


# ---------- Attendance ----------
def has_checkin_today(employee_id: int) -> bool:
    today_start = datetime.combine(date.today(), datetime.min.time()).isoformat()
    today_end = datetime.combine(date.today(), datetime.max.time()).isoformat()
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT 1 FROM attendance
            WHERE employee_id = ? AND check_in BETWEEN ? AND ?
            LIMIT 1
        """,
            (employee_id, today_start, today_end),
        )
        return c.fetchone() is not None


def has_open_session(employee_id: int) -> bool:
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT 1 FROM attendance WHERE employee_id = ? AND check_out IS NULL LIMIT 1",
            (employee_id,),
        )
        return c.fetchone() is not None


def record_check_in(employee_id: int) -> Optional[str]:
    if has_checkin_today(employee_id):
        return None
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO attendance (employee_id, check_in, check_out) VALUES (?, ?, NULL)",
            (employee_id, now),
        )
        conn.commit()
        return now


def record_check_out(employee_id: int) -> Optional[str]:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT id FROM attendance
            WHERE employee_id = ? AND check_out IS NULL
            ORDER BY check_in DESC
            LIMIT 1
        """,
            (employee_id,),
        )
        row = c.fetchone()
        if not row:
            return None
        attendance_id = row[0]
        c.execute(
            "UPDATE attendance SET check_out = ? WHERE id = ?", (now, attendance_id)
        )
        conn.commit()
        return now


def get_work_seconds_in_period(employee_id: int, start_iso: str, end_iso: str) -> int:
    total_seconds = 0
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT check_in, check_out FROM attendance
            WHERE employee_id = ? AND check_out IS NOT NULL
              AND (
                    (check_in BETWEEN ? AND ?)
                 OR (check_out BETWEEN ? AND ?)
                 OR (check_in <= ? AND check_out >= ?)
              )
        """,
            (employee_id, start_iso, end_iso, start_iso, end_iso, start_iso, end_iso),
        )
        rows = c.fetchall()
    for check_in, check_out in rows:
        try:
            in_time = datetime.fromisoformat(check_in)
            out_time = datetime.fromisoformat(check_out)
            period_start = datetime.fromisoformat(start_iso)
            period_end = datetime.fromisoformat(end_iso)
            if in_time < period_start:
                in_time = period_start
            if out_time > period_end:
                out_time = period_end
            delta = (out_time - in_time).total_seconds()
            if delta > 0:
                total_seconds += delta
        except Exception:
            continue
    return int(total_seconds)


def get_month_work_seconds(employee_id: int, year: int, month: int) -> int:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(seconds=1)
    return get_work_seconds_in_period(employee_id, start.isoformat(), end.isoformat())


# ---------- Calculate Salary ----------
def calculate_salary(
    employee_id: int, start_date: str, end_date: str, hourly_wage: float
) -> float:
    try:
        try:
            s = datetime.fromisoformat(start_date)
        except Exception:
            s = datetime.strptime(start_date, "%Y-%m-%d")
        try:
            e = datetime.fromisoformat(end_date)
        except Exception:
            e = datetime.strptime(end_date, "%Y-%m-%d")
        start_iso = datetime(s.year, s.month, s.day, 0, 0, 0).isoformat()
        end_iso = datetime(e.year, e.month, e.day, 23, 59, 59).isoformat()
        seconds = get_work_seconds_in_period(employee_id, start_iso, end_iso)
        hours = seconds / 3600.0
        salary = round(hours * float(hourly_wage), 2)
        return salary
    except Exception as exc:
        raise RuntimeError(f"Failed to calculate salary: {exc}")


# ---------- Admin / User management ----------
def get_all_users() -> list:
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, email, role FROM users")
        return c.fetchall()


def update_user_role(
    user_id: int, new_role: str, actor_user_id: Optional[int] = None
) -> None:
    """
    Update a user's role. Optionally record who performed the change (actor_user_id) in the role_audit table.
    """
    if new_role == "admin" and get_admin_user():
        raise PermissionError(
            "Only one admin account is allowed. Transfer admin role before assigning."
        )
    with _conn() as conn:
        c = conn.cursor()
        # fetch old role for audit
        c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        old_role = row[0] if row else None
        c.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        # insert audit record
        try:
            from datetime import datetime

            changed_at = datetime.now(timezone.utc).isoformat()
            c.execute(
                "INSERT INTO role_audit (changed_user_id, old_role, new_role, actor_user_id, changed_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, old_role, new_role, actor_user_id, changed_at),
            )
        except Exception:
            # do not fail the update if audit insert fails; log and continue
            logger.exception("Failed to write role_audit for user %s", user_id)
        conn.commit()


def delete_user_with_admin_check(
    user_id: int, transfer_to_user_id: Optional[int] = None
) -> bool:
    """
    Prevents deletion of an admin account unless the role is transferred to another user.
    Returns True if deletion succeeded, False otherwise.
    """
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        if not row:
            raise ValueError("User not found.")
        role = row[0]
        if role == "admin":
            if not transfer_to_user_id:
                raise PermissionError(
                    "Admin account cannot be deleted unless the role is transferred."
                )
            # Transfer admin role
            c.execute(
                "UPDATE users SET role = 'admin' WHERE id = ?", (transfer_to_user_id,)
            )
            c.execute("UPDATE users SET role = 'engineer' WHERE id = ?", (user_id,))
        # Now delete the user (and optionally cascade employees) - only delete user row here
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True


def delete_user(user_id: int) -> None:
    with _conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM employees WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()


# ---------- Role Permission Logic ----------
ROLE_HIERARCHY = {
    "admin": 4,
    "high_manager": 3,
    "manager": 2,
    "accountant": 1,
    "engineer": 0,
    "driver": 0,
    "construction_worker": 0,
}

ALLOWED_ROLES = [
    "engineer",
    "accountant",
    "manager",
    "high_manager",
    "admin",
    "driver",
    "construction_worker",
]


def can_edit(target_role: str, actor_role: str) -> bool:
    """Can actor edit target? Only if actor's role is higher."""
    return ROLE_HIERARCHY.get(actor_role, -1) > ROLE_HIERARCHY.get(target_role, -1)


def can_delete(target_role: str, actor_role: str) -> bool:
    """Only admin can delete users (other than admin)"""
    return actor_role == "admin" and target_role != "admin"


def can_view_salary(actor_role: str) -> bool:
    """Who can view salary? Admin, high_manager, accountant."""
    return actor_role in ("admin", "high_manager", "accountant")


def can_count_salary(actor_role: str) -> bool:
    """Who can use salary counting? Only accountant."""
    return actor_role == "accountant"


def can_grant_role(actor_role: str, target_role: str) -> bool:
    """
    Can actor grant target_role? Actor must have higher hierarchy value.
    Non-admins cannot grant admin or high_manager roles.
    """
    # Only manager, high_manager and admin can perform role assignments
    if actor_role not in ("admin", "high_manager", "manager"):
        return False
    # Non-admins cannot grant admin or high_manager roles
    if actor_role != "admin" and target_role in ("admin", "high_manager"):
        return False
    return ROLE_HIERARCHY.get(actor_role, -1) > ROLE_HIERARCHY.get(target_role, -1)


def can_edit_info(actor_role: str, target_role: str) -> bool:
    return can_edit(target_role, actor_role)


def can_view_working_hours(
    actor_role: str, target_user_id: int, actor_user_id: int
) -> bool:
    """Accountant can view all, engineer only self, managers view below their level."""
    if actor_role == "accountant":
        return True
    if actor_role == "engineer":
        return target_user_id == actor_user_id
    target = get_user_by_id(target_user_id)
    if not target:
        return False
    target_role_val = target[-1]
    return can_edit(target_role_val, actor_role)


# Ensure DB and tables exist when the module is imported
try:
    init_db()
except Exception as exc:
    logger.exception("Failed to initialize DB: %s", exc)
