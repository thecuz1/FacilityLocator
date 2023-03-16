from __future__ import annotations

from time import time
from copy import copy
from typing import TYPE_CHECKING

from discord import (
    ui,
    User,
    Member,
    ButtonStyle,
    TextChannel,
    Button,
)
from discord.errors import Forbidden

from .modals import FacilityInformationModal
from .facility import Facility
from .mixins import InteractionCheckedView
from .embeds import FeedbackEmbed, FeedbackType
from .flags import ItemServiceFlags, VehicleServiceFlags
from .embeds import create_list


if TYPE_CHECKING:
    from .context import GuildInteraction, ClientInteraction
    from ..events import Events


class ButtonMessage(Exception):
    pass


class NoServices(ButtonMessage):
    def __init__(self) -> None:
        super().__init__("Select one service")


class NoChanges(ButtonMessage):
    def __init__(self) -> None:
        super().__init__("No changes")


class DynamicListConfirm(InteractionCheckedView):
    """View used when setting a dynamic list"""

    def __init__(
        self,
        *,
        timeout: float = 180,
        original_author: User | Member,
        selected_channel: TextChannel,
        facilities: list[Facility],
    ) -> None:
        super().__init__(timeout=timeout, original_author=original_author)
        self.selected_channel: TextChannel = selected_channel
        self.facilities: list[Facility] = facilities

    @ui.button(label="Set", style=ButtonStyle.green)
    async def confirm(self, interaction: GuildInteraction, _: ui.Button) -> None:
        await self._finish_view(interaction)
        followup = interaction.followup

        facility_list = create_list(self.facilities, interaction.guild)
        messages = []
        for embed in facility_list:
            try:
                message = await self.selected_channel.send(embed=embed)
            except Forbidden:
                embed = FeedbackEmbed(
                    "No permission to send messages in selected channel",
                    FeedbackType.ERROR,
                )
                return await followup.send(embed=embed, ephemeral=True)
            messages.append(message.id)

        try:
            await interaction.client.db.set_list(
                interaction.guild, self.selected_channel, messages
            )
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to set list channel\n```py\n{exc}\n```", FeedbackType.ERROR
            )
            await followup.send(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed("Set list channel", FeedbackType.SUCCESS)
            await followup.send(embed=embed, ephemeral=True)

    @ui.button(label="Disable list", style=ButtonStyle.danger)
    async def disable(self, interaction: GuildInteraction, _: ui.Button):
        await self._finish_view(interaction)
        followup = interaction.followup

        try:
            await interaction.client.db.remove_list(interaction.guild)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to remove list channel\n```py\n{exc}\n```", FeedbackType.ERROR
            )
            await followup.send(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed("Disabled list channel", FeedbackType.SUCCESS)
            await followup.send(embed=embed, ephemeral=True)


class RemoveFacilitiesView(InteractionCheckedView):
    """View used when removing facilities"""

    def __init__(
        self,
        *,
        timeout: float = 180,
        original_author: User | Member,
        facilities: list[Facility],
    ) -> None:
        super().__init__(timeout=timeout, original_author=original_author)
        self.facilities = facilities

    @ui.button(label="Remove", style=ButtonStyle.red)
    async def confirm(self, interaction: GuildInteraction, _: ui.Button) -> None:
        await self._finish_view(interaction)

        followup = interaction.followup
        try:
            await interaction.client.db.remove_facilities(self.facilities)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to remove facilities\n```py\n{exc}\n```", FeedbackType.ERROR
            )
            await followup.send(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed("Removed facilities", FeedbackType.SUCCESS)
            await followup.send(embed=embed, ephemeral=True)
            interaction.client.dispatch(
                "bulk_facility_delete",
                self.facilities,
                interaction,
            )


class ResetView(InteractionCheckedView):
    """View used when resetting and removing all facilities"""

    @ui.button(label="Confirm", style=ButtonStyle.primary)
    async def confirm(self, interaction: ClientInteraction, _: ui.Button) -> None:
        await self._finish_view(remove=True)
        resopnse = interaction.response

        try:
            await interaction.client.db.reset()
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to reset DB\n```py\n{exc}\n```", FeedbackType.ERROR
            )
            await resopnse.send_message(embed=embed, ephemeral=True)
            raise exc
        else:
            events_cog: Events | None = interaction.client.get_cog("Events")
            if events_cog is None:
                return

            query = """SELECT guild_id FROM list"""
            rows = await interaction.client.db.fetch(query)
            for row in rows:
                guild_id = row and row[0]
                guild = interaction.client.get_guild(guild_id)

            guilds = [interaction.client.get_guild(row[0]) for row in rows if row]
            filtered_guilds = list(filter(None, guilds))

            if not filtered_guilds:
                return

            for guild in filtered_guilds:
                await events_cog.update_list(guild)

            embed = FeedbackEmbed(
                f"Reset DB\nUpdated {len(filtered_guilds)} lists", FeedbackType.SUCCESS
            )
            await resopnse.send_message(embed=embed, delete_after=10)


