import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from hr_management_app.src.database.database import (
    ALLOWED_ROLES,
    create_employee,
    create_reset_token,
    create_user,
    get_admin_user,
    get_employee_by_user,
    get_user_by_email,
    reset_password_with_token,
    send_password_reset_email,
    send_verification_code,
    verify_user,
)

logger = logging.getLogger(__name__)


class SignUpWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sign Up")
        self.geometry("480x520")
        self.resizable(False, False)
        self.profile_path = None
        self.create_widgets()
        self.transient(parent)
        self.grab_set()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        row = 0
        ttk.Label(frm, text="Full name:").grid(row=row, column=0, sticky="e")
        self.name_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.name_var).grid(row=row, column=1, sticky="ew")
        row += 1
        ttk.Label(frm, text="Email:").grid(row=row, column=0, sticky="e")
        self.email_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.email_var).grid(row=row, column=1, sticky="ew")
        row += 1
        ttk.Label(frm, text="Password:").grid(row=row, column=0, sticky="e")
        self.pw_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.pw_var, show="*").grid(
            row=row, column=1, sticky="ew"
        )
        row += 1

        ttk.Label(frm, text="DOB (YYYY-MM-DD):").grid(row=row, column=0, sticky="e")
        self.dob_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.dob_var).grid(row=row, column=1, sticky="ew")
        row += 1
        ttk.Label(frm, text="Job title:").grid(row=row, column=0, sticky="e")
        self.job_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.job_var).grid(row=row, column=1, sticky="ew")
        row += 1

        # Role selection is not changeable at signup. New users default to 'engineer'.
        ttk.Label(frm, text="Role:").grid(row=row, column=0, sticky="e")
        self.role_var = tk.StringVar(value="engineer")
        # Use a disabled combobox to show the default role without allowing edits.
        self.role_combo = ttk.Combobox(
            frm, textvariable=self.role_var, values=ALLOWED_ROLES, state="disabled"
        )
        self.role_combo.grid(row=row, column=1, sticky="ew")
        row += 1

        ttk.Label(frm, text="Year start:").grid(row=row, column=0, sticky="e")
        self.year_start_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.year_start_var).grid(
            row=row, column=1, sticky="ew"
        )
        row += 1
        ttk.Label(frm, text="Year end:").grid(row=row, column=0, sticky="e")
        self.year_end_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.year_end_var).grid(
            row=row, column=1, sticky="ew"
        )
        row += 1

        ttk.Label(frm, text="Contract type:").grid(row=row, column=0, sticky="e")
        self.contract_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.contract_var).grid(
            row=row, column=1, sticky="ew"
        )
        row += 1

        ttk.Label(frm, text="Profile picture:").grid(row=row, column=0, sticky="e")
        pic_frame = ttk.Frame(frm)
        pic_frame.grid(row=row, column=1, sticky="ew")
        self.pic_lbl = ttk.Label(pic_frame, text="No file")
        self.pic_lbl.pack(side="left", fill="x", expand=True)
        ttk.Button(pic_frame, text="Choose...", command=self.choose_profile_pic).pack(
            side="right"
        )
        row += 1

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btn_frame, text="Sign Up", command=self.do_sign_up).pack(
            side="left", padx=6
        )
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(
            side="right", padx=6
        )

        frm.columnconfigure(1, weight=1)

    def choose_profile_pic(self):
        path = filedialog.askopenfilename(
            title="Select profile picture",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif"), ("All files", "*.*")],
        )
        if path:
            self.profile_path = path
            self.pic_lbl.config(text=os.path.basename(path))

    def do_sign_up(self):
        name = self.name_var.get().strip()
        email = self.email_var.get().strip().lower()
        pw = self.pw_var.get()
        dob = self.dob_var.get().strip() or None
        job = self.job_var.get().strip() or None
        role = self.role_var.get().strip() or "engineer"
        year_start = (
            int(self.year_start_var.get().strip())
            if self.year_start_var.get().strip()
            else None
        )
        year_end = (
            int(self.year_end_var.get().strip())
            if self.year_end_var.get().strip()
            else None
        )
        contract_type = self.contract_var.get().strip() or None
        profile_pic = self.profile_path

        if not name or not email or not pw:
            messagebox.showerror(
                "Error", "Name, email and password are required", parent=self
            )
            return

        if role == "admin" and get_admin_user():
            messagebox.showerror(
                "Error",
                "Admin account already exists. Choose another role.",
                parent=self,
            )
            return

        code = "{:06d}".format(__import__("random").randint(0, 999999))
        try:
            send_verification_code(email, code)
        except Exception:
            # Log full exception, but show a friendly message to the user.
            logger.exception("Failed to send verification code to %s", email)
            messagebox.showwarning(
                "Email failed",
                "Could not send verification email. For development the code will be shown locally.",
                parent=self,
            )
            # Only show the code (not the exception) so developers can continue locally.
            messagebox.showinfo("Verification code (dev)", f"Code: {code}", parent=self)

        user_code = simpledialog.askstring(
            "Verification", "Enter 6-digit code sent to your email:", parent=self
        )
        if not user_code or user_code.strip() != code:
            messagebox.showerror("Error", "Verification code incorrect", parent=self)
            return

        try:
            user_id = create_user(email, pw, role=role)
            emp_id = create_employee(
                user_id=user_id,
                name=name,
                dob=dob,
                job_title=job,
                role=role,
                year_start=year_start,
                profile_pic=profile_pic,
                contract_type=contract_type,
                year_end=year_end,
            )
            messagebox.showinfo(
                "Success", f"Account created. Employee ID: {emp_id}", parent=self
            )
            self.destroy()
        except Exception as e:
            logger.exception("Failed to create user %s: %s", email, e)
            messagebox.showerror("Error creating account", str(e), parent=self)

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 480
        h = self.winfo_height() or 520
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


class AuthWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sign In")
        self.geometry("380x240")
        self.resizable(False, False)
        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Email:").grid(row=0, column=0, sticky="e")
        self.email_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.email_var).grid(row=0, column=1, sticky="ew")

        ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky="e")
        self.pw_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.pw_var, show="*").grid(
            row=1, column=1, sticky="ew"
        )

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btn_frame, text="Sign In", command=self.sign_in).pack(
            side="left", padx=6
        )
        ttk.Button(btn_frame, text="Sign Up", command=self.open_sign_up).pack(
            side="left", padx=6
        )
        ttk.Button(
            btn_frame, text="Forgot Password", command=self.forgot_password
        ).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Exit", command=self.quit).pack(side="right", padx=6)

        frm.columnconfigure(1, weight=1)

    def sign_in(self):
        email = self.email_var.get().strip().lower()
        pw = self.pw_var.get()
        if not email or not pw:
            messagebox.showerror("Error", "Email and password required", parent=self)
            return
        if not verify_user(email, pw):
            messagebox.showerror("Error", "Invalid credentials", parent=self)
            return

        user = get_user_by_email(email)
        if not user:
            messagebox.showerror("Error", "User record not found", parent=self)
            return
        user_id = user[0]
        role = user[-1]

        emp = get_employee_by_user(user_id)
        emp_id = emp[0] if emp else None

        self.destroy()
        try:
            from hr_management_app.src.gui import HRApp

            app = HRApp(employee_id=emp_id, user_role=role, user_id=user_id)
            app.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start main app: {e}")

    def open_sign_up(self):
        SignUpWindow(self)

    def forgot_password(self):
        email = simpledialog.askstring(
            "Forgot password", "Enter your account email:", parent=self
        )
        if not email:
            return
        email = email.strip().lower()
        user = get_user_by_email(email)
        if not user:
            messagebox.showerror("Error", "Email not found", parent=self)
            return
        try:
            token = create_reset_token(email)
            try:
                send_password_reset_email(email, token)
                messagebox.showinfo(
                    "Reset sent",
                    "Password reset token sent to your email.",
                    parent=self,
                )
            except Exception:
                # Log full exception, but keep UI messaging simple and safe.
                logger.exception("Failed to send reset email to %s", email)
                messagebox.showwarning(
                    "Email failed",
                    "Could not send reset email. For development the token will be shown locally.",
                    parent=self,
                )
                messagebox.showinfo("Reset token (dev)", f"Token: {token}", parent=self)
        except Exception as e:
            logger.exception("Failed to create reset token for %s: %s", email, e)
            messagebox.showerror(
                "Error", f"Failed to create reset token: {e}", parent=self
            )
            return

        token_in = simpledialog.askstring(
            "Reset", "Enter the reset token:", parent=self
        )
        if not token_in:
            return
        new_pw = simpledialog.askstring(
            "Reset", "Enter new password:", show="*", parent=self
        )
        if not new_pw:
            return
        ok = reset_password_with_token(token_in.strip(), new_pw)
        if ok:
            messagebox.showinfo("Success", "Password has been reset.", parent=self)
        else:
            messagebox.showerror("Failed", "Token invalid or expired.", parent=self)

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 380
        h = self.winfo_height() or 240
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    AuthWindow().mainloop()
