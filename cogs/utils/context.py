from __future__ import annotations

from typing import Union, TYPE_CHECKING

from discord import Member, Guild, Thread, Interaction
from discord.ext import commands


if TYPE_CHECKING:
    from discord.abc import GuildChannel

    from bot import FacilityBot


class Context(commands.Context):
    bot: FacilityBot


class ClientInteraction(Interaction):
    client: FacilityBot


class GuildInteraction(ClientInteraction):
    user: Member
    guild: Guild
    guild_id: int
    channel: Union[GuildChannel, Thread]
    channel_id: int
