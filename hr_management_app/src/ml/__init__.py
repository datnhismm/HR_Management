"""ML package shim to help tools and static analysis resolve imports like `ml.imputer_ml`.
This keeps imports lazy and avoids importing heavy ML dependencies at module import time.
"""

from importlib import import_module as _import_module


def __getattr__(name: str):
    try:
        return _import_module(f"ml.{name}")
    except Exception:
        return _import_module(f"src.ml.{name}")
