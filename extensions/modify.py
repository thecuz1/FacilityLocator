import discord
from discord.ext import commands
from discord import app_commands
from extensions.autocomplete import region_autocomplete
from extensions.enums import Service


class ServicesSelectView(discord.ui.View):
    options = []
    for service in Service:
        options.append(discord.SelectOption(
            label=service.value[1], value=service.name))

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @discord.ui.select(options=options, max_values=len(Service), placeholder='Select services')
    async def select_menu(self, interaction: discord.Interaction, select_menu: discord.ui.Select):
        await interaction.response.defer()

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        flag_number = 0
        for selected_service in self.children[0].values:
            service = Service[selected_service]
            flag_number += service.value[0]
        await interaction.response.send_message(flag_number)


class Modify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.autocomplete(region=region_autocomplete)
    @app_commands.rename(facilityname='facility-name', region='region-hex', coordinates='coordinates', maintainer='maintainer', notes='notes')
    async def create(self, interaction: discord.Interaction, facilityname: str, region: str, coordinates: str, maintainer: str, notes: str):
        e = discord.Embed(
            title=facilityname, description=notes, color=0x54A24A)
        e.add_field(name='Hex/Region',
                    value=region)
        e.add_field(name='Coordinates', value=coordinates)
        e.add_field(name='Maintainer', value=maintainer)
        e.add_field(name='Author', value=interaction.user.mention)

        view = ServicesSelectView()

        await interaction.response.send_message(embed=e, view=view, ephemeral=True)
        view.message = await interaction.original_response()


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
