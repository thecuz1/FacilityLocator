from __future__ import annotations

from typing import TYPE_CHECKING
import platform

import discord
from discord.ext import commands
from discord import app_commands, Embed, Colour

from .utils.context import GuildInteraction
from .utils.errors import MessageError
from .utils.embeds import ephemeral_info


if TYPE_CHECKING:
    from bot import FacilityBot


class Misc(commands.Cog):
    def __init__(self, bot: FacilityBot):
        self.bot: FacilityBot = bot

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

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def logs(
        self, interaction: GuildInteraction, ephemeral: bool = False
    ) -> None:
        """View logs for the current guild

        Args:
            ephemeral (bool): Show results to only you. Defaults to False.
        """
        logs = self.bot.guild_logs.get(interaction.guild_id, None)
        if not logs:
            raise MessageError("No logs found", ephemeral=True)

        embed = Embed(title=f"Logs for {interaction.guild.name}", colour=Colour.blue())

        formatted_logs = "> "
        formatted_logs += "\n> ".join(logs)
        embed.description = formatted_logs

        embeds = [embed]

        ephemeral_info_embed = None
        if interaction.namespace.ephemeral is not None:
            pass
        else:
            preference = await self.bot.db.ephemeral_preference(interaction.user.id)
            if preference is None:
                ephemeral_info_embed = await ephemeral_info(self.bot)

            ephemeral = preference or False

        if ephemeral_info_embed:
            embeds.append(ephemeral_info_embed)

        await interaction.response.send_message(embeds=embeds, ephemeral=ephemeral)

    stats = app_commands.Group(
        name="stats",
        description="Stats about the bot",
        guild_only=True,
    )

    @stats.command(name="command")
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def command_stats(
        self, interaction: GuildInteraction, ephemeral: bool = False
    ):
        """Command stats about the bot

        Args:
            ephemeral (bool): Show results to only you. Defaults to False.
        """

        # fmt: off
        make_table=lambda rows,labels=None,centered=False:"".join(["┌"+"┬".join("─"*(max([*(len(str(o)) for o in c),len(str(labels[i])) if labels else 0])+2) for i,c in enumerate(list(zip(*rows))))+"┐\n",("│"+"│".join(f" {str(e).center(k)} "if centered else f" {str(e).ljust(k, ' ')} "for e,k in zip(labels,(max(len(str(o)) for o in [*c,l]) for c,l in zip(list(zip(*rows)),labels))))+"│\n├"+"┼".join("─"*(max([*(len(str(o)) for o in c),len(str(labels[i]))])+2 if labels else 0) for i,c in enumerate(list(zip(*rows))))+"┤\n"if labels else "")+"\n".join("│"+"│".join(f" {str(e).center(l)} "if centered else f" {str(e).ljust(l, ' ')} "for e,l in zip(r, ((max([*(len(str(o)) for o in c),len(str(labels[i])) if labels else 0])) for i,c in enumerate(list(zip(*rows)))))) + "│"for r in rows)+"\n└"+"┴".join("─"*(max([*(len(str(o)) for o in c),len(str(labels[i])) if labels else 0])+2) for i,c in enumerate(list(zip(*rows))))+"┘"])
        # fmt: on

        query = """
            SELECT name, 
                  SUM(CASE WHEN guild_id = ? THEN run_count ELSE 0 END) AS guild_count,
                  SUM(run_count) AS global_count
           FROM command_stats
           GROUP BY name
           ORDER BY name;"""
        rows = await self.bot.db.fetch(query, interaction.guild_id or 0)
        if not rows:
            raise MessageError("No command stats found", ephemeral=True)

        start = "Command Run Counts:```\n"
        table = make_table(
            rows=rows, labels=["command_name", "guild_count", "global_count"]
        )
        embed = Embed(
            description=start + table + "\n```",
            colour=Colour.blue(),
        )

        embeds = [embed]

        ephemeral_info_embed = None
        if interaction.namespace.ephemeral is not None:
            pass
        else:
            preference = await self.bot.db.ephemeral_preference(interaction.user.id)
            if preference is None:
                ephemeral_info_embed = await ephemeral_info(self.bot)

            ephemeral = preference or False

        if ephemeral_info_embed:
            embeds.append(ephemeral_info_embed)

        await interaction.response.send_message(embeds=embeds, ephemeral=ephemeral)


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(Misc(bot))
