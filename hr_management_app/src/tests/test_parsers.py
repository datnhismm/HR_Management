import tempfile
import os
from parsers.file_parser import parse_csv


def test_parse_csv_basic():
    csv = 'Name,Email,Date of Birth\nJohn Doe,john@example.com,1990-05-01\n'
    fd, path = tempfile.mkstemp(suffix='.csv')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(csv)
        rows = parse_csv(path)
        assert isinstance(rows, list)
        assert len(rows) == 1
        assert rows[0]['Name'] == 'John Doe'
    finally:
        os.remove(path)
