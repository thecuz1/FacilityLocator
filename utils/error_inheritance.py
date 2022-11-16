import logging
from discord.ui import View, Item, Modal
from discord import Interaction

view_error_logger = logging.getLogger("view_error")
modal_error_logger = logging.getLogger("modal_error")


class ErrorLoggedView(View):
    """Subclass of ui.View to log any errors to the correct place"""

    async def on_error(
        self, interaction: Interaction, error: Exception, item: Item, /
    ) -> None:
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

    async def on_error(
        self, interaction: Interaction, error: Exception, item: Item, /
    ) -> None:
        """Log any error that happens in a Modal

        Args:
            interaction (Interaction): The interaction that led to the failure.
            error (Exception): The exception that was raised.
            item (Item): The item that failed the dispatch.
        """
        modal_error_logger.error(
            "Ignoring exception in modal %r for item %r", self, item, exc_info=error
        )
