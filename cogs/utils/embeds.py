from __future__ import annotations

import traceback
import re
from typing import TYPE_CHECKING
from enum import Enum, auto
from itertools import groupby

from discord import Embed, Colour, Guild


if TYPE_CHECKING:
    from .facility import Facility


class FeedbackType(Enum):
    SUCCESS = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    COOLDOWN = auto()


class FeedbackEmbed(Embed):
    def __init__(
        self, message: str, feedback_type: FeedbackType, exception: Exception = None
    ):
        match feedback_type:
            case FeedbackType.SUCCESS:
                title = "Success"
                final_message = f":white_check_mark: | {message}"
                embed_colour = Colour.brand_green()
            case FeedbackType.INFO:
                title = "Info"
                final_message = f":information_source: | {message}"
                embed_colour = Colour.blue()
            case FeedbackType.WARNING:
                title = "Warning"
                final_message = f":warning: | {message}"
                embed_colour = Colour.yellow()
            case FeedbackType.ERROR:
                title = "Error"
                final_message = f":x: | {message}"
                embed_colour = Colour.brand_red()
                if exception:
                    final_message += f"\n```py\n{traceback.format_exc()}\n```"
            case FeedbackType.COOLDOWN:
                title = "Cooldown"
                final_message = f":hourglass: | {message}"
                embed_colour = Colour.blue()

        super().__init__(colour=embed_colour, title=title, description=final_message)
        self.set_footer(text="Source Code: https://github.com/thecuz1/FacilityLocator")


def create_list(facility_list: list[Facility], guild: Guild) -> list[Embed]:
    """Generates embeds to list short form facilities

    Args:
        facility_list (list[Facility]): Facilities to generate list from
        guild (Guild): Guild where the list is from

    Returns:
        list[Embed]: List of embeds
    """
    embed = Embed(
        title=f"Facility list ({guild.name}) ({len(facility_list)})",
        description="Format: `ID | Name | Sub-Region`\nFor more info about a facility use the commmand `/view [ID(s)]`",
    )
    embed.colour = Colour.green()

    facility_list.sort(key=lambda facility: facility.region)
    facility_regions = groupby(facility_list, key=lambda facility: facility.region)

    finished_embeds = []

    for region, facilities in facility_regions:
        formatted_list = (
            f"{facility.id_} | {facility.name} | {facility.marker}\n"
            for facility in facilities
        )
        if len(name := f"{region} (0)") + len(embed) + 150 > 6000:
            finished_embeds.append(embed)
            embed = Embed()
            embed.colour = Colour.green()
        embed.add_field(name=name, value="")
        field_index = len(embed.fields) - 1

        for entry in formatted_list:
            previous_value = embed.fields[field_index].value or ""
            new_value = previous_value + entry

            if len(embed) + len(entry) > 6000 or (
                len(new_value) > 1024 and len(embed.fields) == 25
            ):
                finished_embeds.append(embed)
                embed = Embed()
                embed.colour = Colour.green()
                embed.add_field(name=f"{region} (1) (Cont.)", value=entry)
                field_index = 0
            elif len(new_value) > 1024:
                embed.add_field(name=f"{region} (1) (Cont.)", value=entry)
                field_index += 1
            else:
                facility_count = str(new_value.count("\n"))
                field_name = (
                    embed.fields[field_index].name or f"{region} ({facility_count})"
                )
                number_span = re.search(r"\d+", field_name).span()
                updated_name = (
                    field_name[: number_span[0]]
                    + facility_count
                    + field_name[number_span[1] :]
                )
                embed.set_field_at(
                    field_index,
                    name=updated_name,
                    value=new_value,
                )

    if embed not in finished_embeds:
        finished_embeds.append(embed)

    return finished_embeds
