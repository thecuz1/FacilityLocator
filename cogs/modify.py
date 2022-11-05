from datetime import datetime
from typing import Optional
from rapidfuzz.process import extract
import discord
from discord.ext import commands
from discord import app_commands
from utils import Facility, LocationTransformer, FacilityLocation, IdTransformer
from data import REGIONS


async def label_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice]:
    for region in REGIONS:
        try:
            if region in interaction.namespace['region']:
                selected_region = region
                break
        except KeyError:
            break
    try:
        location_list = [marker for region, markers in REGIONS.items() for marker in markers if selected_region == region]
    except NameError:
        location_list = [marker for markers in REGIONS.values() for marker in markers]

    res = extract(current, location_list, limit=25)
    return [app_commands.Choice(name=choice[0], value=choice[0])
            for choice in res]


class RemoveFacilitiesView(discord.ui.View):
    def __init__(self, *, timeout: Optional[float] = 180, original_author: discord.User | discord.Member) -> None:
        super().__init__(timeout=timeout)
        self.original_author = original_author

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.errors.NotFound:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.original_author.id

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.primary)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.followup = interaction.followup
        self.stop()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)


class FacilityInformationModal(discord.ui.Modal, title='Edit Facility Information'):
    def __init__(self, facility) -> None:
        super().__init__()
        self.name = discord.ui.TextInput(label='Facility Name',
                                         default=facility.name,
                                         max_length=100)
        self.maintainer = discord.ui.TextInput(label='Maintainer',
                                               default=facility.maintainer,
                                               max_length=200)
        self.description = discord.ui.TextInput(label='Description',
                                                style=discord.TextStyle.paragraph,
                                                required=False,
                                                default=facility.description,
                                                max_length=1024)
        for item in (self.name, self.maintainer, self.description):
            self.add_item(item)
        self.facility = facility

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.facility.name = str(self.name)
        self.facility.maintainer = str(self.maintainer)
        self.facility.description = str(self.description)

        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed)


class SelectMenu(discord.ui.Select):
    def __init__(self, row: int, placeholder: str, facility: Facility, vehicle_select: bool) -> None:
        options = facility.select_options(vehicle_select)
        super().__init__(row=row, placeholder=placeholder, options=options, min_values=0, max_values=len(options))
        self.vehicle_select = vehicle_select
        self.facility = facility

    async def callback(self, interaction: discord.Interaction) -> None:
        self.facility.set_services(self.values, self.vehicle_select)
        self.options = self.facility.select_options(self.vehicle_select)
        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed, view=self.view)


class ServicesSelectView(discord.ui.View):
    def __init__(self, facility: Facility, original_author: discord.User | discord.Member) -> None:
        super().__init__()
        self.add_item(SelectMenu(0, 'Select item services...', facility, False))
        self.add_item(SelectMenu(1, 'Select vehicle services...', facility, True))
        self.facility = facility
        self.original_author = original_author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.original_author.id

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.errors.NotFound:
            pass

    @discord.ui.button(label='Add Description/Edit', row=2)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        information = FacilityInformationModal(self.facility)
        await interaction.response.send_modal(information)

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.primary, row=2)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.facility.item_services is None and self.facility.vehicle_services is None:
            return await interaction.response.send_message(':warning: Please select at least one service', ephemeral=True)

        if self.facility.changed() is False:
            return await interaction.response.send_message(':warning: No changes', ephemeral=True)

        dt = datetime.now()
        self.facility.creation_time = datetime.timestamp(dt)
        self.followup = interaction.followup
        self.stop()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)


class Modify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.autocomplete(location=label_autocomplete)
    @app_commands.rename(name='facility-name', gps='region', maintainer='maintainer')
    async def create(self, interaction: discord.Interaction, name: app_commands.Range[str, 1, 100], gps: app_commands.Transform[FacilityLocation, LocationTransformer], location: str, maintainer: app_commands.Range[str, 1, 200], coordinates: str = None):
        """Creates a public facility

        Args:
            name (str): Name of facility
            gps (app_commands.Transform[FacilityLocation, LocationTransformer]): Region with optional coordinates
            location (str): Nearest townhall/relic or location
            maintainer (str): Who maintains the facility
            coordinates (str): Optional coordinates (incase it doesn't work in the region field)
        """
        resolved_marker = None
        for marker_tuple in REGIONS.values():
            for marker in marker_tuple:
                if location.lower() in marker.lower():
                    resolved_marker = marker
                    break

        if resolved_marker is None:
            return await interaction.response.send_message(':x: No marker found', ephemeral=True)

        if gps.coordinates is None:
            final_coordinates = coordinates
        else:
            final_coordinates = gps.coordinates

        try:
            final_coordinates = final_coordinates.upper()
        except AttributeError:
            pass
        facility = Facility(name=name, region=gps.region, coordinates=final_coordinates, maintainer=maintainer, author=interaction.user.id, marker=resolved_marker, guild_id=interaction.guild_id)

        view = ServicesSelectView(facility, original_author=interaction.user)
        embed = facility.embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return

        try:
            await self.bot.db.add_facility(facility)
        except Exception as e:
            await view.followup.send(':x: Failed to add facility', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfully added facility', ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    async def modify(self, interaction: discord.Interaction, id: int):
        """Modify faciliy information

        Args:
            id_ (int): ID of facility
        """
        facility = await self.bot.db.get_facility_ids((id,))

        try:
            facility = facility[0]
        except TypeError:
            return await interaction.response.send_message(':x: No facility found', ephemeral=True)

        if self.bot.owner_id != interaction.user.id:
            if facility.author != interaction.user.id:
                return await interaction.response.send_message(':warning: No permission to modify facility ', ephemeral=True)

        view = ServicesSelectView(facility, original_author=interaction.user)
        embed = facility.embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return

        try:
            await self.bot.db.update_facility(facility)
        except Exception as e:
            await view.followup.send(':x: Failed to modify facility', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfully modified facility', ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    async def remove(self, interaction: discord.Interaction, ids: app_commands.Transform[tuple, IdTransformer]):
        """Remove facility

        Args:
            ids (app_commands.Transform[tuple, IdTransformer]): List of facility ID's to remove
        """
        author = interaction.user.id
        facilities = await self.bot.db.get_facility_ids(ids)
        if not facilities:
            return await interaction.response.send_message(':x: No facilities found', ephemeral=True)

        embed = discord.Embed()
        if len(facilities) < len(ids):
            embed.description = f':warning: Only found {len(facilities)}/{len(ids)} facilities\n'

        removed_facilities = None
        if self.bot.owner_id != author:
            removed_facilities = [facilities.pop(index)
                                  for index, facilty in enumerate(facilities[:])
                                  if facilty.author != author]

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

        view = RemoveFacilitiesView(original_author=interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return

        ids = [(facility.id_,) for facility in facilities]
        try:
            await self.bot.db.remove_facilities(ids)
        except Exception as e:
            await view.followup.send(':x: Failed to remove facilities', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfuly removed facilities', ephemeral=True)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def remove_all(self, ctx: commands.Context):
        embed = discord.Embed(title=':warning: Confirm removal of all facilities')
        view = RemoveFacilitiesView(original_author=ctx.author)
        message = await ctx.send(embed=embed, view=view, ephemeral=True)
        view.message = message

        if await view.wait():
            return

        try:
            await self.bot.db.reset()
        except Exception as e:
            await view.followup.send(':x: Failed to remove facilities', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfuly removed facilities', ephemeral=True)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
