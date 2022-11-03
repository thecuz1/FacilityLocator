from discord import Interaction
from discord.ext import commands
from discord import app_commands
import Paginator
from utils import LocationTransformer, FacilityLocation
from data import VEHICLE_SERVICES, ITEM_SERVICES


class Query(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.rename(location='region', item_service='item-service', vehicle_service='vehicle-service')
    @app_commands.choices(item_service=[app_commands.Choice(name=service, value=(1 << index))
                                   for index, service in enumerate(ITEM_SERVICES)],
                          vehicle_service=[app_commands.Choice(name=service, value=(1 << index))
                                           for index, service in enumerate(VEHICLE_SERVICES)])
    async def locate(self, interaction: Interaction, location: app_commands.Transform[FacilityLocation, LocationTransformer] = None, item_service: int = None, vehicle_service: int = None) -> None:
        """Find a facility with optional search parameters

        Args:
            location (app_commands.Transform[FacilityLocation, LocationTransformer], optional): Region to search in
            item_service (int, optional): Item service to look for
            vehicle_service (int, optional): Vehicle service to look for
        """
        try:
            facility_list = await self.bot.db.get_facility(location.region, item_service, vehicle_service)
        except AttributeError:
            facility_list = await self.bot.db.get_facility(service=item_service, vehicle_service=vehicle_service)
        if not facility_list:
            return await interaction.response.send_message(':x: No facilities found', ephemeral=True)
        embeds = [facility.embed()
                  for facility in facility_list]
        await Paginator.Simple().start(interaction, pages=embeds)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Query(bot))
