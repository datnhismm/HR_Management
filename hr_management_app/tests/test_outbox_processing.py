import os
import tempfile
import importlib

import pytest

# Ensure the package uses a test DB by setting env var before importing the database module

temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
TEST_DB_PATH = temp_db.name
os.environ["HR_MANAGEMENT_TEST_DB"] = TEST_DB_PATH

# Now import the database module under test
from hr_management_app.src.database import database as db


def test_enqueue_and_process_outbox_success(monkeypatch):
    """Enqueue an email, mock send_email to succeed, and assert it is marked sent."""
    # Ensure DB tables created for this test DB
    db.init_db()

    sent = []

    def fake_send_email(to_email, subject, body):
        sent.append((to_email, subject, body))

    monkeypatch.setattr(db, "send_email", fake_send_email)

    # Enqueue an email
    out_id = db.enqueue_email_outbox("user@example.com", "Hi", "Body", raw_message="raw")
    assert out_id > 0

    # Process outbox
    processed = db.process_outbox_once()
    assert processed == 1

    # Verify send_email called
    assert len(sent) == 1

    # Check DB row status
    with db._conn() as conn:
        c = conn.cursor()
        c.execute("SELECT status FROM email_outbox WHERE id = ?", (out_id,))
        row = c.fetchone()
        assert row is not None
        assert row[0] == 'sent'


def test_enqueue_and_process_outbox_failure(monkeypatch):
    """Enqueue an email, mock send_email to raise, and assert it is marked failed and attempt_count increments."""
    # Import fresh module to ensure clean state (module uses env var on import)
    importlib.reload(db)
    db.init_db()

    def fake_send_email_fail(to_email, subject, body):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(db, "send_email", fake_send_email_fail)

    out_id = db.enqueue_email_outbox("user2@example.com", "Hello", "Body2", raw_message=None)
    assert out_id > 0

    processed = db.process_outbox_once()
    # Should skip successful count, but it will mark failed
    assert processed == 0

    with db._conn() as conn:
        c = conn.cursor()
        c.execute("SELECT status, attempt_count, last_error FROM email_outbox WHERE id = ?", (out_id,))
        row = c.fetchone()
        assert row is not None
        assert row[0] == 'failed'
        assert row[1] >= 1
        assert row[2] is not None
