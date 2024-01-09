from __future__ import annotations

import logging
import itertools
from typing import TYPE_CHECKING
from rapidfuzz import process

from discord import (
    Guild,
    Message,
    NotFound,
    Embed,
    Colour,
    ForumChannel,
    Thread,
    Forbidden,
    Object,
)
from discord.ext import commands

from .utils.embeds import create_list
from .utils.cost import Building, Cost, building_data


if TYPE_CHECKING:
    from bot import FacilityBot
    from discord.app_commands import Command, ContextMenu

    from .utils.facility import Facility
    from .utils.context import GuildInteraction, ClientInteraction


guild_logger = logging.getLogger("guild_event")
facility_logger = logging.getLogger("facility_event")


def generate_message(building: Building):
    def format_cost(cost: Cost):
        item_texts = []
        for key, value in cost.items():
            item_texts.append(f"**{value}x {key}**")
        return ", ".join(item_texts)

    embed = Embed(title=building.name, colour=Colour.blue())

    final_description = format_cost(building.cost)
    if building.parent:
        final_description += f"\n\nParent (**{building.parent.name}**) cost: {format_cost(building.parent.cost)}"
        final_description += f"\n\nTotal cost: {format_cost(building.total_cost())}"

    embed.description = final_description
    return embed


def process_response(user_input: str):
    choice = process.extractOne(user_input, building_data.keys(), score_cutoff=80)
    if choice:
        building = building_data[choice[0]]
        return generate_message(building)
    return None


class Events(commands.Cog):
    def __init__(self, bot: FacilityBot) -> None:
        self.bot: FacilityBot = bot

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, interaction: ClientInteraction, command: Command | ContextMenu
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
        elif message.content.lower().startswith("how much does"):
            if not message.guild:
                return

            query = """SELECT channel_ids from response WHERE guild_id = ?"""
            channel_row = await self.bot.db.fetch_one(query, message.guild.id)
            if not channel_row:
                return

            channel_ids: list[int] = channel_row[0]
            if message.channel.id not in channel_ids:
                return

            user_input = message.content[13:].strip()
            output = process_response(user_input)
            if output:
                await message.channel.send(embed=output, reference=message)

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
        await self.handle_forum(facility, ctx.guild_id)
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
        await self.handle_forum(after, ctx.guild_id)
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
        for facility in facilities:
            await self.handle_forum(facility, ctx.guild_id, True)
        await self.update_list(ctx.guild)

    async def update_list(self, guild: Guild) -> None:
        list_location = await self.bot.db.get_list(guild)
        if not list_location:
            return

        search_dict = {" guild_id == ? ": guild.id}
        facilities: list[Facility] = await self.bot.db.get_facilities(search_dict)

        channel_id, messages = list_location
        embeds = await create_list(facilities, guild, self.bot)

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

        # TODO: Rework this
        if not isinstance(channel, Thread):
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
                    except Forbidden:
                        break
                else:
                    return

            new_messages = []
            for embed in embeds:
                message = await channel.send(embed=embed)
                new_messages.append(message.id)

            return await self.bot.db.set_list(guild, channel, new_messages)
        else:
            new_messages = []
            for embed, message_id in itertools.zip_longest(
                embeds, messages, fillvalue=None
            ):
                if message_id is None:
                    new_message = await channel.send(embed=embed)
                    new_messages.append(new_message)
                    continue

                message = channel.get_partial_message(message_id)
                if embed is None:
                    await message.delete()
                    continue
                try:
                    await message.edit(embed=embed)
                    new_messages.append(message.id)
                except (NotFound, Forbidden):
                    return

            return await self.bot.db.set_list(guild, channel, new_messages)

    async def handle_forum(
        self, facility: Facility, guild_id: int, delete: bool = False
    ) -> None:
        query = """SELECT forum_id FROM guild_options WHERE guild_id == ?"""
        forum_tuple = await self.bot.db.fetch_one(query, guild_id)
        if not len(forum_tuple) > 0:
            return
        forum_id = forum_tuple[0]
        forum = self.bot.get_channel(forum_id)
        if not isinstance(forum, ForumChannel):
            return

        thread = forum.get_thread(facility.thread_id or 0)
        if delete:
            facility.thread_id = None
            if thread is None:
                return
            return await thread.delete()
        if thread is None:
            thread, _ = await forum.create_thread(
                name=f"{facility.name} - {facility.marker}, {facility.region}",
                embeds=facility.embeds(),
            )
            try:
                await thread.add_user(Object(facility.author))
            except Forbidden:
                pass
            facility.thread_id = thread.id
            await self.bot.db.update_facility(facility)
        else:
            updated_name = f"{facility.name} - {facility.marker}, {facility.region}"
            if thread.name != updated_name:
                await thread.edit(name=updated_name)

            message = thread.starter_message
            if not message:
                message = await thread.fetch_message(thread.id)
            await message.edit(
                embeds=facility.embeds(),
            )


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(Events(bot))
