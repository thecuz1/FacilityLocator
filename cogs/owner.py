from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .utils.embeds import FeedbackEmbed, FeedbackType
from .utils.views import ResetView


if TYPE_CHECKING:
    from bot import FacilityBot
    from .events import Events


class Owner(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: FacilityBot):
        self.bot: FacilityBot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @commands.command()
    async def list_update(
        self, ctx: commands.Context, guild: discord.Guild = commands.CurrentGuild
    ):
        events_cog: Events | None = self.bot.get_cog("Events")
        if events_cog is None:
            return await ctx.message.add_reaction("❌")
        await events_cog.update_list(guild)
        await ctx.message.add_reaction("✅")

    @commands.command(aliases=["clean"])
    async def clear(self, ctx: commands.Context, limit: int = 1) -> None:
        deleted_count = 0
        async for message in ctx.channel.history(limit=100):
            if message.author == self.bot.user:
                try:
                    await message.delete()
                    deleted_count += 1
                except discord.NotFound:
                    pass
                if deleted_count == limit:
                    break

        if deleted_count:
            embed = FeedbackEmbed(
                f"Deleted {deleted_count} messages", FeedbackType.SUCCESS
            )
        else:
            embed = FeedbackEmbed("No messages deleted", FeedbackType.WARNING)

        await ctx.send(embed=embed, delete_after=5)

    @commands.command()
    async def reset(self, ctx: commands.Context):
        embed = FeedbackEmbed("Confirm removal of all facilities", FeedbackType.WARNING)
        view = ResetView(original_author=ctx.author, timeout=30)
        message = await ctx.send(embed=embed, view=view)
        view.message = message


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(Owner(bot))
