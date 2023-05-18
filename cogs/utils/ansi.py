from enum import Enum


class Format(Enum):
    NORMAL = 0
    BOLD = 1
    UNDERLINE = 4


class Colour(Enum):
    GREY = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    PINK = 35
    CYAN = 36
    WHITE = 37
    BACKGROUND_FIREFLY_DARK_BLUE = 40
    BACKGROUND_ORANGE = 41
    BACKGROUND_MARBLE_BLUE = 42
    BACKGROUND_GREYISH_TURQUOISE = 43
    BACKGROUND_GREY = 44
    BACKGROUND_INDIGO = 45
    BACKGROUND_LIGHT_GREY = 46
    BACKGROUND_WHITE = 47


class ANSIColour:
    prefix = "["
    suffix = "m"

    def __init__(
        self,
        bold: bool = False,
        underline: bool = False,
        background_colour: Colour | None = None,
        text_colour: Colour | None = None,
    ) -> None:
        self.parts = [0]

        if bold:
            self.parts.append(Format.BOLD.value)

        if underline:
            self.parts.append(Format.UNDERLINE.value)

        if background_colour:
            self.parts.append(background_colour.value)

        if text_colour:
            self.parts.append(text_colour.value)

    def __str__(self) -> str:
        parts = [str(part) for part in self.parts]
        joined_parts = ";".join(parts)
        return f"{self.prefix}{joined_parts}{self.suffix}"
