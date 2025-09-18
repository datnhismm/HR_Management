class Employee:
    def __init__(self, id, name, position):
        self.id = id
        self.name = name
        self.position = position
        self.contracts = []

    def add_contract(self, contract):
        self.contracts.append(contract)

    def get_info(self):
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "contracts": [
                (
                    c.get_details()
                    if hasattr(c, "get_details")
                    else {
                        "id": getattr(c, "id", None),
                        "terms": getattr(c, "terms", None),
                    }
                )
                for c in self.contracts
            ],
        }


    @staticmethod
    def search(term: str, limit: int = None):
        """Search employees and return list of dict rows for UI consumption."""
        try:
            from hr_management_app.src.database.database import search_employees

            rows = search_employees(term, limit=limit)
            results = []
            for r in rows:
                (
                    eid,
                    user_id,
                    emp_num,
                    name,
                    dob,
                    job_title,
                    role,
                    year_start,
                    year_end,
                    profile_pic,
                    contract_type,
                ) = r
                results.append(
                    {
                        "id": eid,
                        "user_id": user_id,
                        "employee_number": emp_num,
                        "name": name,
                        "dob": dob,
                        "job_title": job_title,
                        "role": role,
                    }
                )
            return results
        except Exception:
            return []
