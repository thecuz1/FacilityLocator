from __future__ import annotations

from typing import TYPE_CHECKING, Optional

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
from .utils.views import DynamicListConfirm
from .utils.errors import MessageError
from .utils.sqlite import AdaptableList


if TYPE_CHECKING:
    from bot import FacilityBot
    from .utils.context import Context, GuildInteraction, ClientInteraction
    from .events import Events


class Config(commands.Cog):
    def __init__(self, bot: FacilityBot):
        self.bot: FacilityBot = bot

    @app_commands.command()
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
                manage_channels=True,
            ),
        }
        try:
            forum = await guild.create_forum(
                "facility list",
                overwrites=overwrites,
            )
        except Forbidden:
            await interaction.response.send_message(
                embed=FeedbackEmbed(
                    "Lack permissions to create forum", FeedbackType.ERROR
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        query = (
            """INSERT OR REPLACE INTO guild_options (guild_id, forum_id) VALUES(?,?)"""
        )
        await self.bot.db.execute(query, guild.id, forum.id)

        tree = self.bot.tree

        toggle_ephemeral_cmd = await tree.get_or_fetch_app_command("toggle_ephemeral")
        create_cmd = await tree.get_or_fetch_app_command("create")
        modify_cmd = await tree.get_or_fetch_app_command("modify")
        view_cmd = await tree.get_or_fetch_app_command("view")
        facility_cmd = await tree.get_or_fetch_app_command("facility")
        locate_cmd = await tree.get_or_fetch_app_command("locate")
        list_cmd = await tree.get_or_fetch_app_command("list")
        remove_ids_cmd = await tree.get_or_fetch_app_command("remove ids")
        remove_ids_cmd = await tree.get_or_fetch_app_command("remove ids")
        remove_facility_cmd = await tree.get_or_fetch_app_command("remove facility")

        embed = Embed(
            title="Commands:",
            description=f"Some of these commands will be visable by default, you can change this behaviour with the command {toggle_ephemeral_cmd and toggle_ephemeral_cmd.mention}",
            colour=Colour.green(),
        )
        embed.add_field(
            name="Create/Modify",
            value=f"""{create_cmd and create_cmd.mention} (Creates a facility and associated thread)
                      {modify_cmd and modify_cmd.mention} (Modifies a facility)""",
            inline=False,
        )
        embed.add_field(
            name="View",
            value=f"""{view_cmd and view_cmd.mention} (Allows multiple IDs)
                      {facility_cmd and facility_cmd.mention} (Displays one facility)
                      {locate_cmd and locate_cmd.mention} (Finds a facility based on search parameters)
                      {list_cmd and list_cmd.mention} (Shows a list of all facilities by region)""",
            inline=False,
        )
        embed.add_field(
            name="Remove",
            value=f"""{remove_ids_cmd and remove_ids_cmd.mention} (Removes a list of facility IDs)
                      {remove_facility_cmd and remove_facility_cmd.mention} (Removes a single facility)""",
            inline=False,
        )

        try:
            help_thread, _ = await forum.create_thread(
                name="How to Use",
                embed=embed,
            )
            await help_thread.edit(pinned=True)
        except Forbidden:
            await interaction.followup.send(
                embed=FeedbackEmbed(
                    "Lack permissions to create threads in forum",
                    FeedbackType.ERROR,
                ),
                ephemeral=True,
            )
            return

        facilities = await self.bot.db.get_facilities({"guild_id = ?": guild.id})
        events: Optional[Events] = self.bot.get_cog("Events")
        if events:
            for facility in facilities:
                await events.handle_forum(facility, guild.id)

        await interaction.followup.send(
            embed=FeedbackEmbed(f"Created forum {forum.mention}", FeedbackType.SUCCESS),
            ephemeral=True,
        )

    @app_commands.command()
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

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.default_permissions(administrator=True)
    async def set_list_channel(
        self, interaction: GuildInteraction, channel: TextChannel | None
    ):
        """Sets list channel to post updates of facilities

        Args:
            channel (TextChannel): Channel to set, defaults to current channel
        """
        selected_channel = channel or interaction.channel

        if not hasattr(selected_channel, "send"):
            raise MessageError("Channel is not supported")

        search_dict = {" guild_id == ? ": interaction.guild_id}

        facility_list = await self.bot.db.get_facilities(search_dict)

        embed = FeedbackEmbed(
            f"Confirm setting {selected_channel.mention} as facility update channel",
            FeedbackType.INFO,
        )
        view = DynamicListConfirm(
            original_author=interaction.user,
            selected_channel=selected_channel,
            facilities=facility_list,
        )
        await view.send(interaction, embed=embed, ephemeral=True)

    response = app_commands.Group(
        name="response",
        description="Response config",
        guild_only=True,
        default_permissions=Permissions(administrator=True),
    )

    @response.command()
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

    @response.command()
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

    @response.command()
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

    @blacklist.command(name="add")
    @commands.is_owner()
    async def blacklist_add(self, ctx: Context, object_id: int, reason: str = ""):
        query = """INSERT OR IGNORE INTO blacklist (object_id, reason) VALUES (?, ?)"""
        await self.bot.db.execute(query, object_id, reason)
        await ctx.send(content=":white_check_mark:")

    @blacklist.command(name="remove")
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
