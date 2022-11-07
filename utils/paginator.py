from typing import Optional
import discord


class PaginationButton(discord.ui.Button):
    def __init__(self, *, emoji: discord.PartialEmoji, next_button: bool):
        super().__init__(emoji=emoji)
        self.next_button = next_button

    async def callback(self, interaction: discord.Interaction) -> None:
        view: Paginator = self.view
        if self.next_button is True:
            if view.current_page == view.total_page_count:
                view.current_page = 1
            else:
                view.current_page += 1
        else:
            if view.current_page == 1:
                view.current_page = view.total_page_count
            else:
                view.current_page -= 1
        view.page_counter.current_page = view.current_page
        await interaction.response.edit_message(embed=view.pages[self.view.current_page - 1], view=view)


class PaginatorPageCounter(discord.ui.Button):
    def __init__(self, current_page: int, total_pages: int) -> None:
        super().__init__(disabled=True)
        self._current_page = current_page
        self.total_pages = total_pages
        self.set_label()

    @property
    def current_page(self):
        return self._current_page

    @current_page.setter
    def current_page(self, new_page: int):
        self._current_page = new_page
        self.set_label()

    def set_label(self) -> None:
        self.label = f'{self.current_page}/{self.total_pages}'


class Paginator(discord.ui.View):
    def __init__(self, *, timeout: Optional[float] = 120) -> None:
        super().__init__(timeout=timeout)

        self.pages = None
        self.total_page_count = None
        self.current_page = 1
        self.original_message = None
        self.author = None
        self.page_counter = None
        self.ephemeral = None

    async def on_timeout(self) -> None:
        """Remove or edit original message on timeout
        """
        try:
            if self.ephemeral:
                return await self.original_message.edit(view=None)
            return await self.original_message.delete()
        except discord.NotFound:
            pass

    async def start(self, interaction: discord.Interaction, pages: list[discord.Embed], ephemeral: bool = False) -> None:
        """Start paginator

        Args:
            interaction (discord.Interaction): Interaction to use
            pages (list[discord.Embed]): List of embeds
        """
        self.ephemeral = ephemeral
        self.pages = pages
        self.total_page_count = len(pages)
        self.author = interaction.user

        previous_button = PaginationButton(emoji=discord.PartialEmoji(name='\U000025c0'), next_button=False)
        self.page_counter = PaginatorPageCounter(self.current_page, self.total_page_count)
        next_button = PaginationButton(emoji=discord.PartialEmoji(name='\U000025b6'), next_button=True)

        for item in (previous_button, self.page_counter, next_button):
            self.add_item(item)

        await interaction.response.send_message(embed=pages[self.current_page - 1], view=self, ephemeral=ephemeral)
        self.original_message = await interaction.original_response()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ignore any interaction that wasn't triggered by the original author

        Args:
            interaction (discord.Interaction): Interaction to check

        Returns:
            bool: Whether to process the interaction
        """
        return interaction.user.id == self.author.id
