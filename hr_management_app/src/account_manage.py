import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from database.database import get_all_users, update_user_role, delete_user

class UserManagementWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("User Management")
        self.geometry("500x350")
        self.resizable(False, False)
        self.parent = parent
        self.create_widgets()
        self.load_users()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(frm, columns=("id", "email", "role"), show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("email", text="Email")
        self.tree.heading("role", text="Role")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("email", width=220, anchor="center")
        self.tree.column("role", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True)

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill="x", pady=8)
        ttk.Button(btn_frame, text="Edit Role", command=self.edit_role).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete User", command=self.delete_user).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.load_users).pack(side="right", padx=5)

    def load_users(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for user in get_all_users():
            self.tree.insert("", "end", values=user)

    def edit_role(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select User", "Please select a user to edit.")
            return
        user = self.tree.item(selected[0])["values"]
        if len(user) != 3:
            messagebox.showerror("Error", "User data is incomplete.")
            return
        user_id, email, role = user
        new_role = simpledialog.askstring("Edit Role", f"Enter new role for {email}:", initialvalue=role, parent=self)
        if new_role and new_role != role:
            update_user_role(user_id, new_role)
            self.load_users()
            messagebox.showinfo("Role Updated", f"Role for {email} updated to {new_role}.")

    def delete_user(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select User", "Please select a user to delete.")
            return
        user = self.tree.item(selected[0])["values"]
        if len(user) != 3:
            messagebox.showerror("Error", "User data is incomplete.")
            return
        user_id, email, role = user
        if messagebox.askyesno("Delete User", f"Are you sure you want to delete {email}?"):
            delete_user(user_id)
            self.load_users()
            messagebox.showinfo("User Deleted", f"User {email} deleted.")