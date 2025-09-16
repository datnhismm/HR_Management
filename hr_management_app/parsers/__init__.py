"""Forwarding package `parsers` that re-exports the implementation under src.parsers.
This helps tools and static analysis resolve imports when running from the repo layout.
"""

try:
    # Preferred layout when running from hr_management_app root
    from src.parsers import file_parser as file_parser
    from src.parsers import mapping_store as mapping_store
    from src.parsers import normalizer as normalizer
except Exception:
    # Fallback to installed / different layout
    from parsers import file_parser as file_parser  # type: ignore
    from parsers import mapping_store as mapping_store  # type: ignore
    from parsers import normalizer as normalizer  # type: ignore

__all__ = ["normalizer", "file_parser", "mapping_store"]
