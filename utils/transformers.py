from typing import NamedTuple
import re
from rapidfuzz.process import extract
import discord
from discord import app_commands
from data import REGIONS


class IdTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> tuple:
        delimiters = " ", ".", ","
        regex_pattern = "|".join(map(re.escape, delimiters))
        res = re.split(regex_pattern, value)
        return tuple(filter(None, res))


class MarkerTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> str:
        resolved_marker = None
        for marker_tuple in REGIONS.values():
            for marker in marker_tuple:
                if value.lower() in marker.lower():
                    resolved_marker = marker
                    break

        if resolved_marker is None:
            await interaction.response.send_message(
                ":x: No marker found", ephemeral=True
            )
            raise ValueError("Incorrect marker passed")
        return resolved_marker

    async def autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice]:
        # try looping through all regions and find the user selected region
        try:
            for region in REGIONS:
                if region.lower() in interaction.namespace["region"].lower():
                    selected_region = region
                    break
        # ignore if the user has not entered a region
        except KeyError:
            pass
        # try creating a list of markers with the user entered region as a restriction
        try:
            marker_generator = [
                marker
                for region, markers in REGIONS.items()
                for marker in markers
                if selected_region == region
            ]
        # ignore if no region was found in user input and create a list of all markers
        except NameError:
            marker_generator = [
                marker for markers in REGIONS.values() for marker in markers
            ]

        # fuzzy search for the most likely user wanted option
        results = extract(current, marker_generator, limit=25)
        # return a list of choice objects from most to least likely what the user wants
        return [
            app_commands.Choice(name=result[0], value=result[0]) for result in results
        ]


class FacilityLocation(NamedTuple):
    region: str
    coordinates: str


class LocationTransformer(app_commands.Transformer):
    async def transform(
        self, interaction: discord.Interaction, value: str
    ) -> FacilityLocation:
        # try searching for coordinates in user sent location
        try:
            coordinates = re.search(
                r"([A-R]\d{1,2}k\d)", value, flags=re.IGNORECASE
            ).group(1)
        # ignore if no coordinates were found
        except AttributeError:
            coordinates = None

        # search for region in user sent location
        for region in REGIONS:
            if region.lower() in value.lower():
                selected_region = region
                break
        # try creating a location with selected region
        try:
            return FacilityLocation(selected_region, coordinates)
        # ignore if no region is found and inform the user
        except UnboundLocalError:
            await interaction.response.send_message(
                ":x: No region found", ephemeral=True
            )
            raise ValueError("Incorrect region passed")

    async def autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice]:
        results = extract(current, tuple(REGIONS), limit=25)
        return [
            app_commands.Choice(name=result[0], value=result[0]) for result in results
        ]
