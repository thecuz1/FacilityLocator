from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord import Guild, Message, NotFound, Interaction
from discord.ext import commands

from .utils.embeds import create_list


if TYPE_CHECKING:
    from bot import FacilityBot
    from discord.app_commands import Command, ContextMenu

    from .utils.facility import Facility
    from .utils.context import GuildInteraction


guild_logger = logging.getLogger("guild_event")
facility_logger = logging.getLogger("facility_event")


class Events(commands.Cog):
    def __init__(self, bot: FacilityBot) -> None:
        self.bot: FacilityBot = bot

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, interaction: Interaction, command: Command | ContextMenu
    ) -> None:
        insert_query = """INSERT INTO command_stats VALUES (?, ?, ?) ON CONFLICT(name, guild_id) DO UPDATE SET run_count = run_count + 1"""
        await self.bot.db.execute(
            insert_query, command.qualified_name, 1, interaction.guild_id or 0
        )

    @commands.Cog.listener()
    async def on_guild_join(
        self,
        guild: Guild,
    ) -> None:
        """Logs when the bot joins a guild

        Args:
            guild (Guild): Guild the bot joined
        """
        guild_logger.info("Bot joined %r (%s)", guild.id, guild.name)

    @commands.Cog.listener()
    async def on_guild_remove(
        self,
        guild: Guild,
    ) -> None:
        """Logs when the bot is removed from a guild

        Args:
            guild (Guild): Guild the bot was removed from
        """
        guild_logger.info("Bot removed from %r (%s)", guild.id, guild.name)

    @commands.Cog.listener()
    async def on_message(
        self,
        message: Message,
    ) -> None:
        """Resopnds when mentioned

        Args:
            message (Message): Message to check for mentions
        """
        if self.bot.user and message.content == f"<@{self.bot.user.id}>":
            info_command = self.bot.get_command("info")
            if info_command is None:
                return
            ctx = await self.bot.get_context(message)
            try:
                await info_command(ctx)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_facility_create(
        self, facility: Facility, ctx: GuildInteraction
    ) -> None:
        """Triggered when a facility is created

        Args:
            facility (Facility): Facility that was created
            ctx (GuildInteraction): Context of facility creation
        """
        facility_logger.info(
            "Facility created by %s with ID: `%s`",
            ctx.user.mention,
            facility.id_,
            extra={"ctx": ctx},
        )
        await self.update_list(ctx.guild)

    @commands.Cog.listener()
    async def on_facility_modify(
        self, before: Facility, after: Facility, ctx: GuildInteraction
    ) -> None:
        """Triggered when a facility is modified

        Args:
            before (Facility): Previous facility
            after (Facility): New facility
            ctx (GuildInteraction): Context of facility modification
        """
        facility_logger.info(
            "Facility ID %r modified by %s",
            after.id_,
            ctx.user.mention,
            extra={"ctx": ctx},
        )
        await self.update_list(ctx.guild)

    @commands.Cog.listener()
    async def on_bulk_facility_delete(
        self, facilities: list[Facility], ctx: GuildInteraction
    ) -> None:
        """Triggered when multiple facilities are removed

        Args:
            facilities (list[Facility]): Facilities that were removed
            ctx (GuildInteraction): Context of facility deletion
        """
        facility_logger.info(
            "Facility ID(s) %r removed by %s",
            [facility.id_ for facility in facilities],
            ctx.user.mention,
            extra={"ctx": ctx},
        )
        await self.update_list(ctx.guild)

    async def update_list(self, guild: Guild) -> None:
        list_location = await self.bot.db.get_list(guild)
        if not list_location:
            return

        search_dict = {" guild_id == ? ": guild.id}
        facilities: list[Facility] = await self.bot.db.get_facilities(search_dict)

        channel_id, messages = list_location
        embeds = create_list(facilities, guild)

        async def remove_messages():
            for message in messages:
                message = channel.get_partial_message(message)
                try:
                    await message.delete()
                except NotFound:
                    pass

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return

        if len(embeds) != len(messages):
            await remove_messages()

        else:
            for message_id, embed in zip(messages, embeds):
                message = channel.get_partial_message(message_id)
                try:
                    await message.edit(embed=embed)
                except NotFound:
                    await remove_messages()
                    break
            else:
                return

        new_messages = []
        for embed in embeds:
            message = await channel.send(embed=embed)
            new_messages.append(message.id)

        await self.bot.db.set_list(guild, channel, new_messages)


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(Events(bot))
