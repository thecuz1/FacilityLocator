from typing import Union

from discord import Member, Guild, Thread, Interaction
from discord.abc import GuildChannel
from discord.ext import commands

from bot import FacilityBot


class Context(commands.Context):
    bot: FacilityBot


class ClientInteraction(Interaction[FacilityBot]):
    pass


class GuildInteraction(ClientInteraction):
    user: Member
    guild: Guild
    guild_id: int
    channel: Union[GuildChannel, Thread]
    channel_id: int
