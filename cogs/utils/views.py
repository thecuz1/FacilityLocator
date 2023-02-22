from time import time
from copy import copy

from discord import (
    ui,
    Interaction,
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
from .context import GuildInteraction


class ButtonMessage(Exception):
    pass


class NoServices(ButtonMessage):
    def __init__(self, *args: object) -> None:
        super().__init__("Select one service")


class NoChanges(ButtonMessage):
    def __init__(self, *args: object) -> None:
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
    async def confirm(self, interaction: Interaction, _: ui.Button) -> None:
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
            embed = FeedbackEmbed("Reset DB", FeedbackType.SUCCESS)
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

        self.item_select.options = self.facility.item_services.select_options()
        self.vehicle_select.options = self.facility.vehicle_services.select_options()

        self.original_button = (
            self.finish.label,
            self.finish.style,
            self.finish.disabled,
        )
        self._update_button()

    def _update_button(self):
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

    @ui.select(
        placeholder="Select item services...",
        max_values=len(ItemServiceFlags),
        min_values=0,
    )
    async def item_select(self, interaction: GuildInteraction, menu: ui.Select) -> None:
        item_services = ItemServiceFlags.from_menu(*menu.values)

        self.facility.item_services = item_services
        menu.options = item_services.select_options()

        self._update_button()
        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed, view=self)

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

        self._update_button()
        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed, view=self)

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
