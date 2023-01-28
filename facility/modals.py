from discord.ui import TextInput
from discord import TextStyle, Interaction
from utils.mixins import ErrorLoggedModal
from facility.main import Facility


class FacilityInformationModal(ErrorLoggedModal, title="Edit Facility Information"):
    """Modal to be shown to the user when editing basic info about a facility"""

    def __init__(self, facility: Facility) -> None:
        super().__init__()
        self.name = TextInput(
            label="Facility Name",
            max_length=100,
        )
        self.maintainer = TextInput(
            label="Maintainer",
            max_length=200,
        )
        self.image_url = TextInput(
            label="Image URL",
            required=False,
            max_length=300,
        )
        self.description = TextInput(
            label="Description",
            style=TextStyle.paragraph,
            required=False,
            max_length=1024,
        )
        for key, value in self.__dict__.items():
            if not isinstance(value, TextInput):
                continue
            value.default = getattr(facility, key, None)
            self.add_item(value)

        self.facility: Facility = facility

    async def on_submit(self, interaction: Interaction, /) -> None:
        for key, value in self.__dict__.items():
            if not isinstance(value, TextInput):
                continue
            setattr(self.facility, key, str(value))

        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed)
