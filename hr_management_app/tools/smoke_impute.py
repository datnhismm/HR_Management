"""Smoke test: parse the existing dummy XLSX and show imputation results for first N rows."""
from parsers.file_parser import parse_excel
from parsers.normalizer import map_columns, validate_and_clean
from ml.imputer import infer_missing_fields
from ui_import import _collect_db_stats

path = r"src/tests/fixtures/dummy_employees_2000.xlsx"
raws = parse_excel(path)
print(f"Total rows parsed: {len(raws)}")
cleaned_batch = []
for r in raws[:20]:
    mapped = map_columns(r)
    cleaned, problems = validate_and_clean(mapped)
    cleaned_batch.append(cleaned)

stats = _collect_db_stats()
imputed = infer_missing_fields(cleaned_batch, db_stats=stats)
for i, (orig, imp) in enumerate(zip(cleaned_batch, imputed), start=1):
    print(f"Row {i}")
    for k in sorted(set(list(orig.keys()) + list(imp.keys()))):
        print(f"  {k}: original={orig.get(k)!r} imputed={imp.get(k)!r}")
    print()
