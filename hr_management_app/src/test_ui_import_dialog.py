import csv
import os
import tkinter as tk
from pathlib import Path

import database.database as db
import ui_import
from parsers.file_parser import parse_csv
from parsers.normalizer import map_columns, validate_and_clean


def test_importdialog_load_and_import(tmp_path, monkeypatch):
    # Use a temp DB
    test_db = tmp_path / "test_hr_ui.db"
    db.DB_NAME = str(test_db)
    db.init_db()

    # Create a CSV with a small typo in header to test fuzzy mapping
    csv_path = tmp_path / "employees_ui.csv"
    headers = ["Full Name", "emal", "birthdate", "Job Title", "Role", "joined", "left", "contract"]
    row = ["Bob Example", "bob@example.com", "1987-08-01", "Developer", "engineer", "2019", "", "permanent"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(row)

    # Monkeypatch MappingPreviewDialog to avoid interactive blocking
    # Simple non-GUI preview object. We'll stub ImportDialog.wait_window to avoid GUI blocking.
    class DummyPreview:
        def __init__(self, parent, mapping_debug, prefill=None, prethreshold=None):
            # Simulate user accepting defaults (no changes)
            self.mapping = {k: (v[0] if isinstance(v, (list, tuple)) else v, v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else None) for k, v in (mapping_debug or {}).items()}
            self.threshold = prethreshold or 80

    monkeypatch.setattr(ui_import, "MappingPreviewDialog", DummyPreview)
    # Make ImportDialog.wait_window a no-op to avoid actual GUI wait for the preview dialog
    monkeypatch.setattr(ui_import.ImportDialog, "wait_window", lambda self, win=None: None)

    # Create a hidden root and the ImportDialog
    root = tk.Tk()
    root.withdraw()
    dlg = ui_import.ImportDialog(root)
    try:
        dlg.path_var.set(str(csv_path))
        dlg._load()

        # expect one record loaded and valid
        assert len(dlg.records) == 1
        cleaned = dlg.records[0]["cleaned"]
        problems = dlg.records[0]["problems"]
        assert not problems
        email = cleaned.get("email")
        assert email == "bob@example.com"

        # perform import
        dlg.import_all()

        # verify user and employee in db
        user = db.get_user_by_email(email)
        assert user is not None
        user_id = user[0]
        emp = db.get_employee_by_user(user_id)
        assert emp is not None
    finally:
        try:
            dlg.destroy()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
