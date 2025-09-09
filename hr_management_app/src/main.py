from contracts.models import Contract
from contracts.views import display_contracts
from database.database import (
    init_db,
    add_contract_to_db,
    get_all_contracts,
    calculate_salary,
)
import sys
import logging

logger = logging.getLogger(__name__)

# attendance functions (use the stable names available in database.database)
try:
    from database.database import record_check_in as check_in, record_check_out as check_out
except Exception as exc:
    logger.exception("Attendance functions not available: %s", exc)

    def check_in(employee_id):
        raise RuntimeError("No check_in function available in database.database")

    def check_out(employee_id):
        raise RuntimeError("No check_out function available in database.database")


def add_contract():
    try:
        id_ = int(input("Enter contract ID: ").strip())
        employee_id = int(input("Enter employee ID: ").strip())
        start_date = input("Enter start date (YYYY-MM-DD): ").strip()
        end_date = input("Enter end date (YYYY-MM-DD): ").strip()
        terms = input("Enter contract terms: ").strip()
        contract = Contract(id=id_, employee_id=employee_id, start_date=start_date, end_date=end_date, terms=terms)
        add_contract_to_db(contract)
        print("Contract added successfully!\n")
    except Exception as e:
        logger.exception("Error adding contract: %s", e)
        print(f"Error adding contract: {e}")


def load_contracts_from_db():
    rows = get_all_contracts()
    # adapt to Contract constructor signature; if different this may need adjustment
    return [Contract(*row) for row in rows]


def attendance_menu():
    try:
        employee_id = int(input("Enter your employee ID: ").strip())
    except ValueError:
        print("Invalid employee ID.")
        return
    print("1. Check-in")
    print("2. Check-out")
    choice = input("Select an option: ").strip()
    try:
        if choice == "1":
            check_in(employee_id)
            print("Check-in recorded.")
        elif choice == "2":
            check_out(employee_id)
            print("Check-out recorded.")
        else:
            print("Invalid option.")
    except Exception as e:
        logger.exception("Attendance error: %s", e)
        print(f"Attendance error: {e}")


def salary_menu():
    try:
        employee_id = int(input("Enter employee ID: ").strip())
        start_date = input("Enter start date (YYYY-MM-DD): ").strip()
        end_date = input("Enter end date (YYYY-MM-DD): ").strip()
        hourly_wage = float(input("Enter hourly wage: ").strip())
        salary = calculate_salary(employee_id, start_date, end_date, hourly_wage)
        print(f"Salary for employee {employee_id} from {start_date} to {end_date}: {salary:.2f}")
    except Exception as e:
        logger.exception("Error calculating salary: %s", e)
        print(f"Error calculating salary: {e}")


def cli_main():
    print("Welcome to the HR Management System (CLI)")
    while True:
        contracts = load_contracts_from_db()
        print("\nMenu:")
        print("1. View Contracts")
        print("2. Add Contract")
        print("3. Attendance")
        print("4. Calculate Salary")
        print("5. Exit")
        choice = input("Select an option: ").strip()
        if choice == "1":
            display_contracts(contracts)
        elif choice == "2":
            add_contract()
        elif choice == "3":
            attendance_menu()
        elif choice == "4":
            salary_menu()
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    # initialize DB
    init_db()

    # CLI mode: pass 'cli' on command line (python main.py cli)
    if len(sys.argv) > 1 and sys.argv[1].lower() == "cli":
        cli_main()
        sys.exit(0)

    # GUI mode: import and run auth GUI (import locally to avoid circular imports)
    try:
        from auth_gui import AuthWindow
    except Exception as e:
        logger.exception("Failed to import auth GUI: %s", e)
        print(f"Failed to import auth GUI: {e}")
        print("If you want to use the CLI, run: python main.py cli")
        sys.exit(1)

    auth = AuthWindow()
    auth.mainloop()