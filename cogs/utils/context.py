from typing import Union

from discord import Member, Guild, VoiceChannel, TextChannel, Thread, Interaction
from discord.abc import GuildChannel
from discord.ext import commands

from bot import FacilityBot


class GuildContext(commands.Context):
    author: Member
    guild: Guild
    channel: Union[VoiceChannel, TextChannel, Thread]
    me: Member
    prefix: str


class GuildInteraction(Interaction):
    user: Member
    guild: Guild
    guild_id: int
    channel: Union[GuildChannel, Thread]
    channel_id: int
    client: FacilityBot
