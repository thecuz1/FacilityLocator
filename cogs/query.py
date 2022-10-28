import discord
from discord.ext import commands
from discord import app_commands
import Paginator
from utils.facility import LocationTransformer, FacilityLocation


class Query(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.rename(location='region')
    async def locate(self, interaction: discord.Interaction, location: app_commands.Transform[FacilityLocation, LocationTransformer]):
        facility_list = await self.bot.db.get_facility(location.region)
        if not facility_list:
            return await interaction.response.send_message(':x: No facilities in requested region', ephemeral=True)
        embeds = [facility.embed()
                  for facility in facility_list]
        await Paginator.Simple().start(interaction, pages=embeds)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Query(bot))
