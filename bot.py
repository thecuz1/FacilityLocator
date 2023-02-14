import logging
import sys
import os
from collections import deque
from pathlib import Path
from dotenv import load_dotenv

import discord
from discord.ext import commands

from cogs import EXTENSIONS

logger = logging.getLogger(__name__)

load_dotenv()

# sqlite file to use
DB_FILE = Path() / "data.sqlite"
# prefix to use for regular commands, defaults to '.'
BOT_PREFIX = os.environ.get("BOT_PREFIX")
# token to use
TOKEN = os.environ.get("BOT_TOKEN")


class EmbedHelp(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            embed = discord.Embed(description=page, colour=discord.Colour.blue())
            await destination.send(embed=embed)


class FacilityBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or(BOT_PREFIX or "."),
            intents=intents,
            help_command=EmbedHelp(),
        )
        self.guild_logs: dict[str, deque] = {}
        from cogs.utils.sqlite import Database

        self.db = Database(self, DB_FILE)

    async def on_ready(self) -> None:
        logger.info("Logged in as %r (ID: %r)", self.user.name, self.user.id)
        logger.info("Discordpy version: %r", discord.__version__)
        logger.info("Python version: %r", sys.version)

    async def setup_hook(self) -> None:
        self.owner_id = self.application and self.application.owner.id

        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
            except Exception:
                logger.exception("Failed loading exension %r", extension)
            else:
                logger.info("Loaded extension %r", extension)

        if not DB_FILE.exists():
            await self.db.create()

    async def start(self) -> None:
        await super().start(TOKEN)
