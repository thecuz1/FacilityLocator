from discord import (
    ui,
    Interaction,
    ButtonStyle,
    Embed,
    NotFound,
    User,
    Member,
)
from .mixins import InteractionCheckedView


class Paginator(InteractionCheckedView):
    def __init__(self, *, timeout: float = 120, original_author: User | Member) -> None:
        super().__init__(timeout=timeout, original_author=original_author)

        self.ephemeral = None
        self.pages = None
        self.total_page_count = None
        self.author = None
        self.current_page = None
        self.original_message = None

    async def on_timeout(self) -> None:
        """Remove view on timeout
        """
        try:
            return await self.original_message.edit(view=None)
        except NotFound:
            pass

    async def start(
        self,
        interaction: Interaction,
        pages: list[Embed],
        ephemeral: bool = False
    ) -> None:
        """Start paginator

        Args:
            interaction (Interaction): Interaction to use
            pages (list[Embed]): List of embeds
        """
        self.ephemeral = ephemeral
        self.pages = pages
        self.total_page_count = len(pages)
        self.author = interaction.user
        self.current_page = 0

        self._update_labels(self.current_page)

        await interaction.response.send_message(
            embed=pages[self.current_page],
            view=self,
            ephemeral=ephemeral
        )
        self.original_message = await interaction.original_response()

    def _update_labels(self, page_number: int) -> None:
        max_pages = self.total_page_count
        self.go_to_first_page.disabled = page_number == 0
        self.go_to_last_page.disabled = max_pages is None or (page_number + 1) >= max_pages
        self.go_to_current_page.label = f'{page_number + 1}/{max_pages}'
        self.go_to_next_page.disabled = max_pages is not None and (page_number + 1) >= max_pages
        self.go_to_previous_page.disabled = page_number == 0

    async def show_page(self, interaction: Interaction, page_number: int) -> None:
        page = self.pages[page_number]
        self.current_page = page_number
        self._update_labels(page_number)
        if interaction.response.is_done():
            if self.original_message:
                await self.original_message.edit(embed=page, view=self)
        else:
            await interaction.response.edit_message(embed=page, view=self)

    async def show_checked_page(self, interaction: Interaction, page_number: int) -> None:
        max_pages = self.total_page_count
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(interaction, page_number)
            elif max_pages > page_number >= 0:
                await self.show_page(interaction, page_number)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    @ui.button(label='≪', style=ButtonStyle.grey)
    async def go_to_first_page(self, interaction: Interaction, _: ui.Button):
        """go to the first page"""
        await self.show_page(interaction, 0)

    @ui.button(label='Back', style=ButtonStyle.blurple)
    async def go_to_previous_page(self, interaction: Interaction, _: ui.Button):
        """go to the previous page"""
        await self.show_checked_page(interaction, self.current_page - 1)

    @ui.button(label='Current', style=ButtonStyle.grey, disabled=True)
    async def go_to_current_page(self, interaction: Interaction, button: ui.Button):
        pass

    @ui.button(label='Next', style=ButtonStyle.blurple)
    async def go_to_next_page(self, interaction: Interaction, _: ui.Button):
        """go to the next page"""
        await self.show_checked_page(interaction, self.current_page + 1)

    @ui.button(label='≫', style=ButtonStyle.grey)
    async def go_to_last_page(self, interaction: Interaction, _: ui.Button):
        """go to the last page"""
        await self.show_page(interaction, self.total_page_count - 1)
