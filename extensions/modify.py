import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
from extensions.autocomplete import region_autocomplete


class ServicesView(discord.ui.View):
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    async def switch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if button.style == discord.ButtonStyle.secondary:
            button.style = discord.ButtonStyle.primary
        else:
            button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

    async def invert_all_buttons(self, button: discord.ui.Button):
        if button.style == discord.ButtonStyle.secondary:
            button.style = discord.ButtonStyle.primary
        else:
            button.style = discord.ButtonStyle.secondary
        return button

    @discord.ui.button(label='Bcons')
    async def bcons(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Pcons & Pipes')
    async def pcons_pipes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Scons')
    async def scons(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Oil & Petrol')
    async def Oil(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Heavy Oil')
    async def heavy_oil(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Enriched Oil')
    async def enricked_oil(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Cams & Pams')
    async def cams_pams(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Sams & Hams')
    async def sams_hams(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Nams')
    async def nams(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Light Assembly')
    async def ls(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Light Assembly (Motor Pool)')
    async def ls_mp(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Light Assembly (Rocket Factory)')
    async def ls_rf(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Light Assembly (Field Station)')
    async def ls_fs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Light Assembly (Tank Factory)')
    async def ls_tf(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Light Assembly (Weapons Platform)')
    async def ls_wp(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Modification Center')
    async def mc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Ammo Factory')
    async def af(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Ammo Factory (Rocket)')
    async def af_rocket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Ammo Factory (Large Shell)')
    async def af_shell(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Large Assembly')
    async def la(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Large Assembly (Train)')
    async def la_train(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Large Assembly (Heavy Tank)')
    async def la_ht(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_button(interaction, button)

    @discord.ui.button(label='Cancel', row=4, style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label='Invert Selection', row=4, style=discord.ButtonStyle.blurple)
    async def invert(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            if item.label in ['Finish', 'Invert Selection', 'Cancel']:
                continue
            await self.invert_all_buttons(item)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label='Finish', row=4, style=discord.ButtonStyle.success)
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
        # e.add_field(name='Services',value=services)
        e.add_field(name='Author', value=interaction.user.mention)

        view = ServicesView()
        await interaction.response.send_message('Add additional details below', embed=e, view=view, ephemeral=True)

        view.message = await interaction.original_response()


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
