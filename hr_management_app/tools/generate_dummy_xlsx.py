"""Generate a dummy XLSX with 2000 people for ML testing.

Creates: hr_management_app/src/tests/fixtures/dummy_employees_2000.xlsx
Columns: NAME, EMAIL, DOB, JOB_TITLE, ROLE, YEAR_START, YEAR_END, CONTRACT_TYPE
"""

import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src" / "tests" / "fixtures"
OUT.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT / "dummy_employees_2000.xlsx"

NUM = 2000
random.seed(42)

ALLOWED_ROLES = [
    "engineer",
    "accountant",
    "manager",
    "high_manager",
    "admin",
    "driver",
    "construction_worker",
]

JOB_TITLES = [
    "Software Engineer",
    "Senior Engineer",
    "Accountant",
    "Project Manager",
    "Site Supervisor",
    "Operations Coordinator",
    "HR Specialist",
    "Construction Worker",
    "Driver",
]

CONTRACT_TYPES = ["full_time", "part_time", "contract", "temporary"]


# Helper: random DOB between 1955-01-01 and 2000-12-31
def random_dob():
    start = date(1955, 1, 1)
    end = date(2000, 12, 31)
    days = (end - start).days
    d = start + timedelta(days=random.randrange(days))
    return d.isoformat()


# Helper: year start between 1995 and 2024
def random_year_start():
    return random.randint(1995, 2024)


# Helper: year end sometimes empty
def random_year_end(start):
    if random.random() < 0.4:
        # still employed
        return ""
    # end between start and start+10
    return str(start + random.randint(0, 10))


# Generate rows
rows = []
for i in range(1, NUM + 1):
    first = f"First{i}"
    last = f"Last{i}"
    name = f"{first} {last}"
    email = f"{first.lower()}.{last.lower()}.{i}@example.com"
    dob = random_dob()
    job = random.choice(JOB_TITLES)
    role = random.choice(ALLOWED_ROLES)
    ys = random_year_start()
    ye = random_year_end(ys)
    contract = random.choice(CONTRACT_TYPES)
    rows.append([name, email, dob, job, role, str(ys), ye, contract])

try:
    from openpyxl import Workbook
except Exception as exc:
    raise SystemExit(
        "openpyxl not installed. Run: python -m pip install openpyxl"
    ) from exc

wb = Workbook()
ws = wb.active
assert ws is not None
ws.title = "employees"
headers = [
    "NAME",
    "EMAIL",
    "DOB",
    "JOB_TITLE",
    "ROLE",
    "YEAR_START",
    "YEAR_END",
    "CONTRACT_TYPE",
]
ws.append(headers)
for r in rows:
    ws.append(r)

wb.save(OUT_FILE)
print(f"Wrote {str(OUT_FILE)} ({OUT_FILE.stat().st_size} bytes)")
