import os
import logging
from logging.config import dictConfig
import sys
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands
from utils import Database, NoVoiceFilter

load_dotenv()

MAIN_DIR = Path()

LOG_DIR = MAIN_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

COG_DIR = MAIN_DIR / 'cogs'
EXTENSIONS = [
    f'{COG_DIR}.{result.stem}'
    for result in COG_DIR.iterdir()
    if result.is_file() and result.suffix == '.py'
]

DB_FILE = MAIN_DIR / 'data.sqlite'
BOT_PREFIX = os.environ.get('BOT_PREFIX')
TOKEN = os.environ.get('FACILITYLOCATOR_API_TOKEN')


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.owner_id = 195009659793440768
        self.db = Database(self, DB_FILE)

    async def on_ready(self):
        logger.info('Logged in as %r (ID: %r)', self.user.name, self.user.id)
        logger.info('Discordpy version: %r', discord.__version__)
        logger.info('Python version: %r', sys.version)

    async def setup_hook(self):
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
            except Exception:
                logger.exception('Failed loading exension %r', extension)
            else:
                logger.info('Loaded extension %r', extension)

        if not DB_FILE.exists():
            await self.db.create()


intents = discord.Intents.all()
bot = Bot(BOT_PREFIX, intents=intents, help_command=None)

dictConfig(
    {
        'version': 1,
        'formatters': {
            'default': {
                'format': '[{asctime}] [{levelname:<8}] {name}: {message}',
                'datefmt': "%Y-%m-%d %H:%M:%S",
                'style': '{'
            },
            'slim': {
                'format': '[{asctime}] {name}: {message}',
                'datefmt': "%Y-%m-%d %H:%M:%S",
                'style': '{'
            },
            'notime': {
                'format': '[{levelname:<8}] {name}: {message}',
                'datefmt': "%Y-%m-%d %H:%M:%S",
                'style': '{'
            },
            'discord_message': {
                'format': '{message} <t:{created:.0f}:R>',
                'style': '{'
            },
        },
        'handlers': {
            'discord_file': {
                'class': 'logging.FileHandler',
                'filename': LOG_DIR / 'discord.log',
                'encoding': 'utf-8',
                'mode': 'w',
                'formatter': 'default',
                'filters': [NoVoiceFilter()],
            },
            'bot_log': {
                'class': 'logging.FileHandler',
                'filename': LOG_DIR / 'bot.log',
                'encoding': 'utf-8',
                'mode': 'w',
                'formatter': 'default',
            },
            'console_log': {
                'class': 'logging.StreamHandler',
                'formatter': 'notime',
            },
            'error_file': {
                'class': 'logging.FileHandler',
                'filename': LOG_DIR / 'errors.log',
                'encoding': 'utf-8',
                'mode': 'a',
                'formatter': 'default',
            },
            'guild_event_file': {
                'class': 'logging.FileHandler',
                'filename': LOG_DIR / 'guild.log',
                'encoding': 'utf-8',
                'mode': 'a',
                'formatter': 'slim',
            },
            'facility_event_file': {
                'class': 'utils.ExtraInfoFileHandler',
                'filename': LOG_DIR / 'facility.log',
                'encoding': 'utf-8',
                'mode': 'a',
                'formatter': 'slim',
            },
            'facility_event_guild': {
                'class': 'utils.GuildHandler',
                'bot': bot,
                'formatter': 'discord_message',
            },
        },
        'loggers': {
            '__main__': {
                'level': logging.INFO,
                'handlers': ['bot_log', 'console_log']
            },
            'utils.sqlite': {
                'level': logging.INFO,
                'handlers': ['bot_log', 'console_log']
            },
            'discord': {
                'level': logging.INFO,
                'handlers': ['discord_file']
            },
            'command_error': {
                'level': logging.INFO,
                'handlers': ['error_file']
            },
            'view_error': {
                'level': logging.INFO,
                'handlers': ['error_file']
            },
            'modal_error': {
                'level': logging.INFO,
                'handlers': ['error_file']
            },
            'guild_event': {
                'level': logging.INFO,
                'handlers': ['guild_event_file']
            },
            'facility_event': {
                'level': logging.INFO,
                'handlers': ['facility_event_file', 'facility_event_guild']
            },
        }
    }
)
logger = logging.getLogger(__name__)

bot.run(TOKEN, log_handler=None)
