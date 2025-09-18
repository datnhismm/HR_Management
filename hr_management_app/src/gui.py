import logging
import os
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk
from types import SimpleNamespace
from typing import Optional

# database helpers
from hr_management_app.src.database.database import (
    ALLOWED_ROLES,
    _conn,
    add_contract_to_db,
    can_count_salary,
    can_delete,
    can_edit_info,
    can_grant_role,
    delete_user,
    delete_user_with_admin_check,
    get_all_contracts_filtered,
    get_all_users,
    get_employee_by_id,
    get_month_work_seconds,
    get_user_by_id,
    has_open_session,
    init_db,
    record_check_in,
    record_check_out,
    update_employee,
    update_user_role,
)
from hr_management_app.src.contracts.models import Contract
from hr_management_app.src.employees.models import Employee

# optional PIL for profile pictures
logger = logging.getLogger(__name__)
try:
    from PIL import Image, ImageTk  # type: ignore
except Exception as exc:
    Image = None
    ImageTk = None
    logger.info("Pillow not available: image features disabled (%s)", exc)

init_db()


class EmployeeProfileWindow(tk.Toplevel):
    def __init__(self, parent, emp_id: int, actor_role: str, actor_user_id: int):
        super().__init__(parent)
        self.emp_id = emp_id
        self.actor_role = actor_role
        self.actor_user_id = actor_user_id
        self.title("Employee Profile")
        self.geometry("420x420")
        self.resizable(False, False)
        self.create_widgets()
        self.load_employee()
        self.transient(parent)
        self.grab_set()
        self.center_window()

    def create_widgets(self):
        # Menu bar
        menubar = tk.Menu(self)
        contracts_menu = tk.Menu(menubar, tearoff=0)
        # Use a lambda to defer attribute access (helps some static analyzers)
        contracts_menu.add_command(
            label="Subsets",
            command=lambda: getattr(self, "open_contract_subsets", lambda: None)(),
        )
        menubar.add_cascade(label="Contracts", menu=contracts_menu)
        self.config(menu=menubar)

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Employee ID:").grid(row=0, column=0, sticky="e")
        self.empnum_lbl = ttk.Label(frm, text="")
        self.empnum_lbl.grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Full name:").grid(row=1, column=0, sticky="e")
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(frm, textvariable=self.name_var)
        self.name_entry.grid(row=1, column=1, sticky="ew")

        ttk.Label(frm, text="DOB (YYYY-MM-DD):").grid(row=2, column=0, sticky="e")
        self.dob_var = tk.StringVar()
        self.dob_entry = ttk.Entry(frm, textvariable=self.dob_var)
        self.dob_entry.grid(row=2, column=1, sticky="ew")

        ttk.Label(frm, text="Job title:").grid(row=3, column=0, sticky="e")
        self.job_var = tk.StringVar()
        self.job_entry = ttk.Entry(frm, textvariable=self.job_var)
        self.job_entry.grid(row=3, column=1, sticky="ew")

        ttk.Label(frm, text="Role:").grid(row=4, column=0, sticky="e")
        self.role_var = tk.StringVar()
        self.role_combo = ttk.Combobox(
            frm, textvariable=self.role_var, values=ALLOWED_ROLES, state="readonly"
        )
        self.role_combo.grid(row=4, column=1, sticky="ew")

        ttk.Label(frm, text="Year start:").grid(row=5, column=0, sticky="e")
        self.year_start_var = tk.StringVar()
        self.year_start_entry = ttk.Entry(frm, textvariable=self.year_start_var)
        self.year_start_entry.grid(row=5, column=1, sticky="ew")

        ttk.Label(frm, text="Year end:").grid(row=6, column=0, sticky="e")
        self.year_end_var = tk.StringVar()
        self.year_end_entry = ttk.Entry(frm, textvariable=self.year_end_var)
        self.year_end_entry.grid(row=6, column=1, sticky="ew")

        ttk.Label(frm, text="Contract type:").grid(row=7, column=0, sticky="e")
        self.contract_var = tk.StringVar()
        self.contract_entry = ttk.Entry(frm, textvariable=self.contract_var)
        self.contract_entry.grid(row=7, column=1, sticky="ew")

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=(12, 0), sticky="ew")
        self.save_btn = ttk.Button(btn_frame, text="Save", command=self.save)
        self.save_btn.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(
            side="right", padx=5
        )

        frm.columnconfigure(1, weight=1)

    def load_employee(self):
        row = get_employee_by_id(self.emp_id)
        if not row:
            messagebox.showerror("Error", "Employee not found", parent=self)
            self.destroy()
            return
        (
            emp_id,
            user_id,
            empnum,
            name,
            dob,
            job_title,
            role,
            year_start,
            year_end,
            profile_pic,
            contract_type,
        ) = row
        self.empnum_lbl.config(text=str(empnum))
        self.name_var.set(name or "")
        self.dob_var.set(dob or "")
        self.job_var.set(job_title or "")
        self.role_var.set(role or ALLOWED_ROLES[0])
        self.role_combo.set(role or ALLOWED_ROLES[0])
        self.year_start_var.set(str(year_start) if year_start else "")
        self.year_end_var.set(str(year_end) if year_end else "")
        self.contract_var.set(contract_type or "")

        target_user = get_user_by_id(user_id)
        target_role = target_user[-1] if target_user else ""
        can_edit_fields = can_edit_info(self.actor_role, target_role) or (
            self.actor_user_id == user_id
        )
        # restrict which roles actor can assign
        if self.actor_role != "admin":
            allowed = [r for r in ALLOWED_ROLES if can_grant_role(self.actor_role, r)]
            self.role_combo.config(values=allowed)
            if self.role_var.get() not in allowed:
                self.role_var.set(allowed[0] if allowed else "")
        state = "normal" if can_edit_fields else "disabled"
        for w in [
            self.name_entry,
            self.dob_entry,
            self.job_entry,
            self.role_combo,
            self.year_start_entry,
            self.year_end_entry,
            self.contract_entry,
            self.save_btn,
        ]:
            w.config(state=state)

    def save(self):
        kwargs = {
            "name": self.name_var.get().strip(),
            "dob": self.dob_var.get().strip() or None,
            "job_title": self.job_var.get().strip() or None,
            "role": self.role_var.get().strip() or None,
            "year_start": (
                int(self.year_start_var.get().strip())
                if self.year_start_var.get().strip()
                else None
            ),
            "year_end": (
                int(self.year_end_var.get().strip())
                if self.year_end_var.get().strip()
                else None
            ),
            "contract_type": self.contract_var.get().strip() or None,
        }
        try:
            update_employee(
                self.emp_id,
                **{k: v for k, v in kwargs.items() if v is not None or k == "name"},
            )
            messagebox.showinfo("Saved", "Employee updated", parent=self)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 420
        h = self.winfo_height() or 420
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