class BaseServicesSelectView(InteractionCheckedView):
    """Base view used when creating or modifying services of a facility"""

    finish: Button

    def __init__(self, *, facility: Facility, original_author: User | Member) -> None:
        super().__init__(original_author=original_author)
        for item in (self.edit, self.quit):
            self.remove_item(item)
            self.add_item(item)
        self.initial_facility = copy(facility)
        self.facility = facility

        item_options = self.facility.item_services.select_options()

        self.item_select.options = item_options[:25]

        if len(item_options) > 25:
            self.excess_item_select.options = item_options[25:50]
        else:
            self.remove_item(self.excess_item_select)

        self.vehicle_select.options = self.facility.vehicle_services.select_options()

        self.original_button = (
            self.finish.label,
            self.finish.style,
            self.finish.disabled,
        )
        self.update_button()

    def update_button(self):
        try:
            self._checks()
        except ButtonMessage as exc:
            self.finish.label = str(exc)
            self.finish.style = ButtonStyle.blurple
            self.finish.disabled = True
        else:
            label, style, disabled = self.original_button

            self.finish.label = label
            self.finish.style = style
            self.finish.disabled = disabled

    def _checks(self) -> bool:
        if not self.facility.has_one_service():
            raise NoServices()

    def _update_item_services(self):
        values = self.item_select.values + self.excess_item_select.values
        item_services = ItemServiceFlags.from_menu(*values)

        self.facility.item_services = item_services
        self.item_select.options = item_services.select_options()[:25]
        self.excess_item_select.options = item_services.select_options()[25:50]

        self.update_button()

    @ui.select(
        placeholder="Select item services...",
        max_values=len(ItemServiceFlags[:25]),
        min_values=0,
    )
    async def item_select(self, interaction: GuildInteraction, _: ui.Select) -> None:
        self._update_item_services()

        embeds = self.facility.embeds()
        await interaction.response.edit_message(embeds=embeds, view=self)

    @ui.select(
        placeholder="(OVERFLOW) Select item services...",
        max_values=len(ItemServiceFlags[25:50]),
        min_values=0,
    )
    async def excess_item_select(
        self, interaction: GuildInteraction, _: ui.Select
    ) -> None:
        self._update_item_services()

        embeds = self.facility.embeds()
        await interaction.response.edit_message(embeds=embeds, view=self)

    @ui.select(
        placeholder="Select vehicle services...",
        max_values=len(VehicleServiceFlags),
        min_values=0,
    )
    async def vehicle_select(
        self, interaction: GuildInteraction, menu: ui.Select
    ) -> None:
        vehicle_services = VehicleServiceFlags.from_menu(*menu.values)

        self.facility.vehicle_services = vehicle_services
        menu.options = vehicle_services.select_options()

        self.update_button()
        embeds = self.facility.embeds()
        await interaction.response.edit_message(embeds=embeds, view=self)

    @ui.button(label="Add Description/Edit")
    async def edit(self, interaction: GuildInteraction, _: ui.Button) -> None:
        information = FacilityInformationModal(self.facility, self)
        await interaction.response.send_modal(information)

    @ui.button(label="Quit", style=ButtonStyle.red)
    async def quit(self, interaction: GuildInteraction, _: ui.Button) -> None:
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class CreateFacilityView(BaseServicesSelectView):
    """View when creating a facility"""

    @ui.button(label="Create", style=ButtonStyle.green)
    async def finish(self, interaction: GuildInteraction, _: ui.Button) -> None:
        await self._finish_view(interaction)
        if self.facility.creation_time is None:
            self.facility.creation_time = int(time())

        followup = interaction.followup
        try:
            facility_id = await interaction.client.db.add_facility(self.facility)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to create facility\n```py\n{exc}\n```", FeedbackType.ERROR
            )
            await followup.send(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed(
                f"Created facility with ID: `{facility_id}`", FeedbackType.SUCCESS
            )
            self.facility.id_ = facility_id
            await followup.send(
                embed=embed,
                ephemeral=True,
            )
            interaction.client.dispatch(
                "facility_create",
                self.facility,
                interaction,
            )


class ModifyFacilityView(BaseServicesSelectView):
    """View when modifying a facility"""

    def _checks(self) -> bool:
        super()._checks()

        if not self.facility.changed():
            raise NoChanges()

    @ui.button(label="Update", style=ButtonStyle.green)
    async def finish(self, interaction: GuildInteraction, _: ui.Button) -> None:
        await self._finish_view(interaction)
        if self.facility.creation_time is None:
            self.facility.creation_time = int(time())

        followup = interaction.followup
        try:
            await interaction.client.db.update_facility(self.facility)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to modify facility\n```py\n{exc}\n```", FeedbackType.ERROR
            )
            await followup.send(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed("Modified facility", FeedbackType.SUCCESS)
            await followup.send(embed=embed, ephemeral=True)
            interaction.client.dispatch(
                "facility_modify",
                self.initial_facility,
                self.facility,
                interaction,
            )
