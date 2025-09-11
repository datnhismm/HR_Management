import os
import sqlite3
from contextlib import contextmanager
import hashlib
import secrets
import smtplib
import random
import logging
import csv
from datetime import datetime, timedelta, date, timezone
from email.message import EmailMessage
from typing import List, Tuple, Optional

DB_NAME = "hr_management.db"

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
    path = os.path.join(os.path.dirname(__file__), DB_NAME)
    conn = sqlite3.connect(path)
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
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY,
                employee_id INTEGER,
                start_date TEXT,
                end_date TEXT,
                terms TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                check_in TEXT,
                check_out TEXT
            )
        ''')
        c.execute('''
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
        ''')
        c.execute('''
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
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS role_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                changed_user_id INTEGER,
                old_role TEXT,
                new_role TEXT,
                actor_user_id INTEGER,
                changed_at TEXT
            )
        ''')
        c.execute('''
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
        ''')
        conn.commit()


def record_imputation_audit(row_index: int, field: str, old_value: Optional[str], new_value: Optional[str], source: str = "import_preview", actor_user_id: Optional[int] = None) -> None:
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
                (row_index, field, old_value, new_value, source, actor_user_id, applied_at),
            )
            conn.commit()
    except Exception:
        logger.exception("Failed to write imputation_audit for row %s field %s", row_index, field)


def export_imputation_audit_csv(path: str) -> int:
    """Export imputation_audit table to CSV. Returns number of rows exported."""
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT row_index, field, old_value, new_value, source, actor_user_id, applied_at FROM imputation_audit ORDER BY id")
            rows = c.fetchall()
        # write CSV
        with open(path, "w", newline='', encoding='utf-8') as fh:
            writer = csv.writer(fh)
            writer.writerow(["row_index", "field", "old_value", "new_value", "source", "actor_user_id", "applied_at"])
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
        c.execute('''
            INSERT OR REPLACE INTO contracts (id, employee_id, start_date, end_date, terms)
            VALUES (?, ?, ?, ?, ?)
        ''', (contract.id, contract.employee_id, contract.start_date, contract.end_date, contract.terms))
        conn.commit()

def get_all_contracts() -> List[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        c.execute('SELECT id, employee_id, start_date, end_date, terms FROM contracts')
        return c.fetchall()

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
        raise PermissionError("There is already an admin account. Only one admin is allowed.")
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (email, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                      (email, pwd_hash, salt.hex(), role))
            conn.commit()
            lid = c.lastrowid
            return int(lid) if lid is not None else 0
    except sqlite3.IntegrityError as ie:
        raise ValueError("Email already registered") from ie
    except Exception as exc:
        raise RuntimeError(f"Failed to create user: {exc}") from exc

def get_user_by_email(email: str) -> Optional[Tuple]:
    email = email.strip().lower()
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, email, password_hash, salt, reset_token, reset_expiry, totp_secret, role FROM users WHERE email = ?", (email,))
        return c.fetchone()

def get_user_by_id(user_id: int) -> Optional[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, email, password_hash, salt, reset_token, reset_expiry, totp_secret, role FROM users WHERE id = ?", (user_id,))
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
        c.execute("UPDATE users SET reset_token = ?, reset_expiry = ? WHERE email = ?", (token, expiry, email.strip().lower()))
        conn.commit()
    return token

def reset_password_with_token(token: str, new_password: str) -> bool:
    now_dt = datetime.now(timezone.utc)
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, email, reset_expiry FROM users WHERE reset_token = ?", (token,))
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
        c.execute("UPDATE users SET password_hash = ?, salt = ?, reset_token = NULL, reset_expiry = NULL WHERE reset_token = ?",
                  (pwd_hash, salt.hex(), token))
        conn.commit()
    return True

# ---------- Email helpers (requires email_config.py) ----------
def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Send an email using settings in src/email_config.py.
    Raises RuntimeError with a helpful message on failure.
    """
    try:
        from email_config import SMTP_SERVER, SMTP_PORT, SMTP_USE_SSL, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL, SMTP_CONFIGURED
    except Exception as e:
        logger.exception("Failed to import email_config: %s", e)
        raise RuntimeError("Missing or invalid email_config.py in src/ — create it with SMTP settings.") from e

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
def create_employee(user_id: Optional[int],
                    name: str,
                    dob: Optional[str],
                    job_title: Optional[str],
                    role: Optional[str],
                    year_start: Optional[int],
                    profile_pic: Optional[str],
                    contract_type: Optional[str],
                    year_end: Optional[int] = None) -> int:
    """
    Creates an employee row. Accepts keyword args (used by GUI/signup).
    """
    # basic validation
    current_year = datetime.now(timezone.utc).year
    if year_start is not None:
        if not (1975 <= int(year_start) <= current_year):
            raise ValueError(f"year_start must be between 1975 and {current_year}")
    if role is not None and role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role '{role}'. Allowed roles: {', '.join(ALLOWED_ROLES)}")

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
            c.execute('''
                INSERT INTO employees (user_id, employee_number, name, dob, job_title, role, year_start, year_end, profile_pic, contract_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, employee_number, name, dob, job_title, role, year_start, year_end, profile_pic, contract_type))
            conn.commit()
            lid = c.lastrowid
            return int(lid) if lid is not None else 0
    except sqlite3.IntegrityError as ie:
        raise ValueError("Employee creation failed: unique constraint violation") from ie
    except Exception as exc:
        raise RuntimeError(f"Failed to create employee: {exc}") from exc

