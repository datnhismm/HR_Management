"""Forwarding package `ml` that re-exports implementations under src.ml."""

try:
    from src.ml import imputer_heuristic as imputer_heuristic
    from src.ml import imputer_ml as imputer_ml
except Exception:
    from ml import imputer_heuristic as imputer_heuristic  # type: ignore
    from ml import imputer_ml as imputer_ml  # type: ignore

__all__ = ["imputer_ml", "imputer_heuristic"]
