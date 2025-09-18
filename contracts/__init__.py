"""Forwarding package for contracts used by tools/tests."""

try:
    from hr_management_app.src.contracts import models as models
    from hr_management_app.src.contracts import views as views
except Exception:
    from hr_management_app.contracts import models as models  # type: ignore
    from hr_management_app.contracts import views as views  # type: ignore

__all__ = ["models", "views"]
