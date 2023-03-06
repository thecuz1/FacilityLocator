from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord.ui import View, Item, Modal
from discord.errors import NotFound
from discord.ext import commands


if TYPE_CHECKING:
    from discord import Interaction, User, Member, Message

    from bot import FacilityBot


view_error_logger = logging.getLogger("view_error")
modal_error_logger = logging.getLogger("modal_error")


class BaseView(View):
    """Subclass of view that adds basic functionality"""

    def __init__(self, *, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.message: Message | None = None

    async def send(
        self,
        ctx_or_interaction: commands.Context[FacilityBot] | Interaction,
        *args,
        **kwargs,
    ) -> Message:
        if isinstance(ctx_or_interaction, commands.Context):
            ctx = ctx_or_interaction
            self.message = await ctx.send(args, kwargs, view=self)
        else:
            interaction = ctx_or_interaction
            await interaction.response.send_message(*args, **kwargs, view=self)
            self.message = await interaction.original_response()
        return self.message

    async def on_timeout(self) -> None:
        """Call finish view"""
        await self._finish_view()

    async def _finish_view(
        self, interaction: Interaction | None = None, remove: bool = False
    ) -> None:
        self.stop()
        if remove:
            try:
                await self.message.delete()
            except NotFound:
                pass
            return

        if interaction:
            await interaction.response.defer(ephemeral=True, thinking=True)

        for item in self.children:
            item.disabled = True

        if self.message:
            try:
                await self.message.edit(view=self)
            except NotFound:
                pass

    async def on_error(self, _: Interaction, error: Exception, item: Item, /) -> None:
        """Log any error that happens in a view

        Args:
            interaction (Interaction): The interaction that led to the failure.
            error (Exception): The exception that was raised.
            item (Item): The item that failed the dispatch.
        """
        view_error_logger.error(
            "Ignoring exception in view %r for item %r", self, item, exc_info=error
        )


class ErrorLoggedModal(Modal):
    """Subclass of ui.Modal to log any errors to the correct place"""

    async def on_error(self, interaction: Interaction, error: Exception, /) -> None:
        """Log any error that happens in a Modal

        Args:
            interaction (Interaction): The interaction that led to the failure.
            error (Exception): The exception that was raised.
            item (Item): The item that failed the dispatch.
        """
        modal_error_logger.error(
            "Ignoring exception in modal %r:", self, exc_info=error
        )


class InteractionCheckedView(BaseView):
    """View to check interaction"""

    def __init__(self, *, timeout: float = 180, original_author: User | Member) -> None:
        super().__init__(timeout=timeout)
        self.original_author = original_author

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        """Only allow bot owner and author to control the menu

        Args:
            interaction (Interaction): Interaction to check

        Returns:
            bool: Whether to process the interaction
        """
        if interaction.user and interaction.user.id in (
            interaction.client.owner_id,
            self.original_author.id,
        ):
            return True
        await interaction.response.send_message(
            ":x: This menu cannot be controlled by you!",
            ephemeral=True,
        )
        return False
