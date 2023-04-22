from typing import Self, TypeVar


BD = TypeVar("BD", bound="BuildingData")


class Cost(dict):
    def __iadd__(self, other: Self):
        if not isinstance(other, Cost):
            raise NotImplementedError()

        combined_dict = self.copy()

        for key, value in other.items():
            if key in combined_dict:
                combined_dict[key] += value
            else:
                combined_dict[key] = value
        return combined_dict


class Building:
    def __init__(
        self,
        name: str,
        cost: Cost,
        upgrades: list[Self] | None = None,
        parent: Self | None = None,
    ):
        self.name: str = name
        self.cost: Cost = cost
        self.upgrades: list[Self] = upgrades or []
        self.parent: Self | None = parent

    def get_all_parents(self) -> list[Self]:
        parents = []
        current = self.parent
        while current is not None:
            parents.append(current)
            current = current.parent
        return parents

    def total_cost(self):
        cost = self.cost
        for building in self.get_all_parents():
            cost += building.cost
        return cost


item_data = {"Cmats": Cost(salvage=10), "Bmats": Cost(salvage=2)}


# needs rework
class BuildingData(dict):
    data = {
        "Materials Factory": Building(
            "Materials Factory",
            Cost(Bmats=200),
            upgrades=["Forge", "Metal Press", "Assembly Bay", "Smelter"],
        ),
        "Forge": Building("Forge", Cost(Cmats=200), parent="Materials Factory"),
        "Metal Press": Building(
            "Metal Press", Cost(Cmats=25), parent="Materials Factory"
        ),
        "Assembly Bay": Building(
            "Assembly Bay", Cost(Bmats=50), parent="Materials Factory"
        ),
        "Smelter": Building("Smelter", Cost(Cmats=25), parent="Materials Factory"),
        "Metalworks Factory": Building("Metalworks Factory", Cost(Cmats=125)),
        "Blast Furnace": Building(
            "Blast Furnace", Cost(Pcons=200), parent="Metalworks Factory"
        ),
        "Engineering Station": Building(
            "Engineering Station", Cost(Pcons=150), parent="Metalworks Factory"
        ),
        "Recycler": Building("Recycler", Cost(Cmats=25), parent="Metalworks Factory"),
        "Ammunition Factory": Building("Ammunition Factory", Cost(Pcons=25)),
        "Rocket Ammunition Factory": Building(
            "Rocket Ammunition Factory", Cost(Pcons=65), parent="Ammunition Factory"
        ),
        "Diesel Power Plant": Building(
            "Diesel Power Plant",
            Cost(Bmats=150),
        ),
        "Petrol Power Plant": Building(
            "Petrol Power Plant", Cost(Cmats=100), parent="Diesel Power Plant"
        ),
        "Power Station": Building("Power Station", Cost(Pcons=25)),
        "Sulfuric Reactor": Building(
            "Sulfuric Reactor", Cost(Scons=25), parent="Power Station"
        ),
        "Large Assembly Factory": Building("Large Assembly Factory", Cost(Pcons=250)),
        "Train Assembly": Building(
            "Train Assembly", Cost(Scons=150), parent="Large Assembly Factory"
        ),
        "Heavy Tank Assembly": Building(
            "Heavy Tank Assembly", Cost(Scons=150), parent="Large Assembly Factory"
        ),
        "Field Modification Center": Building(
            "Field Modification Center",
            Cost(Pcons=250),
        ),
        "Resource Transfer Station": Building(
            "Resource Transfer Station",
            Cost(Cmats=35),
        ),
        "Material Transfer Station": Building(
            "Material Transfer Station",
            Cost(Cmats=35),
        ),
        "Liquid Transfer Station": Building(
            "Liquid Transfer Station",
            Cost(Cmats=35),
        ),
        "Coal Refinery": Building(
            "Coal Refinery",
            Cost(Cmats=50),
        ),
        "Coke Furnace": Building(
            "Coke Furnace", Cost(Cmats=200), parent="Coal Refinery"
        ),
        "Coal Liquefier": Building(
            "Coal Liquefier", Cost(Pcons=25), parent="Coal Refinery"
        ),
        "Advanced Coal Liquefier": Building(
            "Advanced Coal Liquefier", Cost(Scons=65), parent="Coal Refinery"
        ),
        "Oil Refinery": Building("Oil Refinery", Cost(Cmats=50)),
        "Reformer": Building("Reformer", Cost(Cmats=200), parent="Oil Refinery"),
        "Cracking Unit": Building(
            "Cracking Unit", Cost(Pcons=20), parent="Oil Refinery"
        ),
        "Petrochemical Plant": Building(
            "Petrochemical Plant", Cost(Scons=25), parent="Oil Refinery"
        ),
        "Light Vehicle Assembly Station": Building(
            "Light Vehicle Assembly Station", Cost(Cmats=75)
        ),
        "Motor Pool": Building(
            "Motor Pool", Cost(Cmats=200), parent="Light Vehicle Assembly Station"
        ),
        "Rocket Factory": Building(
            "Rocket Factory", Cost(Pcons=65), parent="Light Vehicle Assembly Station"
        ),
        "Field Station": Building(
            "Field Station", Cost(Scons=25), parent="Light Vehicle Assembly Station"
        ),
        "Tank Factory": Building(
            "Tank Factory", Cost(Pcons=200), parent="Light Vehicle Assembly Station"
        ),
        "Weapons Platform": Building(
            "Weapons Platform", Cost(Scons=20), parent="Light Vehicle Assembly Station"
        ),
    }

    def __init__(self):
        super().__init__(self.data)
        self._resolve_buildings()

    def _resolve_buildings(self):
        for value in self.values():
            if value.parent:
                value.parent = self[value.parent]
            if value.upgrades:
                value.upgrades = [self[upgrade] for upgrade in value.upgrades[:]]


building_data: dict[str, Building] = BuildingData()


class BuildingsMeta(type):
    pass


class Buildings(metaclass=BuildingsMeta):
    pass
