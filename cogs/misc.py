import platform

from discord.ext import commands
import discord

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


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(Misc(bot))
