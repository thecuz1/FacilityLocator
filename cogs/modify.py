import discord
from discord.ext import commands
from discord import app_commands
from utils.autocomplete import region_autocomplete
from utils.enums import Service


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
        self.stop()


class Modify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.autocomplete(region=region_autocomplete)
    @app_commands.rename(facilityname='facility-name', region='region-coordinates', maintainer='maintainer', notes='notes')
    async def create(self, interaction: discord.Interaction, facilityname: str, region: str, maintainer: str, notes: str):
        author = interaction.user
        e = discord.Embed(title=facilityname,
                          description=notes,
                          color=0x54A24A)
        e.add_field(name='Region-Coordinates', value=region)
        e.add_field(name='Maintainer', value=maintainer)
        e.add_field(name='Author', value=author.mention)

        view = ServicesSelectView()

        await interaction.response.send_message(embed=e, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        if await view.wait():
            return
        await self.bot.db.add_facility(
            facilityname, region, maintainer, view.flag_number, notes, author.id)
        await view.last_interaction.response.send_message(':white_check_mark: Successfully added facility', ephemeral=True)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
