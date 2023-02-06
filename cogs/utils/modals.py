from discord.ui import TextInput
from discord import TextStyle, Interaction

from .mixins import ErrorLoggedModal
from .facility import Facility


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

    def __init__(self, facility: Facility) -> None:
        super().__init__()
        for key, value in self.__dict__.items():
            if not isinstance(value, TextInput):
                continue
            value.default = getattr(facility, key, None)

        self.facility: Facility = facility

    async def on_submit(self, interaction: Interaction, /) -> None:
        for key, value in self.__dict__.items():
            if not isinstance(value, TextInput):
                continue
            setattr(self.facility, key, str(value))

        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed)
