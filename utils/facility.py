from typing import NamedTuple
import re
from rapidfuzz.process import extract
import discord
from discord import app_commands
from data import REGIONS, ITEM_SERVICES, VEHICLE_SERVICES


class FacilityLocation(NamedTuple):
    region: str
    coordinates: str


class LocationTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> FacilityLocation:
        try:
            coordinates = re.search(
                r'([A-R]\d{1,2}k\d)', value, flags=re.IGNORECASE).group(1)
        except AttributeError:
            coordinates = ''

        for region in REGIONS:
            if region in value:
                region_name = region
                break
        try:
            return FacilityLocation(region_name, coordinates)
        except UnboundLocalError:
            await interaction.response.send_message(':x: No region found', ephemeral=True)
            raise ValueError('Incorrect region passed')


    async def autocomplete(self, interaction: discord.Interaction, current) -> list[app_commands.Choice]:
        res = extract(current, list(REGIONS), limit=25)
        return [app_commands.Choice(name=choice[0], value=choice[0])
                for choice in res]


class Facility:
    def __init__(self, *, id_: int = 0, name: str, description: str = '', region: str, coordinates: str = '', maintainer: str, author: int, item_services = 0, vehicle_services = 0) -> None:
        self.id_ = id_
        self.name = name
        self.description = description
        self.region = region
        self.coordinates = coordinates
        self.maintainer = maintainer
        self.author = author
        self.item_services = item_services
        self.vehicle_services = vehicle_services
        self.initial_hash = hash((self.__class__, id_, name, description, region, coordinates, maintainer, author, item_services, vehicle_services))

    def changed(self) -> bool:
        return self.initial_hash != hash((self.__class__, self.id_, self.name, self.description, self.region, self.coordinates, self.maintainer, self.author, self.item_services, self.vehicle_services))

    def embed(self) -> discord.Embed:
        facility_location = self.region
        region_embed_name = 'Region'
        if self.coordinates:
            facility_location += f'-{self.coordinates}'
            region_embed_name += '-Coordinates'

        embed = discord.Embed(title=self.name,
                              description=self.description,
                              color=0x54A24A)
        embed.add_field(name=region_embed_name, value=facility_location)
        embed.add_field(name='Maintainer', value=self.maintainer)
        embed.add_field(name='Author', value=f'<@{self.author}>')

        if self.id_:
            embed.set_footer(text=f'ID: {self.id_}')

        def format_services(service_tuple: tuple, services_number: int) -> str:
            formatted_services = '```ansi\n\u001b[0;32m'
            for index, service in enumerate(service_tuple):
                if (1 << index) & services_number:
                    formatted_services += f'{service}\n'
            formatted_services += '```'
            return formatted_services
        if self.item_services > 0:
            formatted_services = format_services(ITEM_SERVICES, self.item_services)
            embed.add_field(name='Services', value=formatted_services)

        if self.vehicle_services > 0:
            formatted_services = format_services(VEHICLE_SERVICES, self.vehicle_services)
            embed.add_field(name='Vehicle Services', value=formatted_services)
        return embed

    def select_options(self, vehicle: bool = False) -> list[discord.SelectOption]:
        if vehicle:
            return [discord.SelectOption(label=service, value=service, default=bool((1 << index) & self.vehicle_services))
                    for index, service in enumerate(VEHICLE_SERVICES)]
        return [discord.SelectOption(label=service, value=service, default=bool((1 << index) & self.item_services))
                for index, service in enumerate(ITEM_SERVICES)]

    def set_services(self, services: list[str], vehicle: bool = False) -> None:
        if vehicle:
            self.vehicle_services = 0
            for index, service in enumerate(VEHICLE_SERVICES):
                if service in services:
                    self.vehicle_services += (1 << index)
        else:
            self.item_services = 0
            for index, service in enumerate(ITEM_SERVICES):
                if service in services:
                    self.item_services += (1 << index)
