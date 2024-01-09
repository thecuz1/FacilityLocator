from __future__ import annotations

import re
from contextlib import contextmanager
from typing import NamedTuple, TYPE_CHECKING
from rapidfuzz.process import extract

from discord.ext import commands
from discord import app_commands, Member, Attachment

from .utils.embeds import (
    FeedbackEmbed,
    FeedbackType,
    create_list,
    ephemeral_info,
)
from .utils.facility import Facility
from .utils.views import ModifyFacilityView, RemoveFacilitiesView, CreateFacilityView
from .utils.regions import REGIONS, all_markers
from .utils.flags import ItemServiceFlags, VehicleServiceFlags
from .utils.paginator import Paginator
from .utils.transformers import FacilityTransformer, IdTransformer
from .utils.errors import MessageError


if TYPE_CHECKING:
    from bot import FacilityBot
    from .utils.context import GuildInteraction


class MarkerTransformer(app_commands.Transformer):
    async def transform(self, interaction: GuildInteraction, value: str, /) -> str:
        for marker in all_markers():
            if value.lower() in marker.lower():
                return marker

        raise MessageError("No marker found")

    async def autocomplete(
        self, interaction: GuildInteraction, value: str, /
    ) -> list[app_commands.Choice]:
        def generate_options(markers):
            results = extract(value, markers, limit=25)
            return [
                app_commands.Choice(name=result[0], value=result[0])
                for result in results
            ]

        ns_region = interaction.namespace.region
        if not isinstance(ns_region, str):
            if ns_region is None:
                pass
            else:
                raise TypeError(f"Unexpected namespace type {type(ns_region)}")
        elif not ns_region == "":
            for region, markers in REGIONS.items():
                if region.lower() in ns_region.lower():
                    return generate_options(markers)

        return generate_options(all_markers())


class FacilityLocation(NamedTuple):
    region: str
    coordinates: str


class LocationTransformer(app_commands.Transformer):
    async def transform(
        self, interaction: GuildInteraction, value: str, /
    ) -> FacilityLocation:
        match = re.search(r"[A-R]\d{1,2}K\d", value, flags=re.IGNORECASE)
        if match:
            coordinates = match.group()
        else:
            coordinates = ""

        for region in REGIONS:
            if region.lower() in value.lower():
                return FacilityLocation(region, coordinates.upper())

        raise MessageError("Invalid region")

    async def autocomplete(
        self, interaction: GuildInteraction, value: str, /
    ) -> list[app_commands.Choice]:
        results = extract(value, tuple(REGIONS), limit=25)
        return [
            app_commands.Choice(name=result[0], value=result[0]) for result in results
        ]


class VehicleTransformer(app_commands.Transformer):
    async def transform(
        self, interaction: GuildInteraction, value: str, /
    ) -> tuple[str, int]:
        for vehicle, flag in VehicleServiceFlags.all_vehicles():
            if vehicle in value:
                return vehicle, flag.flag_value
        raise MessageError("Invalid vehicle")

    async def autocomplete(
        self, _: GuildInteraction, value: str, /
    ) -> list[app_commands.Choice[str]]:
        choices = [name for name, _ in VehicleServiceFlags.all_vehicles()]
        sorted_choices = extract(value, choices, limit=25)
        return [
            app_commands.Choice(name=choice[0], value=choice[0])
            for choice in sorted_choices
        ]


class ItemTransformer(app_commands.Transformer):
    async def transform(self, interaction: GuildInteraction, value: str, /) -> int:
        try:
            service = ItemServiceFlags.MAPPED_FLAGS[value]
        except KeyError:
            raise MessageError("Not a valid service", ephemeral=True)

        return service.flag_value

    async def autocomplete(
        self, _interaction: GuildInteraction, value: str, /
    ) -> list[app_commands.Choice[str]]:
        choices = list(ItemServiceFlags.MAPPED_FLAGS.keys())
        sorted_choices = extract(value, choices, limit=25)

        app_choices = []
        for name, _, _ in sorted_choices:
            flag = ItemServiceFlags.MAPPED_FLAGS[name]
            app_choices.append(app_commands.Choice(name=flag.display_name, value=name))

        return app_choices


