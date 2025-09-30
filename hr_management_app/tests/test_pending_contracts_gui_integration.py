import importlib
import os
import tempfile
import time
import tkinter as tk
from tkinter import ttk


def _setup_temp_db(tmp_path):
    dbfile = tmp_path / "gui_pending_test.db"
    dbfile.write_text("")
    os.environ["HR_MANAGEMENT_TEST_DB"] = str(dbfile)
    db = importlib.import_module("hr_management_app.src.database.database")
    importlib.reload(db)
    db.init_db()
    return db


def _reload_gui_module():
    gui = importlib.import_module("hr_management_app.src.gui")
    importlib.reload(gui)
    return gui


def test_pending_contract_window_selects_focused_id(tmp_path):
    # Prepare isolated DB and modules
    db = _setup_temp_db(tmp_path)
    gui = _reload_gui_module()

    # submit a pending contract
    pid = db.submit_pending_contract(
        contract_id=None,
        employee_id=77,
        construction_id=None,
        parent_contract_id=None,
        area="GUI Test Area",
        incharge="GUI Tester",
        start_date="2025-01-01",
        end_date="2025-12-31",
        terms="Integration test pending",
        file_path=None,
        submitted_by=None,
    )
    assert int(pid) > 0

    # Create the application as a manager so the Pending Approvals button is enabled
    app = gui.HRApp(employee_id=None, user_role="manager", user_id=1)

    try:
        # Ensure Tk has processed widget creation
        app.update_idletasks()
        app.update()

        # Open the pending contracts window focused on our pending id
        app.open_pending_contracts(focus_pending_id=int(pid))

        # Let Tk create the Toplevel and populate the Treeview
        app.update_idletasks()
        app.update()

        # Find the Pending Contracts Toplevel by title
        pending_win = None
        for w in app.winfo_children():
            try:
                if isinstance(w, tk.Toplevel) and w.title() == "Pending Contracts":
                    pending_win = w
                    break
            except Exception:
                continue

        assert pending_win is not None, "Pending Contracts window was not created"

        # Find the Treeview widget inside the pending window
        def find_tree(widget):
            if isinstance(widget, ttk.Treeview):
                return widget
            for c in widget.winfo_children():
                res = find_tree(c)
                if res:
                    return res
            return None

        tree = find_tree(pending_win)
        assert tree is not None, "Could not find pending Treeview"

        # Ensure a selection exists and corresponds to our pending id
        sel = tree.selection()
        assert sel, "No selection in Pending Contracts tree"
        vals = tree.item(sel[0])["values"]
        # first column is pending id
        assert int(vals[0]) == int(pid)

    finally:
        try:
            # close any open windows and the app cleanly
            for w in list(app.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass
            app.destroy()
        except Exception:
            pass
