import os
import tempfile
import importlib
import smtplib
import threading
import time

import pytest

# Use a temporary test DB
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
os.environ["HR_MANAGEMENT_TEST_DB"] = temp_db.name

from hr_management_app.src.database import database as db


class DummySMTP:
    def __init__(self, server, port, timeout=15):
        self.server = server
        self.port = port
        self.timeout = timeout
        self.logged_in = False
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def ehlo(self):
        pass

    def starttls(self):
        pass

    def login(self, user, password):
        if user == "baduser":
            raise smtplib.SMTPAuthenticationError(535, b"Auth failed")
        self.logged_in = True

    def send_message(self, msg):
        # simulate send by recording message subject
        self.sent.append(msg.get('Subject'))


class DummySMTP_SSL(DummySMTP):
    pass


def test_process_outbox_with_smtp_success(monkeypatch):
    db.init_db()

    # monkeypatch SMTP classes in smtplib
    monkeypatch.setattr(smtplib, 'SMTP', lambda server, port, timeout=15: DummySMTP(server, port, timeout))
    monkeypatch.setattr(smtplib, 'SMTP_SSL', lambda server, port, timeout=15: DummySMTP_SSL(server, port, timeout))

    # ensure email_config considers SMTP_CONFIGURED True for the test run
    import importlib
    import hr_management_app.src.email_config as email_config

    # temporarily set env vars used by email_config
    monkeypatch.setenv('SMTP_SERVER', 'smtp.example.com')
    monkeypatch.setenv('SMTP_USER', 'user')
    monkeypatch.setenv('SMTP_PASSWORD', 'pass')

    importlib.reload(email_config)
    # Ensure the name used by send_email's "from email_config import ..." resolves
    import sys
    sys.modules['email_config'] = email_config

    # enqueue a message
    out_id = db.enqueue_email_outbox('to@example.com', 'Subject A', 'Body', raw_message='raw')
    assert out_id > 0

    processed = db.process_outbox_once()
    assert processed == 1

    with db._conn() as conn:
        c = conn.cursor()
        c.execute('SELECT status FROM email_outbox WHERE id = ?', (out_id,))
        row = c.fetchone()
        assert row[0] == 'sent'


def test_process_outbox_with_smtp_auth_fail(monkeypatch):
    # fresh DB state
    importlib.reload(db)
    db.init_db()

    monkeypatch.setattr(smtplib, 'SMTP', lambda server, port, timeout=15: DummySMTP(server, port, timeout))
    monkeypatch.setattr(smtplib, 'SMTP_SSL', lambda server, port, timeout=15: DummySMTP_SSL(server, port, timeout))

    # set bad user to trigger SMTPAuthenticationError in DummySMTP.login
    monkeypatch.setenv('SMTP_SERVER', 'smtp.example.com')
    monkeypatch.setenv('SMTP_USER', 'baduser')
    monkeypatch.setenv('SMTP_PASSWORD', 'badpass')

    import hr_management_app.src.email_config as email_config
    importlib.reload(email_config)
    import sys
    sys.modules['email_config'] = email_config

    out_id = db.enqueue_email_outbox('to2@example.com', 'Subject B', 'Body2', raw_message=None)
    assert out_id > 0

    processed = db.process_outbox_once()
    # processing should handle auth error and mark failed (processed count will be 0)
    assert processed == 0

    with db._conn() as conn:
        c = conn.cursor()
        c.execute('SELECT status, last_error FROM email_outbox WHERE id = ?', (out_id,))
        row = c.fetchone()
        assert row[0] == 'failed'
        assert row[1] is not None