class EmployeeManagementWindow(tk.Toplevel):
    def __init__(self, parent, actor_role: str, actor_user_id: int):
        super().__init__(parent)
        self.actor_role = actor_role
        # Restrict certain roles from opening this management window
        if self.actor_role in ("driver", "construction_worker"):
            from tkinter import messagebox

            messagebox.showerror(
                "Access Denied", "You do not have permission to manage employees."
            )
            self.destroy()
            return
        self.actor_user_id = actor_user_id
        self.title("Employee Management")
        self.geometry("900x420")
        self.resizable(True, True)
        self.create_widgets()
        self.load_employees()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)

        # Employee search controls
        search_frame = ttk.Frame(frm)
        search_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.emp_search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.emp_search_var).pack(
            side="left", fill="x", expand=True, padx=(6, 6)
        )
        ttk.Button(search_frame, text="Search", command=self.search_employees_handler).pack(side="right")

        cols = (
            "id",
            "empnum",
            "name",
            "job",
            "role",
            "year_start",
            "year_end",
            "contract",
            "user_id",
        )
        self.tree = ttk.Treeview(frm, columns=cols, show="headings")
        headings = [
            "DB ID",
            "Employee#",
            "Name",
            "Job Title",
            "Role",
            "Year Start",
            "Year End",
            "Contract",
            "User ID",
        ]
        for c, h in zip(cols, headings):
            self.tree.heading(c, text=h)
            self.tree.column(c, anchor="center")
        self.tree.pack(fill="both", expand=True)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Edit Selected", command=self.edit_selected).pack(
            side="left", padx=4
        )
        self.delete_btn = ttk.Button(
            btns, text="Delete Selected", command=self.delete_selected
        )
        self.delete_btn.pack(side="left", padx=4)
        ttk.Button(btns, text="Refresh", command=self.load_employees).pack(
            side="right", padx=4
        )

        if not can_delete("user", self.actor_role):
            self.delete_btn.config(state="disabled")

    def load_employees(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        # If a search term is provided, use the Employee.search wrapper
        term = (getattr(self, "emp_search_var", None) and self.emp_search_var.get()) or ""
        if term:
            try:
                rows = Employee.search(term)
                for r in rows:
                    self.tree.insert(
                        "",
                        "end",
                        values=(
                            r.get("id"),
                            r.get("employee_number"),
                            r.get("name"),
                            r.get("job_title"),
                            r.get("role"),
                            None,
                            None,
                            None,
                            r.get("user_id"),
                        ),
                    )
                return
            except Exception:
                # fallback to full listing on error
                pass
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, employee_number, name, job_title, role, year_start, year_end, contract_type, user_id FROM employees ORDER BY employee_number"
            )
            for row in c.fetchall():
                self.tree.insert("", "end", values=row)

    def search_employees_handler(self):
        self.load_employees()

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select one employee first", parent=self)
            return
        vals = self.tree.item(sel[0])["values"]
        emp_id = int(vals[0])
        win = EmployeeProfileWindow(
            self,
            emp_id,
            self.actor_role,
            int(self.actor_user_id) if self.actor_user_id is not None else 0,
        )
        self.wait_window(win)
        self.load_employees()

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select one employee first", parent=self)
            return
        vals = self.tree.item(sel[0])["values"]
        emp_id, empnum, name, job, role, _, _, _, user_id = vals
        emp_id = int(emp_id)
        user_id = int(user_id) if user_id is not None else None
        if not messagebox.askyesno("Confirm", f"Delete employee {name} (#{empnum})?"):
            return
        try:
            if role == "admin":
                users = get_all_users()
                other = [u for u in users if u[0] != user_id]
                if not other:
                    messagebox.showerror(
                        "Error", "No other user to transfer admin role to.", parent=self
                    )
                    return
                choices = "\n".join(f"{u[0]}: {u[1]} ({u[2]})" for u in other)
                tid = simpledialog.askinteger(
                    "Transfer Admin",
                    f"Target user id to transfer admin to:\n{choices}",
                    parent=self,
                )
                if not tid:
                    return
                if user_id is None:
                    raise ValueError("Target user id is missing for admin transfer")
                delete_user_with_admin_check(int(user_id), transfer_to_user_id=int(tid))
            else:
                with _conn() as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
                    conn.commit()
            messagebox.showinfo("Deleted", "Employee removed", parent=self)
            self.load_employees()
        except Exception as e:
            messagebox.showerror("Error deleting", str(e), parent=self)

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 900
        h = self.winfo_height() or 420
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


