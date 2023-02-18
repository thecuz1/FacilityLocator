from discord import app_commands, TextChannel
from discord.ext import commands

from bot import FacilityBot
from .utils.context import Context, GuildInteraction, ClientInteraction
from .utils.embeds import FeedbackEmbed, FeedbackType
from .utils.views import DynamicListConfirm
from .utils.errors import MessageError


class Config(commands.Cog):
    def __init__(self, bot: FacilityBot):
        self.bot: FacilityBot = bot

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

        if not isinstance(selected_channel, TextChannel):
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
