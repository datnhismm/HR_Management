"""Parsers package shim to help tools and static analysis resolve imports.
This file intentionally keeps imports lazy to avoid heavy dependencies at import time.
"""

from importlib import import_module as _import_module


def __getattr__(name: str):
    # lazily import submodules when accessed as `parsers.normalizer`
    try:
        return _import_module(f"parsers.{name}")
    except Exception:
        # try local package layout when tools run from package root
        return _import_module(f"src.parsers.{name}")
