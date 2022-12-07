from enum import Enum, auto
from discord import Embed, Colour
import traceback


class feedbackType(Enum):
    SUCCESS = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    COOLDOWN = auto()


class FeedbackEmbed(Embed):
    def __init__(
        self, message: str, feedback_type: feedbackType, exception: Exception = None
    ):
        match feedback_type:
            case feedbackType.SUCCESS:
                title = "Success"
                final_message = f":white_check_mark: | {message}"
                embed_colour = Colour.brand_green()
            case feedbackType.INFO:
                title = "Info"
                final_message = f":information_source: | {message}"
                embed_colour = Colour.blue()
            case feedbackType.WARNING:
                title = "Warning"
                final_message = f":warning: | {message}"
                embed_colour = Colour.yellow()
            case feedbackType.ERROR:
                title = "Error"
                final_message = f":x: | {message}"
                embed_colour = Colour.brand_red()
                if exception:
                    formatted_exception = "\n".join(
                        traceback.format_exception(exception)
                    )
                    final_message += f"\n```py\n{formatted_exception}\n```"
            case feedbackType.COOLDOWN:
                title = "Cooldown"
                final_message = f":hourglass: | {message}"
                embed_colour = Colour.blue()

        super().__init__(colour=embed_colour, title=title, description=final_message)
        self.set_footer(text="Source Code: https://github.com/thecuz1/FacilityLocator")
