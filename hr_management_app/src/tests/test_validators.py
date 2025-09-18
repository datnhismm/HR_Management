import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from ui_validators import validate_contract_fields


def test_validate_contract_fields_ok():
    cid, eid, s, e = validate_contract_fields("1", "2", "2025-01-01", "2025-12-31")
    assert cid == 1 and eid == 2 and s == "2025-01-01" and e == "2025-12-31"


@pytest.mark.parametrize(
    "cid,eid,start,end",
    [
        ("", "1", "2025-01-01", "2025-12-31"),
        ("a", "1", "2025-01-01", "2025-12-31"),
        ("1", "b", "2025-01-01", "2025-12-31"),
        ("1", "2", "2025-01-01", "2024-12-31"),
        ("1", "2", "bad", "2025-12-31"),
    ],
)
def test_validate_contract_fields_bad(cid, eid, start, end):
    with pytest.raises(ValueError):
        validate_contract_fields(cid, eid, start, end)
