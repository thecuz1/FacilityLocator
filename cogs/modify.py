import discord
from discord.ext import commands
from discord import app_commands
from utils import LocationTransformer, FacilityLocation, IdTransformer, MarkerTransformer
from facility import Facility, CreateFacilityView, ModifyFacilityView, RemoveFacilitiesView, ResetView


class Modify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 20, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.rename(name='facility-name', location='region')
    async def create(
        self,
        interaction: discord.Interaction,
        name: app_commands.Range[str, 1, 100],
        location: app_commands.Transform[FacilityLocation, LocationTransformer],
        marker: app_commands.Transform[str, MarkerTransformer],
        maintainer: app_commands.Range[str, 1, 200],
        coordinates: str = None
    ) -> None:
        """Creates a public facility

        Args:
            name (str): Name of facility
            location (app_commands.Transform[FacilityLocation, LocationTransformer]): Region with optional coordinates in the form of region-coordinates from ctrl-click of map
            marker (str): Nearest townhall/relic or location
            maintainer (str): Who maintains the facility
            coordinates (str): Optional coordinates (incase it doesn't work in the region field)
        """
        final_coordinates = coordinates or location.coordinates

        try:
            final_coordinates = final_coordinates.upper()
        except AttributeError:
            pass
        facility = Facility(name=name, region=location.region, coordinates=final_coordinates, maintainer=maintainer, author=interaction.user.id, marker=marker, guild_id=interaction.guild_id)

        view = CreateFacilityView(facility=facility, original_author=interaction.user, bot=self.bot)
        embed = facility.embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.rename(id_='id')
    async def modify(self, interaction: discord.Interaction, id_: int):
        """Modify faciliy information

        Args:
            id_ (int): ID of facility
        """
        facility = await self.bot.db.get_facility_id(id_)

        if facility is None:
            return await interaction.response.send_message(':x: No facility found', ephemeral=True)

        if self.bot.owner_id != interaction.user.id:
            if facility.can_modify(interaction) is False:
                return await interaction.response.send_message(':x: No permission to modify facility', ephemeral=True)

        view = ModifyFacilityView(facility=facility, original_author=interaction.user, bot=self.bot)
        embed = facility.embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def remove(self, interaction: discord.Interaction, ids: app_commands.Transform[tuple, IdTransformer]):
        """Remove facility

        Args:
            ids (app_commands.Transform[tuple, IdTransformer]): List of facility ID's to remove with a delimiter of ',' or a space ' ' Ex. 1,3 4 8
        """
        author = interaction.user
        facilities = await self.bot.db.get_facility_ids(ids)

        if not facilities:
            return await interaction.response.send_message(':x: No facilities found', ephemeral=True)

        embed = discord.Embed()
        if len(facilities) < len(ids):
            embed.description = f':warning: Only found {len(facilities)}/{len(ids)} facilities\n'

        removed_facilities = None
        if self.bot.owner_id != author.id:
            removed_facilities = [facilities.pop(index)
                                  for index, facility in enumerate(facilities[:])
                                  if facility.can_modify(interaction) is False]

        def format_facility(facility: list[Facility]) -> str:
            message = '```\n'
            for facilty in facility:
                previous_message = message
                message += f'{facilty.id_:3} - {facilty.name}\n'
                if len(message) > 1000:
                    message = previous_message
                    message += 'Truncated entries...'
                    break
            message += '```'
            return message

        if removed_facilities:
            message = format_facility(removed_facilities)
            embed.add_field(name=':x: No permission to delete facilties:',
                            value=message)
        if facilities:
            message = format_facility(facilities)
            embed.add_field(name=':white_check_mark: Permission to delete facilties:',
                            value=message)
        else:
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        view = RemoveFacilitiesView(original_author=author, bot=self.bot, facilities=facilities)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def reset(self, ctx: commands.Context):
        embed = discord.Embed(title=':warning: Confirm removal of all facilities')
        view = ResetView(original_author=ctx.author, timeout=30, bot=self.bot)
        message = await ctx.send(embed=embed, view=view)
        view.message = message


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
