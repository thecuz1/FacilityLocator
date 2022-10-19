import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
from extensions.autocomplete import region_autocomplete

services = ['Bcons', 'Pcons & Pipes', 'Scons', 'Oil & Petrol', 'Heavy Oil', 'Enriched Oil', 'Cams & Pams', 'Sams & Hams', 'Nams', 'Light Assembly',
            'Light Assembly (Motor Pool)', 'Light Assembly (Rocket Factory)', 'Light Assembly (Field Station)', 'Light Assembly (Tank Factory)', 'Light Assembly (Weapons Platform)', 'Modification Center', 'Ammo Factory', 'Ammo Factory (Rocket)', 'Ammo Factory (Large Shell)', 'Large Assembly', 'Large Assembly (Train)', 'Large Assembly (Heavy Tank)']


class ServicesSelectMenu(discord.ui.Select):
    def __init__(self):
        options = []
        for service in services:
            options.append(discord.SelectOption(label=service))
        super().__init__(max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()


class ServicesSelectView(discord.ui.View):
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.success, row=4)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass


class Modify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        view = ServicesSelectView()
        select = ServicesSelectMenu()
        view.add_item(select)

        await interaction.response.send_message('Select services below', embed=e, view=view, ephemeral=True)
        view.message = await interaction.original_response()


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
