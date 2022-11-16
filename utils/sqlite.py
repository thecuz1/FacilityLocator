from typing import List, Dict
import logging
import aiosqlite
from facility import Facility

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, bot, db_file) -> None:
        self.bot = bot
        self.db_file = db_file

    async def create(self):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('''
                CREATE TABLE "facilities" (
                "id_"	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                "name"	TEXT,
                "description"	TEXT,
                "region"	TEXT,
                "coordinates"	TEXT,
                "marker"	INTEGER,
                "maintainer"	TEXT,
                "author"	INTEGER,
                "item_services"	INTEGER,
                "vehicle_services"	INTEGER,
                "creation_time"	INTEGER,
                "guild_id"	INTEGER
            );''')
            await db.commit()
            logger.info('Created database %r', str(self.db_file))

    async def get_all_facilities(self) -> List[Facility]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            results = await db.execute("SELECT * FROM facilities")
            rows = await results.fetchall()
            return [
                Facility(**row)
                for row in rows
            ]

    async def add_facility(self, facility: Facility) -> None:
        async with aiosqlite.connect(self.db_file) as db:
            values = (facility.name, facility.description, facility.region, facility.coordinates, facility.marker, facility.maintainer, facility.author, facility.item_services, facility.vehicle_services, facility.creation_time, facility.guild_id)
            cur = await db.cursor()
            await cur.execute("INSERT INTO facilities (name, description, region, coordinates, marker, maintainer, author, item_services, vehicle_services, creation_time, guild_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
            await db.commit()

    async def get_facilities(self, search_dict: Dict[str, str | int]) -> List[Facility]:
        if not search_dict:
            return await self.get_all_facilities()
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            sql = "SELECT * FROM facilities WHERE "
            sql += "AND".join(search_dict.keys())

            result = await db.execute(sql, tuple(search_dict.values()))
            fetched_results = await result.fetchall()
            return [
                Facility(**row)
                for row in fetched_results
            ]

    async def get_facility_ids(self, ids) -> List[Facility]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            facility_list = []
            for lookup_id in ids:
                res = await db.execute("SELECT * FROM facilities WHERE id_ == ?", (lookup_id,))
                fetched_result = await res.fetchone()
                if not fetched_result:
                    continue
                facility = Facility(**fetched_result)
                facility_list.append(facility)
            return facility_list

    async def get_facility_id(self, id_: int) -> Facility | None:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            res = await db.execute("SELECT * FROM facilities WHERE id_ == ?", (id_,))
            fetched_result = await res.fetchone()
            if not fetched_result:
                return None
            return Facility(**fetched_result)

    async def remove_facilities(self, facilities) -> None:
        async with aiosqlite.connect(self.db_file) as db:
            ids = [(facility.id_,) for facility in facilities]
            await db.executemany("DELETE FROM facilities WHERE id_ == ?", ids)
            await db.commit()
    
    async def update_facility(self, facility) -> None:
        async with aiosqlite.connect(self.db_file) as db:
            values = (facility.name, facility.description, facility.maintainer, facility.item_services, facility.vehicle_services, facility.id_)
            await db.execute("UPDATE facilities SET name = ?, description = ?, maintainer = ?, item_services = ?, vehicle_services = ? WHERE id_ == ?", values)
            await db.commit()

    async def reset(self) -> None:
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("DELETE FROM facilities")
            await db.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name == 'facilities'")
            await db.commit()
            await db.execute("VACUUM")
            await db.commit()
        logger.info('Removed all entries from facilities and executed VACUUM')
