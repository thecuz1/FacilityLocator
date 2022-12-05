import asyncio
import os
import logging
from logging.config import dictConfig
import sys
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands
from utils import Database, NoVoiceFilter, FilterLevel

# load .env file
load_dotenv()

# set the main directory
MAIN_DIR = Path()

# set log directory
LOG_DIR = MAIN_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# generate a list of extensions to load
COG_DIR = MAIN_DIR / "cogs"
EXTENSIONS = [
    f"{COG_DIR}.{result.stem}"
    for result in COG_DIR.iterdir()
    if result.is_file() and result.suffix == ".py"
]

# sqlite file to use
DB_FILE = MAIN_DIR / "data.sqlite"
# prefix to use for regular commands, defaults to '.'
BOT_PREFIX = os.environ.get("BOT_PREFIX")
# token to use
TOKEN = os.environ.get("BOT_TOKEN")
# can be set to None but will use api call on every start of the bot
OWNER_ID = os.environ.get("OWNER_ID")


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.owner_id = OWNER_ID
        self.db = Database(self, DB_FILE)

    async def on_ready(self):
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

    async def setup_hook(self):
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
            except Exception:
                logger.exception("Failed loading exension %r", extension)
            else:
                logger.info("Loaded extension %r", extension)

        if not DB_FILE.exists():
            await self.db.create()


intents = discord.Intents.all()
bot = Bot(BOT_PREFIX or ".", intents=intents, help_command=None)

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[{asctime}] [{levelname:<8}] {name}: {message}",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "style": "{",
            },
            "slim": {
                "format": "[{asctime}] {name}: {message}",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "style": "{",
            },
            "notime": {
                "format": "[{levelname:<8}] {name}: {message}",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "style": "{",
            },
            "discord_message": {
                "format": "{message} <t:{created:.0f}:R>",
                "style": "{",
            },
        },
        "handlers": {
            "discord_log": {
                "class": "logging.FileHandler",
                "filename": LOG_DIR / "discord.log",
                "encoding": "utf-8",
                "mode": "w",
                "formatter": "default",
            },
            "bot_log": {
                "class": "logging.FileHandler",
                "filename": LOG_DIR / "bot.log",
                "encoding": "utf-8",
                "mode": "w",
                "formatter": "default",
            },
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "notime",
                "filters": ["no_errors"],
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": logging.ERROR,
                "stream": sys.stderr,
                "formatter": "notime",
            },
            "guild_event_log": {
                "class": "logging.FileHandler",
                "filename": LOG_DIR / "guild.log",
                "encoding": "utf-8",
                "mode": "a",
                "formatter": "slim",
            },
            "facility_event_log": {
                "class": "utils.ExtraInfoFileHandler",
                "filename": LOG_DIR / "facility.log",
                "encoding": "utf-8",
                "mode": "a",
                "formatter": "slim",
            },
            "facility_event_guild": {
                "class": "utils.GuildHandler",
                "bot": bot,
                "formatter": "discord_message",
            },
        },
        "filters": {
            "no_voice_warning": {
                "()": NoVoiceFilter,
            },
            "no_errors": {
                "()": FilterLevel,
                "level": "WARNING",
            },
        },
        "loggers": {
            "__main__": {
                "level": logging.INFO,
                "handlers": ["bot_log", "stderr", "stdout"],
            },
            "utils": {
                "level": logging.INFO,
                "handlers": ["bot_log", "stderr", "stdout"],
            },
            "discord": {
                "level": logging.INFO,
                "handlers": ["discord_log"],
                "filters": ["no_voice_warning"],
            },
            "command_error": {
                "level": logging.INFO,
                "handlers": ["bot_log", "stderr", "stdout"],
            },
            "view_error": {
                "level": logging.INFO,
                "handlers": ["bot_log", "stderr", "stdout"],
            },
            "modal_error": {
                "level": logging.INFO,
                "handlers": ["bot_log", "stderr", "stdout"],
            },
            "guild_event": {"level": logging.INFO, "handlers": ["guild_event_log"]},
            "facility_event": {
                "level": logging.INFO,
                "handlers": ["facility_event_log", "facility_event_guild"],
            },
        },
    }
)
logger = logging.getLogger(__name__)

bot.run(TOKEN, log_handler=None)
