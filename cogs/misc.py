import platform

import discord
from discord.ext import commands
from discord import app_commands, Embed, Colour

from bot import FacilityBot
from .utils.context import GuildInteraction
from .utils.errors import MessageError


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
    async def logs(self, interaction: GuildInteraction, ephemeral: bool = True) -> None:
        """View logs for the current guild

        Args:
            ephemeral (bool): Show results to only you (defaults to True)
        """
        logs = self.bot.guild_logs.get(interaction.guild_id, None)
        if not logs:
            raise MessageError("No logs found")

        embed = Embed(title=f"Logs for {interaction.guild.name}", colour=Colour.blue())

        formatted_logs = "> "
        formatted_logs += "\n> ".join(logs)
        embed.description = formatted_logs
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # remove eventually
    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def setup(self, interaction: GuildInteraction):
        """Decommissioned in favor of integrations"""
        await interaction.response.send_message(
            ":x: Decommissioned in favour of `Guild Settings > Integrations > Bots and Apps`",
            ephemeral=True,
        )


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(Misc(bot))
