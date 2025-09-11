import os
import unittest
from hr_management_app.src.parsers.file_parser import parse_csv

class ParserCsvTests(unittest.TestCase):
    def test_parse_csv_basic(self):
        p = os.path.join(os.getcwd(), 'tmp_parser.csv')
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write('name,email\nAlice,alice@example.com\nBob,bob@example.com\n')
        try:
            raws = parse_csv(p)
            self.assertEqual(len(raws), 2)
            self.assertEqual(raws[0]['name'], 'Alice')
        finally:
            if os.path.exists(p):
                os.remove(p)

if __name__ == '__main__':
    unittest.main()
