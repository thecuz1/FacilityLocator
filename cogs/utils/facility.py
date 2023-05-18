from typing import Optional
from functools import reduce

import discord

from .flags import ItemServiceFlags, VehicleServiceFlags
from .ansi import Colour, ANSIColour


class Facility:
    """Represents a facility

    Args:
        id_ (int, optional): ID
        name (str): Name
        description (str, optional): Description
        region (str): Region
        coordinates (str, optional): Coordinates within region
        marker (str): Location in region
        maintainer (str): Maintainer
        author (int): Author ID
        item_services (ItemServiceFlags, optional): Item services
        vehicle_services (VehicleServiceFlags, optional): Vehicle services
        creation_time (int, optional): Creation time of facility
        guild_id (int): Guild facility was created in
        image_url (str): Image url to use in embed
    """

    def __init__(
        self,
        *,
        name: str,
        region: str,
        marker: str,
        maintainer: str,
        author: int,
        guild_id: int,
        **options,
    ) -> None:
        self.id_: Optional[int] = options.pop("id_", None)
        self.name: str = name
        self.description: str = options.pop("description", "")
        self.region: str = region
        self.coordinates: Optional[str] = options.pop("coordinates", None)
        self.marker: str = marker
        self.maintainer: str = maintainer
        self.author: int = author

        item_services: ItemServiceFlags = options.pop(
            "item_services", ItemServiceFlags()
        )
        if not isinstance(item_services, ItemServiceFlags):
            raise TypeError(
                f"item_services must be ItemServiceFlags not {type(item_services)}"
            )
        self.item_services = item_services

        vehicle_services: VehicleServiceFlags = options.pop(
            "vehicle_services", VehicleServiceFlags()
        )
        if not isinstance(vehicle_services, VehicleServiceFlags):
            raise TypeError(
                f"vehicle_services must be VehicleServiceFlags not {type(vehicle_services)}"
            )
        self.vehicle_services = vehicle_services

        self.creation_time: Optional[int] = options.pop("creation_time", None)
        self.image_url: str = options.pop("image_url", "")
        self.guild_id: int = guild_id
        self.initial_hash: int = self.__current_hash()

    def __current_hash(self) -> int:
        return hash(
            (
                self.id_,
                self.name,
                self.description,
                self.region,
                self.coordinates,
                self.marker,
                self.maintainer,
                self.author,
                self.item_services.value,
                self.vehicle_services.value,
                self.image_url,
            )
        )

    def __repr__(self) -> str:
        return (
            f"<Facility id={self.id_} author_id={self.author} guild_id={self.guild_id}>"
        )

    def changed(self) -> bool:
        """Determine whether the facility has changed from initial instance

        Returns:
            bool: If facility has changed
        """
        return self.initial_hash != self.__current_hash()

    def embeds(
        self,
        item_service_highlight: ItemServiceFlags = ItemServiceFlags(),
        vehicle_service_highlight: VehicleServiceFlags = VehicleServiceFlags(),
        vehicle_highlight: str = "",
    ) -> list[discord.Embed]:
        """Generates a list of embeds for viewing the facility

        Returns:
            list[discord.Embed]: Embeds representing the current state of facility
        """
        embeds: list[discord.Embed] = []

        facility_location = f"> Region : {self.region}\n> Marker : {self.marker}\n"
        if self.coordinates:
            facility_location += f"> Coordinates : {self.coordinates}\n"

        creation_info = f"> Author : <@{self.author}>\n> Guild ID : {self.guild_id}\n"
        if self.creation_time:
            creation_info += f"> Created : <t:{self.creation_time}:R>\n"
        if self.id_:
            creation_info += f"> ID : {self.id_}\n"

        embed = discord.Embed(
            title=self.name, description=self.description, color=0x54A24A
        )
        if self.image_url:
            image_embed = discord.Embed(
                type="image", colour=discord.Colour.dark_embed()
            ).set_image(url=self.image_url)
            embeds.append(image_embed)
        embed.add_field(name="Location:", value=facility_location)
        embed.add_field(name="Maintainer:", value=self.maintainer)
        embed.add_field(name="Creation Info:", value=creation_info)

        embed.set_footer(text="Source Code: https://github.com/thecuz1/FacilityLocator")

        start = "```ansi\n"
        end = "\n```"

        if self.item_services:
            service_list: list[str] = []

            for name, flag in self.item_services.MAPPED_FLAGS.items():
                if getattr(self.item_services, name) is False:
                    continue

                if getattr(item_service_highlight, name) is True:
                    service_list.append(
                        f"\u001b[0;34m> {flag.display_name}\u001b[0;32m"
                    )
                else:
                    service_list.append(flag.display_name)

            services = "\n".join(service_list)
            embed.add_field(
                name="Item Services:",
                value=f"{start}{ANSIColour(text_colour=Colour.GREEN)}{services}{end}",
            )

        if self.vehicle_services:
            service_list: list[str] = []
            vehicles: list[list[str]] = [[]]

            for name, flag in self.vehicle_services.MAPPED_FLAGS.items():
                if getattr(self.vehicle_services, name) is False:
                    continue

                if getattr(vehicle_service_highlight, name) is True:
                    service_list.append(
                        f"{ANSIColour(bold=True, text_colour=Colour.BLUE)}> {flag.ansi}{flag.display_name}"
                    )
                else:
                    service_list.append(f"{flag.ansi}{flag.display_name}")

                if flag.produces:
                    vehicle_list = list(flag.produces)
                    vehicle_list[0] = f"{flag.ansi}{vehicle_list[0]}"

                    if vehicle_highlight:
                        for i, k in enumerate(vehicle_list):
                            if vehicle_highlight in k:
                                vehicle_list[
                                    i
                                ] = f"{ANSIColour(bold=True, text_colour=Colour.BLUE)}> {flag.ansi}{k}"
                                break

                    length_vehicle_list = 0
                    for k in vehicle_list:
                        length_vehicle_list += len(k)
                    length_vehicle_list += len(vehicle_list) - 1

                    length_vehicles = 0
                    for k in vehicles[-1]:
                        length_vehicles += len(k)
                    length_vehicles += len(vehicles[-1]) - 1

                    if length_vehicle_list + length_vehicles > 860:
                        vehicles.append(vehicle_list)
                    else:
                        vehicles[-1].extend(vehicle_list)

            services = "\n".join(service_list)

            embed.add_field(
                name="Vehicle Services:",
                value=f"{start}{services}{end}",
            )

            if vehicles[0]:
                vehicles[0].insert(
                    0,
                    f"{ANSIColour(bold=True, underline=True)}List generated from vehicle services and doesn't take into account resources to build listed vehicles.",
                )
                for index, vehicle_list in enumerate(vehicles):
                    joined_vehicles = "\n".join(vehicle_list)
                    name = "Vehicles:" if index == 0 else "Vehicles (Cont.):"
                    embed.add_field(
                        name=name,
                        value=f"{start}{joined_vehicles}{end}",
                        inline=False,
                    )

        embeds.append(embed)
        return embeds

    def can_modify(self, interaction: discord.Interaction) -> bool:
        """Returns true if the passed interaction has the ability to modify the facility

        Args:
            interaction (discord.Interaction): The interaction to check

        Returns:
            bool: Whether the facility can be modified
        """
        return self.author == interaction.user.id

    def has_one_service(self) -> bool:
        return self.item_services or self.vehicle_services
