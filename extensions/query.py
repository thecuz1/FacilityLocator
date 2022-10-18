import discord
from discord.ext import commands
from discord import app_commands
import Paginator
from extensions.autocomplete import region_autocomplete


class Query(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.autocomplete(region=region_autocomplete)
    async def fl(self, interaction: discord.Interaction, region: str):
        facilitylist = await self.bot.db.getFacility(region)
        if not facilitylist:
            return await interaction.response.send_message(':x: No facilities in requested region')
        embeds = []
        for facility in facilitylist:
            facilityname, region, coordinates, maintainer, services, notes, userid = facility
            e = discord.Embed(
                title=facilityname, description=notes, color=0x54A24A)
            e.add_field(name='Hex/Region',
                        value=region)
            e.add_field(name='Coordinates', value=coordinates)
            e.add_field(name='Maintainer', value=maintainer)
            e.add_field(name='Services',
                        value=services)
            e.add_field(name='Author', value=interaction.user.mention)
            embeds.append(e)
        await Paginator.Simple().start(interaction, pages=embeds)
        # await interaction.response.send_message(embed=e)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Query(bot))
