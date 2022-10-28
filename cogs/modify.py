from copy import deepcopy
import enum
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils.enums import Service
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

        self.facility.services = 0
        for service in select_menu.values:
            service = Service[service]
            self.facility.services += service.value[0]

        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Add Description/Edit')
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        information = FacilityInformationModal(self.facility)
        await interaction.response.send_modal(information)

        if await information.wait():
            return

        embed = self.facility.embed()
        await information.last_interaction.response.edit_message(embed=embed)

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.primary)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.facility.services <= 0:
            return await interaction.response.send_message('⚠️ Please select at least one service', ephemeral=True)

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
        author_id = interaction.user.id
        facility = Facility(name, location.region, location.coordinates, maintainer, author_id)

        view = ServicesSelectView()
        view.facility = facility
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
            return await interaction.response.send_message(':x: No facility found / No permission', ephemeral=True)
        facility_id, name, region, coordinates, maintainer, services_number, description, author = facility[0]

        facility = Facility(name, region, coordinates, maintainer, author, facility_id, services_number, description)

        view = ServicesSelectView()
        view.facility = facility
        embed = facility.embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return

        try:
            pass
            # await self.bot.db.add_facility(facility.name, region, coordinates, facility.maintainer, facility.services, facility.description, author.id)
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
                              if not facilty.author_id == author_id]

        if removed_facilities:
            message = '```\n'
            for facilty in removed_facilities:
                previous_message = message
                message += f'{facilty.facility_id:3} - {facilty.name}\n'
                if len(message) > 1000:
                    message = previous_message
                    message += 'Truncated entries...'
                    break
            message += '```'
            embed.add_field(name=':x: No permission to delete following facilties',
                            value=message)
        if facilities:
            message = '```\n'
            for facilty in facilities:
                previous_message = message
                message += f'{facilty.facility_id:3} - {facilty.name}\n'
                if len(message) > 1000:
                    message = previous_message
                    message += 'Truncated entries...'
                    break
            message += '```'
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
