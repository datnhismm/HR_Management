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
