from __future__ import annotations

import logging
from urllib.parse import urlparse
from typing import TYPE_CHECKING, Generator

from discord.ui import TextInput
from discord import TextStyle, Interaction, HTTPException, Embed, Colour

from .mixins import ErrorLoggedModal


if TYPE_CHECKING:
    from .facility import Facility
    from .views import BaseServicesSelectView


logger = logging.getLogger(__name__)


class FacilityInformationModal(ErrorLoggedModal, title="Edit Facility Information"):
    """Modal to be shown to the user when editing basic info about a facility"""

    name = TextInput(
        label="Facility Name",
        min_length=1,
        max_length=100,
    )
    maintainer = TextInput(
        label="Maintainer",
        min_length=1,
        max_length=200,
    )
    image_url = TextInput(
        label="Image URL",
        required=False,
        max_length=300,
    )
    description = TextInput(
        label="Description",
        style=TextStyle.paragraph,
        required=False,
        max_length=1024,
    )

    def __init__(self, facility: Facility, view: BaseServicesSelectView) -> None:
        super().__init__()

        self.facility: Facility = facility
        self.old_image_url = facility.image_url

        self.view: BaseServicesSelectView = view

        for name, text_input in self._text_imputs():
            text_input.default = getattr(facility, name)

    def _text_imputs(self) -> Generator[tuple[str, TextInput], None, None]:
        for key, value in self.__dict__.items():
            if not isinstance(value, TextInput):
                continue
            yield key, value

    async def on_submit(self, interaction: Interaction, /) -> None:
        for name, text_input in self._text_imputs():
            stripped_value = str(text_input).strip()
            setattr(self.facility, name, stripped_value)

        embed_list: list[Embed] = []

        url = self.facility.image_url
        if self._url_valid(url) is False:
            self.facility.image_url = self.old_image_url

            invalid_url_embed = Embed(
                description=":x: | image_url was invalid and has been reset",
                colour=Colour.red(),
            )
            embed_list.append(invalid_url_embed)

        self.view.update_button()
        embed_list = self.facility.embeds() + embed_list
        try:
            await interaction.response.edit_message(embeds=embed_list, view=self.view)
        except HTTPException as exc:
            if exc.code != 50035:
                raise exc
            logger.exception("URL: %r was rejected", url)
            self.facility.image_url = self.old_image_url

    def _url_valid(self, url: str):
        if "" == url:
            return True

        if " " in url:
            return False

        result = urlparse(url)

        if result.scheme not in ("https", "http"):
            return False

        sld, _, tld = result.netloc.rpartition(".")
        tld, _, _ = tld.partition(":")
        if not sld or len(tld) < 2:
            return False

        return True
