from dataclasses import dataclass
from typing import NamedTuple
import re
import discord
from discord import app_commands
from utils.enums import Region


class FacilityLocation(NamedTuple):
    region: str
    coordinates: str


@dataclass
class Facility:
    name: str
    location: FacilityLocation
    maintainer: str
    services: int = 0
    description: str = ''


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
        if len(choice_list) > 25:
            choice_list = choice_list[0:25]
        return choice_list
