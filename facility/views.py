from time import time
import logging
from discord import ui, errors, Interaction, User, Member, ButtonStyle, Message
from discord.ext.commands import Bot
from facility.modals import FacilityInformationModal
from facility.main import Facility
from utils.mixins import InteractionCheckedView
from utils.feedback import FeedbackEmbed, feedbackType
from data import ITEM_SERVICES, VEHICLE_SERVICES

facility_logger = logging.getLogger("facility_event")


class BaseFacilityView(InteractionCheckedView):
    """Base view used for a facility"""

    def __init__(
        self, *, timeout: float = 180, original_author: User | Member, bot: Bot
    ) -> None:
        super().__init__(timeout=timeout, original_author=original_author)
        self.message: Message | None = None
        self.bot = bot

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
            facility_logger.info(
                "Facility ID(s) %r removed by %s",
                [facility.id_ for facility in self.facilities],
                interaction.user.mention,
                extra={
                    "guild_id": interaction.guild_id,
                    "guild_name": interaction.guild.name,
                },
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
                f"Created facility with the ID: `{facility_id}`", feedbackType.SUCCESS
            )
            await followup.send(
                embed=embed,
                ephemeral=True,
            )
            facility_logger.info(
                "Facility created by %s",
                interaction.user.mention,
                extra={
                    "guild_id": interaction.guild_id,
                    "guild_name": interaction.guild.name,
                },
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
            facility_logger.info(
                "Facility ID %r modified by %s",
                self.facility.id_,
                interaction.user.mention,
                extra={
                    "guild_id": interaction.guild_id,
                    "guild_name": interaction.guild.name,
                },
            )
