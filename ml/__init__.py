"""Top-level forwarding package for ml used by tools and scripts."""
try:
    from hr_management_app.src.ml import imputer_ml as imputer_ml
    from hr_management_app.src.ml import imputer_heuristic as imputer_heuristic
except Exception:
    from hr_management_app.ml import imputer_ml as imputer_ml  # type: ignore
    from hr_management_app.ml import imputer_heuristic as imputer_heuristic  # type: ignore

__all__ = ["imputer_ml", "imputer_heuristic"]
