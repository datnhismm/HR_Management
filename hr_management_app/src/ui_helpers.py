import tkinter as tk
from tkinter import ttk
from typing import List, Optional

def role_selection_dialog(parent, email: str, current_role: str, allowed: List[str]) -> Optional[str]:
    """Modal dialog to pick a role from allowed list. Returns selected role or None."""
    dlg = tk.Toplevel(parent)
    dlg.title("Select Role")
    dlg.transient(parent)
    dlg.resizable(False, False)
    tk.Label(dlg, text=f"User: {email}").pack(padx=12, pady=(12,4))
    role_var = tk.StringVar(value=current_role)
    combo = ttk.Combobox(dlg, textvariable=role_var, values=allowed, state="readonly")
    combo.pack(padx=12, pady=6)
    result = [None]
    def on_ok():
        result[0] = role_var.get()
        dlg.destroy()
    def on_cancel():
        dlg.destroy()
    btnf = ttk.Frame(dlg)
    btnf.pack(pady=8)
    ttk.Button(btnf, text="OK", command=on_ok).pack(side="left", padx=6)
    ttk.Button(btnf, text="Cancel", command=on_cancel).pack(side="right", padx=6)
    dlg.grab_set()
    parent.wait_window(dlg)
    return result[0]
