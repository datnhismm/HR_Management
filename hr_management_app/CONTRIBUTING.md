Contributing
============

Thank you for contributing to this project. This short guide helps you run the project's formatting and linting tools locally and set up a pre-commit hook so your changes remain consistent.

Required tools
--------------
- Python 3.11+ (the project uses Python 3.13 in CI locally, but tools work with 3.11+)
- pip (or your preferred package manager)

Install developer tools
-----------------------
Install the minimal tooling into your environment:

    python -m pip install --upgrade pip
    python -m pip install black isort ruff pre-commit

Using the formatters/linter
---------------------------
Run these commands from the repository root (where CONTRIBUTING.md lives):

    # sort imports
    python -m isort .

    # format code
    python -m black .

    # lint and auto-fix where safe
    python -m ruff check --fix .

    # verify no lint issues remain
    python -m ruff check .

Pre-commit hooks (recommended)
--------------------------------
This repository includes a .pre-commit-config.yaml. To enable the pre-commit hooks locally run:

    python -m pip install pre-commit
    pre-commit install
    # To run hooks against all files (first time)
    pre-commit run --all-files

Notes
-----
- The pre-commit hooks run isort, black, and ruff --fix automatically.
- If you run into environment-specific issues, creating and activating a venv or using python -m pip helps keep things isolated.

If you want, I can create a branch and open a PR that adds these files and commits the formatting changes I already made.
