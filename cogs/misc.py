from typing import Optional, Literal
from discord.ext import commands
import discord
import platform
from utils import FeedbackEmbed, feedbackType


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def reload(self, ctx, extension):
        try:
            await self.bot.reload_extension(extension)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to reload extension `{extension}`", feedbackType.ERROR, exc
            )
            return await ctx.send(embed=embed)

        embed = FeedbackEmbed(f"Reloaded `{extension}`", feedbackType.SUCCESS)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def load(self, ctx, extension):
        try:
            await self.bot.load_extension(extension)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to load extension `{extension}`", feedbackType.ERROR, exc
            )
            return await ctx.send(embed=embed)

        embed = FeedbackEmbed(f"Loaded `{extension}`", feedbackType.SUCCESS)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def unload(self, ctx, extension):
        try:
            await self.bot.unload_extension(extension)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to unload extension `{extension}`", feedbackType.ERROR, exc
            )
            return await ctx.send(embed=embed)

        embed = FeedbackEmbed(f"Unloaded `{extension}`", feedbackType.SUCCESS)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            embed = FeedbackEmbed(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}",
                feedbackType.SUCCESS,
            )
            return await ctx.send(embed=embed)

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        embed = FeedbackEmbed(
            "Synced the tree to {ret}/{len(guilds)}.", feedbackType.SUCCESS
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
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
                f"Deleted {deleted_count} messages", feedbackType.SUCCESS
            )
            return await ctx.send(embed=embed, delete_after=5)

        embed = FeedbackEmbed("No messages deleted", feedbackType.WARNING)
        await ctx.send(embed=embed, delete_after=5)

    @commands.command()
    @commands.guild_only()
    async def info(self, ctx: commands.Context):
        embed = discord.Embed(title="Bot Information", colour=discord.Colour.blue())
        embed.description = (
            "A simple discord bot to track facilities created in Python using discordpy"
        )
        embed.add_field(name="Discord.py Version", value=discord.__version__)
        embed.add_field(name="Python Version", value=platform.python_version())
        embed.add_field(name="Developer", value="<@195009659793440768>")
        embed.add_field(
            name="Source Code",
            value="[github](https://github.com/thecuz1/FacilityLocator)",
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Misc(bot))
