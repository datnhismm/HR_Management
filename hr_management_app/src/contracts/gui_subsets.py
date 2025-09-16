import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from database import database as db
from hr_management_app.src.database.database import get_status_color


def status_choices():
    from hr_management_app.src.database.database import STATUS_CHOICES

    return STATUS_CHOICES


def show_contract_subsets(contract_id: int, actor_user_id: Optional[int] = None):
    root = tk.Tk()
    root.title(f"Contract {contract_id} Subsets")
    frame = ttk.Frame(root, padding=10)
    frame.grid()

    from .models import contract_progress

    progress = contract_progress(contract_id)

    ttk.Label(
        frame,
        text=f"Progress: {progress['percent_complete']}% ({progress['completed']}/{progress['total']})",
    ).grid(column=0, row=0, sticky="w")

    # list subsets
    for idx, s in enumerate(progress["details"], start=1):
        # color swatch
        sw = tk.Canvas(frame, width=18, height=18, highlightthickness=1)
        sw.create_rectangle(0, 0, 18, 18, fill=s["color"], outline="#000")
        sw.grid(column=0, row=idx, sticky="w", pady=2, padx=(0, 6))
        lbl = ttk.Label(frame, text=f"{s['title']} [{s['status']}]")
        lbl.grid(column=1, row=idx, sticky="w", pady=2)
        # if actor allowed, provide a dropdown to change status
        allowed = False
        if actor_user_id:
            actor = db.get_user_by_id(actor_user_id)
            if actor and actor[-1] in (
                "accountant",
                "manager",
                "high_manager",
                "admin",
            ):
                allowed = True
        if allowed:
            var = tk.StringVar(value=s["status"])
            combo = ttk.Combobox(
                frame,
                textvariable=var,
                values=status_choices(),
                state="readonly",
                width=30,
            )
            combo.grid(column=2, row=idx, padx=6)

            def on_change(event, subset_id=s["id"], var=var):
                new = var.get()
                if not messagebox.askyesno("Confirm", f'Change status to "{new}"?'):
                    # revert
                    var.set(s["status"])
                    return
                try:
                    from hr_management_app.src.database.database import (
                        update_subset_status,
                    )

                    update_subset_status(subset_id, new, actor_user_id=actor_user_id)
                    messagebox.showinfo("Status", "Updated")
                    # refresh swatch and label text
                    sw.delete("all")
                    sw.create_rectangle(
                        0, 0, 18, 18, fill=get_status_color(new), outline="#000"
                    )
                    lbl.config(text=f"{s['title']} [{new}]")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
                    var.set(s["status"])

            combo.bind("<<ComboboxSelected>>", on_change)

    root.mainloop()


if __name__ == "__main__":
    # quick manual runner: show subsets for contract 1 as admin if available
    admin = db.get_admin_user()
    if admin:
        show_contract_subsets(1, actor_user_id=admin[0])
