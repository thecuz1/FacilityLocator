from typing import NamedTuple
import re
import discord
from discord import app_commands
from utils.enums import Region, Service


class FacilityLocation(NamedTuple):
    region: str
    coordinates: str


class LocationTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str):
        try:
            coordinates = re.search(
                r'([A-R]\d{1,2}k\d)', value, flags=re.IGNORECASE).group(1)
        except AttributeError:
            coordinates = ''

        region = None
        for name, member in Region.__members__.items():
            if name in value or member.value in value:
                region = name
                break
        if region is None:
            await interaction.response.send_message(':x: No region found', ephemeral=True)
            raise ValueError('Incorrect region passed')
        return FacilityLocation(region, coordinates)

    async def autocomplete(self, interaction: discord.Interaction, current):
        choice_list = [app_commands.Choice(name=member.value, value=name)
                       for name, member in Region.__members__.items()
                       if current.lower() in member.value.lower()]
        return choice_list[:25]


class Facility:
    def __init__(self, name, region, coordinates, maintainer, author_id, facility_id = 0, services = 0, description = '') -> None:
        self.name = name
        self.region = region
        self.region_name = Region[region].value
        self.coordinates = coordinates
        self.maintainer = maintainer
        self.author_id = author_id
        self.facility_id = facility_id
        self.services = services
        self.description = description

    def embed(self) -> discord.Embed:
        facility_location = self.region_name
        region_embed_name = 'Region'
        if self.coordinates:
            facility_location += f'-{self.coordinates}'
            region_embed_name += '-Coordinates'

        embed = discord.Embed(title=self.name,
                              description=self.description,
                              color=0x54A24A)
        embed.add_field(name=region_embed_name, value=facility_location)
        embed.add_field(name='Maintainer', value=self.maintainer)
        embed.add_field(name='Author', value=f'<@{self.author_id}>')

        if self.facility_id:
            embed.set_footer(text=f'ID: {self.facility_id}')

        if self.services > 0:
            formatted_services = '```ansi\n\u001b[0;32m'
            for service in Service:
                if service.value[0] & self.services:
                    formatted_services += f'{service.value[1]}\n'
            formatted_services += '```'
            embed.add_field(name='Services', value=formatted_services)

        return embed

    def select_options(self) -> list[discord.SelectOption]:
        return [discord.SelectOption(label=service.value[1], value=name, default=bool(service.value[0] & self.services))
                for name, service in Service.__members__.items()]
