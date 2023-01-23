import logging
from discord import Guild, Message, User, Member, NotFound
from discord.ext import commands
from facility import Facility
from facility import create_list

guild_logger = logging.getLogger("guild_event")
facility_logger = logging.getLogger("facility_event")


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

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
        """Logs when the bot is remove from a guild

        Args:
            guild (Guild): Guild the bot was remove from
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
        self, facility: Facility, user: User | Member, guild: Guild
    ):
        """Triggered when a facility is created

        Args:
            facility (Facility): Facility that was created
            user (User | Member): User that created
            guild (Guild): Guild command was ran
        """
        facility_logger.info(
            "Facility created by %s with ID: `%s`",
            user.mention,
            facility.id_,
            extra={
                "guild_id": guild.id,
                "guild_name": guild.name,
            },
        )
        await self.update_list(guild)

    @commands.Cog.listener()
    async def on_facility_modify(
        self, facility: Facility, user: User | Member, guild: Guild
    ):
        """Triggered when a facility is modified

        Args:
            facility (Facility): Facility that was modified
            user (User | Member): User that modified
            guild (Guild): Guild command was ran
        """
        facility_logger.info(
            "Facility ID %r modified by %s",
            facility.id_,
            user.mention,
            extra={
                "guild_id": guild.id,
                "guild_name": guild.name,
            },
        )
        await self.update_list(guild)

    @commands.Cog.listener()
    async def on_bulk_facility_delete(
        self, facilities: list[Facility], user: User | Member, guild: Guild
    ):
        """Triggered when multiple facilities are removed

        Args:
            facilities (list[Facility]): Facilities that were removed
            user (User | Member): User that removed them
            guild (Guild): Guild where command was ran
        """
        facility_logger.info(
            "Facility ID(s) %r removed by %s",
            [facility.id_ for facility in facilities],
            user.mention,
            extra={
                "guild_id": guild.id,
                "guild_name": guild.name,
            },
        )
        await self.update_list(guild)

    async def update_list(self, guild: Guild):
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
