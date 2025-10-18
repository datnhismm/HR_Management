Contributing
============

Thanks for contributing! This file explains how to run tests locally, regenerate the developer manual, and basic guidelines for changes.

Running tests locally
---------------------

1. Create a Python virtual environment and activate it.

   Windows (PowerShell):

   ```powershell
   py -3 -m venv .venv; .\.venv\Scripts\Activate.ps1
   py -3 -m pip install --upgrade pip
   py -3 -m pip install -r hr_management_app/requirements.txt
   py -3 -m pip install pytest python-docx
   ```

2. Run the test suite:

   ```powershell
   py -3 -m pytest -q
   ```

Generating the developer manual
-------------------------------

The repository contains a generator script at `tools/generate_code_manual.py` that produces a Word `.docx` manual under `reports/`.

1. Ensure `python-docx` is installed (see above).
2. Run the generator:

```powershell
py -3 tools/generate_code_manual.py
```

This will run the tests and write a file like `reports/system_manual_YYYYMMDDTHHMMSSZ.docx`.

CI and artifacts
----------------

The GitHub Actions workflow `CI` runs tests and generates the developer manual on successful pushes to `main`. The generated `.docx` is uploaded as a workflow artifact named `developer-manual`.

Style and formatting
--------------------

We recommend using `pre-commit` with ruff/black/isort configured in `hr_management_app/`. Please run the formatter and linters before opening a PR.

Questions
---------

If anything is unclear or you need help running tests locally, open an issue or contact the maintainers.
