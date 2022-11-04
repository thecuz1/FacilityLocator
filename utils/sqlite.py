from typing import Union
import aiosqlite
from utils import Facility


class DataBase:
    def __init__(self, bot, db_name) -> None:
        self.bot = bot
        self.db_name = db_name

    async def add_facility(self, facility: Facility) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            values = (facility.name, facility.description, facility.region, facility.coordinates, facility.marker, facility.maintainer, facility.author, facility.item_services, facility.vehicle_services)
            cur = await db.cursor()
            await cur.execute("INSERT INTO facilities (name, description, region, coordinates, marker, maintainer, author, item_services, vehicle_services) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
            await db.commit()

    async def get_facility(self, region = None, service = None, vehicle_service = None) -> Union[list[Facility], None]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            sql = "SELECT * FROM facilities"
            variabls = []
            first = True

            if region or service or vehicle_service:
                sql += "  WHERE "
            if region is not None:
                if first:
                    sql += "region == ?"
                    first = False
                else:
                    sql += "AND region == ?"
                variabls.append(region)
            if service is not None:
                if first:
                    sql += "item_services & ?"
                    first = False
                else:
                    sql += "AND item_services & ?"
                variabls.append(service)
            if vehicle_service is not None:
                if first:
                    sql += "vehicle_services & ?"
                    first = False
                else:
                    sql += "AND vehicle_services & ?"
                variabls.append(vehicle_service)

            res = await db.execute(sql, tuple(variabls))
            fetched_result = await res.fetchall()
            if not fetched_result:
                return None
            return [Facility(**row)
                    for row in fetched_result]

    async def get_facility_ids(self, ids) -> Union[list[Facility], None]:
        async with aiosqlite.connect(self.db_name) as db:
            facility_list = []
            for lookup_id in ids:
                db.row_factory = aiosqlite.Row
                res = await db.execute("SELECT * FROM facilities WHERE id_ == ?", (lookup_id,))
                fetched_result = await res.fetchall()
                if not fetched_result:
                    continue
                facility = Facility(**fetched_result[0])
                facility_list.append(facility)
            if not facility_list:
                return None
            return facility_list

    async def remove_facilities(self, ids) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            await db.executemany("DELETE FROM facilities WHERE id_ == ?", ids)
            await db.commit()
    
    async def update_facility(self, facility) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            values = (facility.name, facility.description, facility.region, facility.coordinates, facility.marker, facility.maintainer, facility.author, facility.item_services, facility.vehicle_services, facility.id_)
            await db.execute("UPDATE facilities SET name = ?, description = ?, region = ?, coordinates = ?, marker = ?, maintainer = ?, author = ?, item_services = ?, vehicle_services = ? WHERE id_ == ?", values)
            await db.commit()
