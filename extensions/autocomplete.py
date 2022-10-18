import discord
from discord.ext import commands
from discord import app_commands

regions = ['DeadLands', 'Ash Fields', 'Westgate',
                        'Kalokai', 'Red River', 'Achrithia', 'Terminus', 'The Fingers', 'Origin', 'Great March', 'The HeartLands', 'Shackled Chasm', 'Umbral Wildwood', 'Allods Bright', 'The Drowned Vale', 'Tempest Island', 'Fishermans Row', 'Loch Mór', 'Endless Shore', 'Godcrofts', 'Farranac Coast', 'The Oarbreaker Isles', 'Marban Hollow', 'Weathered Expanse', 'Morgens Crossing', 'The Linn of Mercy', 'Stonecradle', 'Nevish Line', 'Callahans Passage', 'Viper Pit', 'Clanshead Valley', 'The Moors', 'Callums Cape', 'Reaching Trail', 'Howl County', 'Speaking Woods', 'Basin Sionnach']


async def region_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    choice_list = [app_commands.Choice(name=region, value=region)
                   for region in regions if current.lower() in region.lower()]
    if len(choice_list) > 25:
        choice_list = choice_list[0:25]
    return choice_list
