#!/usr/bin/env python3
"""Scan workspace .py files for syntax errors and simple import/runtime errors.

This script will:
- Walk the repo tree
- For each .py file, try to compile() to detect SyntaxError
- For each module under hr_management_app/src, attempt an import by path using runpy.run_path and capture exceptions
- Print a compact report
"""
import os
import sys
import compileall
import runpy
import traceback

root = os.path.abspath('.')
py_files = []
for dirpath, dirs, files in os.walk(root):
    # skip virtualenv folders
    if '.venv' in dirpath.split(os.sep) or 'venv' in dirpath.split(os.sep):
        continue
    for f in files:
        if f.endswith('.py'):
            py_files.append(os.path.join(dirpath, f))

syntax_errors = {}
for p in py_files:
    try:
        with open(p, 'r', encoding='utf-8') as fh:
            src = fh.read()
        compile(src, p, 'exec')
    except Exception as e:
        syntax_errors[p] = traceback.format_exc()

# Now attempt to run modules under hr_management_app/src to catch runtime import errors for those entrypoints
runtime_errors = {}
base_dir = os.path.join(root, 'hr_management_app', 'src')
if os.path.isdir(base_dir):
    for dirpath, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith('.py'):
                p = os.path.join(dirpath, f)
                try:
                    runpy.run_path(p, run_name='__main__')
                except SystemExit:
                    # allow SystemExit from scripts; record as OK
                    pass
                except Exception:
                    runtime_errors[p] = traceback.format_exc()

print('=== Syntax errors ===')
if not syntax_errors:
    print('None')
else:
    for p,e in syntax_errors.items():
        print(p)
        print(e.splitlines()[-3:])

print('\n=== Runtime errors when executing modules under hr_management_app/src ===')
if not runtime_errors:
    print('None')
else:
    for p,e in runtime_errors.items():
        print(p)
        # print only the exception summary
        lines = e.splitlines()
        print('\n'.join(lines[-6:]))

# exit status
if syntax_errors or runtime_errors:
    sys.exit(2)
else:
    sys.exit(0)
