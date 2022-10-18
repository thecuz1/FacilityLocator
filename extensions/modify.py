import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
from extensions.autocomplete import region_autocomplete

services = ['Bcons', 'Pcons & Pipes', 'Scons', 'Oil & Petrol', 'Heavy Oil', 'Enriched Oil', 'Cams & Pams', 'Sams & Hams', 'Nams', 'Light Assembly',
            'Light Assembly (Motor Pool)', 'Light Assembly (Rocket Factory)', 'Light Assembly (Field Station)', 'Light Assembly (Tank Factory)', 'Light Assembly (Weapons Platform)', 'Modification Center', 'Ammo Factory', 'Ammo Factory (Rocket)', 'Ammo Factory (Large Shell)', 'Large Assembly', 'Large Assembly (Train)', 'Large Assembly (Heavy Tank)']


class Button(discord.ui.Button):

    def __init__(self, label):
        super().__init__(label=label)

    async def callback(self, interaction: discord.Interaction):
        if self.style == discord.ButtonStyle.secondary:
            self.style = discord.ButtonStyle.primary
        else:
            self.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self.view)


class ServicesSelectView(discord.ui.View):
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    async def select_test(self, interaction: discord.Interaction):
        await interaction.response.send_message(interaction.data)


class ServicesView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.static_buttons = ['Invert Selection', 'Finish']

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label='Invert Selection', style=discord.ButtonStyle.primary, row=4)
    async def invert(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            if item.label in self.static_buttons:
                continue
            elif item.style == discord.ButtonStyle.secondary:
                item.style = discord.ButtonStyle.primary
            else:
                item.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.success, row=4)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass


class Modify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @ app_commands.command()
    @ app_commands.autocomplete(region=region_autocomplete)
    async def fladd(self, interaction: discord.Interaction, facilityname: str, region: str, coordinates: str, maintainer: str, services: str, notes: str):
        e = discord.Embed(
            title=facilityname, description=notes, color=0x54A24A)
        e.add_field(name='Hex/Region',
                    value=region)
        e.add_field(name='Coordinates', value=coordinates)
        e.add_field(name='Maintainer', value=maintainer)
        e.add_field(name='Services',
                    value=services)
        e.add_field(name='Author', value=interaction.user.mention)
        await self.bot.db.addFacility(facilityname, region, coordinates, maintainer, services, notes, interaction.user.id)
        await interaction.response.send_message(':white_check_mark: primaryfully added facility', embed=e)

    @ app_commands.command()
    @ app_commands.autocomplete(region=region_autocomplete)
    @ app_commands.rename(facilityname='facility-name', region='region-hex', coordinates='coordinates', maintainer='maintainer', notes='notes')
    async def create(self, interaction: discord.Interaction, facilityname: str, region: str, coordinates: str, maintainer: str, notes: str):
        e = discord.Embed(
            title=facilityname, description=notes, color=0x54A24A)
        e.add_field(name='Hex/Region',
                    value=region)
        e.add_field(name='Coordinates', value=coordinates)
        e.add_field(name='Maintainer', value=maintainer)
        e.add_field(name='Author', value=interaction.user.mention)

        view = ServicesView()
        for service in services:
            button = Button(label=service)
            view.add_item(button)
        children = view.children
        for button in view.static_buttons:
            for ui_button in children:
                if ui_button.label == button:
                    # print(ui_button.label)
                    view.remove_item(ui_button)
                    ui_button.row = 4
                    view.add_item(ui_button)
                    # print(children)

        await interaction.response.send_message('Select services below', embed=e, view=view, ephemeral=True)

        view.message = await interaction.original_response()

    @ app_commands.command()
    @ app_commands.autocomplete(region=region_autocomplete)
    @ app_commands.rename(facilityname='facility-name', region='region-hex', coordinates='coordinates', maintainer='maintainer', notes='notes')
    async def createselect(self, interaction: discord.Interaction, facilityname: str, region: str, coordinates: str, maintainer: str, notes: str):
        e = discord.Embed(
            title=facilityname, description=notes, color=0x54A24A)
        e.add_field(name='Hex/Region',
                    value=region)
        e.add_field(name='Coordinates', value=coordinates)
        e.add_field(name='Maintainer', value=maintainer)
        e.add_field(name='Author', value=interaction.user.mention)

        view = ServicesSelectView()
        select_options = []
        for service in services:
            select_options.append(discord.SelectOption(label=service))

        select = discord.ui.Select(
            options=select_options,
            max_values=len(select_options))
        select.callback = view.select_test
        view.add_item(select)
        print(view.children)

        await interaction.response.send_message('Select services below', embed=e, view=view, ephemeral=True)

        view.message = await interaction.original_response()


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
