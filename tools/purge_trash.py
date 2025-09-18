"""CLI to list and purge trashed contracts.

Usage:
  python tools/purge_trash.py --list
  python tools/purge_trash.py --purge 123 456
  python tools/purge_trash.py --purge-all
"""

import argparse

from hr_management_app.src.database import database


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Manage trashed contracts")
    p.add_argument("--list", action="store_true", help="List trashed contracts")
    p.add_argument("--purge", nargs="*", type=int, help="Purge specific contract ids")
    p.add_argument(
        "--purge-all", action="store_true", help="Purge all trashed contracts"
    )
    args = p.parse_args(argv)

    if args.list:
        rows = database.list_trashed_contracts()
        if not rows:
            print("No trashed contracts")
            return 0
        for r in rows:
            print(f"{r[0]}\t{r[6] or ''}\t{r[7] or ''}\t{r[11] or ''}")
        return 0

    if args.purge_all:
        confirm = input("Really purge ALL trashed contracts? Type 'YES' to confirm: ")
        if confirm != "YES":
            print("Aborted")
            return 1
        ids = [r[0] for r in database.list_trashed_contracts()]
        for cid in ids:
            database.delete_contract_and_descendants(cid)
        print(f"Purged {len(ids)} contracts")
        return 0

    if args.purge:
        for cid in args.purge:
            database.delete_contract_and_descendants(cid)
        print(f"Purged {len(args.purge)} contracts")
        return 0

    p.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
