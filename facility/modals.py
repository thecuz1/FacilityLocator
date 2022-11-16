from discord.ui import TextInput
from discord import TextStyle, Interaction
from utils.error_inheritance import ErrorLoggedModal
from facility.main import Facility


class FacilityInformationModal(ErrorLoggedModal, title="Edit Facility Information"):
    """Modal to be shown to the user when editing basic info about a facility
    """
    def __init__(self, facility: Facility) -> None:
        super().__init__()
        self.name = TextInput(
            label="Facility Name",
            default=facility.name,
            max_length=100,
        )
        self.maintainer = TextInput(
            label="Maintainer",
            default=facility.maintainer,
            max_length=200,
        )
        self.description = TextInput(
            label="Description",
            style=TextStyle.paragraph,
            required=False,
            default=facility.description,
            max_length=1024,
        )
        for item in (self.name, self.maintainer, self.description):
            self.add_item(item)
        self.facility = facility

    async def on_submit(self, interaction: Interaction, /) -> None:
        self.facility.name = str(self.name)
        self.facility.maintainer = str(self.maintainer)
        self.facility.description = str(self.description)

        embed = self.facility.embed()
        await interaction.response.edit_message(embed=embed)
