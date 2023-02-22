from typing import Optional

import discord

from .flags import ItemServiceFlags, VehicleServiceFlags


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

    def embed(self) -> discord.Embed:
        """Generates a embed for viewing the facility

        Returns:
            discord.Embed: Embed filled in with current state of facility
        """
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
            embed.set_image(url=self.image_url)
        embed.add_field(name="Location:", value=facility_location)
        embed.add_field(name="Maintainer:", value=self.maintainer)
        embed.add_field(name="Creation Info:", value=creation_info)

        embed.set_footer(text="Source Code: https://github.com/thecuz1/FacilityLocator")

        start = "```ansi\n\u001b[0;32m"
        end = "\n```"

        if self.item_services:
            services = "\n".join(
                (name for name, enabled in self.item_services if enabled)
            )
            embed.add_field(
                name="Item Services:",
                value=f"{start}{services}{end}",
            )

        if self.vehicle_services:
            services = "\n".join(
                (name for name, enabled in self.vehicle_services if enabled)
            )
            embed.add_field(name="Vehicle Services:", value=f"{start}{services}{end}")
        return embed

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