class ManageUsersWindow(tk.Toplevel):
    def __init__(self, parent, actor_role: str, actor_user_id: Optional[int] = None):
        super().__init__(parent)
        self.actor_role = actor_role
        self.actor_user_id = actor_user_id
        self.title("Manage Users")
        self.geometry("640x420")
        self.create_widgets()
        self.load_users()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        cols = ("id", "email", "role")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings")
        for c, h in zip(cols, ("ID", "Email", "Role")):
            self.tree.heading(c, text=h)
            self.tree.column(c, anchor="center")
        self.tree.pack(fill="both", expand=True)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Refresh", command=self.load_users).pack(side="left")
        self.change_role_btn = ttk.Button(
            btns, text="Change Role", command=self.change_role
        )
        self.change_role_btn.pack(side="left", padx=4)
        ttk.Button(btns, text="Delete User", command=self.delete_user).pack(
            side="left", padx=4
        )

        # Only manager, high_manager and admin may change/grant roles
        if self.actor_role not in ("admin", "high_manager", "manager"):
            self.change_role_btn.config(state="disabled")

    def load_users(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        users = get_all_users()
        for u in users:
            self.tree.insert("", "end", values=u)

    def change_role(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select user first", parent=self)
            return
        vals = self.tree.item(sel[0])["values"]
        uid, email, cur_role = vals
        uid = int(uid)
        allowed = [r for r in ALLOWED_ROLES if can_grant_role(self.actor_role, r)]
        if not allowed:
            messagebox.showerror(
                "Permission Denied", "You cannot grant any roles.", parent=self
            )
            return

        from ui_helpers import role_selection_dialog

        new_role = role_selection_dialog(self, email, cur_role, allowed)
        if not new_role:
            return
        try:
            update_user_role(uid, new_role, actor_user_id=self.actor_user_id)
            messagebox.showinfo("Updated", "Role updated.", parent=self)
            self.load_users()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def delete_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select user first", parent=self)
            return
        vals = self.tree.item(sel[0])["values"]
        uid, email, role = vals
        uid = int(uid)
        if not messagebox.askyesno("Confirm", f"Delete user {email} ({role})?"):
            return
        try:
            if role == "admin":
                users = get_all_users()
                other = [u for u in users if u[0] != uid]
                if not other:
                    messagebox.showerror(
                        "Error", "No other user to transfer admin to.", parent=self
                    )
                    return
                choices = "\n".join(f"{u[0]}: {u[1]} ({u[2]})" for u in other)
                tid = simpledialog.askinteger(
                    "Transfer Admin",
                    f"Target user id to transfer admin to:\n{choices}",
                    parent=self,
                )
                if not tid:
                    return
                delete_user_with_admin_check(uid, transfer_to_user_id=int(tid))
            else:
                delete_user(uid)
            messagebox.showinfo("Deleted", "User removed", parent=self)
            self.load_users()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 640
        h = self.winfo_height() or 420
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


class HRApp(tk.Tk):
    def __init__(
        self,
        employee_id: Optional[int] = None,
        user_role: str = "engineer",
        user_id: Optional[int] = None,
    ):
        super().__init__()
        self.title("HR Management")
        self.geometry("900x560")
        self.resizable(False, False)
        self.employee_id = employee_id
        self.user_role = user_role
        self.user_id = user_id
        # explicit attribute so static analyzers know this attribute exists
        self.contracts_list = None
        self.employee = None
        self.profile_image = None
        self.create_widgets()
        self.load_contracts()
        # sorting state: (column, asc_bool)
        self._contract_sort = (None, True)
        if self.employee_id:
            self.load_employee_profile()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.destroy()
        import sys

        sys.exit(0)

    def create_widgets(self):
        left_frame = ttk.Frame(self, padding=10)
        left_frame.place(x=10, y=10, width=420, height=540)

        profile_box = ttk.Frame(left_frame)
        profile_box.pack(fill="x", pady=(0, 8))
        self.photo_lbl = ttk.Label(profile_box)
        self.photo_lbl.pack(side="left", padx=(0, 8))
        info_frame = ttk.Frame(profile_box)
        info_frame.pack(side="left", fill="both", expand=True)
        self.name_label = ttk.Label(
            info_frame, text="Name", font=("Segoe UI", 11, "bold")
        )
        self.name_label.pack(anchor="w")
        self.job_label = ttk.Label(info_frame, text="Job Title", font=("Segoe UI", 10))
        self.job_label.pack(anchor="w")
        ttk.Button(
            info_frame, text="View / Edit Profile", command=self.open_own_profile
        ).pack(anchor="w", pady=(6, 0))

        self.manage_users_btn = ttk.Button(
            info_frame, text="Manage Users", command=self.open_manage_users
        )
        self.manage_users_btn.pack(anchor="w", pady=(6, 0))
        if self.user_role != "admin":
            self.manage_users_btn.config(state="disabled")
        if self.user_role in ("driver", "construction_worker"):
            # restricted roles should not see/manage users
            self.manage_users_btn.pack_forget()

        summary_frame = ttk.Frame(left_frame)
        summary_frame.pack(fill="x", pady=(8, 8))
        ttk.Label(summary_frame, text="Month (YYYY-MM)").grid(
            row=0, column=0, sticky="w"
        )
        self.month_var = tk.StringVar(value=datetime.now().strftime("%Y-%m"))
        ttk.Entry(summary_frame, textvariable=self.month_var, width=12).grid(
            row=0, column=1, sticky="w", padx=6
        )
        ttk.Label(summary_frame, text="Hourly wage").grid(row=1, column=0, sticky="w")
        self.wage_var = tk.StringVar(value="0.0")
        ttk.Entry(summary_frame, textvariable=self.wage_var, width=12).grid(
            row=1, column=1, sticky="w", padx=6
        )
        self.calc_btn = ttk.Button(
            summary_frame, text="Calc Month", command=self.calc_month
        )
        self.calc_btn.grid(row=0, column=2, rowspan=2, padx=8)
        self.month_result = ttk.Label(summary_frame, text="Hours: 0.00  Salary: 0.00")
        self.month_result.grid(row=2, column=0, columnspan=3, pady=(6, 0), sticky="w")

        # Drivers and construction workers have restricted UI; they cannot use salary calc or see contracts
        if not can_count_salary(self.user_role) or self.user_role in (
            "driver",
            "construction_worker",
        ):
            self.calc_btn.config(state="disabled")

        # Contracts list: hidden for driver and construction worker
        if self.user_role not in ("driver", "construction_worker"):
            ttk.Label(left_frame, text="Contracts").pack(anchor="w")
            # search/filter (live)
            search_fr = ttk.Frame(left_frame)
            search_fr.pack(fill="x", pady=(0, 4))
            self.search_var = tk.StringVar()
            entry = ttk.Entry(search_fr, textvariable=self.search_var)
            entry.pack(side="left", fill="x", expand=True)
            # explicit Search button for non-live activation
            ttk.Button(search_fr, text="Search", command=self.load_contracts).pack(
                side="right", padx=(4, 0)
            )
            # show trashed contracts toggle
            self.show_trash_var = tk.BooleanVar(value=False)
            try:
                chk = ttk.Checkbutton(
                    search_fr,
                    text="Show Trash",
                    variable=self.show_trash_var,
                    command=self.load_contracts,
                )
            except Exception:
                # older ttk versions may not accept variable kw; fall back
                chk = ttk.Checkbutton(
                    search_fr, text="Show Trash", command=self.load_contracts
                )
            chk.pack(side="right", padx=(6, 0))
            # live filter: trace changes
            try:
                self.search_var.trace_add("write", lambda *_: self.load_contracts())
            except Exception:
                # older tk versions
                self.search_var.trace("w", lambda *_: self.load_contracts())

            # hierarchical multi-column tree of contracts
            cols = ("cid", "area", "incharge", "start", "end", "subsets")
            self.contracts_tree = ttk.Treeview(
                left_frame, columns=cols, show="headings"
            )
            # define headings (clickable for sorting)
            self.contracts_tree.heading(
                "cid", text="ID", command=lambda: self._sort_contracts_by("cid")
            )
            self.contracts_tree.heading(
                "area", text="Area", command=lambda: self._sort_contracts_by("area")
            )
            self.contracts_tree.heading(
                "incharge",
                text="In-charge",
                command=lambda: self._sort_contracts_by("incharge"),
            )
            self.contracts_tree.heading(
                "start", text="Start", command=lambda: self._sort_contracts_by("start")
            )
            self.contracts_tree.heading(
                "end", text="End", command=lambda: self._sort_contracts_by("end")
            )
            self.contracts_tree.heading(
                "subsets",
                text="# Subsets",
                command=lambda: self._sort_contracts_by("subsets"),
            )
            # hide cid column width
            self.contracts_tree.column("cid", width=60, anchor="center")
            self.contracts_tree.column("area", width=120, anchor="w")
            self.contracts_tree.column("incharge", width=120, anchor="w")
            self.contracts_tree.column("start", width=90, anchor="center")
            self.contracts_tree.column("end", width=90, anchor="center")
            self.contracts_tree.column("subsets", width=80, anchor="center")
            self.contracts_tree.pack(fill="both", expand=True, pady=(5, 5))
            # allow columns to be resized/stretched
            self.contracts_tree.column("cid", stretch=False)
            self.contracts_tree.column("area", stretch=True)
            self.contracts_tree.column("incharge", stretch=True)
            self.contracts_tree.column("start", stretch=False)
            self.contracts_tree.column("end", stretch=False)
            self.contracts_tree.column("subsets", stretch=False)

            # double-click to view details
            self.contracts_tree.bind(
                "<Double-1>", lambda e: self.view_selected_contract()
            )
            # right-click context menu
            self._contract_menu = tk.Menu(self, tearoff=0)
            self._contract_menu.add_command(
                label="View Details", command=self.view_selected_contract
            )
            self._contract_menu.add_command(
                label="Add Subcontract", command=self.prefill_add_subcontract
            )
            self._contract_menu.add_command(
                label="Show Subsets", command=self.open_contract_subsets
            )
            self._contract_menu.add_command(
                label="Open Attached File", command=self._open_attached_file
            )
            self._contract_menu.add_command(
                label="Open Containing Folder", command=self._open_containing_folder
            )
            self._contract_menu.add_command(
                label="Download Attached File", command=self._download_attached_file
            )
            self._contract_menu.add_command(
                label="Restore Contract", command=self._restore_contract
            )
            self._contract_menu.add_separator()
            self._contract_menu.add_command(
                label="Delete Contract", command=self._delete_contract
            )
            self.contracts_tree.bind("<Button-3>", self._on_tree_right_click)
            self.contracts_list = None
        else:
            self.contracts_list = None
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill="x", pady=(5, 0))
        ttk.Button(btn_frame, text="Refresh", command=self.load_contracts).pack(
            side="left"
        )
        ttk.Button(
            btn_frame, text="Open Trash Manager", command=self.open_trash_manager
        ).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Undo History", command=self.open_undo_history).pack(
            side="left", padx=6
        )
        ttk.Button(
            btn_frame, text="View Details", command=self.view_selected_contract
        ).pack(side="left", padx=5)
        ttk.Button(
            btn_frame, text="Add Subcontract", command=self.prefill_add_subcontract
        ).pack(side="left", padx=5)

        right_frame = ttk.Frame(self, padding=10)
        right_frame.place(x=440, y=10, width=450, height=540)

        check_frame = ttk.LabelFrame(right_frame, text="Attendance", padding=10)
        check_frame.pack(fill="x", pady=(0, 10))
        self.check_status_lbl = ttk.Label(check_frame, text="Not checked in")
        self.check_status_lbl.grid(row=0, column=0, sticky="w")
        self.check_btn = ttk.Button(
            check_frame, text="Check In", command=self.toggle_check
        )
        self.check_btn.grid(row=0, column=1, sticky="e", padx=4)
        check_frame.columnconfigure(0, weight=1)

        add_frame = ttk.LabelFrame(right_frame, text="Add Contract", padding=10)
        add_frame.pack(fill="x", pady=(0, 10))
        self.entry_cid = tk.StringVar()
        # now used for construction-specific contracts
        self.entry_construction_id = tk.StringVar()
        # hierarchical parent contract id (optional)
        self.entry_parent_contract_id = tk.StringVar()
        # metadata
        self.entry_area = tk.StringVar()
        self.entry_incharge = tk.StringVar()
        self.entry_start = tk.StringVar()
        self.entry_end = tk.StringVar()
        self.entry_terms = tk.StringVar()
        ttk.Label(add_frame, text="Contract ID").grid(row=0, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.entry_cid).grid(
            row=0, column=1, sticky="ew"
        )
        ttk.Label(add_frame, text="Construction ID").grid(row=1, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.entry_construction_id).grid(
            row=1, column=1, sticky="ew"
        )
        ttk.Label(add_frame, text="Parent Contract ID (optional)").grid(
            row=1, column=2, sticky="w", padx=(8, 0)
        )
        ttk.Entry(add_frame, textvariable=self.entry_parent_contract_id).grid(
            row=1, column=3, sticky="ew"
        )
        ttk.Label(add_frame, text="Start (YYYY-MM-DD)").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Entry(add_frame, textvariable=self.entry_start).grid(
            row=2, column=1, sticky="ew"
        )
        ttk.Label(add_frame, text="Area").grid(row=2, column=2, sticky="w", padx=(8, 0))
        ttk.Entry(add_frame, textvariable=self.entry_area).grid(
            row=2, column=3, sticky="ew"
        )
        ttk.Label(add_frame, text="End (YYYY-MM-DD)").grid(row=3, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.entry_end).grid(
            row=3, column=1, sticky="ew"
        )
        ttk.Label(add_frame, text="In-charge").grid(
            row=3, column=2, sticky="w", padx=(8, 0)
        )
        ttk.Entry(add_frame, textvariable=self.entry_incharge).grid(
            row=3, column=3, sticky="ew"
        )
        ttk.Label(add_frame, text="Terms").grid(row=4, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.entry_terms).grid(
            row=4, column=1, sticky="ew"
        )
        # file attachment
        self.contract_file_path_var = tk.StringVar()
        ttk.Button(
            add_frame,
            text="Attach File",
            command=lambda: self.pick_contract_file(parent=self),
        ).grid(row=5, column=0, sticky="w", pady=(6, 0))
        self.file_lbl = ttk.Label(add_frame, textvariable=self.contract_file_path_var)
        self.file_lbl.grid(row=5, column=1, sticky="w", pady=(6, 0))
        add_frame.columnconfigure(1, weight=1)
        add_frame.columnconfigure(3, weight=1)
        self.add_contract_btn = ttk.Button(
            add_frame, text="Add Contract", command=self.add_contract
        )
        self.add_contract_btn.grid(row=6, column=0, columnspan=2, pady=(8, 0))

        if self.user_role not in ("admin", "high_manager"):
            self.add_contract_btn.config(state="disabled")
        if self.user_role in ("driver", "construction_worker"):
            # visually hide the add contract section for restricted roles
            add_frame.pack_forget()

        self.manage_emp_btn = ttk.Button(
            right_frame, text="Manage Employees", command=self.open_employee_management
        )
        self.manage_emp_btn.pack(fill="x", pady=(6, 0))
        if self.user_role not in ("admin", "high_manager"):
            self.manage_emp_btn.config(state="disabled")
        if self.user_role in ("driver", "construction_worker"):
            self.manage_emp_btn.pack_forget()
        # Import from file feature
        try:
            # Prefer package-qualified import to support running the app as a package/module.
            try:
                from hr_management_app.src.ui_import import ImportDialog  # type: ignore
            except Exception:
                # Fallback for environments where the package path isn't set.
                from ui_import import ImportDialog  # type: ignore

            self.import_btn = ttk.Button(
                right_frame,
                text="Import Employees from File",
                command=lambda: ImportDialog(self),
            )
            self.import_btn.pack(fill="x", pady=(6, 0))
            if self.user_role not in ("admin", "high_manager"):
                self.import_btn.config(state="disabled")
            if self.user_role in ("driver", "construction_worker"):
                self.import_btn.pack_forget()
        except Exception as exc:
            # optional feature; if imports aren't available do not crash GUI
            logger.info("Import feature unavailable: %s", exc)

    def open_manage_users(self):
        if self.user_role != "admin":
            messagebox.showerror("Permission Denied", "Only admin can manage users.")
            return
        # pass current actor id so role changes are audited
        ManageUsersWindow(
            self,
            self.user_role,
            int(self.user_id) if self.user_id is not None else None,
        )

    def load_employee_profile(self):
        if self.employee_id is None:
            return
        row = get_employee_by_id(int(self.employee_id))
        if not row:
            return
        (
            emp_id,
            user_id,
            empnum,
            name,
            dob,
            job_title,
            role,
            year_start,
            year_end,
            profile_pic,
            contract_type,
        ) = row
        self.employee = {
            "id": emp_id,
            "empnum": empnum,
            "name": name,
            "dob": dob,
            "job_title": job_title,
            "role": role,
            "year_start": year_start,
            "year_end": year_end,
            "profile_pic": profile_pic,
            "contract_type": contract_type,
            "user_id": user_id,
        }
        if profile_pic and os.path.exists(profile_pic) and Image and ImageTk:
            try:
                img = Image.open(profile_pic)
                img = img.resize((64, 64))
                self.profile_image = ImageTk.PhotoImage(img)
                self.photo_lbl.config(image=self.profile_image)
            except Exception:
                self.photo_lbl.config(text="No Image")
        else:
            self.photo_lbl.config(text="No Image")

        self.name_label.config(text=name or "Name")
        self.job_label.config(text=job_title or "Job Title")
        self.update_check_state()

    def update_check_state(self):
        if not self.employee_id:
            self.check_status_lbl.config(text="No employee selected")
            self.check_btn.config(state="disabled")
            return
        open_session = has_open_session(int(self.employee_id))
        self.check_status_lbl.config(
            text=("Open session" if open_session else "Not checked in")
        )
        self.check_btn.config(
            text=("Check Out" if open_session else "Check In"), state="normal"
        )

    def open_own_profile(self):
        if not self.employee_id or not self.employee:
            messagebox.showinfo(
                "No profile", "No employee profile available", parent=self
            )
            return
        win = EmployeeProfileWindow(
            self,
            int(self.employee_id),
            self.user_role,
            int(self.user_id) if self.user_id is not None else 0,
        )
        self.wait_window(win)
        self.load_employee_profile()

    def open_employee_management(self):
        EmployeeManagementWindow(
            self, self.user_role, int(self.user_id) if self.user_id is not None else 0
        )

    def open_contract_subsets(self):
        try:
            from contracts.gui_subsets import show_contract_subsets

            # if a contract is selected in listbox, use it; otherwise prompt
            cid = None
            if self.contracts_list and self.contracts_list.curselection():
                text = self.contracts_list.get(self.contracts_list.curselection()[0])
                cid = int(text.split("|")[0].strip())
            else:
                cid = simpledialog.askinteger(
                    "Contract ID", "Enter contract id to view subsets", parent=self
                )
            if not cid:
                return
            show_contract_subsets(
                int(cid),
                actor_user_id=int(self.user_id) if self.user_id is not None else None,
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def prefill_add_subcontract(self):
        """Pre-fill the Add Contract form's parent_contract_id with the selected contract in the tree/list."""
        try:
            selected_cid = None
            if hasattr(self, "contracts_tree") and self.contracts_tree is not None:
                sel = self.contracts_tree.selection()
                if sel:
                    selected_cid = self.contracts_tree.item(sel[0], "values")[0]
            elif self.contracts_list is not None:
                sel = self.contracts_list.curselection()
                if sel:
                    text = self.contracts_list.get(sel[0])
                    selected_cid = text.split("|")[0].strip()
            if not selected_cid:
                messagebox.showinfo(
                    "Select", "Select a contract first to add a subcontract."
                )
                return
            self.entry_parent_contract_id.set(str(selected_cid))
            # best-effort focus: try the parent id entry widget if present
            try:
                # the parent id entry is the second row, column 3 widget; attempt to find by grid
                for child in self.winfo_children():
                    try:
                        _ = child.nametowidget(child.winfo_name())
                    except Exception:
                        _ = child
                # we avoid fragile lookups; leave focus to the user if not found
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_tree_right_click(self, event):
        # Select the item under mouse and popup context menu
        try:
            item = self.contracts_tree.identify_row(event.y)
            if item:
                # select it
                self.contracts_tree.selection_set(item)
                # show menu at pointer
                try:
                    self._contract_menu.tk_popup(event.x_root, event.y_root)
                finally:
                    self._contract_menu.grab_release()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _sort_contracts_by(self, column: str):
        # toggle sort direction if same column
        cur_col, asc = getattr(self, "_contract_sort", (None, True))
        if cur_col == column:
            asc = not asc
        else:
            asc = True
        self._contract_sort = (column, asc)
        # reload tree with sort applied
        self.load_contracts()

    def _open_attached_file(self):
        try:
            # find selected contract id
            sel = self.contracts_tree.selection()
            if not sel:
                messagebox.showinfo("Select", "Select a contract first.")
                return
            cid = int(self.contracts_tree.item(sel[0], "values")[0])
            from contracts.models import Contract

            contract = Contract.retrieve_contract(cid)
            if not contract:
                messagebox.showinfo("Not found", "Contract not found.")
                return
            file_path = getattr(contract, "file_path", None)
            if not file_path:
                messagebox.showinfo("No file", "No attached file for this contract.")
                return
            try:
                if sys.platform == "win32":
                    os.startfile(file_path)  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    subprocess.run(["open", file_path], check=False)
                else:
                    subprocess.run(["xdg-open", file_path], check=False)
            except Exception as e:
                messagebox.showerror("Open File", f"Failed to open file: {e}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _open_containing_folder(self):
        try:
            sel = self.contracts_tree.selection()
            if not sel:
                messagebox.showinfo("Select", "Select a contract first.")
                return
            cid = int(self.contracts_tree.item(sel[0], "values")[0])
            from contracts.models import Contract

            contract = Contract.retrieve_contract(cid)
            if not contract:
                messagebox.showinfo("Not found", "Contract not found.")
                return
            file_path = getattr(contract, "file_path", None)
            if not file_path:
                messagebox.showinfo("No file", "No attached file for this contract.")
                return
            folder = os.path.dirname(file_path)
            try:
                if sys.platform == "win32":
                    subprocess.run(["explorer", folder], check=False)
                elif sys.platform == "darwin":
                    subprocess.run(["open", folder], check=False)
                else:
                    subprocess.run(["xdg-open", folder], check=False)
            except Exception as e:
                messagebox.showerror("Open Folder", f"Failed to open folder: {e}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _download_attached_file(self):
        try:
            sel = self.contracts_tree.selection()
            if not sel:
                messagebox.showinfo("Select", "Select a contract first.")
                return
            cid = int(self.contracts_tree.item(sel[0], "values")[0])
            import shutil

            from contracts.models import Contract

            contract = Contract.retrieve_contract(cid)
            if not contract:
                messagebox.showinfo("Not found", "Contract not found.")
                return
            file_path = getattr(contract, "file_path", None)
            if not file_path or not os.path.exists(file_path):
                messagebox.showinfo("No file", "No attached file for this contract.")
                return
            dest = filedialog.asksaveasfilename(
                title="Save attached file as", initialfile=os.path.basename(file_path)
            )
            if not dest:
                return
            try:
                shutil.copy2(file_path, dest)
                messagebox.showinfo("Saved", f"File saved to {dest}")
            except Exception as e:
                messagebox.showerror("Save Failed", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete_contract(self):
        try:
            sel = self.contracts_tree.selection()
            if not sel:
                messagebox.showinfo("Select", "Select a contract first.")
                return
            cid = int(self.contracts_tree.item(sel[0], "values")[0])
            from hr_management_app.src.database.database import (  # use soft-delete instead of hard delete
                get_child_contracts,
                get_subsets_count,
                soft_delete_contract,
            )

            # check for subsets and child contracts
            child_contracts = get_child_contracts(cid)
            subsets_count = get_subsets_count(cid)
            if child_contracts or subsets_count > 0:
                details = []
                if subsets_count:
                    details.append(f"{subsets_count} subsets")
                if child_contracts:
                    details.append(f"{len(child_contracts)} subcontracts")
                msg = (
                    f"Contract {cid} has " + ", ".join(details) + ".\n"
                    "Delete will cascade and remove all descendants and subsets. Continue?"
                )
                if not messagebox.askyesno("Cascade Delete Confirmation", msg):
                    return
                # perform recursive soft-delete
                soft_delete_contract(cid, cascade=True)
            else:
                if not messagebox.askyesno(
                    "Confirm", f"Delete contract {cid}? This cannot be undone."
                ):
                    return
                # safe to delete single contract
                from contracts.models import Contract

                contract = Contract.retrieve_contract(cid)
                if not contract:
                    messagebox.showinfo("Not found", "Contract not found.")
                    return
                # soft-delete single contract (no cascade)
                try:
                    soft_delete_contract(cid, cascade=False)
                except Exception:
                    # fallback: hard delete via model
                    contract.delete()
            messagebox.showinfo("Deleted", "Contract deleted.")
            self.load_contracts()
        except Exception as e:
            messagebox.showerror("Error", str(e))
        else:
            # show undo toast for quick restore
            try:
                self._show_undo_toast(cid)
            except Exception:
                pass

    def _restore_contract(self):
        try:
            sel = self.contracts_tree.selection()
            if not sel:
                messagebox.showinfo("Select", "Select a contract first.")
                return
            cid = int(self.contracts_tree.item(sel[0], "values")[0])
            from hr_management_app.src.database.database import restore_contract

            restore_contract(cid, cascade=True)
            messagebox.showinfo("Restored", "Contract restored.")
            self.load_contracts()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_contracts(self):
        # If contracts_list is not present for this role, skip
        try:
            # clear existing tree
            if hasattr(self, "contracts_tree") and self.contracts_tree is not None:
                for ch in self.contracts_tree.get_children():
                    self.contracts_tree.delete(ch)
            # include deleted rows only when requested via the Show Trash checkbox
            try:
                rows = get_all_contracts_filtered(
                    include_deleted=(
                        self.show_trash_var.get()
                        if hasattr(self, "show_trash_var")
                        else False
                    )
                )
            except Exception:
                # fallback to older helper
                from hr_management_app.src.database.database import (
                    get_all_contracts as _gac,
                )

                rows = _gac()
            # build a map of id -> children to assemble a simple tree and a row lookup
            nodes = {}
            children_map = {}
            rows_by_id = {}
            for row in rows:
                # Expected new shape: id, employee_id, construction_id, parent_contract_id, start_date, end_date, area, incharge, terms, file
                if len(row) >= 10:
                    cid = row[0]
                    parent_id = row[3]
                    start = row[4]
                    end = row[5]
                    area = row[6]
                    incharge = row[7]
                    terms = row[8]
                else:
                    cid = row[0] if len(row) > 0 else None
                    parent_id = None
                    start = row[3] if len(row) > 3 else None
                    end = row[4] if len(row) > 4 else None
                    area = None
                    incharge = None
                    terms = None
                nodes[cid] = f"{cid} | Area:{area or 'N/A'} | {start} → {end}"
                rows_by_id[cid] = {
                    "area": area,
                    "incharge": incharge,
                    "start": start,
                    "end": end,
                    "terms": terms,
                    "parent_id": parent_id,
                }
                children_map.setdefault(parent_id, []).append(cid)

            # prepare search/filter
            search = (
                self.search_var.get().strip()
                if hasattr(self, "search_var")
                else ""
            )
            # if a search term is provided, prefer DB-backed search to get matching ids
            match_ids = set()
            if search:
                try:
                    # Contract.search returns Contract objects
                    matches = Contract.search(
                        search, include_deleted=(
                            self.show_trash_var.get()
                            if hasattr(self, "show_trash_var")
                            else False
                        )
                    )
                    match_ids = {int(m.id) for m in matches if getattr(m, "id", None) is not None}
                except Exception:
                    match_ids = set()

            # determine which nodes to include: include node if it or a descendant matches search
            include_cache = {}

            def node_matches(cid_val: int) -> bool:
                # If no search, all nodes match by default
                if not search:
                    return True
                # DB matched ids take precedence
                if cid_val in match_ids:
                    return True
                info = rows_by_id.get(cid_val, {})
                for f in (info.get("area"), info.get("incharge"), info.get("terms")):
                    if f and search in str(f).lower():
                        return True
                return False

            def should_include(cid_val: int) -> bool:
                if cid_val in include_cache:
                    return include_cache[cid_val]
                # own match
                if node_matches(cid_val):
                    include_cache[cid_val] = True
                    return True
                # descendant match
                for ch in children_map.get(cid_val, []):
                    if should_include(ch):
                        include_cache[cid_val] = True
                        return True
                include_cache[cid_val] = False
                return False

            # For multi-column tree, collect rows then insert with hierarchy; support sorting
            def insert_subtree(parent, parent_node):
                rows_to_insert = []
                for child_id in children_map.get(parent, []):
                    if not should_include(child_id):
                        continue
                    info = rows_by_id.get(child_id, {})
                    area = info.get("area")
                    incharge = info.get("incharge")
                    start = info.get("start")
                    end = info.get("end")
                    # subset count
                    subs_count = 0
                    try:
                        from hr_management_app.src.database.database import (
                            get_subsets_for_contract,
                        )

                        subs = get_subsets_for_contract(child_id)
                        subs_count = len(subs)
                    except Exception:
                        subs_count = 0
                    rows_to_insert.append(
                        (
                            child_id,
                            area or "",
                            incharge or "",
                            start or "",
                            end or "",
                            subs_count,
                        )
                    )

                # apply sorting if requested
                sort_col, asc = getattr(self, "_contract_sort", (None, True))
                if sort_col:
                    col_index = {
                        "cid": 0,
                        "area": 1,
                        "incharge": 2,
                        "start": 3,
                        "end": 4,
                        "subsets": 5,
                    }.get(sort_col, 0)
                    try:
                        rows_to_insert.sort(
                            key=lambda r: (
                                r[col_index] if r[col_index] is not None else ""
                            )
                        )
                        if not asc:
                            rows_to_insert.reverse()
                    except Exception:
                        pass

                for vals in rows_to_insert:
                    node_id = self.contracts_tree.insert(
                        parent_node, "end", values=vals
                    )
                    insert_subtree(vals[0], node_id)

            # insert roots (parent is None)
            insert_subtree(None, "")
        except Exception as e:
            try:
                messagebox.showerror(
                    "Error", f"Failed to load contracts:\n{e}", parent=self
                )
            except Exception:
                messagebox.showerror("Error", f"Failed to load contracts:\n{e}")

    # ---- Trash manager and undo toast ----
    def open_trash_manager(self):
        win = tk.Toplevel(self)
        win.title("Trash Manager")
        win.geometry("700x420")
        frm = ttk.Frame(win, padding=8)
        frm.pack(fill="both", expand=True)

        cols = ("id", "area", "incharge", "deleted_at")
        tree = ttk.Treeview(frm, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c.title())
            tree.column(c, anchor="center")
        tree.pack(fill="both", expand=True)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Refresh", command=lambda: self._load_trash(tree)).pack(
            side="left"
        )
        ttk.Button(
            btns,
            text="Restore Selected",
            command=lambda: self._restore_selected_from_trash(tree),
        ).pack(side="left", padx=4)
        ttk.Button(
            btns,
            text="Purge Selected",
            command=lambda: self._purge_selected_from_trash(tree),
        ).pack(side="left", padx=4)
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right")

        self._load_trash(tree)

    def _load_trash(self, tree):
        for i in tree.get_children():
            tree.delete(i)
        try:
            from hr_management_app.src.database.database import list_trashed_contracts

            rows = list_trashed_contracts()
            for r in rows:
                # r shape: id, employee_id, construction_id, parent_id, start, end, area, incharge, terms, file, deleted, deleted_at
                tree.insert(
                    "", "end", values=(r[0], r[6] or "", r[7] or "", r[11] or "")
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load trash: {e}")

    def _restore_selected_from_trash(self, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select item(s) to restore")
            return
        ids = [int(tree.item(s)["values"][0]) for s in sel]
        try:
            from hr_management_app.src.database.database import restore_contract

            for cid in ids:
                restore_contract(cid, cascade=True)
            messagebox.showinfo("Restored", "Selected contracts restored")
            self.load_contracts()
            self._load_trash(tree)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _purge_selected_from_trash(self, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select item(s) to purge")
            return
        if not messagebox.askyesno("Confirm", "Permanently delete selected contracts?"):
            return
        ids = [int(tree.item(s)["values"][0]) for s in sel]
        try:
            from hr_management_app.src.database.database import (
                delete_contract_and_descendants,
            )

            for cid in ids:
                delete_contract_and_descendants(cid)
            messagebox.showinfo("Purged", "Selected contracts permanently deleted")
            self.load_contracts()
            self._load_trash(tree)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _show_undo_toast(self, contract_id: int, timeout: int = 6):
        # polished transient Toplevel with a progress bar and Undo button
        try:
            toast = tk.Toplevel(self)
            toast.overrideredirect(True)
            toast.attributes("topmost", True)
            # frame with relief and padding for a modern look
            frm = ttk.Frame(toast, padding=6, relief="raised", borderwidth=1)
            frm.pack(fill="both", expand=True)

            lbl = ttk.Label(
                frm, text=f"Contract {contract_id} moved to Trash", anchor="w"
            )
            lbl.pack(side="top", fill="x")

            inner = ttk.Frame(frm)
            inner.pack(side="top", fill="x", pady=(6, 0))
            undo_btn = ttk.Button(
                inner,
                text="Undo",
                command=lambda: [self._undo_restore(contract_id), toast.destroy()],
            )
            undo_btn.pack(side="left")
            # small "View History" link
            hist_btn = ttk.Button(
                inner,
                text="View History",
                command=lambda: [self.open_undo_history(), toast.destroy()],
            )
            hist_btn.pack(side="left", padx=(6, 0))

            # progress bar showing time left
            pb = ttk.Progressbar(frm, mode="determinate", maximum=timeout * 10)
            pb.pack(side="top", fill="x", pady=(6, 0))

            # position near main window bottom-right
            self.update_idletasks()
            width = 340
            height = 84
            x = max(self.winfo_rootx() + self.winfo_width() - width - 12, 12)
            y = max(self.winfo_rooty() + self.winfo_height() - height - 12, 12)
            toast.geometry(f"{width}x{height}+{x}+{y}")

            # add to undo history stack
            if not hasattr(self, "_undo_history"):
                self._undo_history = []  # list of (id, ts)
            import time

            self._undo_history.insert(0, (contract_id, int(time.time())))
            # keep limited history
            if len(self._undo_history) > 10:
                self._undo_history = self._undo_history[:10]

            # animate progress bar in 100ms steps
            def tick(remaining: int = timeout * 10):
                try:
                    if remaining <= 0:
                        toast.destroy()
                        return
                    pb["value"] = (timeout * 10) - remaining
                    toast.after(100, lambda: tick(remaining - 1))
                except Exception:
                    try:
                        toast.destroy()
                    except Exception:
                        pass

            tick()
        except Exception:
            pass

    def _undo_restore(self, cid: int):
        try:
            from hr_management_app.src.database.database import restore_contract

            restore_contract(cid, cascade=False)
            self.load_contracts()
        except Exception:
            pass

    def open_undo_history(self):
        # shows a small window with recent deletions and restore buttons
        win = tk.Toplevel(self)
        win.title("Undo History")
        win.geometry("420x320")
        frm = ttk.Frame(win, padding=8)
        frm.pack(fill="both", expand=True)

        cols = ("id", "deleted_at")
        tree = ttk.Treeview(frm, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c.title())
            tree.column(c, anchor="center")
        tree.pack(fill="both", expand=True)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(
            btns, text="Refresh", command=lambda: self._populate_undo_history(tree)
        ).pack(side="left")
        ttk.Button(
            btns,
            text="Restore Selected",
            command=lambda: self._restore_from_history(tree),
        ).pack(side="left", padx=4)
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right")

        self._populate_undo_history(tree)

    def _populate_undo_history(self, tree):
        for i in tree.get_children():
            tree.delete(i)
        entries = getattr(self, "_undo_history", [])
        # try to enrich with deleted_at from DB if available
        try:
            from hr_management_app.src.database.database import get_contract_by_id

            for cid, ts in entries:
                row = get_contract_by_id(cid, include_deleted=True)
                deleted_at = None
                if row:
                    deleted_at = (
                        row.get("deleted_at")
                        if isinstance(row, dict)
                        else row[11] if len(row) > 11 else None
                    )
                tree.insert("", "end", values=(cid, deleted_at or ts))
        except Exception:
            for cid, ts in entries:
                tree.insert("", "end", values=(cid, ts))

    def _restore_from_history(self, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select item(s) to restore")
            return
        ids = [int(tree.item(s)["values"][0]) for s in sel]
        try:
            from hr_management_app.src.database.database import restore_contract

            for cid in ids:
                restore_contract(cid, cascade=False)
            messagebox.showinfo("Restored", "Selected contracts restored")
            self.load_contracts()
            # remove restored from history
            self._undo_history = [
                e for e in getattr(self, "_undo_history", []) if e[0] not in ids
            ]
            self._populate_undo_history(tree)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def view_selected_contract(self):
        # support both tree and list selection
        cid = None
        if hasattr(self, "contracts_tree") and self.contracts_tree is not None:
            sel = self.contracts_tree.selection()
            if not sel:
                messagebox.showinfo("Info", "Select a contract first.")
                return
            item = sel[0]
            cid = self.contracts_tree.item(item, "values")[0]
        else:
            if self.contracts_list is None:
                messagebox.showinfo(
                    "Unavailable", "Contracts are not available for your role."
                )
                return
            sel = self.contracts_list.curselection()
            if not sel:
                messagebox.showinfo("Info", "Select a contract first.")
                return
            text = self.contracts_list.get(sel[0])
            cid = text.split("|")[0].strip()
        try:
            from contracts.models import Contract

            contract = Contract.retrieve_contract(int(cid))
            if contract:
                # show a details window with an Open File button when applicable
                details = contract.get_details()
                win = tk.Toplevel(self)
                win.title(f"Contract {contract.id}")
                frm = ttk.Frame(win, padding=8)
                frm.pack(fill="both", expand=True)
                text = tk.Text(frm, height=12, width=60)
                text.insert("1.0", "\n".join(f"{k}: {v}" for k, v in details.items()))
                text.config(state="disabled")
                text.pack(fill="both", expand=True)
                btn_fr = ttk.Frame(frm)
                btn_fr.pack(fill="x", pady=(6, 0))
                # open attached file if present
                file_path = getattr(contract, "file_path", None)
                if file_path:

                    def _open():
                        try:
                            if sys.platform == "win32":
                                os.startfile(file_path)  # type: ignore[attr-defined]
                            elif sys.platform == "darwin":
                                subprocess.run(["open", file_path], check=False)
                            else:
                                subprocess.run(["xdg-open", file_path], check=False)
                        except Exception as e:
                            messagebox.showerror(
                                "Open File", f"Failed to open file: {e}"
                            )

                    ttk.Button(btn_fr, text="Open Attached File", command=_open).pack(
                        side="left", padx=4
                    )
                ttk.Button(btn_fr, text="Close", command=win.destroy).pack(
                    side="right", padx=4
                )
                self.wait_window(win)
            else:
                messagebox.showinfo("Not found", "Contract not found in DB.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_contract(self):
        try:
            cid_text = self.entry_cid.get().strip()
            eid_text = self.entry_construction_id.get().strip()
            start = self.entry_start.get().strip()
            end = self.entry_end.get().strip()
            terms = self.entry_terms.get().strip()

            try:
                from ui_validators import validate_contract_fields

                cid, eid, start_iso, end_iso, parent_id = validate_contract_fields(
                    cid_text, eid_text, start, end, self.entry_parent_contract_id.get()
                )
            except Exception as ve:
                messagebox.showerror("Validation", str(ve), parent=self)
                return

            # note: construction_id is independent of employees; allow empty employee id for construction-only contracts
            # if a file was attached, store it and set file_path; surface errors to the user
            file_path = self.contract_file_path_var.get() or None
            stored_path = None
            if file_path:
                try:
                    from hr_management_app.src.contracts.models import (
                        store_contract_file,
                    )

                    stored_path = store_contract_file(file_path, construction_id=eid)
                except Exception as exc:
                    # Surface storage error to user and abort the add
                    logger.exception("Failed to store contract file: %s", exc)
                    messagebox.showerror(
                        "File error",
                        f"Failed to store attached file: {exc}",
                        parent=self,
                    )
                    return

            c = SimpleNamespace(
                id=cid,
                employee_id=None,
                construction_id=eid,
                parent_contract_id=parent_id,
                area=(self.entry_area.get().strip() or None),
                incharge=(self.entry_incharge.get().strip() or None),
                start_date=start_iso,
                end_date=end_iso,
                terms=terms,
                file_path=stored_path,
            )
            add_contract_to_db(c)
            messagebox.showinfo("Success", "Contract added.", parent=self)
            self.clear_add_fields()
            self.load_contracts()
        except Exception as e:
            messagebox.showerror("Error adding contract", str(e))

    def clear_add_fields(self):
        self.entry_cid.set("")
        self.entry_construction_id.set("")
        self.entry_parent_contract_id.set("")
        self.entry_area.set("")
        self.entry_incharge.set("")
        self.entry_start.set("")
        self.entry_end.set("")
        self.entry_terms.set("")
        self.contract_file_path_var.set("")

    def pick_contract_file(self, parent=None):
        """Open a file picker for pdf/docx and set the selected path into the UI var."""
        try:
            filetypes = [
                ("PDF files", "*.pdf"),
                ("Word documents", "*.docx"),
                ("All files", "*"),
            ]
            path = filedialog.askopenfilename(
                title="Select contract file", filetypes=filetypes, parent=parent
            )
            if path:
                self.contract_file_path_var.set(path)
        except Exception as e:
            try:
                messagebox.showerror("File select", str(e), parent=parent)
            except Exception:
                messagebox.showerror("File select", str(e))

    def toggle_check(self):
        if not self.employee_id:
            messagebox.showinfo("No employee", "No employee selected", parent=self)
            return
        if has_open_session(int(self.employee_id)):
            out = record_check_out(int(self.employee_id))
            if out:
                messagebox.showinfo("Checked out", f"Checked out at {out}", parent=self)
            else:
                messagebox.showerror(
                    "Error", "No open session to check out", parent=self
                )
        else:
            inn = record_check_in(int(self.employee_id))
            if inn:
                messagebox.showinfo("Checked in", f"Checked in at {inn}", parent=self)
            else:
                messagebox.showerror("Error", "Already checked in today", parent=self)
        self.update_check_state()

    def calc_month(self):
        if not self.employee_id:
            messagebox.showinfo("No employee", "No employee selected", parent=self)
            return
        if not can_count_salary(self.user_role):
            messagebox.showerror(
                "Permission Denied",
                "You do not have permission to use salary counting.",
                parent=self,
            )
            return
        ym = self.month_var.get().strip()
        try:
            year_s, month_s = ym.split("-")
            year = int(year_s)
            month = int(month_s)
        except Exception:
            messagebox.showerror("Error", "Month must be YYYY-MM", parent=self)
            return
        try:
            seconds = get_month_work_seconds(int(self.employee_id), year, month)
            hours = seconds / 3600.0
            wage = float(self.wage_var.get().strip() or 0.0)
            salary = round(hours * wage, 2)
            self.month_result.config(text=f"Hours: {hours:.2f}  Salary: {salary:.2f}")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 900
        h = self.winfo_height() or 560
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    HRApp(employee_id=None, user_role="engineer", user_id=None).mainloop()
