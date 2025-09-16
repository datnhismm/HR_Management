import logging
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk
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
    get_all_contracts,
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
        with _conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, employee_number, name, job_title, role, year_start, year_end, contract_type, user_id FROM employees ORDER BY employee_number"
            )
            for row in c.fetchall():
                self.tree.insert("", "end", values=row)

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
            self.contracts_list = tk.Listbox(left_frame, height=18)
            self.contracts_list.pack(fill="both", expand=True, pady=(5, 5))
        else:
            self.contracts_list = None
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill="x", pady=(5, 0))
        ttk.Button(btn_frame, text="Refresh", command=self.load_contracts).pack(
            side="left"
        )
        ttk.Button(
            btn_frame, text="View Details", command=self.view_selected_contract
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
        self.entry_eid = tk.StringVar()
        self.entry_start = tk.StringVar()
        self.entry_end = tk.StringVar()
        self.entry_terms = tk.StringVar()
        ttk.Label(add_frame, text="Contract ID").grid(row=0, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.entry_cid).grid(
            row=0, column=1, sticky="ew"
        )
        ttk.Label(add_frame, text="Employee ID").grid(row=1, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.entry_eid).grid(
            row=1, column=1, sticky="ew"
        )
        ttk.Label(add_frame, text="Start (YYYY-MM-DD)").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Entry(add_frame, textvariable=self.entry_start).grid(
            row=2, column=1, sticky="ew"
        )
        ttk.Label(add_frame, text="End (YYYY-MM-DD)").grid(row=3, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.entry_end).grid(
            row=3, column=1, sticky="ew"
        )
        ttk.Label(add_frame, text="Terms").grid(row=4, column=0, sticky="w")
        ttk.Entry(add_frame, textvariable=self.entry_terms).grid(
            row=4, column=1, sticky="ew"
        )
        add_frame.columnconfigure(1, weight=1)
        self.add_contract_btn = ttk.Button(
            add_frame, text="Add Contract", command=self.add_contract
        )
        self.add_contract_btn.grid(row=5, column=0, columnspan=2, pady=(8, 0))

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
            from ui_import import ImportDialog

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
        except Exception:
            # optional feature; if imports aren't available do not crash GUI
            logger.info("Import feature unavailable (missing dependencies)")

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

    def load_contracts(self):
        # If contracts_list is not present for this role, skip
        if self.contracts_list is None:
            return
        try:
            self.contracts_list.delete(0, tk.END)
        except Exception:
            pass
        try:
            rows = get_all_contracts()
            for row in rows:
                cid, eid, start, end, terms = row
                self.contracts_list.insert(
                    tk.END, f"{cid} | Emp:{eid} | {start} → {end}"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load contracts:\n{e}")

    def view_selected_contract(self):
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
                from contracts.views import view_contract

                view_contract(contract)
                details = contract.get_details()
                detail_text = "\n".join(f"{k}: {v}" for k, v in details.items())
                messagebox.showinfo("Contract Details", detail_text)
            else:
                messagebox.showinfo("Not found", "Contract not found in DB.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_contract(self):
        try:
            cid_text = self.entry_cid.get().strip()
            eid_text = self.entry_eid.get().strip()
            start = self.entry_start.get().strip()
            end = self.entry_end.get().strip()
            terms = self.entry_terms.get().strip()

            try:
                from ui_validators import validate_contract_fields

                cid, eid, start_iso, end_iso = validate_contract_fields(
                    cid_text, eid_text, start, end
                )
            except Exception as ve:
                messagebox.showerror("Validation", str(ve), parent=self)
                return

            # verify employee exists
            if get_employee_by_id(eid) is None:
                messagebox.showerror(
                    "Validation", f"Employee id {eid} does not exist.", parent=self
                )
                return

            c = SimpleNamespace(
                id=cid,
                employee_id=eid,
                start_date=start_iso,
                end_date=end_iso,
                terms=terms,
            )
            add_contract_to_db(c)
            messagebox.showinfo("Success", "Contract added.", parent=self)
            self.clear_add_fields()
            self.load_contracts()
        except Exception as e:
            messagebox.showerror("Error adding contract", str(e))

    def clear_add_fields(self):
        self.entry_cid.set("")
        self.entry_eid.set("")
        self.entry_start.set("")
        self.entry_end.set("")
        self.entry_terms.set("")

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
