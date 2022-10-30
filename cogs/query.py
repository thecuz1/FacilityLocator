from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
import Paginator
from utils.enums import Service, VehicleService
from utils.facility import LocationTransformer, FacilityLocation


class Query(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.rename(location='region')
    @app_commands.choices(service=[app_commands.Choice(name=service.value, value=(1 << index))
                                   for index, service in enumerate(Service)],
                          vehicle_service=[app_commands.Choice(name=service.value, value=(1 << index))
                                           for index, service in enumerate(VehicleService)])
    async def locate(self, interaction: discord.Interaction, location: app_commands.Transform[FacilityLocation, LocationTransformer], service: Optional[int] = 0, vehicle_service: Optional[int] = 0):
        facility_list = await self.bot.db.get_facility(location.region, service, vehicle_service)
        if not facility_list:
            return await interaction.response.send_message(':x: No facilities in requested region', ephemeral=True)
        embeds = [facility.embed()
                  for facility in facility_list]
        await Paginator.Simple().start(interaction, pages=embeds)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Query(bot))
