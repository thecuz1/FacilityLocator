import re
import discord
from discord.ext import commands
from discord import app_commands
from utils.facility import Facility, LocationTransformer, FacilityLocation


class RemoveFacilitiesView(discord.ui.View):
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.primary)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.followup = interaction.followup
        self.stop()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)


class IdTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> tuple:
        delimiters = ' ', '.', ','
        regex_pattern = '|'.join(map(re.escape, delimiters))
        res = re.split(regex_pattern, value)
        return tuple(filter(None, res))


class FacilityInformationModal(discord.ui.Modal, title='Edit Facility Information'):
    def __init__(self, facility) -> None:
        super().__init__()
        self.name = discord.ui.TextInput(label='Facility Name',
                                         default=facility.name)
        self.maintainer = discord.ui.TextInput(label='Maintainer',
                                               default=facility.maintainer)
        self.description = discord.ui.TextInput(label='Description',
                                                style=discord.TextStyle.paragraph,
                                                required=False,
                                                default=facility.description)
        for item in [self.name, self.maintainer, self.description]:
            self.add_item(item)
        self.facility = facility

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.facility.name = str(self.name)
        self.facility.maintainer = str(self.maintainer)
        self.facility.description = str(self.description)

        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed)


class SelectMenu(discord.ui.Select):
    def __init__(self, row: int, placeholder: str, facility: Facility, options: list[discord.SelectOption], vehicle_select: bool) -> None:
        super().__init__(row=row, placeholder=placeholder, options=options, min_values=0, max_values=len(options))
        self.vehicle_select = vehicle_select
        self.facility = facility

    async def callback(self, interaction: discord.Interaction) -> None:
        self.facility.set_services(self.values, self.vehicle_select)
        self.options = self.facility.select_options(self.vehicle_select)
        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed, view=self.view)


class ServicesSelectView(discord.ui.View):
    def __init__(self, facility: Facility) -> None:
        super().__init__()
        self.add_item(SelectMenu(0, 'Select item services...', facility, facility.select_options(False), False))
        self.add_item(SelectMenu(1, 'Select vehicle services...', facility, facility.select_options(True), True))
        self.facility = facility

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label='Add Description/Edit', row=2)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        information = FacilityInformationModal(self.facility)
        await interaction.response.send_modal(information)

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.primary, row=2)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.facility.services <= 0:
            return await interaction.response.send_message(':warning: Please select at least one service', ephemeral=True)

        if self.facility.changed() is False:
            return await interaction.response.send_message(':warning: No changes', ephemeral=True)

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
    @app_commands.rename(name='facility-name', location='region-coordinates', maintainer='maintainer')
    async def create(self, interaction: discord.Interaction, name: str, location: app_commands.Transform[FacilityLocation, LocationTransformer], maintainer: str):
        author_id = interaction.user.id
        facility = Facility(name, location.region, location.coordinates, maintainer, author_id)

        view = ServicesSelectView(facility)
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
        facility = await self.bot.db.get_facility_ids((id,))
        if not facility:
            return await interaction.response.send_message(':x: No facility found', ephemeral=True)

        facility = facility[0]

        if facility.author_id != interaction.user.id:
            return await interaction.response.send_message(':warning: No permission to modify facility ', ephemeral=True)

        view = ServicesSelectView(facility)
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
        author_id = interaction.user.id
        facilities = await self.bot.db.get_facility_ids(ids)
        if not facilities:
            return await interaction.response.send_message(':x: No facilities found', ephemeral=True)

        embed = discord.Embed()
        if len(facilities) < len(ids):
            embed.description = f':warning: Only found {len(facilities)}/{len(ids)} facilities\n'

        removed_facilities = [facilities.pop(index)
                              for index, facilty in enumerate(facilities)
                              if facilty.author_id != author_id]

        def format_facility(facility: list[Facility]) -> str:
            message = '```\n'
            for facilty in facility:
                previous_message = message
                message += f'{facilty.facility_id:3} - {facilty.name}\n'
                if len(message) > 1000:
                    message = previous_message
                    message += 'Truncated entries...'
                    break
            message += '```'
            return message

        if removed_facilities:
            message = format_facility(removed_facilities)
            embed.add_field(name=':x: No permission to delete following facilties',
                            value=message)
        if facilities:
            message = format_facility(facilities)
            embed.add_field(name=':white_check_mark: Permission to delete following facilties',
                            value=message)
        else:
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        view = RemoveFacilitiesView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return

        ids = [(facility.facility_id,) for facility in facilities]
        try:
            await self.bot.db.remove_facilities(ids)
        except Exception as e:
            await view.followup.send(':x: Failed to remove facilities', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfuly removed facilities', ephemeral=True)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
