import discord
from discord.ext import commands
from discord import app_commands
import Paginator
from utils.autocomplete import region_autocomplete
from utils.enums import Service


class Query(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.autocomplete(region=region_autocomplete)
    async def locate(self, interaction: discord.Interaction, region: str):
        facilitylist = await self.bot.db.get_facility(region)
        if not facilitylist:
            return await interaction.response.send_message(':x: No facilities in requested region')
        embeds = []
        for facility in facilitylist:
            facility_id, facilityname, region, maintainer, services_number, notes, author = facility
            author = self.bot.get_user(author)
            e = discord.Embed(title=facilityname,
                              description=notes,
                              color=0x54A24A)
            e.add_field(name='Region-Coordinates', value=region)
            e.add_field(name='Maintainer', value=maintainer)
            e.add_field(name='Author', value=author.mention)
            e.set_footer(text=f'Internal ID: {facility_id}')

            formatted_services = '```ansi\n'
            for name, member in Service.__members__.items():
                if member.value[0] & services_number:
                    formatted_services += f'[0;32m{member.value[1]}\n'
            formatted_services += '```'
            e.add_field(name='Services', value=formatted_services)
            embeds.append(e)
        await Paginator.Simple().start(interaction, pages=embeds)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Query(bot))
