from copy import deepcopy
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils.enums import Service, Region
from utils.facility import Facility, LocationTransformer, FacilityLocation


class RemoveFacilitiesView(discord.ui.View):
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
    
    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.primary)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.followup = interaction.followup
        self.stop()


class IdTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str):
        delimiters = ' ', '.', ','
        regex_pattern = '|'.join(map(re.escape, delimiters))
        res = re.split(regex_pattern, value)
        id_list = tuple(filter(None, res))
        return id_list


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
    async def create(self, interaction: discord.Interaction, name: str, location: app_commands.Transform[FacilityLocation, LocationTransformer], maintainer: str):
        author = interaction.user
        facility_location = f'{Region[location.region].value}'
        region_embed_name = 'Region'
        if location.coordinates:
            facility_location += f'-{location.coordinates}'
            region_embed_name += '-Coordinates'
        embed = discord.Embed(title=name,
                              color=0x54A24A)
        embed.add_field(name=region_embed_name,
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
        (region, coordinates) = facility.location
        if coordinates is None:
            coordinates = ''
        try:
            await self.bot.db.add_facility(facility.name, region, coordinates, facility.maintainer, facility.services, facility.description, author.id)
        except Exception as e:
            await view.followup.send(':x: Failed to add facility', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfully added facility', ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    async def remove(self, interaction: discord.Interaction, ids: app_commands.Transform[set, IdTransformer]):
        facilities = await self.bot.db.get_facility_ids(ids)
        if not facilities:
            return await interaction.response.send_message(':x: No facilities found', ephemeral=True)
        if len(facilities) < len(ids):
            message = f':warning: Only found {len(facilities)}/{len(ids)} facilities```\n'
        else:
            message = ':white_check_mark: Found all facilties```\n'
        for facilty in facilities:
            previous_message = message
            message += f'{facilty[0]:3} - {facilty[1]}\n'
            if len(message) > 4000:
                message = previous_message
                message += 'Truncated entries...'
                break
        message += '```Confirm removal of listed facilities'

        view = RemoveFacilitiesView()
        await interaction.response.send_message(message, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return
        ids = [(facility[0],) for facility in facilities]
        try:
            await self.bot.db.remove_facilities(ids)
        except Exception as e:
            await view.followup.send(':x: Failed to remove facilityies', ephemeral=True)
            raise e
        else:
            await view.followup.send(':white_check_mark: Successfuly removed facilities', ephemeral=True)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
