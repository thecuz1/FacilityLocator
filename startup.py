import os
import logging
from logging.config import dictConfig
import sys
from dotenv import load_dotenv
import discord
from discord.ext import commands
from utils import Database

load_dotenv()


class NoVoiceFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith('PyNaCl')


LOGGING_CONFIG = {
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
    },
    'handlers': {
        'discord_handler': {
            'class': 'logging.FileHandler',
            'filename': 'logs/discord.log',
            'encoding': 'utf-8',
            'mode': 'w',
            'formatter': 'default',
            'filters': [NoVoiceFilter()],
        },
        'command_error_handler': {
            'class': 'logging.FileHandler',
            'filename': 'logs/command_errors.log',
            'encoding': 'utf-8',
            'mode': 'a',
            'formatter': 'default',
        },
        'guild_event_handler': {
            'class': 'logging.FileHandler',
            'filename': 'logs/guild.log',
            'encoding': 'utf-8',
            'mode': 'a',
            'formatter': 'slim',
        },
        'facility_event_handler': {
            'class': 'logging.FileHandler',
            'filename': 'logs/facility.log',
            'encoding': 'utf-8',
            'mode': 'a',
            'formatter': 'slim',
        },
    },
    'loggers': {
        'discord': {
            'level': logging.INFO,
            'handlers': ['discord_handler']
        },
        'extensions': {
            'level': logging.INFO,
            'handlers': ['discord_handler']
        },
        'utils.sqlite': {
            'level': logging.INFO,
            'handlers': ['discord_handler']
        },
        'command_errors': {
            'level': logging.INFO,
            'handlers': ['command_error_handler']
        },
        'guild_event': {
            'level': logging.INFO,
            'handlers': ['guild_event_handler']
        },
        'facility_event': {
            'level': logging.INFO,
            'handlers': ['facility_event_handler']
        },
    }
}
EXTENSIONS = ('cogs.modify', 'cogs.query', 'cogs.misc', 'cogs.error_handler', 'cogs.events')
DB_NAME = 'data.sqlite'
BOT_PREFIX = os.environ.get('BOT_PREFIX')
TOKEN = os.environ.get('FACILITYLOCATOR_API_TOKEN')

dictConfig(LOGGING_CONFIG)

extensions_logger = logging.getLogger('extensions')


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.db = Database(self, DB_NAME)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print(f'Discordpy version: {discord.__version__}')
        print(f'Python version: {sys.version}')
        print('---------')
        sys.stdout.flush()

    async def setup_hook(self):
        self.owner_id = 195009659793440768
        for extension in EXTENSIONS:
            await self.load_extension(extension)
            extensions_logger.info('Loaded %r', extension)

        if not os.path.exists(DB_NAME):
            await self.db.create()

intents = discord.Intents.all()

bot = Bot(BOT_PREFIX, intents=intents, help_command=None)
bot.run(TOKEN, log_handler=None)
