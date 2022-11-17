from collections import deque
from logging import Handler, LogRecord
import logging


class ExtraInfoFileHandler(logging.FileHandler):
    def format(self, record: LogRecord) -> str:
        formatted_record = super().format(record)
        formatted_record += f' in {record.guild_id} ({record.guild_name})'
        return formatted_record


class GuildHandler(Handler):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot
        bot.guild_logs = {}

    def emit(self, record: LogRecord) -> None:
        """Add log record to the guild

        Args:
            record (LogRecord): Record to add
        """
        guild_deque = self.bot.guild_logs.get(record.guild_id, deque(maxlen=50))

        formatted_record = self.format(record)
        guild_deque.append(formatted_record)

        self.bot.guild_logs[record.guild_id] = guild_deque

    def format(self, record: LogRecord) -> str:
        formatted_record = super().format(record)
        return formatted_record.replace("'", ' ')


class NoVoiceFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith('PyNaCl')


class FilterLevel(logging.Filter):
    def __init__(self, *, level) -> None:
        super().__init__()
        self.level = getattr(logging, level)

    def filter(self, record):
        return record.levelno <= self.level
