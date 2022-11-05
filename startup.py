import os
import logging
import sys
from dotenv import load_dotenv
import aiosqlite
import discord
from discord.ext import commands
from utils.sqlite import DataBase

load_dotenv('.env')

handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')

EXTENSIONS = ('cogs.modify', 'cogs.query', 'cogs.misc', 'cogs.error_handler')


class Bot(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print(f'Discordpy version: {discord.__version__}')
        print(f'Python version: {sys.version}')
        print('---------')

    async def setup_hook(self):
        self.owner_id = 195009659793440768
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        db_name = 'data.sqlite'
        if not os.path.exists(db_name):
            async with aiosqlite.connect(db_name) as db:
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
                print(f'Created {db_name}')
        self.db = DataBase(self, db_name)


intents = discord.Intents.all()

bot = Bot(os.environ.get('BOT_PREFIX'), intents=intents, help_command=None)
bot.run(os.environ.get('FACILITYLOCATOR_API_TOKEN'), log_handler=handler)
