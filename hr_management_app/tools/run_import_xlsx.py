"""Headless importer: load an XLSX file and run the same pipeline used by the UI import.

Usage: adjust INPUT_PATH constant or pass via environment/PYTHONPATH and run.
"""

import sys
from pathlib import Path

# ensure project src is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    from hr_management_app.src.database.database import (
        create_employee,
        create_user,
        get_user_by_email,
    )
    from hr_management_app.src.parsers.file_parser import parse_excel
    from hr_management_app.src.parsers.normalizer import map_columns, validate_and_clean
except Exception:
    from hr_management_app.src.database.database import (  # type: ignore
        create_employee,
        create_user,
        get_user_by_email,
    )
    from parsers.file_parser import parse_excel  # type: ignore
    from parsers.normalizer import map_columns, validate_and_clean  # type: ignore

INPUT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "tests"
    / "fixtures"
    / "dummy_employees_2000.xlsx"
)

if not INPUT.exists():
    print(f"Input file not found: {INPUT}")
    raise SystemExit(2)

print(f"Loading {INPUT}")
rows = parse_excel(str(INPUT))
print(f"Read {len(rows)} rows from XLSX")

created_users = 0
created_employees = 0
skipped = 0
errors = []

for idx, r in enumerate(rows, start=1):
    try:
        mapped = map_columns(r)
        cleaned, problems = validate_and_clean(mapped)
        if problems:
            skipped += 1
            continue
        email = cleaned.get("email")
        if email:
            existing = get_user_by_email(email)
            if not existing:
                pwd = "tmp-pass"
                create_user(email, pwd)
                created_users += 1
            user = get_user_by_email(email)
            uid = user[0] if user else None
        else:
            uid = None
        ys = cleaned.get("year_start")
        ye = cleaned.get("year_end")
        create_employee(
            user_id=uid or 0,
            name=cleaned.get("name") or "",
            dob=cleaned.get("dob"),
            job_title=cleaned.get("job_title"),
            role=cleaned.get("role"),
            year_start=ys,
            profile_pic=None,
            contract_type=cleaned.get("contract_type"),
            year_end=ye,
        )
        created_employees += 1
    except Exception as e:
        errors.append(str(e))
        if idx % 100 == 0:
            print(
                f"Processed {idx} rows: created_users={created_users}, created_employees={created_employees}, skipped={skipped}, errors={len(errors)}"
            )

print("--- Import summary ---")
print(f"Total rows: {len(rows)}")
print(f"Created users: {created_users}")
print(f"Created employees: {created_employees}")
print(f"Skipped (validation errors): {skipped}")
print(f"Errors: {len(errors)}")
if errors:
    print("Sample errors:")
    for e in errors[:10]:
        print("-", e)
