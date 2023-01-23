from itertools import groupby
import re
from discord import Embed, Colour, Guild
from facility import Facility


def create_list(facility_list: list[Facility], guild: Guild) -> list[Embed]:
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
