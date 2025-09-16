import csv

from hr_management_app.src.database import database as db
from hr_management_app.src.parsers.file_parser import parse_csv
from hr_management_app.src.parsers.normalizer import map_columns, validate_and_clean


def test_import_flow_with_fuzzy_headers(tmp_path):
    # place DB in a temp file to avoid touching repo DB
    test_db = tmp_path / "test_hr.db"
    db.DB_NAME = str(test_db)
    db.init_db()

    csv_path = tmp_path / "employees.csv"
    # introduce typos to force fuzzy matching (e.g., 'emal')
    headers = [
        "Full Name",
        "emal",
        "birthdate",
        "Job Title",
        "Role",
        "joined",
        "left",
        "contract",
    ]
    row = [
        "Alice Example",
        "alice@example.com",
        "1990-05-12",
        "Engineer",
        "engineer",
        "2018",
        "",
        "permanent",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(row)

    raws = parse_csv(str(csv_path))
    assert len(raws) == 1
    mapped = map_columns(raws[0])
    cleaned, problems = validate_and_clean(mapped)
    assert not problems, f"Validation failed: {problems}"

    # create user and employee
    email = cleaned.get("email") or ""
    user_id = db.create_user(
        str(email), "password123", role=str(cleaned.get("role") or "engineer")
    )
    assert user_id > 0
    emp_id = db.create_employee(
        user_id=user_id,
        name=str(cleaned.get("name") or ""),
        dob=cleaned.get("dob"),
        job_title=str(cleaned.get("job_title") or ""),
        role=str(cleaned.get("role") or ""),
        year_start=cleaned.get("year_start"),
        profile_pic=None,
        contract_type=cleaned.get("contract_type"),
        year_end=cleaned.get("year_end"),
    )
    assert emp_id > 0

    # verify user and employee retrieval
    u = db.get_user_by_email(email)
    assert u is not None and u[1] == email
    e = db.get_employee_by_user(user_id)
    assert e is not None and e[3] == cleaned.get("name")
