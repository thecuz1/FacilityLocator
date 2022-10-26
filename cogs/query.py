import discord
from discord.ext import commands
from discord import app_commands
import Paginator
from utils.enums import Service, Region
from utils.facility import LocationTransformer, FacilityLocation


class Query(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.rename(location='region')
    async def locate(self, interaction: discord.Interaction, location: app_commands.Transform[FacilityLocation, LocationTransformer]):
        facility_list = await self.bot.db.get_facility(location.region)
        if not facility_list:
            return await interaction.response.send_message(':x: No facilities in requested region', ephemeral=True)
        embeds = []
        for facility in facility_list:
            facility_id, name, region, coordinates, maintainer, services_number, description, author = facility
            facility_location = f'{Region[region].value}'
            region_embed_name = 'Region'
            if coordinates:
                facility_location += f'-{coordinates}'
                region_embed_name += '-Coordinates'
            embed = discord.Embed(title=name,
                                  description=description,
                                  color=0x54A24A)
            embed.add_field(name=region_embed_name, value=facility_location)
            embed.add_field(name='Maintainer', value=maintainer)
            embed.add_field(name='Author', value=f'<@{author}>')
            embed.set_footer(text=f'ID: {facility_id}')

            formatted_services = '```ansi\n\u001b[0;32m'
            for member in Service:
                if member.value[0] & services_number:
                    formatted_services += f'{member.value[1]}\n'
            formatted_services += '```'
            embed.add_field(name='Services', value=formatted_services)
            embeds.append(embed)
        await Paginator.Simple().start(interaction, pages=embeds)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Query(bot))