def get_employee_by_user(user_id: int) -> Optional[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, user_id, employee_number, name, dob, job_title, role, year_start, year_end, profile_pic, contract_type FROM employees WHERE user_id = ?", (user_id,))
        return c.fetchone()

def get_employee_by_id(emp_id: int) -> Optional[Tuple]:
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, user_id, employee_number, name, dob, job_title, role, year_start, year_end, profile_pic, contract_type FROM employees WHERE id = ?", (emp_id,))
        return c.fetchone()

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
        c.execute('''
            SELECT 1 FROM attendance
            WHERE employee_id = ? AND check_in BETWEEN ? AND ?
            LIMIT 1
        ''', (employee_id, today_start, today_end))
        return c.fetchone() is not None

def has_open_session(employee_id: int) -> bool:
    with _conn() as conn:
        c = conn.cursor()
        c.execute('SELECT 1 FROM attendance WHERE employee_id = ? AND check_out IS NULL LIMIT 1', (employee_id,))
        return c.fetchone() is not None

def record_check_in(employee_id: int) -> Optional[str]:
    if has_checkin_today(employee_id):
        return None
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        c = conn.cursor()
        c.execute('INSERT INTO attendance (employee_id, check_in, check_out) VALUES (?, ?, NULL)', (employee_id, now))
        conn.commit()
        return now

def record_check_out(employee_id: int) -> Optional[str]:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id FROM attendance
            WHERE employee_id = ? AND check_out IS NULL
            ORDER BY check_in DESC
            LIMIT 1
        ''', (employee_id,))
        row = c.fetchone()
        if not row:
            return None
        attendance_id = row[0]
        c.execute('UPDATE attendance SET check_out = ? WHERE id = ?', (now, attendance_id))
        conn.commit()
        return now

def get_work_seconds_in_period(employee_id: int, start_iso: str, end_iso: str) -> int:
    total_seconds = 0
    with _conn() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT check_in, check_out FROM attendance
            WHERE employee_id = ? AND check_out IS NOT NULL
              AND (
                    (check_in BETWEEN ? AND ?)
                 OR (check_out BETWEEN ? AND ?)
                 OR (check_in <= ? AND check_out >= ?)
              )
        ''', (employee_id, start_iso, end_iso, start_iso, end_iso, start_iso, end_iso))
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
def calculate_salary(employee_id: int, start_date: str, end_date: str, hourly_wage: float) -> float:
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

def update_user_role(user_id: int, new_role: str, actor_user_id: Optional[int] = None) -> None:
    """
    Update a user's role. Optionally record who performed the change (actor_user_id) in the role_audit table.
    """
    if new_role == "admin" and get_admin_user():
        raise PermissionError("Only one admin account is allowed. Transfer admin role before assigning.")
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

def delete_user_with_admin_check(user_id: int, transfer_to_user_id: Optional[int] = None) -> bool:
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
                raise PermissionError("Admin account cannot be deleted unless the role is transferred.")
            # Transfer admin role
            c.execute("UPDATE users SET role = 'admin' WHERE id = ?", (transfer_to_user_id,))
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

def can_view_working_hours(actor_role: str, target_user_id: int, actor_user_id: int) -> bool:
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