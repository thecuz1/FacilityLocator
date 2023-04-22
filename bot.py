from __future__ import annotations

import logging
import sys
import os
from typing import TYPE_CHECKING
from pathlib import Path
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands

from cogs import EXTENSIONS


if TYPE_CHECKING:
    from collections import deque

    from discord.abc import Snowflake

    AppCommandStore = dict[str, app_commands.AppCommand]

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


class CommandTree(app_commands.CommandTree):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._global_app_commands: AppCommandStore = {}
        self._guild_app_commands: dict[int, AppCommandStore] = {}

    def get_app_command(
        self,
        value: str | int,
        guild: Snowflake | int | None = None,
    ) -> app_commands.AppCommand | None:
        def search_dict(d: AppCommandStore) -> app_commands.AppCommand | None:
            for cmd_name, cmd in d.items():
                if value == cmd_name or (str(value).isdigit() and int(value) == cmd.id):
                    return cmd
            return None

        if guild:
            guild_id = guild.id if not isinstance(guild, int) else guild
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not self.fallback_to_global:
                return search_dict(guild_commands)
            else:
                return search_dict(guild_commands) or search_dict(
                    self._global_app_commands
                )
        else:
            return search_dict(self._global_app_commands)

    async def get_or_fetch_app_command(
        self,
        value: str | int,
        guild: Snowflake | int | None = None,
    ) -> app_commands.AppCommand | None:
        command = self.get_app_command(value, guild)
        if command is not None:
            return command

        await self.fetch_commands(guild=guild)
        command = self.get_app_command(value, guild)
        return command

    async def fetch_command(
        self, command_id: int, /, *, guild: Snowflake | None = None
    ) -> app_commands.AppCommand:
        res = await super().fetch_command(command_id, guild=guild)
        await self._update_cache([res], guild=guild)
        return res

    async def fetch_commands(
        self, *, guild: Snowflake | None = None
    ) -> list[app_commands.AppCommand]:
        res = await super().fetch_commands(guild=guild)
        await self._update_cache(res, guild=guild)
        return res

    @staticmethod
    def _unpack_app_commands(
        command_list: list[app_commands.AppCommand],
    ) -> AppCommandStore:
        ret: AppCommandStore = {}

        def unpack_options(
            options: list[
                app_commands.AppCommand
                | app_commands.AppCommandGroup
                | app_commands.Argument
            ],
        ):
            for option in options:
                if isinstance(option, app_commands.AppCommandGroup):
                    ret[option.qualified_name] = option
                    unpack_options(option.options)

        for command in command_list:
            ret[command.name] = command
            unpack_options(command.options)

        return ret

    async def _update_cache(
        self,
        command_list: list[app_commands.AppCommand],
        guild: Snowflake | int | None = None,
    ) -> None:
        _guild: Snowflake | None = None
        if guild is not None:
            if isinstance(guild, int):
                _guild = discord.Object(guild)
            else:
                _guild = guild

        if _guild:
            self._guild_app_commands[_guild.id] = self._unpack_app_commands(
                command_list
            )
        else:
            self._global_app_commands = self._unpack_app_commands(command_list)

    async def sync(
        self, *, guild: Snowflake | None = None
    ) -> list[app_commands.AppCommand]:
        res = await super().sync(guild=guild)
        await self._update_cache(res, guild=guild)
        return res


class FacilityBot(commands.Bot):
    tree: CommandTree

    def __init__(self) -> None:
        intents = discord.Intents(
            guilds=True, members=True, messages=True, message_content=True
        )
        super().__init__(
            command_prefix=commands.when_mentioned_or(BOT_PREFIX or "."),
            intents=intents,
            help_command=EmbedHelp(),
            tree_cls=CommandTree,
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
            except commands.ExtensionError:
                logger.exception("Failed loading exension %r", extension)
            else:
                logger.info("Loaded extension %r", extension)

        if not DB_FILE.exists():
            await self.db.create()

    async def start(self) -> None:
        await super().start(TOKEN)
