from __future__ import annotations

import traceback
import re
from typing import TYPE_CHECKING
from enum import Enum, auto
from itertools import groupby

from discord import Embed, Colour, Guild


if TYPE_CHECKING:
    from bot import FacilityBot
    from .facility import Facility


class FeedbackType(Enum):
    SUCCESS = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    COOLDOWN = auto()


class FeedbackEmbed(Embed):
    def __init__(
        self,
        message: str,
        feedback_type: FeedbackType,
        exception: Exception | None = None,
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


class LimitException(Exception):
    def __init__(self, continued: bool = False) -> None:
        self.continued: bool = continued


class MaximumFields(LimitException):
    pass


class MaximumCharacters(LimitException):
    pass


class EmbedPage(Embed):
    def __init__(self, *args, **kwargs):
        super().__init__(colour=Colour.green(), *args, **kwargs)

        self.mapped_index: dict[str, int] = {}
        self.count: dict[str, int] = {}

    def _new_field_name(self, *, region: str, continued: bool):
        return f"{region} (1) (cont.)" if continued else f"{region} (1)"

    def add_entry(self, region: str, entry: str, continued: bool = False):
        try:
            index = self.mapped_index[region]
        except KeyError:
            field_name = self._new_field_name(region=region, continued=continued)
            self.add_field(region=region, name=field_name, value=entry)
        else:
            field = self.fields[index]

            updated_value = f"{field.value or ''}\n{entry}"
            facility_count = str(len(updated_value.splitlines()))

            number_start, number_end = re.search(r"\d+", field.name or "").span()

            updated_name = (
                field.name[:number_start] + facility_count + field.name[number_end:]
            )

            if len(updated_value) > 1024:
                field_name = self._new_field_name(region=region, continued=True)
                self.add_field(region=region, name=field_name, value=entry)
            else:
                self.set_field_at(
                    index,
                    region=region,
                    name=updated_name,
                    value=updated_value,
                )

    def add_field(
        self,
        *,
        region: str,
        name: str,
        value: str,
        inline: bool = False,
    ):
        try:
            if self.fields == 25:
                raise MaximumFields()
            if len(self) + len(name) + len(value) > 6000:
                raise MaximumCharacters()
        except LimitException as exc:
            count = self.count.get(region, 0)
            exc.continued = bool(count)
            raise exc

        super().add_field(name=name, value=value, inline=inline)

        try:
            self.count[region] += 1
        except KeyError:
            self.count[region] = 1

        index = len(self.fields) - 1
        self.mapped_index[region] = index

    def set_field_at(
        self,
        index: int,
        *,
        region: str,
        name: str,
        value: str,
        inline: bool = True,
    ):
        field = self.fields[index]
        embed_length = len(self) - len(field.name) - len(field.value)

        try:
            if embed_length + len(name) + len(value) > 6000:
                raise MaximumCharacters()
        except LimitException as exc:
            count = self.count.get(region, 0)
            exc.continued = bool(count)
            raise exc

        return super().set_field_at(index, name=name, value=value, inline=inline)

    def fix_wrapping(self):
        for index, field in enumerate(self.fields):
            value = field.value or ""
            entries = value.splitlines()

            if any(len(entry) > 30 for entry in entries):
                super().set_field_at(
                    index,
                    name=field.name,
                    value=field.value,
                    inline=False,
                )


class Paginator:
    def __init__(self) -> None:
        self.embeds: list[EmbedPage] = []

    @classmethod
    async def create(cls, guild_name: str, total_facilities: int, bot: FacilityBot):
        pnr = cls()
        help_cmd = await bot.tree.get_or_fetch_app_command("help")

        pnr._new_embed(
            title=f"Facility list ({guild_name}) ({total_facilities})",
            description=f"Run the command {help_cmd and help_cmd.mention} for a list of commands to add or locate a facility by service.",
        )
        return pnr

    def _new_embed(self, *args, **kwargs) -> EmbedPage:
        embed = EmbedPage(*args, **kwargs)
        self.embeds.append(embed)
        return embed

    def add_entry(self, region: str, entry: str):
        embed = self.embeds[-1]
        try:
            embed.add_entry(region, entry)
        except LimitException as exc:
            new_embed = self._new_embed()
            new_embed.add_entry(region, entry, exc.continued)


async def create_list(
    facility_list: list[Facility], guild: Guild, bot: FacilityBot
) -> list[Embed]:
    """Generates embeds to list short form facilities

    Args:
        facility_list (list[Facility]): Facilities to generate list from
        guild (Guild): Guild where the list is from

    Returns:
        list[Embed]: List of embeds
    """
    paginator = await Paginator.create(guild.name, len(facility_list), bot)

    facility_list.sort(key=lambda facility: facility.region)
    facility_regions = groupby(facility_list, key=lambda facility: facility.region)

    for region, facilities in facility_regions:
        formatted_list = []
        for facility in facilities:
            if facility.thread_id:
                formatted_list.append(f"{facility.id_} | <#{facility.thread_id}>")
            else:
                formatted_list.append(
                    f"{facility.id_} | {facility.name.strip()} | {facility.marker}"
                )
        for entry in formatted_list:
            paginator.add_entry(region, entry)

    return paginator.embeds


async def ephemeral_info(bot: FacilityBot) -> Embed:
    command = await bot.tree.get_or_fetch_app_command("toggle_ephemeral")
    return Embed(
        description=f"Not expecting this message to be viewable by everyone? You can change your preference with the command {command and command.mention}. This message will not be shown again.",
        colour=Colour.blue(),
    )


class HelpEmbed(Embed):
    @classmethod
    async def create(cls, bot: FacilityBot):
        tree = bot.tree

        toggle_ephemeral_cmd = await tree.get_or_fetch_app_command("toggle_ephemeral")
        create_cmd = await tree.get_or_fetch_app_command("create")
        modify_cmd = await tree.get_or_fetch_app_command("modify")
        view_cmd = await tree.get_or_fetch_app_command("view")
        facility_cmd = await tree.get_or_fetch_app_command("facility")
        locate_cmd = await tree.get_or_fetch_app_command("locate")
        list_cmd = await tree.get_or_fetch_app_command("list")
        remove_ids_cmd = await tree.get_or_fetch_app_command("remove ids")
        remove_ids_cmd = await tree.get_or_fetch_app_command("remove ids")
        remove_facility_cmd = await tree.get_or_fetch_app_command("remove facility")

        embed = cls(
            title="Commands:",
            description=f"Some of these commands will be visable by default, you can change this behaviour with the command {toggle_ephemeral_cmd and toggle_ephemeral_cmd.mention}",
            colour=Colour.green(),
        )
        embed.add_field(
            name="Create/Modify",
            value=f"""{create_cmd and create_cmd.mention} (Creates a facility and associated thread)
                      {modify_cmd and modify_cmd.mention} (Modifies a facility)""",
            inline=False,
        )
        embed.add_field(
            name="View",
            value=f"""{view_cmd and view_cmd.mention} (Allows multiple IDs)
                      {facility_cmd and facility_cmd.mention} (Displays one facility)
                      {locate_cmd and locate_cmd.mention} (Finds a facility based on search parameters)
                      {list_cmd and list_cmd.mention} (Shows a list of all facilities by region)""",
            inline=False,
        )
        embed.add_field(
            name="Remove",
            value=f"""{remove_ids_cmd and remove_ids_cmd.mention} (Removes a list of facility IDs)
                      {remove_facility_cmd and remove_facility_cmd.mention} (Removes a single facility)""",
            inline=False,
        )
        return embed
