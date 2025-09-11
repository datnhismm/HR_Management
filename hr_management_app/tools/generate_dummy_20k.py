"""Generate a dummy Excel file with 20,000 people for ML testing.
Creates: hr_management_app/data/dummy_import_20k.xlsx
Columns: email,name,job_title,role,year_start
Approximately 1,000 rows will have 1-3 random missing fields.

Run with the project venv: .\.venv\Scripts\python.exe hr_management_app\tools\generate_dummy_20k.py
"""
import os
import random
from openpyxl import Workbook

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(OUT_DIR, exist_ok=True)
OUT_FILE = os.path.join(OUT_DIR, 'dummy_import_20k.xlsx')

NUM_ROWS = 20000
NUM_MISSING = 1000  # approx rows that will have at least one missing field

FIRST_NAMES = [
    'Alex','Sam','Jamie','Taylor','Jordan','Morgan','Casey','Chris','Pat','Drew',
    'Lee','Robin','Cameron','Avery','Riley','Peyton','Blake','Rowan','Evan','Quinn'
]
LAST_NAMES = [
    'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
    'Hernandez','Lopez','Gonzalez','Wilson','Anderson','Thomas','Taylor','Moore','Jackson','Martin'
]
JOB_TITLES = [
    'Software Engineer','Senior Software Engineer','Data Scientist','Product Manager','Sales Executive',
    'HR Specialist','Marketing Manager','QA Engineer','DevOps Engineer','Customer Success Manager'
]
ROLES = ['engineering','data','product','sales','hr','marketing','ops','support']

EMAIL_DOMAINS = ['example.com','example.org','test.com','fakecorp.com']

random.seed(42)


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_email(name, idx):
    base = ''.join(c for c in name.lower() if c.isalpha() or c == ' ').replace(' ', '.')
    return f"{base}.{idx}@{random.choice(EMAIL_DOMAINS)}"


def random_year_start():
    return random.randint(1995, 2024)


def create_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = 'people'
    headers = ['email','name','job_title','role','year_start']
    ws.append(headers)

    missing_indices = set(random.sample(range(1, NUM_ROWS+1), NUM_MISSING))

    for i in range(1, NUM_ROWS+1):
        name = random_name()
        email = random_email(name, i)
        job = random.choice(JOB_TITLES)
        role = random.choice(ROLES)
        year = random_year_start()

        # introduce some variation
        if random.random() < 0.02:
            name = name.upper()
        if random.random() < 0.01:
            email = None

        # If this row is selected for missing data, blank 1-3 random fields
        if i in missing_indices:
            fields = ['email','name','job_title','role','year_start']
            n_missing = random.randint(1,3)
            to_blank = random.sample(fields, n_missing)
            if 'email' in to_blank:
                email = None
            if 'name' in to_blank:
                name = None
            if 'job_title' in to_blank:
                job = None
            if 'role' in to_blank:
                role = None
            if 'year_start' in to_blank:
                year = None

        row = [email, name, job, role, year]
        ws.append(row)

    wb.save(OUT_FILE)
    return OUT_FILE


if __name__ == '__main__':
    print('Generating dummy XLSX...')
    path = create_workbook()
    size = os.path.getsize(path)
    print(f'Wrote {path} ({size // 1024} KB)')
