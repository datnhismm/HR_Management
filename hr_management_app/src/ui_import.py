import os
import secrets
import os
import secrets
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

from parsers.file_parser import parse_csv, parse_excel, parse_docx
from parsers.normalizer import map_columns, map_columns_debug, validate_and_clean, FUZZY_THRESHOLD
from parsers.mapping_store import load_config, save_config
from ml.ner import extract_entities
from database.database import create_user, create_employee, get_user_by_email


class ImportDialog(tk.Toplevel):
    """Dialog for importing employees from spreadsheet or docx files.

    Keeps a preview table and allows importing selected or all valid rows.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Import Employees")
        self.geometry("900x480")
        self.transient(parent)
        self.grab_set()
        self.records: List[Dict[str, Any]] = []
        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)

        top = ttk.Frame(frm)
        top.pack(fill="x", pady=(0, 8))
        self.path_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.path_var).pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="Browse...", command=self.choose_file).pack(side="left", padx=6)
        ttk.Button(top, text="Load", command=self.load_file).pack(side="left")

        cols = ("idx", "name", "email", "dob", "job_title", "role", "year_start", "year_end", "contract_type", "problems")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=14)
        headings = ["#", "Name", "Email", "DOB", "Job Title", "Role", "Year Start", "Year End", "Contract", "Problems"]
        for c, h in zip(cols, headings):
            self.tree.heading(c, text=h)
            self.tree.column(c, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_edit_row)

        self.status = ttk.Label(frm, text="No file loaded.")
        self.status.pack(fill="x", pady=(6, 0))

        import os
        import secrets
        import logging
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
        from typing import List, Dict, Any, Optional, Tuple

        logger = logging.getLogger(__name__)

        from parsers.file_parser import parse_csv, parse_excel, parse_docx
        from parsers.normalizer import map_columns, map_columns_debug, validate_and_clean, FUZZY_THRESHOLD
        from parsers.mapping_store import load_config, save_config
        from ml.ner import extract_entities
        from database.database import create_user, create_employee, get_user_by_email


        class ImportDialog(tk.Toplevel):
            """Import employees from CSV/XLSX/DOCX with preview, mapping, and settings."""

            def __init__(self, parent):
                super().__init__(parent)
                self.parent = parent
                self.title("Import Employees")
                self.geometry("900x480")
                self.transient(parent)
                self.grab_set()
                self.records: List[Dict[str, Any]] = []
                self.create_widgets()
                self.center_window()

            def create_widgets(self):
                frm = ttk.Frame(self, padding=8)
                frm.pack(fill="both", expand=True)

                top = ttk.Frame(frm)
                top.pack(fill="x", pady=(0, 8))
                self.path_var = tk.StringVar()
                ttk.Entry(top, textvariable=self.path_var).pack(side="left", fill="x", expand=True)
                ttk.Button(top, text="Browse...", command=self.choose_file).pack(side="left", padx=6)
                ttk.Button(top, text="Load", command=self.load_file).pack(side="left")

                cols = ("idx", "name", "email", "dob", "job_title", "role", "year_start", "year_end", "contract_type", "problems")
                self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=14)
                headings = ["#", "Name", "Email", "DOB", "Job Title", "Role", "Year Start", "Year End", "Contract", "Problems"]
                for c, h in zip(cols, headings):
                    self.tree.heading(c, text=h)
                    self.tree.column(c, anchor="w")
                self.tree.pack(fill="both", expand=True)
                self.tree.bind("<Double-1>", self.on_edit_row)

                self.status = ttk.Label(frm, text="No file loaded.")
                self.status.pack(fill="x", pady=(6, 0))

                btns = ttk.Frame(frm)
                btns.pack(fill="x", pady=6)
                ttk.Button(btns, text="Import Selected", command=self.import_selected).pack(side="left", padx=6)
                ttk.Button(btns, text="Import All", command=self.import_all).pack(side="left", padx=6)
                ttk.Button(btns, text="Settings", command=self.open_settings).pack(side="right", padx=6)
                ttk.Button(btns, text="Close", command=self.destroy).pack(side="right", padx=6)

            def choose_file(self):
                p = filedialog.askopenfilename(title="Select file", filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx;*.xls"), ("Word", "*.docx"), ("All", "*.*")], parent=self)
                if p:
                    self.path_var.set(p)

            def load_file(self):
                path = self.path_var.get().strip()
                if not path or not os.path.exists(path):
                    messagebox.showerror("File missing", "Please select a valid file.", parent=self)
                    return
                ext = os.path.splitext(path)[1].lower()
                try:
                    if ext == ".csv":
                        raws = parse_csv(path)
                    elif ext in (".xlsx", ".xls"):
                        raws = parse_excel(path)
                    elif ext == ".docx":
                        raws = parse_docx(path)
                        if not raws:
                            try:
                                import docx

                                doc = docx.Document(path)
                                text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                                if text.strip():
                                    ent = extract_entities(text)
                                    if ent:
                                        raws = [ent]
                            except Exception:
                                logger.debug("docx ML extraction failed", exc_info=True)
                    else:
                        raws = parse_csv(path)
                except Exception as e:
                    logger.exception("Failed to parse file: %s", e)
                    messagebox.showerror("Parse error", f"Failed to parse file: {e}", parent=self)
                    return

                cfg = load_config()
                mapping_debug = None
                if raws:
                    try:
                        _, mapping_debug = map_columns_debug(raws[0], fuzzy_threshold=cfg.get("threshold", FUZZY_THRESHOLD))
                    except Exception:
                        mapping_debug = None

                    if mapping_debug:
                        dlg = MappingPreviewDialog(self, mapping_debug, prefill=cfg.get("mappings", {}), prethreshold=cfg.get("threshold", FUZZY_THRESHOLD))
                        self.wait_window(dlg)
                        if getattr(dlg, "mapping", None) is not None:
                            cfg.setdefault("mappings", {})
                            cfg["mappings"].update({k: v[0] for k, v in dlg.mapping.items() if v[0]})
                            cfg["threshold"] = dlg.threshold
                            save_config(cfg)
                            for rec in raws:
                                for orig, (mapped_field, _) in dlg.mapping.items():
                                    if mapped_field and orig in rec:
                                        rec[mapped_field] = rec.pop(orig)

                self.records = []
                for r in raws:
                    mapped = map_columns(r, fuzzy_threshold=cfg.get("threshold", FUZZY_THRESHOLD))
                    cleaned, problems = validate_and_clean(mapped)
                    self.records.append({"raw": r, "mapped": mapped, "cleaned": cleaned, "problems": problems})

                for i in self.tree.get_children():
                    self.tree.delete(i)
                for idx, rec in enumerate(self.records, start=1):
                    c = rec["cleaned"]
                    problems = ", ".join(rec["problems"]) if rec["problems"] else ""
                    self.tree.insert("", "end", values=(idx, c.get("name"), c.get("email"), c.get("dob"), c.get("job_title"), c.get("role"), c.get("year_start"), c.get("year_end"), c.get("contract_type"), problems))
                self.status.config(text=f"Loaded {len(self.records)} records. Review and click Import Selected or Import All.")

            def import_selected(self):
                sel = self.tree.selection()
                if not sel:
                    messagebox.showinfo("Select", "Select rows to import or use Import All.", parent=self)
                    return
                indices = [int(self.tree.item(s)["values"][0]) - 1 for s in sel]
                self._do_import(indices)

            def on_edit_row(self, event=None):
                sel = self.tree.selection()
                if not sel:
                    return
                try:
                    idx = int(self.tree.item(sel[0])["values"][0]) - 1
                except Exception:
                    return
                if idx < 0 or idx >= len(self.records):
                    return
                EditRowDialog(self, idx, self.records[idx])
                rec = self.records[idx]
                c = rec["cleaned"]
                problems = ", ".join(rec["problems"]) if rec["problems"] else ""
                for item in self.tree.get_children():
                    vals = self.tree.item(item)["values"]
                    try:
                        if int(vals[0]) - 1 == idx:
                            self.tree.item(item, values=(idx + 1, c.get("name"), c.get("email"), c.get("dob"), c.get("job_title"), c.get("role"), c.get("year_start"), c.get("year_end"), c.get("contract_type"), problems))
                            break
                    except Exception:
                        continue

            def import_all(self):
                if not self.records:
                    messagebox.showinfo("No data", "Load a file first.", parent=self)
                    return
                self._do_import(list(range(len(self.records))))

            def _do_import(self, indices: List[int]):
                created = 0
                skipped = 0
                errors: List[str] = []
                for i in indices:
                    rec = self.records[i]
                    cleaned = rec["cleaned"]
                    if rec["problems"]:
                        skipped += 1
                        continue
                    email = cleaned.get("email")
                    user_id: Optional[int] = None
                    try:
                        if email:
                            existing = get_user_by_email(email)
                            if existing:
                                user_id = existing[0]
                            else:
                                pwd = secrets.token_urlsafe(8)
                                user_id = create_user(email, pwd)
                        emp_id = create_employee(
                            user_id=user_id,
                            name=cleaned.get("name"),
                            dob=cleaned.get("dob"),
                            job_title=cleaned.get("job_title"),
                            role=cleaned.get("role"),
                            year_start=cleaned.get("year_start"),
                            profile_pic=None,
                            contract_type=cleaned.get("contract_type"),
                            year_end=cleaned.get("year_end"),
                        )
                        created += 1
                    except Exception as e:
                        logger.exception("Import row failed: %s", e)
                        errors.append(str(e))

                summary = f"Imported: {created}\nSkipped (validation): {skipped}\nErrors: {len(errors)}"
                if errors:
                    summary += "\n\n" + "\n".join(errors[:10])
                messagebox.showinfo("Import Summary", summary, parent=self)
                try:
                    if hasattr(self.parent, "load_employees"):
                        self.parent.load_employees()
                except Exception:
                    pass

            def open_settings(self):
                cfg = load_config()
                dlg = SettingsDialog(self, cfg)
                self.wait_window(dlg)
                if getattr(dlg, "saved", False):
                    save_config(dlg.config)
                    messagebox.showinfo("Settings", "Settings saved.", parent=self)

            def center_window(self):
                self.update_idletasks()
                w = self.winfo_width() or 900
                h = self.winfo_height() or 480
                ws = self.winfo_screenwidth()
                hs = self.winfo_screenheight()
                x = (ws // 2) - (w // 2)
                y = (hs // 2) - (h // 2)
                self.geometry(f"{w}x{h}+{x}+{y}")


        class EditRowDialog(tk.Toplevel):
            def __init__(self, parent: ImportDialog, index: int, record: dict):
                super().__init__(parent)
                self.parent = parent
                self.index = index
                self.record = record
                self.title(f"Edit Row {index+1}")
                self.transient(parent)
                self.grab_set()
                self.create_widgets()
                self.center_window()

            def create_widgets(self):
                frm = ttk.Frame(self, padding=8)
                frm.pack(fill="both", expand=True)
                cleaned = self.record.get("cleaned", {})
                self.vars: Dict[str, tk.StringVar] = {}
                fields = ["name", "email", "dob", "job_title", "role", "year_start", "year_end", "contract_type"]
                for i, f in enumerate(fields):
                    ttk.Label(frm, text=f.replace("_", " ").title() + ":").grid(row=i, column=0, sticky="e")
                    v = tk.StringVar(value=str(cleaned.get(f) or ""))
                    self.vars[f] = v
                    ttk.Entry(frm, textvariable=v, width=40).grid(row=i, column=1, sticky="w")

                btns = ttk.Frame(frm)
                btns.grid(row=len(fields), column=0, columnspan=2, pady=(8, 0))
                ttk.Button(btns, text="Save", command=self.on_save).pack(side="left", padx=6)
                ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

            def on_save(self):
                mapped: Dict[str, Any] = {}
                for k, v in self.vars.items():
                    mapped[k] = v.get().strip()
                cleaned, problems = validate_and_clean(mapped)
                self.record["mapped"] = mapped
                self.record["cleaned"] = cleaned
                self.record["problems"] = problems
                self.destroy()

            def center_window(self):
                self.update_idletasks()
                w = self.winfo_width() or 500
                h = self.winfo_height() or 320
                ws = self.winfo_screenwidth()
                hs = self.winfo_screenheight()
                x = (ws // 2) - (w // 2)
                y = (hs // 2) - (h // 2)
                self.geometry(f"{w}x{h}+{x}+{y}")


        class MappingPreviewDialog(tk.Toplevel):
            def __init__(self, parent, mapping_debug: Dict[str, Tuple[str, int]], prefill: Optional[Dict[str, str]] = None, prethreshold: Optional[int] = None):
                super().__init__(parent)
                self.parent = parent
                self.mapping_debug = mapping_debug or {}
                self.mapping: Optional[Dict[str, Tuple[Optional[str], Optional[int]]]] = None
                self.threshold = prethreshold if prethreshold is not None else FUZZY_THRESHOLD
                self.prefill = prefill or {}
                self.title("Preview Header Mapping")
                self.transient(parent)
                self.grab_set()
                self.create_widgets()
                self.center_window()

            def create_widgets(self):
                frm = ttk.Frame(self, padding=8)
                frm.pack(fill="both", expand=True)
                ttk.Label(frm, text="Adjust inferred header mappings (leave blank to ignore):").pack(anchor="w")
                self.entries: Dict[str, tk.StringVar] = {}
                for orig, (mapped, score) in self.mapping_debug.items():
                    row = ttk.Frame(frm)
                    row.pack(fill="x", pady=2)
                    ttk.Label(row, text=orig, width=30).pack(side="left")
                    pre = self.prefill.get(orig, mapped or "")
                    v = tk.StringVar(value=str(pre))
                    self.entries[orig] = v
                    ttk.Entry(row, textvariable=v, width=30).pack(side="left", padx=6)
                    score_text = "exact" if score is None else f"{score}%"
                    ttk.Label(row, text=score_text, width=8).pack(side="left")

                thr_row = ttk.Frame(frm)
                thr_row.pack(fill="x", pady=(8, 0))
                ttk.Label(thr_row, text="Fuzzy threshold (0-100):").pack(side="left")
                self.thr_var = tk.IntVar(value=self.threshold)
                ttk.Spinbox(thr_row, from_=0, to=100, textvariable=self.thr_var, width=5).pack(side="left", padx=6)

                btns = ttk.Frame(frm)
                btns.pack(fill="x", pady=(8, 0))
                ttk.Button(btns, text="Apply", command=self.on_apply).pack(side="left", padx=6)
                ttk.Button(btns, text="Cancel", command=self.on_cancel).pack(side="left")

            def on_apply(self):
                out: Dict[str, Tuple[Optional[str], Optional[int]]] = {}
                for orig, v in self.entries.items():
                    val = v.get().strip()
                    if val:
                        out[orig] = (val, self.mapping_debug.get(orig, (None, None))[1])
                    else:
                        out[orig] = (None, self.mapping_debug.get(orig, (None, None))[1])
                self.mapping = out
                self.threshold = int(self.thr_var.get())
                self.destroy()

            def on_cancel(self):
                self.mapping = None
                self.destroy()

            def center_window(self):
                self.update_idletasks()
                w = self.winfo_width() or 600
                h = self.winfo_height() or 360
                ws = self.winfo_screenwidth()
                hs = self.winfo_screenheight()
                x = (ws // 2) - (w // 2)
                y = (hs // 2) - (h // 2)
                self.geometry(f"{w}x{h}+{x}+{y}")


        class SettingsDialog(tk.Toplevel):
            def __init__(self, parent, config: Dict[str, Any]):
                super().__init__(parent)
                self.parent = parent
                self.config = dict(config or {})
                self.saved = False
                self.title("Import Settings")
                self.transient(parent)
                self.grab_set()
                self.create_widgets()
                self.center_window()

            def create_widgets(self):
                frm = ttk.Frame(self, padding=8)
                frm.pack(fill="both", expand=True)
                thr = int(self.config.get("threshold", FUZZY_THRESHOLD))
                ttk.Label(frm, text="Fuzzy threshold (0-100):").grid(row=0, column=0, sticky="w")
                self.thr_var = tk.IntVar(value=thr)
                ttk.Spinbox(frm, from_=0, to=100, textvariable=self.thr_var, width=6).grid(row=0, column=1, sticky="w", padx=6)
                btns = ttk.Frame(frm)
                btns.grid(row=1, column=0, columnspan=2, pady=(8, 0))
                ttk.Button(btns, text="Save", command=self.on_save).pack(side="left", padx=6)
                ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

            def on_save(self):
                self.config["threshold"] = int(self.thr_var.get())
                self.saved = True
                self.destroy()

            def center_window(self):
                self.update_idletasks()
                w = self.winfo_width() or 320
                h = self.winfo_height() or 120
                ws = self.winfo_screenwidth()
                hs = self.winfo_screenheight()
                x = (ws // 2) - (w // 2)
                y = (hs // 2) - (h // 2)
                self.geometry(f"{w}x{h}+{x}+{y}")
                        mapped[k] = v.get().strip()
                    cleaned, problems = validate_and_clean(mapped)
                    self.record["mapped"] = mapped
                    self.record["cleaned"] = cleaned
                    self.record["problems"] = problems
                    self.destroy()

                def center_window(self):
                    self.update_idletasks()
                    w = self.winfo_width() or 500
                    h = self.winfo_height() or 320
                    ws = self.winfo_screenwidth()
                    hs = self.winfo_screenheight()
                    x = (ws // 2) - (w // 2)
                    y = (hs // 2) - (h // 2)
                    self.geometry(f"{w}x{h}+{x}+{y}")


            class MappingPreviewDialog(tk.Toplevel):
                def __init__(self, parent, mapping_debug: Dict[str, Tuple[str, int]], prefill: Optional[Dict[str, str]] = None, prethreshold: Optional[int] = None):
                    super().__init__(parent)
                    self.parent = parent
                    self.mapping_debug = mapping_debug or {}
                    self.mapping: Optional[Dict[str, Tuple[Optional[str], Optional[int]]]] = None
                    self.threshold = prethreshold if prethreshold is not None else FUZZY_THRESHOLD
                    self.prefill = prefill or {}
                    self.title("Preview Header Mapping")
                    self.transient(parent)
                    self.grab_set()
                    self.create_widgets()
                    self.center_window()

                def create_widgets(self):
                    frm = ttk.Frame(self, padding=8)
                    frm.pack(fill="both", expand=True)
                    ttk.Label(frm, text="Adjust inferred header mappings (leave blank to ignore):").pack(anchor="w")
                    self.entries: Dict[str, tk.StringVar] = {}
                    for orig, (mapped, score) in self.mapping_debug.items():
                        row = ttk.Frame(frm)
                        row.pack(fill="x", pady=2)
                        ttk.Label(row, text=orig, width=30).pack(side="left")
                        pre = self.prefill.get(orig, mapped or "")
                        v = tk.StringVar(value=str(pre))
                        self.entries[orig] = v
                        ttk.Entry(row, textvariable=v, width=30).pack(side="left", padx=6)
                        score_text = "exact" if score is None else f"{score}%"
                        ttk.Label(row, text=score_text, width=8).pack(side="left")

                    thr_row = ttk.Frame(frm)
                    thr_row.pack(fill="x", pady=(8, 0))
                    ttk.Label(thr_row, text="Fuzzy threshold (0-100):").pack(side="left")
                    self.thr_var = tk.IntVar(value=self.threshold)
                    ttk.Spinbox(thr_row, from_=0, to=100, textvariable=self.thr_var, width=5).pack(side="left", padx=6)

                    btns = ttk.Frame(frm)
                    btns.pack(fill="x", pady=(8, 0))
                    ttk.Button(btns, text="Apply", command=self.on_apply).pack(side="left", padx=6)
                    ttk.Button(btns, text="Cancel", command=self.on_cancel).pack(side="left")

                def on_apply(self):
                    out: Dict[str, Tuple[Optional[str], Optional[int]]] = {}
                    for orig, v in self.entries.items():
                        val = v.get().strip()
                        if val:
                            out[orig] = (val, self.mapping_debug.get(orig, (None, None))[1])
                        else:
                            out[orig] = (None, self.mapping_debug.get(orig, (None, None))[1])
                    self.mapping = out
                    self.threshold = int(self.thr_var.get())
                    self.destroy()

                def on_cancel(self):
                    self.mapping = None
                    self.destroy()

                def center_window(self):
                    self.update_idletasks()
                    w = self.winfo_width() or 600
                    h = self.winfo_height() or 360
                    ws = self.winfo_screenwidth()
                    hs = self.winfo_screenheight()
                    x = (ws // 2) - (w // 2)
                    y = (hs // 2) - (h // 2)
                    self.geometry(f"{w}x{h}+{x}+{y}")


            class SettingsDialog(tk.Toplevel):
                def __init__(self, parent, config: Dict[str, Any]):
                    super().__init__(parent)
                    self.parent = parent
                    self.config = dict(config or {})
                    self.saved = False
                    self.title("Import Settings")
                    self.transient(parent)
                    self.grab_set()
                    self.create_widgets()
                    self.center_window()

                def create_widgets(self):
                    frm = ttk.Frame(self, padding=8)
                    frm.pack(fill="both", expand=True)
                    thr = int(self.config.get("threshold", FUZZY_THRESHOLD))
                    ttk.Label(frm, text="Fuzzy threshold (0-100):").grid(row=0, column=0, sticky="w")
                    self.thr_var = tk.IntVar(value=thr)
                    ttk.Spinbox(frm, from_=0, to=100, textvariable=self.thr_var, width=6).grid(row=0, column=1, sticky="w", padx=6)
                    btns = ttk.Frame(frm)
                    btns.grid(row=1, column=0, columnspan=2, pady=(8, 0))
                    ttk.Button(btns, text="Save", command=self.on_save).pack(side="left", padx=6)
                    ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

                def on_save(self):
                    self.config["threshold"] = int(self.thr_var.get())
                    self.saved = True
                    self.destroy()

                def center_window(self):
                    self.update_idletasks()
                    w = self.winfo_width() or 320
                    h = self.winfo_height() or 120
                    ws = self.winfo_screenwidth()
                    hs = self.winfo_screenheight()
                    x = (ws // 2) - (w // 2)
                    y = (hs // 2) - (h // 2)
                    self.geometry(f"{w}x{h}+{x}+{y}")
        self.prefill = prefill or {}
        self.title("Preview Header Mapping")
        self.transient(parent)
        self.grab_set()
        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Adjust inferred header mappings (leave blank to ignore):").pack(anchor="w")
        self.entries: Dict[str, tk.StringVar] = {}
        for orig, (mapped, score) in self.mapping_debug.items():
            row = ttk.Frame(frm)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=orig, width=30).pack(side="left")
            pre = self.prefill.get(orig, mapped or "")
            v = tk.StringVar(value=str(pre))
            self.entries[orig] = v
            ttk.Entry(row, textvariable=v, width=30).pack(side="left", padx=6)
            score_text = "exact" if score is None else f"{score}%"
            ttk.Label(row, text=score_text, width=8).pack(side="left")

        thr_row = ttk.Frame(frm)
        thr_row.pack(fill="x", pady=(8, 0))
        ttk.Label(thr_row, text="Fuzzy threshold (0-100):").pack(side="left")
        self.thr_var = tk.IntVar(value=self.threshold)
        ttk.Spinbox(thr_row, from_=0, to=100, textvariable=self.thr_var, width=5).pack(side="left", padx=6)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Apply", command=self.on_apply).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancel", command=self.on_cancel).pack(side="left")

    def on_apply(self):
        out: Dict[str, Tuple[Optional[str], Optional[int]]] = {}
        for orig, v in self.entries.items():
            val = v.get().strip()
            if val:
                out[orig] = (val, self.mapping_debug.get(orig, (None, None))[1])
            else:
                out[orig] = (None, self.mapping_debug.get(orig, (None, None))[1])
        self.mapping = out
        self.threshold = int(self.thr_var.get())
        self.destroy()

    def on_cancel(self):
        self.mapping = None
        self.destroy()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 600
        h = self.winfo_height() or 360
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.config = dict(config or {})
        self.saved = False
        self.title("Import Settings")
        self.transient(parent)
        self.grab_set()
        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        thr = int(self.config.get("threshold", FUZZY_THRESHOLD))
        ttk.Label(frm, text="Fuzzy threshold (0-100):").grid(row=0, column=0, sticky="w")
        self.thr_var = tk.IntVar(value=thr)
        ttk.Spinbox(frm, from_=0, to=100, textvariable=self.thr_var, width=6).grid(row=0, column=1, sticky="w", padx=6)
        btns = ttk.Frame(frm)
        btns.grid(row=1, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btns, text="Save", command=self.on_save).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

    def on_save(self):
        self.config["threshold"] = int(self.thr_var.get())
        self.saved = True
        self.destroy()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 320
        h = self.winfo_height() or 120
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


class ImportDialog(tk.Toplevel):
    """Dialog to import employees from CSV/XLSX/DOCX files.

    Workflow:
    - User selects a file
    - Parser returns list of raw rows
    - Columns are mapped, cleaned and validated
    - Preview shown in a table with problems
    - User can import selected rows; creates user (if email present) and employee rows
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Import Employees from File")
        self.geometry("900x480")
        self.transient(parent)
        self.grab_set()
        self.records: List[Dict[str, Any]] = []
        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)

        top = ttk.Frame(frm)
        top.pack(fill="x", pady=(0, 8))
        self.path_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.path_var).pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="Browse...", command=self.choose_file).pack(side="left", padx=6)
        ttk.Button(top, text="Load", command=self.load_file).pack(side="left")

        cols = ("idx", "name", "email", "dob", "job_title", "role", "year_start", "year_end", "contract_type", "problems")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=14)
        headings = ["#", "Name", "Email", "DOB", "Job Title", "Role", "Year Start", "Year End", "Contract", "Problems"]
        for c, h in zip(cols, headings):
            self.tree.heading(c, text=h)
            self.tree.column(c, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_edit_row)

        # status and buttons
        self.status = ttk.Label(frm, text="No file loaded.")
        self.status.pack(fill="x", pady=(6, 0))

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Import Selected", command=self.import_selected).pack(side="left", padx=6)
        ttk.Button(btns, text="Import All", command=self.import_all).pack(side="left", padx=6)
        ttk.Button(btns, text="Settings", command=self.open_settings).pack(side="right", padx=6)
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right", padx=6)

    def choose_file(self):
        p = filedialog.askopenfilename(title="Select file", filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx;*.xls"), ("Word", "*.docx"), ("All", "*.*")], parent=self)
        if p:
            self.path_var.set(p)

    def load_file(self):
        path = self.path_var.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("File missing", "Please select a valid file.", parent=self)
            return
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in (".csv",):
                raws = parse_csv(path)
            elif ext in (".xlsx", ".xls"):
                raws = parse_excel(path)
            elif ext in (".docx",):
                raws = parse_docx(path)
                # if docx parser returned no table rows, try ML extraction on full text
                if not raws:
                    try:
                        import docx

                        doc = docx.Document(path)
                        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                        if text.strip():
                            ent = extract_entities(text)
                            if ent:
                                raws = [ent]
                    except Exception:
                        pass
            else:
                # try CSV as fallback
                raws = parse_csv(path)
        except Exception as e:
            logger.exception("Failed to parse file: %s", e)
            messagebox.showerror("Parse error", f"Failed to parse file: {e}", parent=self)
            return

        # load stored config and offer header mapping preview for first row
        cfg = load_config()
        mapping_debug = None
        if raws:
            try:
                _, mapping_debug = map_columns_debug(raws[0], fuzzy_threshold=cfg.get("threshold", FUZZY_THRESHOLD))
            except Exception:
                mapping_debug = None

            if mapping_debug:
                dlg = MappingPreviewDialog(self, mapping_debug, prefill=cfg.get("mappings", {}), prethreshold=cfg.get("threshold", FUZZY_THRESHOLD))
                self.wait_window(dlg)
                if getattr(dlg, "mapping", None) is not None:
                    # persist mapping and threshold
                    cfg.setdefault("mappings", {})
                    cfg["mappings"].update({k: v[0] for k, v in dlg.mapping.items() if v[0]})
                    cfg["threshold"] = dlg.threshold
                    save_config(cfg)
                    # apply mapping to all raw rows
                    for rec in raws:
                        for orig, (mapped_field, _) in dlg.mapping.items():
                            if mapped_field and orig in rec:
                                rec[mapped_field] = rec.pop(orig)

        # now normalize and validate
        self.records = []
        for r in raws:
            mapped = map_columns(r, fuzzy_threshold=cfg.get("threshold", FUZZY_THRESHOLD))
            cleaned, problems = validate_and_clean(mapped)
            self.records.append({"raw": r, "mapped": mapped, "cleaned": cleaned, "problems": problems})

        # populate tree
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, rec in enumerate(self.records, start=1):
            c = rec["cleaned"]
            problems = ", ".join(rec["problems"]) if rec["problems"] else ""
            self.tree.insert("", "end", values=(idx, c.get("name"), c.get("email"), c.get("dob"), c.get("job_title"), c.get("role"), c.get("year_start"), c.get("year_end"), c.get("contract_type"), problems))
        self.status.config(text=f"Loaded {len(self.records)} records. Review and click Import Selected or Import All.")

    def import_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select rows to import or use Import All.", parent=self)
            return
        indices = [int(self.tree.item(s)["values"][0]) - 1 for s in sel]
        self._do_import(indices)

    def on_edit_row(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        try:
            idx = int(self.tree.item(sel[0])["values"][0]) - 1
        except Exception:
            return
        if idx < 0 or idx >= len(self.records):
            return
        EditRowDialog(self, idx, self.records[idx])
        # refresh the tree row after editing
        rec = self.records[idx]
        c = rec["cleaned"]
        problems = ", ".join(rec["problems"]) if rec["problems"] else ""
        # find the tree item and update values
        for item in self.tree.get_children():
            vals = self.tree.item(item)["values"]
            try:
                if int(vals[0]) - 1 == idx:
                    self.tree.item(item, values=(idx + 1, c.get("name"), c.get("email"), c.get("dob"), c.get("job_title"), c.get("role"), c.get("year_start"), c.get("year_end"), c.get("contract_type"), problems))
                    break
            except Exception:
                continue

    def import_all(self):
        if not self.records:
            messagebox.showinfo("No data", "Load a file first.", parent=self)
            return
        self._do_import(list(range(len(self.records))))

    def _do_import(self, indices: List[int]):
        created = 0
        skipped = 0
        errors = []
        for i in indices:
            rec = self.records[i]
            cleaned = rec["cleaned"]
            # skip rows with problems
            if rec["problems"]:
                skipped += 1
                continue
            email = cleaned.get("email")
            user_id = None
            try:
                if email:
                    existing = get_user_by_email(email)
                    if existing:
                        user_id = existing[0]
                    else:
                        pwd = secrets.token_urlsafe(8)
                        user_id = create_user(email, pwd)
                # create employee
                emp_id = create_employee(
                    user_id=user_id,
                    name=cleaned.get("name"),
                    dob=cleaned.get("dob"),
                    job_title=cleaned.get("job_title"),
                    role=cleaned.get("role"),
                    year_start=cleaned.get("year_start"),
                    profile_pic=None,
                    contract_type=cleaned.get("contract_type"),
                    year_end=cleaned.get("year_end"),
                )
                created += 1
            except Exception as e:
                logger.exception("Import row failed: %s", e)
                errors.append(str(e))

        summary = f"Imported: {created}\nSkipped (validation): {skipped}\nErrors: {len(errors)}"
        if errors:
            summary += "\n\n" + "\n".join(errors[:10])
        messagebox.showinfo("Import Summary", summary, parent=self)
        # refresh parent list if it exists
        try:
            if hasattr(self.parent, 'load_employees'):
                self.parent.load_employees()
        except Exception:
            pass

    def open_settings(self):
        cfg = load_config()
        dlg = SettingsDialog(self, cfg)
        self.wait_window(dlg)
        if getattr(dlg, "saved", False):
            save_config(dlg.config)
            messagebox.showinfo("Settings", "Settings saved.", parent=self)

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 900
        h = self.winfo_height() or 480
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
class EditRowDialog(tk.Toplevel):
    def __init__(self, parent: ImportDialog, index: int, record: dict):
        super().__init__(parent)
        self.parent = parent
        self.index = index
        self.record = record
        self.title(f"Edit Row {index+1}")
        self.transient(parent)
        self.grab_set()
        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        cleaned = self.record.get("cleaned", {})
        # create entry for each field
        self.vars = {}
        fields = ["name", "email", "dob", "job_title", "role", "year_start", "year_end", "contract_type"]
        for i, f in enumerate(fields):
            ttk.Label(frm, text=f.replace("_", " ").title() + ":").grid(row=i, column=0, sticky="e")
            v = tk.StringVar(value=str(cleaned.get(f) or ""))
            self.vars[f] = v
            ttk.Entry(frm, textvariable=v, width=40).grid(row=i, column=1, sticky="w")

        btns = ttk.Frame(frm)
        btns.grid(row=len(fields), column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btns, text="Save", command=self.on_save).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

    def on_save(self):
        # build a mapped record from the entries and re-validate
        mapped = {}
        # map entries back to possible keys expected by normalize
        mapped["name"] = self.vars["name"].get().strip()
        mapped["email"] = self.vars["email"].get().strip()
        mapped["dob"] = self.vars["dob"].get().strip()
        mapped["job_title"] = self.vars["job_title"].get().strip()
        mapped["role"] = self.vars["role"].get().strip()
        mapped["year_start"] = self.vars["year_start"].get().strip()
        mapped["year_end"] = self.vars["year_end"].get().strip()
        mapped["contract_type"] = self.vars["contract_type"].get().strip()
        cleaned, problems = validate_and_clean(mapped)
        # update the record
        self.record["mapped"] = mapped
        self.record["cleaned"] = cleaned
        self.record["problems"] = problems
        self.destroy()


class MappingPreviewDialog(tk.Toplevel):
    """Simple dialog that lists inferred mappings for the first row and lets the user override or clear them.

    dlg.mapping will be a dict original_key -> (chosen_canonical_or_empty, score) or None if cancelled.
    """

    def __init__(self, parent, mapping_debug: Dict[str, Tuple[str, int]], prefill: Dict[str, str] = None, prethreshold: int = None):
        super().__init__(parent)
        self.parent = parent
        self.mapping_debug = mapping_debug
        self.mapping = None
        self.threshold = prethreshold if prethreshold is not None else FUZZY_THRESHOLD
        self.prefill = prefill or {}
        self.title("Preview Header Mapping")
        self.transient(parent)
        self.grab_set()
        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Adjust inferred header mappings (leave blank to ignore):").pack(anchor="w")
        self.entries = {}
        for orig, (mapped, score) in self.mapping_debug.items():
            row = ttk.Frame(frm)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=orig, width=30).pack(side="left")
            pre = self.prefill.get(orig, mapped or "")
            v = tk.StringVar(value=str(pre))
            self.entries[orig] = v
            ttk.Entry(row, textvariable=v, width=30).pack(side="left", padx=6)
            score_text = "exact" if score is None else f"{score}%"
            ttk.Label(row, text=score_text, width=8).pack(side="left")

        thr_row = ttk.Frame(frm)
        thr_row.pack(fill="x", pady=(8, 0))
        ttk.Label(thr_row, text="Fuzzy threshold (0-100):").pack(side="left")
        self.thr_var = tk.IntVar(value=self.threshold)
        ttk.Spinbox(thr_row, from_=0, to=100, textvariable=self.thr_var, width=5).pack(side="left", padx=6)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Apply", command=self.on_apply).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancel", command=self.on_cancel).pack(side="left")

    def on_apply(self):
        out = {}
        for orig, v in self.entries.items():
            val = v.get().strip()
            if val:
                out[orig] = (val, self.mapping_debug[orig][1])
            else:
                out[orig] = (None, self.mapping_debug[orig][1])
        self.mapping = out
        self.threshold = int(self.thr_var.get())
        self.destroy()

    def on_cancel(self):
        self.mapping = None
        self.destroy()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 600
        h = self.winfo_height() or 360
        ws = self.winfo_screenwidth()
        except Exception:
        

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.config = dict(config or {})
        self.saved = False
        self.title("Import Settings")
        self.transient(parent)
        self.grab_set()
        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        thr = int(self.config.get("threshold", FUZZY_THRESHOLD))
        ttk.Label(frm, text="Fuzzy threshold (0-100):").grid(row=0, column=0, sticky="w")
        self.thr_var = tk.IntVar(value=thr)
        ttk.Spinbox(frm, from_=0, to=100, textvariable=self.thr_var, width=6).grid(row=0, column=1, sticky="w", padx=6)
        btns = ttk.Frame(frm)
        btns.grid(row=1, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btns, text="Save", command=self.on_save).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

    def on_save(self):
        self.config["threshold"] = int(self.thr_var.get())
        self.saved = True
        self.destroy()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 320
        h = self.winfo_height() or 120
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
