import logging
from datetime import datetime
from typing import Optional
from asyncio import sleep
import discord
from discord.ext import commands
from discord import app_commands
from utils import Facility, LocationTransformer, FacilityLocation, IdTransformer, MarkerTransformer
from data import ITEM_SERVICES, VEHICLE_SERVICES

facility_logger = logging.getLogger('facility_event')


class RemoveFacilitiesView(discord.ui.View):
    def __init__(self, *, timeout: Optional[float] = 180, original_author: discord.User | discord.Member) -> None:
        super().__init__(timeout=timeout)
        self.original_author = original_author

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.delete()
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
        self.name = discord.ui.TextInput(
            label='Facility Name',
            default=facility.name,
            max_length=100
        )
        self.maintainer = discord.ui.TextInput(
            label='Maintainer',
            default=facility.maintainer,
            max_length=200
        )
        self.description = discord.ui.TextInput(
            label='Description',
            style=discord.TextStyle.paragraph,
            required=False,
            default=facility.description,
            max_length=1024
        )
        for item in (self.name, self.maintainer, self.description):
            self.add_item(item)
        self.facility = facility

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.facility.name = str(self.name)
        self.facility.maintainer = str(self.maintainer)
        self.facility.description = str(self.description)

        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed)


class ServicesSelectView(discord.ui.View):
    def __init__(self, facility: Facility, original_author: discord.User | discord.Member) -> None:
        super().__init__()
        self.facility = facility
        self.original_author = original_author
        self._update_options()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id in (interaction.client.owner_id, self.original_author.id):
            return True
        await interaction.response.send_message(':x: This menu cannot be controlled by you, sorry!', ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.errors.NotFound:
            pass

    def _update_options(self) -> None:
        self.item_select.options = self.facility.select_options(False)
        self.vehicle_select.options = self.facility.select_options(True)

    @discord.ui.select(placeholder='Select item services...', max_values=len(ITEM_SERVICES))
    async def item_select(self, interaction: discord.Interaction, menu: discord.ui.Select) -> None:
        self.facility.set_services(menu.values, False)
        self._update_options()
        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(placeholder='Select vehicle services...', max_values=len(VEHICLE_SERVICES))
    async def vehicle_select(self, interaction: discord.Interaction, menu: discord.ui.Select) -> None:
        self.facility.set_services(menu.values, True)
        self._update_options()
        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Add Description/Edit')
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        information = FacilityInformationModal(self.facility)
        await interaction.response.send_modal(information)

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.primary)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.facility.item_services == 0 and self.facility.vehicle_services == 0:
            return await interaction.response.send_message(':warning: Please select at least one service', ephemeral=True)

        if self.facility.changed() is False:
            return await interaction.response.send_message(':warning: No changes', ephemeral=True)

        if self.facility.creation_time is None:
            dt = datetime.now()
            self.facility.creation_time = int(datetime.timestamp(dt))

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

        view = ServicesSelectView(facility, original_author=interaction.user)
        embed = facility.embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return

        try:
            await self.bot.db.add_facility(facility)
            facility_logger.info(
                'Facility created by %r',
                interaction.user.mention,
                extra={
                    'guild_id': interaction.guild_id,
                    'guild_name': interaction.guild.name
                }
            )
        except Exception as e:
            await view.followup.send(':x: Failed to create facility', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfully created facility', ephemeral=True)

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

        view = ServicesSelectView(facility, original_author=interaction.user)
        embed = facility.embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return

        try:
            await self.bot.db.update_facility(facility)
            facility_logger.info(
                'Facility ID %r modified by %r',
                facility.id_,
                interaction.user.mention,
                extra={
                    'guild_id': interaction.guild_id,
                    'guild_name': interaction.guild.name
                }
            )
        except Exception as e:
            await view.followup.send(':x: Failed to modify facility', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfully modified facility', ephemeral=True)

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

        view = RemoveFacilitiesView(original_author=author)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return

        try:
            await self.bot.db.remove_facilities(facilities)
            facility_logger.info(
                'Facility ID(s) %r removed by %r',
                [facility.id_ for facility in facilities],
                interaction.user.mention,
                extra={
                    'guild_id': interaction.guild_id,
                    'guild_name': interaction.guild.name
                }
            )
        except Exception as e:
            await view.followup.send(':x: Failed to remove facilities', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfuly removed facilities', ephemeral=True)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def reset(self, ctx: commands.Context):
        embed = discord.Embed(title=':warning: Confirm removal of all facilities')
        view = RemoveFacilitiesView(original_author=ctx.author, timeout=30)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

        if await view.wait():
            return

        try:
            await self.bot.db.reset()
        except Exception as e:
            await view.followup.send(':x: Failed to remove facilities', ephemeral=True)
            raise e
        else:
            message = await view.followup.send(':white_check_mark: Successfuly removed facilities', wait=True)
            await sleep(10)
            await view.message.delete()
            await message.delete()


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
