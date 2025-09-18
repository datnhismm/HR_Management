import os
import tempfile
import traceback

from hr_management_app.src.contracts.models import Contract, store_contract_file
from hr_management_app.src.database.database import (
    init_db,
)

init_db()
# create a temporary fake PDF file
fd, path = tempfile.mkstemp(suffix=".pdf")
os.close(fd)
with open(path, "wb") as f:
    f.write(b"%PDF-1.4\n%Fake PDF for test\n")

print("Created temp file:", path)
try:
    dest = store_contract_file(path, construction_id=12345)
    print("store_contract_file returned:", dest, os.path.exists(dest))
    # create a contract object and add to DB
    c = Contract(
        id=7777,
        employee_id=None,
        construction_id=12345,
        start_date="2025-01-01",
        end_date="2025-12-31",
        terms="T",
        file_path=dest,
    )
    # use contract.save() which commits
    c.save()
    # read back
    loaded = Contract.retrieve_contract(7777)
    print("Loaded contract:", loaded)
    print("Loaded file_path:", getattr(loaded, "file_path", None))
    # verify file exists
    print("Exists at loaded path:", os.path.exists(getattr(loaded, "file_path", "")))
except Exception:
    traceback.print_exc()
finally:
    try:
        os.remove(path)
    except Exception:
        pass
