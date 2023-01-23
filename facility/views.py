from time import time
from discord import (
    ui,
    errors,
    Interaction,
    User,
    Member,
    ButtonStyle,
    Message,
    TextChannel,
)
from discord.ext.commands import Bot
from facility.modals import FacilityInformationModal
from facility.main import Facility

from utils.mixins import InteractionCheckedView
from utils.feedback import FeedbackEmbed, feedbackType
from data import ITEM_SERVICES, VEHICLE_SERVICES


class BaseFacilityView(InteractionCheckedView):
    """Base view used for a facility"""

    def __init__(
        self, *, timeout: float = 180, original_author: User | Member, bot: Bot
    ) -> None:
        super().__init__(timeout=timeout, original_author=original_author)
        self.message: Message | None = None
        self.bot: Bot = bot

    async def on_timeout(self) -> None:
        """Call finish view"""
        await self._finish_view(None)

    async def _finish_view(self, interaction: Interaction | None) -> None:
        self.stop()
        for item in self.children:
            item.disabled = True

        if interaction:
            await interaction.response.edit_message(view=self)
        else:
            if self.message:
                try:
                    await self.message.edit(view=self)
                except errors.NotFound:
                    pass


class DynamicListConfirm(BaseFacilityView):
    """View used when setting a dynamic list"""

    def __init__(
        self,
        *,
        timeout: float = 180,
        original_author: User | Member,
        bot: Bot,
        selected_channel: TextChannel,
        facilities: list[Facility],
    ) -> None:
        super().__init__(timeout=timeout, original_author=original_author, bot=bot)
        self.selected_channel: TextChannel = selected_channel
        self.facilities: list[Facility] = facilities

    @ui.button(label="Disable list", style=ButtonStyle.danger)
    async def disable(self, interaction: Interaction, _: ui.Button):
        await self._finish_view(interaction)
        followup = interaction.followup

        try:
            await self.bot.db.remove_list(interaction.guild)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to remove list channel\n```py\n{exc}\n```", feedbackType.ERROR
            )
            await followup.send(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed("Disabled list channel", feedbackType.SUCCESS)
            await followup.send(embed=embed, ephemeral=True)

    @ui.button(label="Confirm", style=ButtonStyle.primary)
    async def confirm(self, interaction: Interaction, _: ui.Button) -> None:
        await self._finish_view(interaction)
        followup = interaction.followup

        # circular import
        from facility import create_list

        facility_list = create_list(self.facilities, interaction.guild)
        messages = []
        for embed in facility_list:
            message = await self.selected_channel.send(embed=embed)
            messages.append(message.id)

        try:
            await self.bot.db.set_list(
                interaction.guild, self.selected_channel, messages
            )
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to set list channel\n```py\n{exc}\n```", feedbackType.ERROR
            )
            await followup.send(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed("Set list channel", feedbackType.SUCCESS)
            await followup.send(embed=embed, ephemeral=True)


class RemoveFacilitiesView(BaseFacilityView):
    """View used when removing facilities"""

    def __init__(
        self,
        *,
        timeout: float = 180,
        original_author: User | Member,
        bot: Bot,
        facilities: list[Facility],
    ) -> None:
        super().__init__(timeout=timeout, original_author=original_author, bot=bot)
        self.facilities = facilities

    @ui.button(label="Confirm", style=ButtonStyle.primary)
    async def confirm(self, interaction: Interaction, _: ui.Button) -> None:
        await self._finish_view(interaction)

        followup = interaction.followup
        try:
            await self.bot.db.remove_facilities(self.facilities)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to remove facilities\n```py\n{exc}\n```", feedbackType.ERROR
            )
            await followup.send(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed("Removed facilities", feedbackType.SUCCESS)
            await followup.send(embed=embed, ephemeral=True)
            self.bot.dispatch(
                "bulk_facility_delete",
                self.facilities,
                interaction.user,
                interaction.guild,
            )


class ResetView(BaseFacilityView):
    """View used when resetting and removing all facilities"""

    async def _finish_view(self, interaction: Interaction | None) -> None:
        self.stop()

        try:
            await self.message.delete()
        except errors.NotFound:
            pass

    @ui.button(label="Confirm", style=ButtonStyle.primary)
    async def confirm(self, interaction: Interaction, _: ui.Button) -> None:
        await self._finish_view(None)
        resopnse = interaction.response

        try:
            await self.bot.db.reset()
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to reset DB\n```py\n{exc}\n```", feedbackType.ERROR
            )
            await resopnse.send_message(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed("Reset DB", feedbackType.SUCCESS)
            await resopnse.send_message(embed=embed, delete_after=10)


class BaseServicesSelectView(BaseFacilityView):
    """Base view used when creating or modifying services of a facility"""

    def __init__(
        self, *, facility: Facility, original_author: User | Member, bot: Bot
    ) -> None:
        super().__init__(original_author=original_author, bot=bot)
        self.facility = facility
        self._update_options()

    def _update_options(self) -> None:
        self.item_select.options = self.facility.select_options(False)
        self.vehicle_select.options = self.facility.select_options(True)

    @ui.select(
        placeholder="Select item services...",
        max_values=len(ITEM_SERVICES),
        min_values=0,
    )
    async def item_select(self, interaction: Interaction, menu: ui.Select) -> None:
        self.facility.set_services(menu.values, False)
        self._update_options()
        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.select(
        placeholder="Select vehicle services...",
        max_values=len(VEHICLE_SERVICES),
        min_values=0,
    )
    async def vehicle_select(self, interaction: Interaction, menu: ui.Select) -> None:
        self.facility.set_services(menu.values, True)
        self._update_options()
        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(label="Add Description/Edit")
    async def edit(self, interaction: Interaction, _: ui.Button) -> None:
        information = FacilityInformationModal(self.facility)
        await interaction.response.send_modal(information)


class CreateFacilityView(BaseServicesSelectView):
    """View when creating a facility"""

    async def _checks(self, interaction: Interaction) -> bool:
        if self.facility.item_services == 0 and self.facility.vehicle_services == 0:
            embed = FeedbackEmbed(
                "Please select at least one service", feedbackType.WARNING
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return False
        return True

    @ui.button(label="Finish", style=ButtonStyle.primary)
    async def finish(self, interaction: Interaction, _: ui.Button) -> None:
        should_continue = await self._checks(interaction)
        if should_continue is False:
            return

        await self._finish_view(interaction)
        if self.facility.creation_time is None:
            self.facility.creation_time = int(time())

        followup = interaction.followup
        try:
            facility_id = await self.bot.db.add_facility(self.facility)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to create facility\n```py\n{exc}\n```", feedbackType.ERROR
            )
            await followup.send(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed(
                f"Created facility with ID: `{facility_id}`", feedbackType.SUCCESS
            )
            self.facility.id_ = facility_id
            await followup.send(
                embed=embed,
                ephemeral=True,
            )
            self.bot.dispatch(
                "facility_create", self.facility, interaction.user, interaction.guild
            )


class ModifyFacilityView(BaseServicesSelectView):
    """View when modifying a facility"""

    async def _checks(self, interaction: Interaction) -> bool:
        if self.facility.item_services == 0 and self.facility.vehicle_services == 0:
            embed = FeedbackEmbed(
                "Please select at least one service", feedbackType.WARNING
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return False

        if self.facility.changed() is False:
            embed = FeedbackEmbed("No changes", feedbackType.WARNING)
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return False
        return True

    @ui.button(label="Finish", style=ButtonStyle.primary)
    async def finish(self, interaction: Interaction, _: ui.Button) -> None:
        should_continue = await self._checks(interaction)
        if should_continue is False:
            return

        await self._finish_view(interaction)
        if self.facility.creation_time is None:
            self.facility.creation_time = int(time())

        followup = interaction.followup
        try:
            await self.bot.db.update_facility(self.facility)
        except Exception as exc:
            embed = FeedbackEmbed(
                f"Failed to modify facility\n```py\n{exc}\n```", feedbackType.ERROR
            )
            await followup.send(embed=embed, ephemeral=True)
            raise exc
        else:
            embed = FeedbackEmbed("Modified facility", feedbackType.SUCCESS)
            await followup.send(embed=embed, ephemeral=True)
            self.bot.dispatch(
                "facility_modify", self.facility, interaction.user, interaction.guild
            )
