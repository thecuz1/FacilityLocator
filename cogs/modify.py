import discord
from discord.ext import commands
from discord import app_commands, Member, User, Interaction
from utils import (
    LocationTransformer,
    FacilityLocation,
    IdTransformer,
    MarkerTransformer,
    FeedbackEmbed,
    feedbackType,
    InteractionCheckedView,
    check_facility_permission,
)
from facility import (
    Facility,
    CreateFacilityView,
    ModifyFacilityView,
    RemoveFacilitiesView,
    ResetView,
)


class SetupView(InteractionCheckedView):
    def __init__(
        self, *, timeout: float = 180, original_author: User | Member, bot: commands.Bot
    ) -> None:
        super().__init__(timeout=timeout, original_author=original_author)
        self.message: None | discord.Message = None
        self.bot: commands.Bot = bot

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Select roles to access facilities...",
        min_values=0,
        max_values=25,
    )
    async def role_select(self, interaction: Interaction, _: discord.ui.RoleSelect):
        await interaction.response.defer()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.blurple)
    async def confirm(self, interaction: Interaction, _: discord.ui.Button):
        role_ids = [role.id for role in self.role_select.values]
        try:
            await self.bot.db.set_roles(role_ids, interaction.guild_id)
        except Exception as exc:
            embed = FeedbackEmbed("Failed to set roles", feedbackType.ERROR, exc)
        else:
            embed = FeedbackEmbed("Set roles for server", feedbackType.SUCCESS)

        await self._finish_view()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_timeout(self) -> None:
        """Call finish view"""
        await self._finish_view()

    async def _finish_view(self, interaction: Interaction | None = None) -> None:
        self.stop()
        for item in self.children:
            item.disabled = True

        if interaction:
            await interaction.response.edit_message(view=self)
        else:
            if self.message:
                try:
                    await self.message.edit(view=self)
                except discord.errors.NotFound:
                    pass


