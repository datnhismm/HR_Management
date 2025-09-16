"""Top-level import shim for `ml` used by tools and scripts."""

from importlib import import_module as _import_module


def __getattr__(name: str):
    try:
        return _import_module(f"ml.{name}")
    except Exception:
        return _import_module(f"src.ml.{name}")
