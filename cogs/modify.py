import discord
from discord.ext import commands
from discord import app_commands
from utils.autocomplete import region_autocomplete
from utils.enums import Service
from copy import deepcopy


class FacilityInformationModal(discord.ui.Modal, title='Edit Facility Information'):
    facility_name = discord.ui.TextInput(label='Facility Name')
    maintainer = discord.ui.TextInput(label='Maintainer')
    description = discord.ui.TextInput(label='Description',
                                       style=discord.TextStyle.paragraph,
                                       required=False)

    def __init__(self, facility_name, maintainer, description):
        super().__init__()
        self.facility_name.default = facility_name
        self.maintainer.default = maintainer
        self.description.default = description

    async def on_submit(self, interaction: discord.Interaction):
        self.submitted = (str(self.facility_name),
                          str(self.maintainer),
                          str(self.description))
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
            for selected_option in select_menu.values:
                if selected_option == option.value:
                    option.default = True
                    break
                option.default = False
        select_menu.options = new_options
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label='Add Description/Edit')
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        information = FacilityInformationModal(
            facility_name=self.facility_name,
            maintainer=self.maintainer,
            description=self.description)
        await interaction.response.send_modal(information)
        if await information.wait():
            return
        self.facility_name, self.maintainer, self.description = information.submitted
        embed = interaction.message.embeds[0]
        embed.description = self.description
        embed.title = self.facility_name
        embed.set_field_at(1, name='Maintainer', value=self.maintainer)
        await information.last_interaction.response.edit_message(embed=embed)

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.primary)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        selected_services = self.children[0].values
        if not len(selected_services) > 0:
            return await interaction.response.send_message('⚠️ Please select at least one service', ephemeral=True)

        flag_number = 0
        for service in selected_services:
            service = Service[service]
            flag_number += service.value[0]
        self.flag_number = flag_number
        self.last_interaction = interaction
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class Modify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.autocomplete(region=region_autocomplete)
    @app_commands.rename(facility_name='facility-name', region='region-coordinates', maintainer='maintainer')
    async def create(self, interaction: discord.Interaction, facility_name: str, region: str, maintainer: str):
        author = interaction.user
        e = discord.Embed(title=facility_name,
                          color=0x54A24A)
        e.add_field(name='Region-Coordinates', value=region)
        e.add_field(name='Maintainer', value=maintainer)
        e.add_field(name='Author', value=author.mention)

        view = ServicesSelectView()
        view.facility_name = facility_name
        view.maintainer = maintainer
        view.description = ''

        await interaction.response.send_message(embed=e, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return
        facility_name = view.facility_name
        maintainer = view.maintainer
        description = view.description
        await self.bot.db.add_facility(
            facility_name, region, maintainer, view.flag_number, description, author.id)
        await view.last_interaction.followup.send(':white_check_mark: Successfully added facility', ephemeral=True)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
