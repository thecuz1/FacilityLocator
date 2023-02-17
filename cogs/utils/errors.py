from discord.app_commands import AppCommandError


class MessageError(AppCommandError):
    def __init__(self, message: str):
        self.message: str = message
