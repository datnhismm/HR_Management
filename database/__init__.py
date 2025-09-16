"""Forwarding package for `database` used by scripts/tools.
Forwards to the implementation under hr_management_app.src.database.
"""
try:
    from hr_management_app.src.database import database as database
except Exception:
    # last resort: try importing a local package
    try:
        from hr_management_app.database import database as database  # type: ignore
    except Exception:
        raise

__all__ = ["database"]
