"""Forwarding package `database` that re-exports src.database.database."""

try:
    from src.database import database as database
except Exception:
    from database import database as database  # type: ignore

__all__ = ["database"]