class FacilityCog(commands.Cog):
    def __init__(self, bot: FacilityBot) -> None:
        self.bot: FacilityBot = bot
        self._users_creating_facility: set[int] = set()

    @contextmanager
    def _facility_create_lock(self, user_id: int):
        if user_id in self._users_creating_facility:
            raise MessageError("Already creating a facility")
        self._users_creating_facility.add(user_id)
        try:
            yield
        finally:
            self._users_creating_facility.remove(user_id)

    @app_commands.command()  # type: ignore[arg-type]
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 20, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.rename(name="facility-name", location="region")
    async def create(
        self,
        interaction: GuildInteraction,
        name: app_commands.Range[str, 1, 100],
        location: app_commands.Transform[FacilityLocation, LocationTransformer],
        marker: app_commands.Transform[str, MarkerTransformer],
        maintainer: app_commands.Range[str, 1, 200],
        coordinates: str = "",
        image: Attachment | None = None,
    ) -> None:
        """Creates a facility

        Args:
            name (str): Name of facility
            location (app_commands.Transform[FacilityLocation, LocationTransformer]): Region with optional coordinates in the form of region-coordinates from ctrl-click of map
            marker (str): Nearest major or minor location
            maintainer (str): Who maintains the facility
            coordinates (str): Optional coordinates (incase it doesn't work in the region field)
            image (discord.Attachment): Image to be displayed along with facility (URL can be set in edit modal)
        """
        with self._facility_create_lock(interaction.user.id):
            final_coordinates = coordinates.upper() or location.coordinates

            query = """SELECT count(id_) FROM facilities WHERE guild_id == ? AND author == ?"""
            facility_count_row = await self.bot.db.fetch_one(
                query, interaction.guild_id, interaction.user.id
            )
            facility_count: int = facility_count_row[0]

            if (
                facility_count >= 20
                and not interaction.user.guild_permissions.administrator
            ):
                raise MessageError(
                    f"Cannot create more then {facility_count} facilities"
                )

            url = image and image.url
            facility = Facility(
                name=name,
                region=location.region,
                coordinates=final_coordinates,
                maintainer=maintainer,
                author=interaction.user.id,
                marker=marker,
                guild_id=interaction.guild_id,
                image_url=url or "",
            )

            view = CreateFacilityView(
                facility=facility, original_author=interaction.user
            )
            embeds = facility.embeds()

            await view.send(interaction, embeds=embeds, ephemeral=True)
            await view.wait()

    @app_commands.command()  # type: ignore[arg-type]
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def modify(
        self,
        interaction: GuildInteraction,
        facility: app_commands.Transform[Facility, FacilityTransformer],
    ):
        """Modify faciliy information

        Args:
            facility (app_commands.Transform[Facility, FacilityTransformer]): Facility to modify, also accepts ID
        """

        if self.bot.owner_id != interaction.user.id:
            if facility.can_modify(interaction) is False:
                if interaction.user.guild_permissions.administrator:
                    pass
                else:
                    raise MessageError("No permission to modify facility")

        view = ModifyFacilityView(facility=facility, original_author=interaction.user)
        embeds = facility.embeds()

        await view.send(interaction, embeds=embeds, ephemeral=True)

    remove = app_commands.Group(
        name="remove", description="Remove facilities", guild_only=True
    )

    @remove.command()  # type: ignore[arg-type]
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def user(self, interaction: GuildInteraction, user: Member):
        """Removes all of the users facilities for the current guild

        Args:
            user (Member): Member's facilities to remove
        """

        search_dict = {
            " guild_id == ? ": interaction.guild_id,
            " author == ? ": user.id,
        }
        facilities = await self.bot.db.get_facilities(search_dict)

        if self.bot.owner_id != interaction.user.id:
            removed_facilities: list[Facility] = []
            for facility in facilities[:]:
                if not facility.can_modify(interaction):
                    if interaction.user.guild_permissions.administrator:
                        continue
                    facilities.remove(facility)
                    removed_facilities.append(facility)

        if not facilities:
            raise MessageError("No facilities/required access")

        facility_amount = len(facilities)
        embed = FeedbackEmbed(
            f"Confirm removing {facility_amount} facilit{'ies' if facility_amount > 1 else 'y'} created by {user.mention} from {interaction.guild.name}",
            FeedbackType.WARNING,
        )
        view = RemoveFacilitiesView(
            original_author=interaction.user, facilities=facilities
        )

        await view.send(interaction, embed=embed, ephemeral=True)

    @remove.command()  # type: ignore[arg-type]
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def ids(
        self,
        interaction: GuildInteraction,
        ids: app_commands.Transform[tuple[int], IdTransformer],
    ):
        """Removes facilities by ID's for the current guild

        Args:
            ids (app_commands.Transform[tuple, IdTransformer]): List of facility ID's to remove with a delimiter of ',' or a space ' ' Ex. 1,3 4 8
        """
        facilities = await self.bot.db.get_facility_ids(ids)
        not_found_facilities = len(ids) - len(facilities)

        removed_facilities: list[Facility] = []
        if self.bot.owner_id != interaction.user.id:
            for facility in facilities[:]:
                if facility.guild_id != interaction.guild_id:
                    facilities.remove(facility)
                    removed_facilities.append(facility)
                    continue
                if not facility.can_modify(interaction):
                    if interaction.user.guild_permissions.administrator:
                        continue
                    facilities.remove(facility)
                    removed_facilities.append(facility)

        if not facilities:
            raise MessageError("No facilities/required access")

        facility_amount = len(facilities)
        embed = FeedbackEmbed(
            f"Confirm removing {facility_amount} facilit{'ies' if facility_amount > 1 else 'y'} from {interaction.guild.name}",
            FeedbackType.WARNING,
        )
        view = RemoveFacilitiesView(
            original_author=interaction.user, facilities=facilities
        )

        removed_facility_amount = len(removed_facilities)
        prevented_message = (
            f":x: Not Removing {removed_facility_amount} facilit{'ies' if removed_facility_amount > 1 else 'y'} due to missing permissions"
            if removed_facility_amount > 0
            else ""
        )

        not_found_message = (
            f":x: {not_found_facilities} facilit{'ies' if not_found_facilities > 1 else 'y'} not found"
            if not_found_facilities > 0
            else ""
        )

        await view.send(
            interaction,
            content="\n".join((prevented_message, not_found_message)),
            embed=embed,
            ephemeral=True,
        )

    @remove.command()  # type: ignore[arg-type]
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def all(self, interaction: GuildInteraction):
        """Removes all facilities for the current guild"""

        search_dict = {"guild_id == ?": interaction.guild_id}
        facilities = await self.bot.db.get_facilities(search_dict)

        if not facilities:
            raise MessageError("No facilities found")

        facility_amount = len(facilities)
        embed = FeedbackEmbed(
            f"Confirm removing {facility_amount} facilit{'ies' if facility_amount > 1 else 'y'} from {interaction.guild.name}",
            FeedbackType.WARNING,
        )
        view = RemoveFacilitiesView(
            original_author=interaction.user, facilities=facilities
        )

        await view.send(
            interaction,
            embed=embed,
            ephemeral=True,
        )

    @remove.command(name="facility")  # type: ignore[arg-type]
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def remove_facility(
        self,
        interaction: GuildInteraction,
        facility: app_commands.Transform[Facility, FacilityTransformer],
    ):
        """Removes a single facility

        Args:
            facility (app_commands.Transform[Facility, FacilityTransformer]): Facility to remove, also accepts ID
        """
        if self.bot.owner_id != interaction.user.id:
            if facility.can_modify(interaction) is False:
                if interaction.user.guild_permissions.administrator is False:
                    raise MessageError("No permission to delete facility")

        facility_list = [facility]

        try:
            await self.bot.db.remove_facilities(facility_list)
        except Exception as exc:
            raise MessageError(
                f"Failed to remove facilities\n```py\n{exc}\n```"
            ) from exc
        else:
            embed = FeedbackEmbed("Removed facility", FeedbackType.SUCCESS)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            interaction.client.dispatch(
                "bulk_facility_delete",
                facility_list,
                interaction,
            )

    @app_commands.command(name="facility")  # type: ignore[arg-type]
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def display_facility(
        self,
        interaction: GuildInteraction,
        facility: app_commands.Transform[Facility, FacilityTransformer],
        ephemeral: bool = False,
    ):
        """Gets and displays info about a facility

        Args:
            facility (app_commands.Transform[Facility, FacilityTransformer]): Facility to display, also accepts ID
            ephemeral (bool, optional): Shows results to only you. Defaults to False.
        """
        embeds = facility.embeds()
        if interaction.namespace.ephemeral is not None:
            pass
        else:
            preference = await self.bot.db.ephemeral_preference(interaction.user.id)
            if preference is None:
                embeds.append(await ephemeral_info(self.bot))

            ephemeral = preference or False

        await interaction.response.send_message(embeds=embeds, ephemeral=ephemeral)

    @app_commands.command()  # type: ignore[arg-type]
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def view(
        self,
        interaction: GuildInteraction,
        ids: app_commands.Transform[tuple[int], IdTransformer],
        ephemeral: bool = False,
    ):
        """View facilities based on their ID's

        Args:
            ids (app_commands.Transform[tuple[int], IdTransformer]): List of facility ID's to view with a delimiter of ',' or a space ' ' Ex. 1,3 4 8
            ephemeral (bool): Show results to only you. Defaults to False
        """
        facilities = await self.bot.db.get_facility_ids(ids)
        if not facilities:
            raise MessageError("No facilities found", ephemeral=True)

        embeds = [
            facility.embeds()
            for facility in facilities
            if facility.guild_id == interaction.guild_id
        ]

        ephemeral_info_embed = None
        if interaction.namespace.ephemeral is not None:
            pass
        else:
            preference = await self.bot.db.ephemeral_preference(interaction.user.id)
            if preference is None:
                ephemeral_info_embed = await ephemeral_info(self.bot)

            ephemeral = preference or False

        await Paginator(original_author=interaction.user).start(
            interaction,
            pages=embeds,
            ephemeral=ephemeral,
            one_time_message=ephemeral_info_embed,
        )

    @app_commands.command()  # type: ignore[arg-type]
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.rename(
        location="region",
        item_service="item-service",
        vehicle_service="vehicle-service",
    )
    @app_commands.choices(
        vehicle_service=[
            app_commands.Choice(name=flag.display_name, value=flag.flag_value)
            for flag in VehicleServiceFlags.MAPPED_FLAGS.values()
        ],
    )
    async def locate(
        self,
        interaction: GuildInteraction,
        location: app_commands.Transform[
            FacilityLocation | None, LocationTransformer
        ] = None,
        item_service: app_commands.Transform[int, ItemTransformer] = 0,
        vehicle_service: int = 0,
        creator: Member | None = None,
        vehicle: app_commands.Transform[tuple[str, int], VehicleTransformer] = ("", 0),
        ephemeral: bool = False,
    ) -> None:
        """Find a facility with optional search parameters

        Args:
            location (app_commands.Transform[FacilityLocation, LocationTransformer], optional): Region to search in
            item_service (int, optional): Item service to look for
            vehicle_service (int, optional): Vehicle service to look for
            creator (Member, optional): Filter by facility creator
            vehicle (tuple[str, int], optional): Vehicle upgrade/build facility to look for
            ephemeral (bool): Show results to only you. Defaults to False.
        """
        vehicle_service = vehicle[1] or vehicle_service

        search_dict = {
            name: value
            for name, value in (
                (" region == ? ", location and location.region),
                (" item_services & ? ", item_service),
                (" vehicle_services & ? ", vehicle_service),
                (" author == ? ", creator and creator.id),
                (" guild_id == ? ", interaction.guild_id),
            )
            if value
        }

        facility_list = await self.bot.db.get_facilities(search_dict)

        if not facility_list:
            raise MessageError("No facilities found", ephemeral=True)

        item_highlight = ItemServiceFlags(item_service)
        vehicle_highlight = VehicleServiceFlags(vehicle_service)

        embeds = [
            facility.embeds(item_highlight, vehicle_highlight, vehicle[0])
            for facility in facility_list
        ]

        ephemeral_info_embed = None
        if interaction.namespace.ephemeral is not None:
            pass
        else:
            preference = await self.bot.db.ephemeral_preference(interaction.user.id)
            if preference is None:
                ephemeral_info_embed = await ephemeral_info(self.bot)

            ephemeral = preference or False

        await Paginator(original_author=interaction.user).start(
            interaction,
            pages=embeds,
            ephemeral=ephemeral,
            one_time_message=ephemeral_info_embed,
        )

    @app_commands.command()  # type: ignore[arg-type]
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def list(self, interaction: GuildInteraction, ephemeral: bool = False):
        """Shows a list of all facilities for the current guild

        Args:
            ephemeral (bool): Show results to only you. Defaults to False.
        """

        search_dict = {" guild_id == ? ": interaction.guild_id}

        facility_list = await self.bot.db.get_facilities(search_dict)

        if not facility_list:
            raise MessageError("No facilities found", ephemeral=True)

        finished_embeds = await create_list(
            facility_list, interaction.guild, interaction.client
        )

        ephemeral_info_embed = None
        if interaction.namespace.ephemeral is not None:
            pass
        else:
            preference = await self.bot.db.ephemeral_preference(interaction.user.id)
            if preference is None:
                ephemeral_info_embed = await ephemeral_info(self.bot)

            ephemeral = preference or False

        if ephemeral_info_embed:
            finished_embeds.append(ephemeral_info_embed)

        await interaction.response.send_message(
            embed=finished_embeds.pop(0), ephemeral=ephemeral
        )

        for embed in finished_embeds:
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(FacilityCog(bot))
