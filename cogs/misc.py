from typing import Optional, Literal
from discord.ext import commands
import discord


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def reload(self, ctx, extension):
        try:
            await self.bot.reload_extension(extension)
        except Exception as e:
            await ctx.send(f':x: Failed to reload extension\n```py\n{e}```')
        else:
            await ctx.send(':white_check_mark: Successfully reloaded')

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def load(self, ctx, extension):
        try:
            await self.bot.load_extension(extension)
        except Exception as e:
            await ctx.send(f':x: Failed to load extension\n```py\n{e}```')
        else:
            await ctx.send(':white_check_mark: Successfully loaded')

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def unload(self, ctx, extension):
        try:
            await self.bot.unload_extension(extension)
        except Exception as e:
            await ctx.send(f':x: Failed to unload extension\n```py\n{e}```')
        else:
            await ctx.send(':white_check_mark: Successfully unloaded')

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
      self, ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
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

            await ctx.send(
                f":white_check_mark: Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f":white_check_mark: Synced the tree to {ret}/{len(guilds)}.")

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def cleanup(self, ctx: commands.Context, limit: int = 10) -> None:
        def bot_message(m):
            return m.author == self.bot.user

        deleted = await ctx.channel.purge(limit=limit + 1, check=bot_message, bulk=False)
        if deleted:
            return await ctx.send(f':white_check_mark: Deleted {len(deleted)} messages', delete_after=5)
        await ctx.send(f':warning: No messages deleted', delete_after=5)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Misc(bot))
