import importlib.util
import os
import sys
import uuid

db_path = os.path.join(os.path.dirname(__file__), "src", "database", "database.py")
spec = importlib.util.spec_from_file_location("dbmod", db_path)
if spec is None or spec.loader is None:
	raise RuntimeError(f"Failed to load database module from {db_path}")
dbmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dbmod)

code = "TEST-" + uuid.uuid4().hex[:8]
print("sending code", code)
dbmod.send_verification_code("dattpgcc200192@fpt.edu.vn", code)
print("sent", code)
