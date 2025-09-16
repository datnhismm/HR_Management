"""Launch the ImportDialog UI with the generated XLSX preloaded.

This will open a Tkinter window. Use this when running on a desktop environment.
"""

import sys
import traceback
from pathlib import Path

# ensure local src is importable when running from tools/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import tkinter as tk

    try:
        from hr_management_app.src.ui_import import ImportDialog
    except Exception:
        from ui_import import ImportDialog  # type: ignore
    p = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "tests"
        / "fixtures"
        / "dummy_employees_2000.xlsx"
    )
    if not p.exists():
        raise FileNotFoundError(f"Fixture not found: {p}")

    root = tk.Tk()
    root.geometry("960x600")
    root.title("Import Dialog Launcher")
    # create and show import dialog
    dlg = ImportDialog(root)
    dlg.path_var.set(str(p))
    try:
        dlg._load()
    except Exception:
        traceback.print_exc()
    root.mainloop()
except Exception:
    traceback.print_exc()
    raise
