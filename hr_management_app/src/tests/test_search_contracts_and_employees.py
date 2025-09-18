import os
from hr_management_app.src.database import database
from hr_management_app.src.contracts.models import Contract
from hr_management_app.src.database.database import _conn


def setup_test_db():
    # use a temp DB file in the package dir
    path = os.path.join(os.path.dirname(__file__), "test_search.db")
    if os.path.exists(path):
        os.remove(path)
    os.environ["HR_MANAGEMENT_TEST_DB"] = path
    # initialize schema
    database.init_db()
    return path


def teardown_test_db(path):
    try:
        os.remove(path)
    except Exception:
        pass


def test_contract_search_basic():
    path = setup_test_db()
    try:
        # insert a few contracts
        c1 = Contract(id=1, employee_id=1, construction_id=100, start_date="2023-01-01", end_date="2023-02-01", terms="Installation of windows")
        c1.save()
        c2 = Contract(id=2, employee_id=2, construction_id=200, start_date="2023-03-01", end_date="2023-04-01", terms="Roof repair and maintenance")
        c2.save()
        # search by numeric construction id
        res = Contract.search("100")
        assert any(r.id == 1 for r in res)
        # search by text
        res2 = Contract.search("roof")
        assert any("roof" in (r.terms or "").lower() for r in res2)
    finally:
        teardown_test_db(path)


def test_employee_search_basic():
    path = setup_test_db()
    try:
        # create a user and employee row directly via DB
        with _conn() as conn:
            c = conn.cursor()
            # create a user
            c.execute("INSERT INTO users (email, password_hash, salt, role) VALUES (?, ?, ?, ?)", ("a@example.com", "h", "s", "engineer"))
            uid = c.lastrowid
            c.execute("INSERT INTO employees (user_id, employee_number, name, dob, job_title, role, year_start) VALUES (?, ?, ?, ?, ?, ?, ?)", (uid, 1001, "Alice Smith", "1990-01-01", "Engineer", "engineer", 2015))
            c.execute("INSERT INTO employees (user_id, employee_number, name, dob, job_title, role, year_start) VALUES (?, ?, ?, ?, ?, ?, ?)", (None, 1002, "Bob Johnson", "1985-01-01", "Accountant", "accountant", 2010))
            conn.commit()
        res = database.search_employees("Alice")
        assert any(r[3] == "Alice Smith" for r in res)
        res2 = database.search_employees("1002")
        assert any(r[2] == 1002 for r in res2)
    finally:
        teardown_test_db(path)