class Modify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 20, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.rename(name="facility-name", location="region")
    @check_facility_permission()
    async def create(
        self,
        interaction: discord.Interaction,
        name: app_commands.Range[str, 1, 100],
        location: app_commands.Transform[FacilityLocation, LocationTransformer],
        marker: app_commands.Transform[str, MarkerTransformer],
        maintainer: app_commands.Range[str, 1, 200],
        coordinates: str = "",
    ) -> None:
        """Creates a public facility

        Args:
            name (str): Name of facility
            location (app_commands.Transform[FacilityLocation, LocationTransformer]): Region with optional coordinates in the form of region-coordinates from ctrl-click of map
            marker (str): Nearest townhall/relic or location
            maintainer (str): Who maintains the facility
            coordinates (str): Optional coordinates (incase it doesn't work in the region field)
        """
        final_coordinates = coordinates or location.coordinates
        final_coordinates = final_coordinates.upper()

        facility = Facility(
            name=name,
            region=location.region,
            coordinates=final_coordinates,
            maintainer=maintainer,
            author=interaction.user.id,
            marker=marker,
            guild_id=interaction.guild_id,
        )

        view = CreateFacilityView(
            facility=facility, original_author=interaction.user, bot=self.bot
        )
        embed = facility.embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.rename(id_="id")
    @check_facility_permission()
    async def modify(self, interaction: discord.Interaction, id_: int):
        """Modify faciliy information

        Args:
            id_ (int): ID of facility
        """
        facility: Facility = await self.bot.db.get_facility_id(id_)

        if facility is None:
            return await interaction.response.send_message(
                ":x: No facility found", ephemeral=True
            )

        if self.bot.owner_id != interaction.user.id:
            if facility.can_modify(interaction) is False:
                return await interaction.response.send_message(
                    ":x: No permission to modify facility", ephemeral=True
                )

        view = ModifyFacilityView(
            facility=facility, original_author=interaction.user, bot=self.bot
        )
        embed = facility.embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def reset(self, ctx: commands.Context):
        embed = FeedbackEmbed("Confirm removal of all facilities", feedbackType.WARNING)
        view = ResetView(original_author=ctx.author, timeout=30, bot=self.bot)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    # @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def setup(self, interaction: discord.Interaction):
        """Setup the roles to allow access to facilities"""
        view = SetupView(original_author=interaction.user, bot=self.bot)

        role_ids: list[int] = await self.bot.db.get_roles(interaction.user.guild.id)

        current_roles = "\n".join("<@&%s>" % role_id for role_id in role_ids)
        if current_roles:
            embed = FeedbackEmbed(
                f"Currently selected roles:\n{current_roles}", feedbackType.INFO
            )
        else:
            embed = FeedbackEmbed(
                "No roles selected, all roles can access facilities", feedbackType.INFO
            )

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )
        view.message = await interaction.original_response()

    remove = app_commands.Group(
        name="remove", description="Remove facilities", guild_only=True
    )

    @remove.command()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @check_facility_permission()
    async def user(self, interaction: Interaction, user: discord.Member):
        """Removes all of the users facilities for the current guild"""
        if not (interaction.guild_id and isinstance(interaction.user, Member)):
            embed = FeedbackEmbed("Not run in guild context", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        search_dict = {
            " guild_id == ? ": interaction.guild_id,
            " author == ? ": user.id,
        }
        facilities: list[Facility] = await self.bot.db.get_facilities(search_dict)

        removed_facilities: list[Facility] = []
        for facility in facilities[:]:
            if facility.guild_id != interaction.guild_id:
                facilities.remove(facility)
                removed_facilities.append(facility)
                continue
            if not facility.can_modify(interaction):
                if interaction.user.guild_permissions.administrator:
                    continue
                facilities.remove(facility)
                removed_facilities.append(facility)

        if not facilities:
            embed = FeedbackEmbed("No facilities/required access", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        facility_amount = len(facilities)
        embed = FeedbackEmbed(
            f"Confirm removing {facility_amount} facilit{'ies' if facility_amount > 1 else 'y'} created by {user.mention} from {interaction.guild.name}",
            feedbackType.WARNING,
        )
        view = RemoveFacilitiesView(
            original_author=interaction.user, bot=self.bot, facilities=facilities
        )

        await interaction.response.send_message(
            view=view,
            embed=embed,
        )
        view.message = await interaction.original_response()

    @remove.command()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @check_facility_permission()
    async def ids(
        self,
        interaction: Interaction,
        ids: app_commands.Transform[tuple, IdTransformer],
    ):
        """Removes facilities by ID's for the current guild

        Args:
            ids (app_commands.Transform[tuple, IdTransformer]): List of facility ID's to remove with a delimiter of ',' or a space ' ' Ex. 1,3 4 8
        """
        if not (interaction.guild_id and isinstance(interaction.user, Member)):
            embed = FeedbackEmbed("Not run in guild context", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        facilities: list[Facility] = await self.bot.db.get_facility_ids(ids)
        not_found_facilities = len(ids) - len(facilities)

        removed_facilities: list[Facility] = []
        for facility in facilities[:]:
            if facility.guild_id != interaction.guild_id:
                facilities.remove(facility)
                removed_facilities.append(facility)
                continue
            if not facility.can_modify(interaction):
                if interaction.user.guild_permissions.administrator:
                    continue
                facilities.remove(facility)
                removed_facilities.append(facility)

        if not facilities:
            embed = FeedbackEmbed("No facilities/required access", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        facility_amount = len(facilities)
        embed = FeedbackEmbed(
            f"Confirm removing {facility_amount} facilit{'ies' if facility_amount > 1 else 'y'} from {interaction.guild.name}",
            feedbackType.WARNING,
        )
        view = RemoveFacilitiesView(
            original_author=interaction.user, bot=self.bot, facilities=facilities
        )

        removed_facility_amount = len(removed_facilities)
        prevented_message = (
            f":x: Not Removing {removed_facility_amount} facilit{'ies' if removed_facility_amount > 1 else 'y'} due to missing permissions"
            if removed_facility_amount > 0
            else ""
        )

        not_found_message = (
            f":x: {not_found_facilities} facilit{'ies' if not_found_facilities > 1 else 'y'} not found"
            if not_found_facilities > 0
            else ""
        )

        await interaction.response.send_message(
            content="\n".join((prevented_message, not_found_message)),
            view=view,
            embed=embed,
            ephemeral=True,
        )
        view.message = await interaction.original_response()

    @remove.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @check_facility_permission()
    async def all(self, interaction: Interaction):
        """Removes all facilities for the current guild"""

        if not (interaction.guild_id and isinstance(interaction.user, Member)):
            embed = FeedbackEmbed("Not run in guild context", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        search_dict = {"guild_id == ?": interaction.guild_id}
        facilities: list[Facility] = await self.bot.db.get_facilities(search_dict)

        if not facilities:
            embed = FeedbackEmbed("No facilities found", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        facility_amount = len(facilities)
        embed = FeedbackEmbed(
            f"Confirm removing {facility_amount} facilit{'ies' if facility_amount > 1 else 'y'} from {interaction.guild.name}",
            feedbackType.WARNING,
        )
        view = RemoveFacilitiesView(
            original_author=interaction.user, bot=self.bot, facilities=facilities
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Modify(bot))
