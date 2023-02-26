from discord.app_commands import AppCommandError


class MessageError(AppCommandError):
    def __init__(self, message: str, ephemeral: bool = True):
        self.message: str = message
        self.ephemeral: bool = ephemeral
