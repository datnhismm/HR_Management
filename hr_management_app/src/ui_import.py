"""Minimal import UI for bulk employee import.

Provides a compact, syntactically-correct implementation of the import
dialogs used by the main GUI. This is intentionally small and easy to
unit-test.
"""

import logging
import os
import secrets
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

logger = logging.getLogger(__name__)

from parsers.file_parser import parse_csv, parse_excel, parse_docx
from parsers.normalizer import FUZZY_THRESHOLD, map_columns, validate_and_clean
from parsers.mapping_store import load_config, save_config
from ml.ner import extract_entities
from database.database import create_employee, create_user, get_user_by_email
from ml.imputer import infer_missing_fields
from database.database import get_all_users
# optional ML imputer (load if model artifact exists)
try:
    from ml.imputer_ml import load_model, predict_batch
except Exception:
    load_model = None
    predict_batch = None


def _collect_db_stats() -> dict:
    """Collect lightweight stats from users/employees to help imputation."""
    stats = {}
    try:
        users = get_all_users()
        emails = [u[1] for u in users if u and u[1]]
        stats["emails"] = emails
    except Exception:
        stats["emails"] = []
    return stats


def _safe_int(val):
    try:
        if val is None or val == "":
            return None
        return int(val)
    except Exception:
        return None


class ImportDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Import Employees")
        self.geometry("880x480")
        try:
            self.transient(parent)
        except Exception:
            pass
        self.grab_set()

        self.path_var = tk.StringVar()
        self.records = []
        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)

        top = ttk.Frame(frm)
        top.pack(fill="x", pady=(0, 8))
        ttk.Entry(top, textvariable=self.path_var).pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="Browse...", command=self._choose).pack(side="left", padx=6)
        ttk.Button(top, text="Load", command=self._load).pack(side="left")

        cols = ("#", "Name", "Email", "DOB", "Job Title", "Role", "Year Start", "Year End", "Contract", "Problems")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=14)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._on_edit_row)

        self.status = ttk.Label(frm, text="No file loaded.")
        self.status.pack(fill="x", pady=(6, 0))

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Import Selected", command=self.import_selected).pack(side="left", padx=6)
        ttk.Button(btns, text="Import All", command=self.import_all).pack(side="left", padx=6)
        ttk.Button(btns, text="Settings", command=self.open_settings).pack(side="right", padx=6)
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right", padx=6)

    def _choose(self):
        p = filedialog.askopenfilename(title="Select file", filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx;*.xls"), ("Word", "*.docx"), ("All", "*.*")], parent=self)
        if p:
            self.path_var.set(p)

    def _load(self):
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
                        import docx as _docx
                        doc = _docx.Document(path)
                        text = "\n".join(p.text for p in doc.paragraphs if p.text and p.text.strip())
                        if text:
                            ent = extract_entities(text)
                            if ent:
                                raws = [ent]
                    except Exception:
                        logger.debug("docx fallback failed", exc_info=True)
            else:
                raws = parse_csv(path)
        except Exception as e:
            logger.exception("Failed to parse file: %s", e)
            messagebox.showerror("Parse error", f"Failed to parse file: {e}", parent=self)
            return

        cfg = load_config() or {}

        # mapping preview (optional helper)
        try:
            from parsers.normalizer import map_columns_debug
        except Exception:
            map_columns_debug = None

        if raws and callable(map_columns_debug):
            try:
                _, mapping_debug = map_columns_debug(raws[0], fuzzy_threshold=cfg.get("threshold", FUZZY_THRESHOLD))
            except Exception:
                mapping_debug = None

            if mapping_debug:
                dlg = MappingPreviewDialog(self, mapping_debug, prefill=cfg.get("mappings", {}), prethreshold=cfg.get("threshold", FUZZY_THRESHOLD))
                self.wait_window(dlg)
                mapping = getattr(dlg, "mapping", None)
                if mapping:
                    cfg.setdefault("mappings", {})
                    for k, v in mapping.items():
                        if v and v[0]:
                            cfg["mappings"][k] = v[0]
                    cfg["threshold"] = dlg.threshold
                    save_config(cfg)
                    for rec in raws:
                        for orig, pair in mapping.items():
                            mapped_field = pair[0] if pair else None
                            if mapped_field and orig in rec:
                                rec[mapped_field] = rec.pop(orig)

        self.records = []
        cleaned_batch = []
        for r in raws:
            mapped = map_columns(r, fuzzy_threshold=cfg.get("threshold", FUZZY_THRESHOLD))
            cleaned, problems = validate_and_clean(mapped)
            cleaned_batch.append(cleaned)
            self.records.append({"raw": r, "mapped": mapped, "cleaned": cleaned, "problems": problems})

        # first try ML imputation if model present
        try:
            if callable(load_model) and callable(predict_batch):
                model = load_model()
                if model:
                    cleaned_batch = predict_batch(cleaned_batch, model)
                    # copy ML-predicted values back into records
                    for rec, imp in zip(self.records, cleaned_batch):
                        rec["cleaned"].update({k: v for k, v in imp.items() if v is not None})
        except Exception:
            logger.exception("ML imputation failed; falling back to heuristics")

        # perform lightweight heuristic imputation for any remaining missing fields
        try:
            db_stats = _collect_db_stats()
            imputed = infer_missing_fields([rec["cleaned"] for rec in self.records], db_stats=db_stats)
            # copy imputed values back into records (only override fields that were missing)
            for rec, imp in zip(self.records, imputed):
                for k, v in imp.items():
                    if rec["cleaned"].get(k) in (None, "") and v is not None:
                        rec["cleaned"][k] = v
        except Exception:
            logger.exception("Imputation failed; continuing without imputation")

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

    def _on_edit_row(self, event=None):
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

    def _do_import(self, indices):
        created = 0
        skipped = 0
        errors = []

        # create users where needed
        for i in indices:
            rec = self.records[i]
            cleaned = rec.get("cleaned") or {}
            problems = rec.get("problems") or []
            if problems:
                skipped += 1
                continue
            email = cleaned.get("email")
            try:
                if email:
                    existing = get_user_by_email(email)
                    if existing:
                        pass
                    else:
                        pwd = secrets.token_urlsafe(8)
                        create_user(email, pwd)
            except Exception as e:
                logger.exception("User create failed: %s", e)
                errors.append(str(e))

        # create employee rows
        for i in indices:
            rec = self.records[i]
            cleaned = rec.get("cleaned") or {}
            problems = rec.get("problems") or []
            if problems:
                continue
            try:
                email = cleaned.get("email")
                user = get_user_by_email(email) if email else None
                # use None for missing users so the employees.user_id column stores NULL
                # rather than 0 which would violate the UNIQUE constraint when repeated
                uid = user[0] if user else None
                ys = _safe_int(cleaned.get("year_start"))
                ye = _safe_int(cleaned.get("year_end"))
                # if a user exists and already has an employee, skip to avoid duplicate
                if uid is not None:
                    from database.database import get_employee_by_user
                    if get_employee_by_user(uid):
                        skipped += 1
                        continue
                create_employee(user_id=uid, name=str(cleaned.get("name") or ""), dob=str(cleaned.get("dob") or ""), job_title=str(cleaned.get("job_title") or ""), role=str(cleaned.get("role") or ""), year_start=ys, profile_pic=None, contract_type=str(cleaned.get("contract_type") or ""), year_end=ye)
                created += 1
            except Exception as e:
                logger.exception("Employee create failed: %s", e)
                errors.append(str(e))

        summary = f"Imported: {created}\nSkipped (validation): {skipped}\nErrors: {len(errors)}"
        if errors:
            summary += "\n\n" + "\n".join(errors[:10])
        messagebox.showinfo("Import Summary", summary, parent=self)
        try:
            if hasattr(self.parent, 'load_employees'):
                self.parent.load_employees()
        except Exception:
            pass

    def open_settings(self):
        cfg = load_config()
        dlg = None
        try:
            dlg = SettingsDialog(self, cfg)
        except Exception:
            messagebox.showerror("Settings", "Cannot open settings dialog.", parent=self)
            return
        self.wait_window(dlg)
        if getattr(dlg, "saved", False):
            save_config(dlg.config)
            messagebox.showinfo("Settings", "Settings saved.", parent=self)

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 880
        h = self.winfo_height() or 480
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


class MappingPreviewDialog(tk.Toplevel):
    def __init__(self, parent, mapping_debug, prefill=None, prethreshold=None):
        super().__init__(parent)
        self.parent = parent
        self.mapping_debug = mapping_debug or {}
        self.prefill = prefill or {}
        self.threshold = prethreshold if prethreshold is not None else FUZZY_THRESHOLD
        self.mapping = None
        self.title("Preview Header Mapping")
        try:
            self.transient(parent)
        except Exception:
            pass
        self.grab_set()
        self._build()
        self.center_window()

    def _build(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Adjust inferred header mappings (leave blank to ignore):").pack(anchor="w")
        self.entries = {}
        for orig, pair in self.mapping_debug.items():
            suggested, score = pair if isinstance(pair, (list, tuple)) else (pair, None)
            row = ttk.Frame(frm)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=str(orig), width=30).pack(side="left")
            pre = self.prefill.get(orig, suggested or "")
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
            score = None
            pair = self.mapping_debug.get(orig)
            if isinstance(pair, (list, tuple)) and len(pair) > 1:
                score = pair[1]
            out[orig] = (val if val else None, score)
        self.mapping = out
        try:
            self.threshold = int(self.thr_var.get())
        except Exception:
            self.threshold = FUZZY_THRESHOLD
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
    def __init__(self, parent, config=None):
        super().__init__(parent)
        self.parent = parent
        self.config = dict(config or {})
        self.saved = False
        try:
            self.transient(parent)
        except Exception:
            pass
        self.grab_set()
        self._build()
        self.center_window()

    def _build(self):
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
        try:
            self.config["threshold"] = int(self.thr_var.get())
        except Exception:
            self.config["threshold"] = FUZZY_THRESHOLD
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


class EditRowDialog(tk.Toplevel):
    def __init__(self, parent, index, record):
        super().__init__(parent)
        self.parent = parent
        self.index = index
        self.record = record
        self.title(f"Edit Row {index+1}")
        try:
            self.transient(parent)
        except Exception:
            pass
        self.grab_set()
        self._build()
        self.center_window()

    def _build(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        cleaned = self.record.get("cleaned", {})
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
        mapped = {}
        mapped["name"] = self.vars["name"].get().strip()
        mapped["email"] = self.vars["email"].get().strip()
        mapped["dob"] = self.vars["dob"].get().strip()
        mapped["job_title"] = self.vars["job_title"].get().strip()
        mapped["role"] = self.vars["role"].get().strip()
        mapped["year_start"] = self.vars["year_start"].get().strip()
        mapped["year_end"] = self.vars["year_end"].get().strip()
        mapped["contract_type"] = self.vars["contract_type"].get().strip()
        cleaned, problems = validate_and_clean(mapped)
        self.record["mapped"] = mapped
        self.record["cleaned"] = cleaned
        self.record["problems"] = problems
        self.destroy()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width() or 480
        h = self.winfo_height() or 320
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


