from discord import app_commands, Member, Permissions
from discord.ext import commands

from bot import FacilityBot
from .utils.context import GuildInteraction
from .utils.facility import Facility
from .utils.views import ModifyFacilityView, RemoveFacilitiesView
from .utils.embeds import FeedbackEmbed, FeedbackType
from .utils.transformers import FacilityTransformer, IdTransformer
from .utils.errors import MessageError


class Admin(commands.Cog):
    def __init__(self, bot: FacilityBot):
        self.bot: FacilityBot = bot

    admin_modify = app_commands.Group(
        name="admin_modify",
        description="Modify facilities",
        guild_only=True,
        default_permissions=Permissions(administrator=True),
    )

    @admin_modify.command(name="facility")
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def modify_facility(
        self,
        interaction: GuildInteraction,
        facility: app_commands.Transform[Facility, FacilityTransformer],
    ):
        """Modify faciliy information

        Args:
            facility (app_commands.Transform[Facility, FacilityTransformer]): Facility to modify, also accepts ID
        """

        view = ModifyFacilityView(facility=facility, original_author=interaction.user)
        embeds = facility.embeds()

        await view.send(interaction, embeds=embeds, ephemeral=True)

    admin_remove = app_commands.Group(
        name="admin_remove",
        description="Remove facilities",
        guild_only=True,
        default_permissions=Permissions(administrator=True),
    )

    @admin_remove.command()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def user(self, interaction: GuildInteraction, user: Member):
        """Removes all of the users facilities for the current guild

        Args:
            user (Member): Member's facilities to remove
        """
        search_dict = {
            " guild_id == ? ": interaction.guild_id,
            " author == ? ": user.id,
        }
        facilities = await self.bot.db.get_facilities(search_dict)

        if not facilities:
            raise MessageError("No facilities")

        facility_amount = len(facilities)
        embed = FeedbackEmbed(
            f"Confirm removing {facility_amount} facilit{'ies' if facility_amount > 1 else 'y'} created by {user.mention} from {interaction.guild.name}",
            FeedbackType.WARNING,
        )
        view = RemoveFacilitiesView(
            original_author=interaction.user, facilities=facilities
        )

        await view.send(interaction, embed=embed, ephemeral=True)

    @admin_remove.command()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def ids(
        self,
        interaction: GuildInteraction,
        ids: app_commands.Transform[tuple[int], IdTransformer],
    ):
        """Removes facilities by ID's for the current guild

        Args:
            ids (app_commands.Transform[tuple, IdTransformer]): List of facility ID's to remove with a delimiter of ',' or a space ' ' Ex. 1,3 4 8
        """
        facilities = await self.bot.db.get_facility_ids(ids, interaction.guild_id)

        if not facilities:
            raise MessageError("No facilities")

        facility_amount = len(facilities)
        not_found_facilities = len(ids) - len(facilities)
        embed = FeedbackEmbed(
            f"Confirm removing {facility_amount} facilit{'ies' if facility_amount > 1 else 'y'} from {interaction.guild.name}",
            FeedbackType.WARNING,
        )
        view = RemoveFacilitiesView(
            original_author=interaction.user, facilities=facilities
        )

        not_found_message = (
            f":x: {not_found_facilities} facilit{'ies' if not_found_facilities > 1 else 'y'} not found"
            if not_found_facilities > 0
            else ""
        )

        await view.send(
            interaction,
            content=not_found_message,
            embed=embed,
            ephemeral=True,
        )

    @admin_remove.command()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def all(self, interaction: GuildInteraction):
        """Removes all facilities for the current guild"""

        search_dict = {"guild_id == ?": interaction.guild_id}
        facilities = await self.bot.db.get_facilities(search_dict)

        if not facilities:
            raise MessageError("No facilities found")

        facility_amount = len(facilities)
        embed = FeedbackEmbed(
            f"Confirm removing {facility_amount} facilit{'ies' if facility_amount > 1 else 'y'} from {interaction.guild.name}",
            FeedbackType.WARNING,
        )
        view = RemoveFacilitiesView(
            original_author=interaction.user, facilities=facilities
        )

        await view.send(
            interaction,
            embed=embed,
            ephemeral=True,
        )

    @admin_remove.command(name="facility")
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def remove_facility(
        self,
        interaction: GuildInteraction,
        facility: app_commands.Transform[Facility, FacilityTransformer],
    ):
        """Removes a single facility

        Args:
            facility (app_commands.Transform[Facility, FacilityTransformer]): Facility to remove, also accepts ID
        """

        facility_list = [facility]

        try:
            await self.bot.db.remove_facilities(facility_list)
        except Exception as exc:
            raise MessageError(
                f"Failed to remove facilities\n```py\n{exc}\n```"
            ) from exc
        else:
            embed = FeedbackEmbed("Removed facility", FeedbackType.SUCCESS)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            interaction.client.dispatch(
                "bulk_facility_delete",
                facility_list,
                interaction,
            )


async def setup(bot: FacilityBot) -> None:
    await bot.add_cog(Admin(bot))
