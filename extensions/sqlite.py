import discord
from discord.ext import commands
import aiosqlite


class DataBase:
    def __init__(self, bot):
        self.bot = bot

    async def addFacility(self, facilityname, region, coordinates, maintainer, services, notes, userid):
        data = [
            facilityname, region, coordinates, maintainer, services, notes, userid
        ]
        async with aiosqlite.connect('data.sqlite') as db:
            cur = await db.cursor()
            await cur.execute("INSERT INTO facilities VALUES(?, ?, ?, ?, ?, ?, ?)", data)
            await db.commit()

    async def getFacility(self, region):
        async with aiosqlite.connect('data.sqlite') as db:
            res = await db.execute("SELECT * FROM facilities WHERE region == ?", (region,))
            return await res.fetchall()


async def setup(bot: commands.bot) -> None:
    bot.db = DataBase(bot)


async def teardown(bot: commands.bot) -> None:
    del bot.db
