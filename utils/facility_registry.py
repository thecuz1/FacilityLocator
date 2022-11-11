from sys import getsizeof
from typing import List, Tuple, Sequence
from utils import Facility, DataBase


class FacilityRegistry:
    """Class repersenting a dictonary of all facilities"""

    def __init__(self, database: DataBase) -> None:
        self.database = database
        self._facilities: List[Facility] = []

    def __len__(self):
        return len(self._facilities)

    def __sizeof__(self) -> int:
        list_size = getsizeof(self._facilities)
        size_generator = (getsizeof(facility) for facility in self._facilities)
        return sum(size_generator) + list_size

    async def fill_cache(self) -> None:
        """Fills cache with all facilities"""
        facilities = await self.database.all_facilities()
        for facility in facilities:
            self.add(facility=facility)

    def add(self, facility: Facility) -> None:
        """Adds a facility to cache

        Args:
            facility (Facility): Facility to add
        """
        self._facilities.append(facility)

    async def create(self, facility: Facility) -> None:
        """Adds new facility to cache and saves it to the database

        Args:
            facility (Facility): Facility to create
        """
        self.add(facility=facility)
        await self.database.add_facility(facility=facility)

    def find(self, id_: int) -> Facility | None:
        """Finds a facility with the given ID

        Args:
            id_ (int): ID to search for

        Returns:
            Facility | None: Returns the facility if found or None
        """
        for facility in self._facilities:
            if facility.id_ == id_:
                return facility
        return None

    def find_multiple(self, ids: Sequence[int]) -> Tuple[Facility]:
        """Finds multiple facilities with given ID's

        Args:
            ids (Sequence[int]): ID's to search for

        Returns:
            Tuple[Facility]: Returns a tuple of the facilities found
        """
        found_facilities = (
            facility for facility in self._facilities if str(facility.id_) in ids
        )
        return tuple(found_facilities)

    async def update(self, facility: Facility) -> None:
        """Updates facility information in the database

        Args:
            facility (Facility): Facility to update
        """
        await self.database.update_facility(facility=facility)
