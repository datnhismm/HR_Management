import json
import os
from typing import Any, Dict


def _default_path() -> str:
    # prefer storing config next to the repository root when possible
    # detect repo root by looking for common repo files (.git or README.md)
    cur = os.getcwd()
    root = None
    p = cur
    while True:
        if os.path.exists(os.path.join(p, ".git")) or os.path.exists(
            os.path.join(p, "README.md")
        ):
            root = p
            break
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    if root:
        return os.path.join(root, ".hr_management_import_mappings.json")
    # fallback to user's home directory
    home = os.path.expanduser("~")
    return os.path.join(home, ".hr_management_import_mappings.json")


def load_config(path: str | None = None) -> Dict[str, Any]:
    p = path or _default_path()
    if not os.path.exists(p):
        return {"threshold": None, "mappings": {}}
    try:
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"threshold": None, "mappings": {}}


def save_config(config: Dict[str, Any], path: str | None = None) -> None:
    p = path or _default_path()
    try:
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2, ensure_ascii=False)
    except Exception:
        # best-effort persistence; ignore failures
        pass
