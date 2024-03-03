from __future__ import annotations

from typing import TYPE_CHECKING

from discord import (
    app_commands,
    TextChannel,
    Permissions,
    Embed,
    Colour,
    PermissionOverwrite,
    Forbidden,
)
from discord.ext import commands

from .utils.embeds import FeedbackEmbed, FeedbackType
from .utils.views import SetDynamicList, create_list
from .utils.errors import MessageError
from .utils.sqlite import AdaptableList
from .events import Events


if TYPE_CHECKING:
    from bot import FacilityBot
    from .utils.context import Context, GuildInteraction, ClientInteraction


class Config(commands.Cog):
    def __init__(self, bot: FacilityBot):
        self.bot: FacilityBot = bot

    @app_commands.command()  # type: ignore[arg-type]
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.default_permissions(administrator=True)
    async def create_fourm(self, interaction: GuildInteraction):
        """Creates fourm channel to list facilities"""
        guild = interaction.guild

        overwrites = {
            guild.default_role: PermissionOverwrite(
                send_messages=False, read_messages=False, send_messages_in_threads=True
            ),
            guild.me: PermissionOverwrite(
                send_messages=True,
                read_messages=True,
                send_messages_in_threads=True,
                manage_channels=True,
                read_message_history=True,
            ),
        }
        try:
            forum = await guild.create_forum(
                "facility list",
                overwrites=overwrites,
            )
        except Forbidden:
            return await interaction.response.send_message(
                embed=FeedbackEmbed(
                    "Lack permissions to create forum", FeedbackType.ERROR
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        query = (
            """INSERT OR REPLACE INTO guild_options (guild_id, forum_id) VALUES(?,?)"""
        )
        await self.bot.db.execute(query, guild.id, forum.id)

        facilities = await self.bot.db.get_facilities({"guild_id = ?": guild.id})

        events = self.bot.get_cog("Events")
        if events is not None and isinstance(events, Events):
            for facility in facilities:
                await events.handle_forum(facility, guild.id)

        facility_list = await create_list(
            facilities, interaction.guild, interaction.client
        )
        initial_embed = facility_list.pop(0)
        try:
            thread, message = await forum.create_thread(
                name="Index", embed=initial_embed
            )
        except Forbidden:
            embed = FeedbackEmbed(
                "No permission to manage forum, must have `Manage Posts`",
                FeedbackType.ERROR,
            )
            return await interaction.followup.send(embed=embed)

        messages = [message.id]

        await thread.edit(locked=True, pinned=True)
        for embed in facility_list:
            message = await thread.send(embed=embed)
            messages.append(message.id)

        try:
            await interaction.client.db.set_list(interaction.guild, thread, messages)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to set list channel\n```py\n{exc}\n```", FeedbackType.ERROR
            )
            await interaction.followup.send(embed=embed)
            raise exc

        await interaction.followup.send(
            embed=FeedbackEmbed(f"Created forum {forum.mention}", FeedbackType.SUCCESS),
            ephemeral=True,
        )

    @app_commands.command()  # type: ignore[arg-type]
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def toggle_ephemeral(self, interaction: ClientInteraction):
        """Toggles user preference for ephemeral messages"""
        query = """SELECT ephemeral FROM user_options WHERE user_id = ?"""
        current_choice_row = await self.bot.db.fetch_one(query, interaction.user.id)
        if not current_choice_row:
            current_choice = False
        else:
            current_choice = current_choice_row[0]

        new_choice = not current_choice
        query = """INSERT OR REPLACE INTO user_options VALUES (?,?)"""
        current_choice_row = await self.bot.db.execute(
            query, interaction.user.id, new_choice
        )

        if new_choice is True:
            await interaction.response.send_message(
                ":white_check_mark: Ephemeral messages have been **enabled** by default",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ":white_check_mark: Ephemeral messages have been **disabled** by default",
                ephemeral=True,
            )

    @app_commands.command()  # type: ignore[arg-type]
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.default_permissions(administrator=True)
    async def set_list_channel(self, interaction: GuildInteraction):
        """Sets list channel to post updates of facilities

        Args:
            channel (TextChannel): Channel to set, defaults to current channel
        """
        search_dict = {" guild_id == ? ": interaction.guild_id}
        facility_list = await self.bot.db.get_facilities(search_dict)
        forum_row = await self.bot.db.fetch_one(
            """SELECT forum_id FROM guild_options WHERE guild_id = ?""",
            interaction.guild_id,
        )
        forum = forum_row[0] if forum_row else None

        embed = FeedbackEmbed(
            "Choose to display list in the forum (button will disable if not setup) or in a normal channel",
            FeedbackType.INFO,
        )
        view = SetDynamicList(
            original_author=interaction.user, facilities=facility_list, forum_id=forum
        )
        await view.send(interaction, embed=embed, ephemeral=True)

    response = app_commands.Group(
        name="response",
        description="Response config",
        guild_only=True,
        default_permissions=Permissions(administrator=True),
    )

    @response.command()  # type: ignore[arg-type]
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def add(self, interaction: GuildInteraction, channel: TextChannel):
        """Adds channel to respond to questions

        Args:
            channel (TextChannel): Channel to add
        """
        query = """SELECT channel_ids from response WHERE guild_id = ?"""
        previous_ids = await self.bot.db.fetch_one(query, interaction.guild_id)

        if previous_ids:
            channel_list: list = previous_ids[0]
            channel_list.append(channel.id)
        else:
            channel_list = [channel.id]

        query = """INSERT OR REPLACE INTO response VALUES (?,?)"""
        await self.bot.db.execute(
            query, interaction.guild_id, AdaptableList(channel_list)
        )
        await interaction.response.send_message(":white_check_mark:")

    @response.command()  # type: ignore[arg-type]
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def remove(self, interaction: GuildInteraction, channel: TextChannel):
        """removes channel from responding to questions

        Args:
            channel (TextChannel): Channel to remove
        """
        query = """SELECT channel_ids from response WHERE guild_id = ?"""
        previous_ids = await self.bot.db.fetch_one(query, interaction.guild_id)

        if previous_ids:
            channel_list: list = previous_ids[0]
            try:
                channel_list.remove(channel.id)
            except ValueError:
                pass

            if channel_list:
                query = """INSERT OR REPLACE INTO response VALUES (?,?)"""
                await self.bot.db.execute(
                    query, interaction.guild_id, AdaptableList(channel_list)
                )
            else:
                query = """DELETE FROM response WHERE guild_id = ?"""
                await self.bot.db.execute(query, interaction.guild_id)
        await interaction.response.send_message(":white_check_mark:")

    @response.command()  # type: ignore[arg-type]
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def list(self, interaction: GuildInteraction):
        """lists channels responding to questions"""
        query = """SELECT channel_ids from response WHERE guild_id = ?"""
        channel_row = await self.bot.db.fetch_one(query, interaction.guild_id)
        if not channel_row:
            raise MessageError("No channels set")
        channel_ids: list[int] = channel_row[0]

        embed = Embed(colour=Colour.blurple())
        items = []
        for index, entry in enumerate(channel_ids):
            items.append(f"{index + 1}. <#{entry}>")

        embed.description = "\n".join(items)
        await interaction.response.send_message(embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def blacklist(self, ctx: Context, object_id: int):
        query = """SELECT * FROM blacklist WHERE object_id = ?;"""
        rows = await self.bot.db.fetch(query, object_id)
        await ctx.send(rows)

    @blacklist.command(name="add")  # type: ignore[arg-type]
    @commands.is_owner()
    async def blacklist_add(self, ctx: Context, object_id: int, reason: str = ""):
        query = """INSERT OR IGNORE INTO blacklist (object_id, reason) VALUES (?, ?)"""
        await self.bot.db.execute(query, object_id, reason)
        await ctx.send(content=":white_check_mark:")

    @blacklist.command(name="remove")  # type: ignore[arg-type]
    @commands.is_owner()
    async def blacklist_remove(self, ctx: Context, object_id: int):
        query = """DELETE FROM blacklist WHERE object_id = ?"""
        await self.bot.db.execute(query, object_id)
        await ctx.send(content=":white_check_mark:")

    async def is_blacklisted(self, entity_id: int) -> bool:
        query = """SELECT 1 FROM blacklist WHERE object_id = ?"""
        result = await self.bot.db.fetch(
            query,
            entity_id,
        )
        return bool(result)

    async def blacklist_interaction_check(self, interaction: ClientInteraction) -> bool:
        is_owner = await interaction.client.is_owner(interaction.user)
        if is_owner:
            return True

        for check_entity in (
            interaction.user.id,
            interaction.guild and interaction.guild.id,
        ):
            if check_entity:
                result = await self.is_blacklisted(check_entity)
                if result:
                    return False

        return True

    async def cog_load(self) -> None:
        tree = self.bot.tree
        tree.interaction_check = self.blacklist_interaction_check

    async def cog_unload(self) -> None:
        tree = self.bot.tree
        tree.interaction_check = tree.__class__.interaction_check

    async def bot_check_once(self, ctx: Context) -> bool:
        is_owner = await ctx.bot.is_owner(ctx.author)
        if is_owner:
            return True

        for check_entity in (ctx.author.id, ctx.guild and ctx.guild.id):
            if check_entity:
                result = await self.is_blacklisted(check_entity)
                if result:
                    return False

        return True


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(Config(bot))
