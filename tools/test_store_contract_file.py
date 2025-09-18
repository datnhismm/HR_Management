import os
import tempfile
import traceback

from hr_management_app.src.contracts.models import store_contract_file

# create a temporary fake PDF file
fd, path = tempfile.mkstemp(suffix=".pdf")
os.close(fd)
with open(path, "wb") as f:
    f.write(b"%PDF-1.4\n%Fake PDF for test\n")

print("Created temp file:", path)
try:
    dest = store_contract_file(path, construction_id=42)
    print("store_contract_file returned:", dest)
    print("Exists at dest:", os.path.exists(dest))
except Exception:
    print("Exception when storing file:")
    traceback.print_exc()
finally:
    try:
        os.remove(path)
    except Exception:
        pass
