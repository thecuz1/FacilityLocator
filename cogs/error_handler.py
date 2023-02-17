import logging

from discord.ext import commands
import discord
from discord.app_commands import errors, CommandOnCooldown

from bot import FacilityBot
from .utils.embeds import FeedbackEmbed, FeedbackType
from .utils.errors import MessageError

command_error_logger = logging.getLogger("command_error")


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot: FacilityBot):
        self.bot: FacilityBot = bot

    async def cog_load(self) -> None:
        tree = self.bot.tree
        tree.on_error = self.on_app_command_error

    async def cog_unload(self) -> None:
        tree = self.bot.tree
        tree.on_error = tree.__class__.on_error

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """The event triggered when an error is raised while invoking a command

        Args:
            ctx (commands.Context): The context used for command invocation
            error (commands.CommandError): The Exception raised
        """

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, "on_error"):
            return

        # This prevents any cogs with an overwritten cog_command_error being handled here.
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (
            commands.CommandNotFound,
            commands.DisabledCommand,
            commands.NoPrivateMessage,
            commands.NotOwner,
            commands.CheckFailure,
        )

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, "original", error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        if isinstance(
            error,
            (
                commands.BadArgument,
                commands.MissingRequiredArgument,
                commands.TooManyArguments,
            ),
        ):
            return await ctx.send(str(error))

        # All other Errors not returned come here.
        command_error_logger.error(
            "Ignoring exception in command %r", ctx.command.name, exc_info=error
        )

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
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
                embed = FeedbackEmbed(
                    f"Try again in {error.retry_after:.2f}s", FeedbackType.COOLDOWN
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

            if isinstance(error, errors.MissingPermissions):
                embed = FeedbackEmbed(
                    f"Missing the following permissions {error.missing_permissions}",
                    FeedbackType.ERROR,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

            if isinstance(error, MessageError):
                embed = FeedbackEmbed(
                    error.message,
                    FeedbackType.ERROR,
                )
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

            ignored = (errors.CheckFailure, errors.TransformerError)

            if isinstance(error, ignored):
                return

            command_error_logger.error(
                "Ignoring exception in command %r", command.name, exc_info=error
            )
        else:
            command_error_logger.error(
                "Ignoring exception in command tree", exc_info=error
            )


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(CommandErrorHandler(bot))
