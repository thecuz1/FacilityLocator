from __future__ import annotations

import re
from typing import TYPE_CHECKING

from discord import app_commands

from .errors import MessageError


if TYPE_CHECKING:
    from .context import GuildInteraction
    from .facility import Facility


class FacilityTransformer(app_commands.Transformer):
    async def transform(self, interaction: GuildInteraction, value: str, /) -> Facility:

        try:
            facility_id = int(value)
        except ValueError as exc:
            match_obj = re.search(r"\d+", value)
            if not match_obj:
                raise MessageError("No facility selected/ID passed") from exc
            facility_id = int(match_obj.group())

        facility = await interaction.client.db.get_facility_id(facility_id)
        if not facility or facility.guild_id != interaction.guild_id:
            raise MessageError("Facility not found")
        return facility

    async def autocomplete(
        self, interaction: GuildInteraction, value: str, /
    ) -> list[app_commands.Choice[str]]:
        prefixed_value = "%" + value + "%"
        query = """SELECT id_, name FROM facilities WHERE guild_id=? AND LOWER(name) LIKE ? LIMIT 12"""
        results: list[tuple[int, str]] = await interaction.client.db.fetch(
            query, interaction.guild_id, prefixed_value.lower()
        )
        return [
            app_commands.Choice(name=f"{id_} - {name}", value=str(id_))
            for id_, name in results
        ]


class IdTransformer(app_commands.Transformer):
    async def transform(self, interaction: GuildInteraction, value: str, /) -> tuple:
        delimiters = " ", ".", ","
        regex_pattern = "|".join(map(re.escape, delimiters))
        res = re.split(regex_pattern, value)
        seperated = tuple(filter(None, res))

        def convert(element: str):
            try:
                return int(element)
            except ValueError:
                return False

        id_tuple = tuple(map(convert, seperated))
        return tuple(filter(None, id_tuple))
