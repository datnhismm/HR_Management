try:
    from hr_management_app.src.ml.imputer import infer_missing_fields
    from hr_management_app.src.parsers.file_parser import parse_excel
    from hr_management_app.src.parsers.normalizer import map_columns, validate_and_clean
    from hr_management_app.src.ui_import import _collect_db_stats
except Exception:
    # fallback for developer convenience when running as scripts from src/
    from ui_import import _collect_db_stats  # type: ignore

    from ml.imputer import infer_missing_fields  # type: ignore
    from parsers.file_parser import parse_excel  # type: ignore
    from parsers.normalizer import map_columns, validate_and_clean  # type: ignore

p = "c:/Users/DELL/Documents/GitHub/HR_Management/hr_management_app/src/tests/fixtures/dummy_employees_2000.xlsx"
raws = parse_excel(p)
print("Total rows parsed:", len(raws))
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
