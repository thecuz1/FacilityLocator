import aiosqlite


class DataBase:
    def __init__(self, bot, db_name):
        self.bot = bot
        self.db_name = db_name

    async def add_facility(self, *args):
        async with aiosqlite.connect(self.db_name) as db:
            cur = await db.cursor()
            await cur.execute("INSERT INTO facilities (name, region, coordinates, maintainer, services, description, author) VALUES(?, ?, ?, ?, ?, ?, ?)", args)
            await db.commit()

    async def get_facility(self, region):
        async with aiosqlite.connect(self.db_name) as db:
            res = await db.execute("SELECT * FROM facilities WHERE region == ?", (region,))
            return await res.fetchall()

    async def get_facility_ids(self, ids):
        async with aiosqlite.connect(self.db_name) as db:
            facility_list = []
            for lookup_id in ids:
                res = await db.execute("SELECT * FROM facilities WHERE id == ?", (lookup_id,))
                fetched_res = await res.fetchall()
                if not fetched_res:
                    continue
                facility_list.append(fetched_res)
            if not facility_list:
                return False
            facility_list = [item[0] for item in facility_list]
            return facility_list

    async def remove_facilities(self, ids):
        async with aiosqlite.connect(self.db_name) as db:
            await db.executemany("DELETE FROM facilities WHERE id == ?", ids)
            await db.commit()
