import tkinter as tk
from tkinter import ttk, messagebox

class AdminAuthPage(tk.Toplevel):
    def __init__(self, parent, user_role):
        super().__init__(parent)
        self.title("Admin Authorization")
        self.geometry("400x200")
        self.resizable(False, False)
        self.user_role = user_role
        self.create_widgets()
        self.center_window()
        self.check_admin()

    def create_widgets(self):
        self.label = ttk.Label(self, text="Welcome, Admin!", font=("Arial", 16))
        self.label.pack(pady=40)
        self.btn_close = ttk.Button(self, text="Close", command=self.destroy)
        self.btn_close.pack(pady=10)

    def check_admin(self):
        if self.user_role != "admin":
            messagebox.showerror("Access Denied", "You do not have admin privileges.", parent=self)
            self.destroy()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')

# Example usage:
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    # Replace "admin" with the actual role from your login logic
    AdminAuthPage(root, user_role="admin")
    root.mainloop()