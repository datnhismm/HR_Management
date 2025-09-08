def display_contracts(contracts):
    for contract in contracts:
        print(f"Contract ID: {contract.id}")
        print(f"Employee ID: {contract.employee_id}")
        print(f"Start Date: {contract.start_date}")
        print(f"End Date: {contract.end_date}")
        print(f"Terms: {contract.terms}")
        print("-" * 20)

def view_contract(contract):
    print(f"Viewing Contract ID: {contract.id}")
    print(f"Employee ID: {contract.employee_id}")
    print(f"Start Date: {contract.start_date}")
    print(f"End Date: {contract.end_date}")
    print(f"Terms: {contract.terms}")