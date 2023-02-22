from urllib.parse import urlparse
import logging

from discord.ui import TextInput
from discord import TextStyle, Interaction, HTTPException, Embed, Colour

from .mixins import ErrorLoggedModal
from .facility import Facility

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

    def __init__(self, facility: Facility, view) -> None:
        super().__init__()
        self.view = view
        self.old_image_url = facility.image_url

        for key, value in self.__dict__.items():
            if not isinstance(value, TextInput):
                continue
            value.default = getattr(facility, key, None)

        self.facility: Facility = facility

    async def on_submit(self, interaction: Interaction, /) -> None:
        for key, value in self.__dict__.items():
            if not isinstance(value, TextInput):
                continue
            stripped_value = str(value).strip()
            setattr(self.facility, key, stripped_value)

        embed_list: list[Embed] = []

        url = self.facility.image_url
        if url:
            valid = self._check_url(url)
            if not valid:
                self.facility.image_url = self.old_image_url

                invalid_url_embed = Embed(
                    description=":x: | image_url was invalid and has been reset",
                    colour=Colour.red(),
                )
                embed_list.append(invalid_url_embed)

        self.view._update_button()
        embed_list.insert(0, self.facility.embed())
        try:
            await interaction.response.edit_message(embeds=embed_list, view=self.view)
        except HTTPException as exc:
            if exc.code != 50035:
                raise exc
            logger.exception("URL: %r was rejected", url)
            self.facility.image_url = self.old_image_url

    def _check_url(self, url: str):
        if " " in url:
            return False

        result = urlparse(url)

        if result.scheme not in ("https", "http"):
            return False

        sld, _, tld = result.netloc.rpartition(".")
        if not sld or not len(tld) >= 2:
            return False

        return True
