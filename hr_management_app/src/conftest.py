import os
import shutil
import tempfile

import pytest

# Session-level DB fixture: create a single temp DB for the whole test session
# and initialize schema once. This is faster for local developer iterations but
# provides weaker isolation than per-test DB files.
_TMP_DIR = tempfile.mkdtemp(prefix="hr_test_db_")
_DB_PATH = os.path.join(_TMP_DIR, "test_hr_management.db")
os.environ["HR_MANAGEMENT_TEST_DB"] = _DB_PATH


@pytest.fixture(scope="session", autouse=True)
def session_db_setup():
    """Ensure schema exists for the session and cleanup at the end."""
    try:
        from hr_management_app.src.database import database as db

        db.init_db()
    except Exception:
        pass
    yield
    try:
        if os.path.exists(_DB_PATH):
            os.remove(_DB_PATH)
        shutil.rmtree(_TMP_DIR, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def clean_tables_before_test():
    """Truncate key tables before each test to provide isolation while reusing the session DB.

    This is faster than creating a fresh DB file per test but avoids state leakage that
    caused unique-email collisions when tests create users.
    """
    try:
        from hr_management_app.src.database import database as db

        with db._conn() as conn:
            c = conn.cursor()
            # Clear user-facing tables that tests mutate
            for t in (
                "imputation_audit",
                "role_audit",
                "attendance",
                "contracts",
                "employees",
                "users",
            ):
                c.execute(f"DELETE FROM {t}")
            conn.commit()
    except Exception:
        # If cleanup fails, let tests surface the issue
        pass
    yield
