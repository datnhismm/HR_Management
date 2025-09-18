"""Top-level forwarding package for parsers used by tools and scripts."""

try:
    from hr_management_app.src.parsers import file_parser as file_parser
    from hr_management_app.src.parsers import mapping_store as mapping_store
    from hr_management_app.src.parsers import normalizer as normalizer
except Exception:
    from hr_management_app.parsers import file_parser as file_parser  # type: ignore
    from hr_management_app.parsers import mapping_store as mapping_store  # type: ignore
    from hr_management_app.parsers import normalizer as normalizer  # type: ignore

__all__ = ["normalizer", "file_parser", "mapping_store"]
