"""Diagnostic: check sklearn import and imputer_ml HAS_SKLEARN flag."""
import traceback
import sys
import os
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

print('sys.executable=', sys.executable)
try:
    import ml.imputer_ml as im
    print('imputer_ml.HAS_SKLEARN =', getattr(im, 'HAS_SKLEARN', None))
except Exception:
    print('Failed importing ml.imputer_ml:')
    traceback.print_exc()

try:
    import sklearn
    print('sklearn imported, version=', sklearn.__version__)
except Exception:
    print('Failed importing sklearn:')
    traceback.print_exc()
