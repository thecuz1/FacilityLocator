from enum import Enum
from typing import NamedTuple
import re
from rapidfuzz.process import extract
import discord
from discord import app_commands
from utils import Region, Service, VehicleService


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
            if name in value or member.value[0] in value:
                region = name
                break
        if region is None:
            await interaction.response.send_message(':x: No region found', ephemeral=True)
            raise ValueError('Incorrect region passed')
        return FacilityLocation(region, coordinates)

    async def autocomplete(self, interaction: discord.Interaction, current):
        res = extract(current, {i.name: i.value[0] for i in Region}, limit=25)
        choice_list = [app_commands.Choice(name=choice[0], value=Region[choice[2]].name)
                       for choice in res]
        return choice_list


class Facility:
    def __init__(self, *, id_: int = 0, name: str, description: str = '', region: str, coordinates: str = '', maintainer: str, author: int, services = 0, vehicle_services = 0) -> None:
        self.facility_id = id_
        self.name = name
        self.description = description
        self.region = region
        self.region_name = Region[region].value[0]
        self.coordinates = coordinates
        self.maintainer = maintainer
        self.author_id = author
        self.services = services
        self.vehicle_services = vehicle_services
        self.initial_hash = hash((self.__class__, id_, name, description, region, coordinates, maintainer, author, services, vehicle_services))

    def changed(self) -> bool:
        return self.initial_hash != hash((self.__class__, self.facility_id, self.name, self.description, self.region, self.coordinates, self.maintainer, self.author_id, self.services, self.vehicle_services))

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

        def format_services(service_enum: Enum, services_number: int) -> str:
            formatted_services = '```ansi\n\u001b[0;32m'
            for index, service in enumerate(service_enum):
                if (1 << index) & services_number:
                    formatted_services += f'{service.value}\n'
            formatted_services += '```'
            return formatted_services
        if self.services > 0:
            formatted_services = format_services(Service, self.services)
            embed.add_field(name='Services', value=formatted_services)

        if self.vehicle_services > 0:
            formatted_services = format_services(VehicleService, self.vehicle_services)
            embed.add_field(name='Vehicle Services', value=formatted_services)
        return embed

    def select_options(self, vehicle: bool = False) -> list[discord.SelectOption]:
        if vehicle:
            return [discord.SelectOption(label=service[1].value, value=service[0], default=bool((1 << index) & self.vehicle_services))
                    for index, service in enumerate(VehicleService.__members__.items())]
        return [discord.SelectOption(label=service[1].value, value=service[0], default=bool((1 << index) & self.services))
                for index, service in enumerate(Service.__members__.items())]

    def set_services(self, services: list[str], vehicle: bool = False) -> None:
        if vehicle:
            self.vehicle_services = 0
            for index, service in enumerate(VehicleService):
                if service.name in services:
                    self.vehicle_services += (1 << index)
        else:
            self.services = 0
            for index, service in enumerate(Service):
                if service.name in services:
                    self.services += (1 << index)
