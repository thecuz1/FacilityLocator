import logging
from discord.ext import commands
import discord
from discord.app_commands import errors, CommandOnCooldown

command_error_logger = logging.getLogger('command_error')


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ) -> None:
        """The event triggered when an error is raised while invoking a command

        Args:
            ctx (commands.Context): The context used for command invocation
            error (commands.CommandError): The Exception raised
        """

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return

        # This prevents any cogs with an overwritten cog_command_error being handled here.
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.CommandNotFound, commands.DisabledCommand, commands.NoPrivateMessage)

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        if isinstance(error, commands.BadArgument):
            return

        # All other Errors not returned come here.
        command_error_logger.error('Ignoring exception in command %r', ctx.command.name, exc_info=error)

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError
    ) -> None:
        """The event triggered when an error is raised while invoking a app command

        Args:
            interaction (discord.Interaction): The interaction used for command invocation
            error (discord.app_commands.AppCommandError): The Exception raised
        """
        command = interaction.command

        if command is not None:
            if command._has_any_error_handlers():
                return

            if isinstance(error, CommandOnCooldown):
                return await interaction.response.send_message(f':hourglass: {str(error)}', ephemeral=True)

            if isinstance(error, errors.TransformerError):
                return

            command_error_logger.error('Ignoring exception in command %r', command.name, exc_info=error)
        else:
            command_error_logger.error('Ignoring exception in command tree', exc_info=error)


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(CommandErrorHandler(bot))
