"""
Simple smoke-test: import core modules and report import-time errors.
Run from project root with the virtualenv Python so imports resolve.
"""
import importlib, traceback, sys
modules = [
    'hr_management_app.src.ml.imputer',
    'hr_management_app.src.ml.imputer_ml',
    'hr_management_app.src.database.database',
    'hr_management_app.src.ui_import',
    'hr_management_app.src.parsers.file_parser',
    'hr_management_app.src.parsers.normalizer',
    'hr_management_app.src.ml.ner'
]
fail = False
for m in modules:
    try:
        importlib.import_module(m)
        print('OK', m)
    except Exception as e:
        print('ERR', m, str(e))
        traceback.print_exc()
        fail = True
if fail:
    sys.exit(2)
else:
    sys.exit(0)
