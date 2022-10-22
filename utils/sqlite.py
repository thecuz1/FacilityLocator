import aiosqlite


class DataBase:
    def __init__(self, bot, db_name):
        self.bot = bot
        self.db_name = db_name

    async def add_facility(self, *args):
        async with aiosqlite.connect(self.db_name) as db:
            cur = await db.cursor()
            await cur.execute("INSERT INTO facilities (facilityname, region, maintainer, services, notes, author) VALUES(?, ?, ?, ?, ?, ?)", args)
            await db.commit()

    async def get_facility(self, region):
        async with aiosqlite.connect(self.db_name) as db:
            res = await db.execute("SELECT * FROM facilities WHERE region == ?", (region,))
            return await res.fetchall()
