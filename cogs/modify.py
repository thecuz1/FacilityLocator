from dataclasses import dataclass
from typing import NamedTuple
import re
from copy import deepcopy
import discord
from discord.ext import commands
from discord import app_commands
from utils.enums import Service, Region


class FacilityLocation(NamedTuple):
    region: str
    coordinates: str


@dataclass
class Facility:
    name: str
    location: FacilityLocation
    maintainer: str
    services: int = 0
    description: str = ''


class RegionTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str):
        try:
            coordinates = re.search(
                r'([A-R]\d{1,2}k\d)', value, flags=re.IGNORECASE).group(1)
        except AttributeError:
            coordinates = ''

        region = None
        for name, member in Region.__members__.items():
            if name in value or member.value in value:
                region = name
                break
        if region is None:
            await interaction.response.send_message(':x: No region found', ephemeral=True)
            raise ValueError('Incorrect region passed')
        return FacilityLocation(region, coordinates)

    async def autocomplete(self, interaction: discord.Interaction, current):
        choice_list = [app_commands.Choice(name=member.value, value=name)
                       for name, member in Region.__members__.items() if current.lower() in member.value.lower()]
        if len(choice_list) > 25:
            choice_list = choice_list[0:25]
        return choice_list


class FacilityInformationModal(discord.ui.Modal, title='Edit Facility Information'):
    name = discord.ui.TextInput(label='Facility Name')
    maintainer = discord.ui.TextInput(label='Maintainer')
    description = discord.ui.TextInput(label='Description',
                                       style=discord.TextStyle.paragraph,
                                       required=False)

    def __init__(self, facility):
        super().__init__()
        self.facility = facility
        self.name.default = facility.name
        self.maintainer.default = facility.maintainer
        self.description.default = facility.description

    async def on_submit(self, interaction: discord.Interaction):
        self.facility.name = str(self.name)
        self.facility.maintainer = str(self.maintainer)
        self.facility.description = str(self.description)

        self.last_interaction = interaction
        self.stop()


class ServicesSelectView(discord.ui.View):
    options = [discord.SelectOption(label=member.value[1], value=name)
               for name, member in Service.__members__.items()]

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @discord.ui.select(options=options, max_values=len(options), placeholder='Select services')
    async def services_menu(self, interaction: discord.Interaction, select_menu: discord.ui.Select):
        new_options = deepcopy(self.options)
        for option in new_options:
            if option.value in select_menu.values:
                option.default = True
        select_menu.options = new_options
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label='Add Description/Edit')
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        information = FacilityInformationModal(self.facility)
        await interaction.response.send_modal(information)

        if await information.wait():
            return
        embed = interaction.message.embeds[0]
        embed.description = self.facility.description
        embed.title = self.facility.name
        embed.set_field_at(1,
                           name='Maintainer',
                           value=self.facility.maintainer)
        await information.last_interaction.response.edit_message(embed=embed)

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.primary)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        selected_services = self.children[0].values
        if not len(selected_services) > 0:
            return await interaction.response.send_message('⚠️ Please select at least one service', ephemeral=True)

        for service in selected_services:
            service = Service[service]
            self.facility.services += service.value[0]

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.followup = interaction.followup
        self.stop()


class Modify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.rename(name='facility-name', location='region-coordinates', maintainer='maintainer')
    async def create(self, interaction: discord.Interaction, name: str, location: app_commands.Transform[Region, RegionTransformer], maintainer: str):
        author = interaction.user
        facility_location = f'{Region[location.region].value}'
        if location.coordinates:
            facility_location += f'-{location.coordinates}'
        embed = discord.Embed(title=name,
                              color=0x54A24A)
        embed.add_field(name='Region-Coordinates',
                        value=facility_location)
        embed.add_field(name='Maintainer', value=maintainer)
        embed.add_field(name='Author', value=author.mention)

        view = ServicesSelectView()
        view.facility = Facility(name, location, maintainer)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return
        facility = view.facility
        try:
            await self.bot.db.add_facility(facility.name, facility_location, facility.maintainer, facility.services, facility.description, author.id)
        except Exception as e:
            await view.followup.send(':x: Failed to add facility', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfully added facility', ephemeral=True)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
