from hr_management_app.src.parsers.normalizer import map_columns, validate_and_clean


def test_map_and_validate():
    row = {
        "Name": "Alice",
        "E-mail": "alice@example.com",
        "DOB": "1985-02-15",
        "Job": "Engineer",
        "Role": "engineer",
        "Year Start": "2010",
    }
    mapped = map_columns(row)
    cleaned, problems = validate_and_clean(mapped)
    assert cleaned["name"] == "Alice"
    assert cleaned["email"] == "alice@example.com"
    assert cleaned["dob"].startswith("1985")
    assert cleaned["job_title"] == "Engineer"
    assert cleaned["role"] == "engineer"
    assert cleaned["year_start"] == 2010
    assert problems == []
