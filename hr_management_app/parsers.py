"""Top-level import shim for `parsers` used by tools and scripts.
This forwards to the package under src if available.
"""

from importlib import import_module as _import_module


def __getattr__(name: str):
    try:
        return _import_module(f"parsers.{name}")
    except Exception:
        return _import_module(f"src.parsers.{name}")
