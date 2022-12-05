import logging
from discord import Guild
from discord.ext import commands

guild_logger = logging.getLogger("guild_event")


class Events(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(
        self,
        guild: Guild,
    ) -> None:
        """Logs when the bot joins a guild

        Args:
            guild (Guild): Guild the bot joined
        """
        guild_logger.info("Bot joined %r (%s)", guild.id, guild.name)

    @commands.Cog.listener()
    async def on_guild_remove(
        self,
        guild: Guild,
    ) -> None:
        """Logs when the bot is remove from a guild

        Args:
            guild (Guild): Guild the bot was remove from
        """
        guild_logger.info("Bot removed from %r (%s)", guild.id, guild.name)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
