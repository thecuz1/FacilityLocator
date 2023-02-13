import copy
import io
import textwrap
import traceback
from typing import Any, Optional, Literal
from contextlib import redirect_stdout

import discord
from discord.ext import commands
from discord import Embed, Colour

from bot import FacilityBot
from . import EXTENSIONS
from .utils.embeds import FeedbackEmbed, FeedbackType
from .utils.views import ResetView


class Owner(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: FacilityBot):
        self.bot: FacilityBot = bot
        self._last_result: Optional[Any] = None

    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    async def _reload_or_load_extension(self, extension: str) -> None:
        try:
            await self.bot.reload_extension(extension)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(extension)

    @commands.group(invoke_without_command=True)
    async def reload(self, ctx: commands.Context, extension):
        try:
            await self.bot.reload_extension(extension)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to reload extension `{extension}`", FeedbackType.ERROR, exc
            )
            return await ctx.send(embed=embed)

        embed = FeedbackEmbed(f"Reloaded `{extension}`", FeedbackType.SUCCESS)
        await ctx.send(embed=embed)

    @reload.command(name="all")
    async def _reload_all(self, ctx: commands.Context):
        statuses = []
        for extension in EXTENSIONS:
            try:
                await self._reload_or_load_extension(extension)
            except Exception:
                statuses.append((":x:", extension))
            else:
                statuses.append((":white_check_mark:", extension))

        embed = Embed(
            colour=Colour.blue(),
            description="\n".join(
                f"{status}: `{module}`" for status, module in statuses
            ),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def load(self, ctx: commands.Context, extension):
        try:
            await self.bot.load_extension(extension)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to load extension `{extension}`", FeedbackType.ERROR, exc
            )
            return await ctx.send(embed=embed)

        embed = FeedbackEmbed(f"Loaded `{extension}`", FeedbackType.SUCCESS)
        await ctx.send(embed=embed)

    @commands.command()
    async def unload(self, ctx: commands.Context, extension):
        try:
            await self.bot.unload_extension(extension)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to unload extension `{extension}`", FeedbackType.ERROR, exc
            )
            return await ctx.send(embed=embed)

        embed = FeedbackEmbed(f"Unloaded `{extension}`", FeedbackType.SUCCESS)
        await ctx.send(embed=embed)

    @commands.command()
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
                FeedbackType.SUCCESS,
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
            "Synced the tree to {ret}/{len(guilds)}.", FeedbackType.SUCCESS
        )
        await ctx.send(embed=embed)

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

    @commands.command()
    async def sudo(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel],
        who: discord.Member | discord.User,
        *,
        command: str,
    ):
        """Run a command as another user optionally in another channel."""
        msg = copy.copy(ctx.message)
        new_channel = channel or ctx.channel
        msg.channel = new_channel
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)

    def cleanup_code(self, content: str) -> str:
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    @commands.command(name="eval")
    async def _eval(self, ctx: commands.Context, *, body: str):
        """Evaluates code"""

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self._last_result,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as exc:
            return await ctx.send(f"```py\n{exc.__class__.__name__}: {exc}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("\u2705")
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f"```py\n{value}\n```")
            else:
                self._last_result = ret
                await ctx.send(f"```py\n{value}{ret}\n```")


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(Owner(bot))
