from discord import Interaction, Embed
from discord.ext import commands
from discord import app_commands
from utils import Paginator
from utils import LocationTransformer, FacilityLocation, IdTransformer
from data import VEHICLE_SERVICES, ITEM_SERVICES


class Query(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.rename(
        location="region",
        item_service="item-service",
        vehicle_service="vehicle-service",
    )
    @app_commands.choices(
        item_service=[
            app_commands.Choice(name=service, value=(1 << index))
            for index, service in enumerate(ITEM_SERVICES)
        ],
        vehicle_service=[
            app_commands.Choice(name=service, value=(1 << index))
            for index, service in enumerate(VEHICLE_SERVICES)
        ],
    )
    async def locate(
        self,
        interaction: Interaction,
        location: app_commands.Transform[FacilityLocation, LocationTransformer] = None,
        item_service: int = None,
        vehicle_service: int = None,
        ephemeral: bool = True,
    ) -> None:
        """Find a facility with optional search parameters

        Args:
            location (app_commands.Transform[FacilityLocation, LocationTransformer], optional): Region to search in
            item_service (int, optional): Item service to look for
            vehicle_service (int, optional): Vehicle service to look for
            ephemeral (bool): Show results to only you (defaults to True)
        """
        region = location and location.region

        search_dict = {
            name: value
            for name, value in (
                (" region == ? ", region),
                (" item_services & ? ", item_service),
                (" vehicle_services & ? ", vehicle_service),
            )
            if value
        }

        facility_list = await self.bot.db.get_facilities(search_dict)

        if not facility_list:
            return await interaction.response.send_message(
                ":x: No facilities found", ephemeral=True
            )
        embeds = [
            facility.embed()
            for facility in facility_list
            if facility.guild_id == interaction.guild_id
        ]
        await Paginator().start(interaction, pages=embeds, ephemeral=ephemeral)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def view(
        self,
        interaction: Interaction,
        ids: app_commands.Transform[tuple, IdTransformer],
        ephemeral: bool = True,
    ):
        """View facilities based on their ID's

        Args:
            ids (app_commands.Transform[tuple, IdTransformer]): List of facility ID's to view with a delimiter of ',' or a space ' ' Ex. 1,3 4 8
            ephemeral (bool): Show results to only you (defaults to True)
        """
        facilities = await self.bot.db.get_facility_ids(ids)
        if not facilities:
            return await interaction.response.send_message(
                ":x: No facilities found", ephemeral=True
            )
        embeds = [
            facility.embed()
            for facility in facilities
            if facility.guild_id == interaction.guild_id
        ]
        await Paginator().start(interaction, pages=embeds, ephemeral=ephemeral)

    @app_commands.command()
    @app_commands.guild_only()
    async def view_logs(
        self,
        interaction: Interaction
    ) -> None:
        logs = self.bot.guild_logs.get(interaction.guild_id, None)
        if not logs:
            return await interaction.response.send_message(':x: No logs found', ephemeral=True)
        embed = Embed(title=f'Logs for {interaction.guild.name}')

        formatted_logs = '> '
        formatted_logs += '\n> '.join(logs)
        embed.description = formatted_logs
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Query(bot))
