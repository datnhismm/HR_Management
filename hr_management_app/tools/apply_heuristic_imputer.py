"""Apply heuristic imputer to an XLSX file and produce an imputed file + report.
Usage: use the project venv python to run this script.
"""
import os
import sys
from pprint import pprint
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from ml.imputer_heuristic import fit_from_records, predict_batch
from openpyxl import load_workbook, Workbook

IN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'dummy_import_20k.xlsx')
OUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'dummy_import_20k_imputed.xlsx')


def read_xlsx(path):
    wb = load_workbook(path, read_only=True)
    ws = wb.active
    # values_only=True returns tuples of values; the first tuple is the header row
    it = ws.iter_rows(values_only=True)
    headers = list(next(it))
    records = []
    for row in it:
        r = dict(zip(headers, row))
        records.append(r)
    return records


def write_xlsx(records, path):
    wb = Workbook()
    ws = wb.active
    if not records:
        wb.save(path)
        return
    headers = list(records[0].keys())
    ws.append(headers)
    for r in records:
        ws.append([r.get(h) for h in headers])
    wb.save(path)


if __name__ == '__main__':
    print('Reading input...')
    recs = read_xlsx(IN_FILE)
    print(f'Read {len(recs)} rows')
    model = fit_from_records(recs)
    imputed = predict_batch(recs, model)

    # compute stats
    counts = {"imputed_email": 0, "imputed_name": 0, "imputed_job": 0, "imputed_year": 0}
    for r in imputed:
        if r.get("_imputed_email"):
            counts["imputed_email"] += 1
        if r.get("_imputed_name"):
            counts["imputed_name"] += 1
        if r.get("_imputed_job"):
            counts["imputed_job"] += 1
        if r.get("_imputed_year"):
            counts["imputed_year"] += 1

    print('Imputation counts:')
    pprint(counts)
    print('Writing imputed workbook...')
    write_xlsx(imputed, OUT_FILE)
    print('Wrote', OUT_FILE)
