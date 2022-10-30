import aiosqlite
from utils.facility import Facility


class DataBase:
    def __init__(self, bot, db_name):
        self.bot = bot
        self.db_name = db_name

    async def add_facility(self, facility: Facility):
        async with aiosqlite.connect(self.db_name) as db:
            values = (facility.name, facility.region, facility.coordinates, facility.maintainer, facility.services, facility.vehicle_services, facility.description, facility.author_id)
            cur = await db.cursor()
            await cur.execute("INSERT INTO facilities (name, region, coordinates, maintainer, services, vehicle_services, description, author) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", values)
            await db.commit()

    async def get_facility(self, region, service = 0, vehicle_service = 0):
        async with aiosqlite.connect(self.db_name) as db:
            if service == 0 & vehicle_service == 0:
                res = await db.execute("SELECT * FROM facilities WHERE region == ?", (region,))
            elif service != 0:
                res = await db.execute("SELECT * FROM facilities WHERE region == ? AND services & ?", (region, service))
            elif vehicle_service != 0:
                res = await db.execute("SELECT * FROM facilities WHERE region == ? AND vehicle_services & ?", (region, vehicle_service))
            fetched_result = await res.fetchall()
            if not fetched_result:
                return None
            return [Facility(name, region, coordinates, maintainer, author_id, facility_id, services, vehicle_services, description)
                    for facility_id, name, region, coordinates, maintainer, services, vehicle_services, description, author_id in fetched_result]

    async def get_facility_ids(self, ids):
        async with aiosqlite.connect(self.db_name) as db:
            facility_list = []
            for lookup_id in ids:
                res = await db.execute("SELECT * FROM facilities WHERE id == ?", (lookup_id,))
                fetched_result = await res.fetchall()
                if not fetched_result:
                    continue
                facility_id, name, region, coordinates, maintainer, services, vehicle_services, description, author_id = fetched_result[0]
                facility = Facility(name, region, coordinates, maintainer, author_id, facility_id, services, vehicle_services, description)
                facility_list.append(facility)
            if not facility_list:
                return False
            return facility_list

    async def remove_facilities(self, ids):
        async with aiosqlite.connect(self.db_name) as db:
            await db.executemany("DELETE FROM facilities WHERE id == ?", ids)
            await db.commit()
    
    async def update_facility(self, facility):
        async with aiosqlite.connect(self.db_name) as db:
            values = (facility.name, facility.region, facility.coordinates, facility.maintainer, facility.services, facility.vehicle_services, facility.description, facility.author_id, facility.facility_id)
            await db.execute("UPDATE facilities SET name = ?, region = ?, coordinates = ?, maintainer = ?, services = ?, vehicle_services = ?, description = ?, author = ? WHERE id == ?", values)
            await db.commit()
