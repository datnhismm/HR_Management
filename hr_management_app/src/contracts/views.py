def display_contracts(contracts):
    for contract in contracts:
        print(f"Contract ID: {contract.id}")
        print(f"Employee ID: {contract.employee_id}")
        print(f"Start Date: {contract.start_date}")
        print(f"End Date: {contract.end_date}")
        print(f"Terms: {contract.terms}")
        # show subsets if present
        try:
            from .models import contract_progress

            progress = contract_progress(contract.id)
            print(
                f"Progress: {progress['percent_complete']}% ({progress['completed']}/{progress['total']})"
            )
            for s in progress["details"]:
                print(f"  - [{s['status']}] {s['title']} (color: {s['color']})")
        except Exception:
            pass
        print("-" * 20)


def view_contract(contract):
    print(f"Viewing Contract ID: {contract.id}")
    print(f"Employee ID: {contract.employee_id}")
    print(f"Start Date: {contract.start_date}")
    print(f"End Date: {contract.end_date}")
    print(f"Terms: {contract.terms}")
    # show subsets
    try:
        from .models import contract_progress

        progress = contract_progress(contract.id)
        print(
            f"Progress: {progress['percent_complete']}% ({progress['completed']}/{progress['total']})"
        )
        for s in progress["details"]:
            print(f"  - [{s['status']}] {s['title']} (color: {s['color']})")
    except Exception:
        pass
