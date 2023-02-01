import logging
import asyncio
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
# can be set to None but will use api call on every start of the bot
OWNER_ID = os.environ.get("OWNER_ID")


class FacilityBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or(BOT_PREFIX or "."),
            intents=intents,
        )
        self.guild_logs: dict[str, deque] = {}
        self.owner_id = OWNER_ID
        from cogs.utils.sqlite import Database

        self.db = Database(self, DB_FILE)

    async def on_ready(self) -> None:
        logger.info("Logged in as %r (ID: %r)", self.user.name, self.user.id)
        logger.info("Discordpy version: %r", discord.__version__)
        logger.info("Python version: %r", sys.version)

        if not self.owner_id:
            logger.warning("Owner ID is not set and will be fetched in 5 seconds")
            await asyncio.sleep(5)
            app_info = await self.application_info()
            self.owner_id = app_info.owner.id
            logger.info("Owner ID set to %r", self.owner_id)
        else:
            try:
                self.owner_id = int(self.owner_id)
            except ValueError:
                self.owner_id = None
                logger.warning(
                    "Owner ID was expected to be a int and failed to convert to int, reset to None"
                )

    async def setup_hook(self) -> None:
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
