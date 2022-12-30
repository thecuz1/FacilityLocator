import discord
from discord.ext import commands
from discord import app_commands, Colour, Member, User, Interaction
from utils import (
    LocationTransformer,
    FacilityLocation,
    IdTransformer,
    MarkerTransformer,
    FeedbackEmbed,
    feedbackType,
    InteractionCheckedView,
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
        role_ids: list[int] = await self.bot.db.get_roles(interaction.user.guild.id)
        member_role_ids = [role.id for role in interaction.user.roles]
        similar_roles = list(set(role_ids).intersection(member_role_ids))
        if not (similar_roles or interaction.user.resolved_permissions.administrator):
            embed = FeedbackEmbed(
                "No permission to create facilities", feedbackType.WARNING
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

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
    async def modify(self, interaction: discord.Interaction, id_: int):
        """Modify faciliy information

        Args:
            id_ (int): ID of facility
        """
        role_ids: list[int] = await self.bot.db.get_roles(interaction.user.guild.id)
        member_role_ids = [role.id for role in interaction.user.roles]
        similar_roles = list(set(role_ids).intersection(member_role_ids))
        if not (similar_roles or interaction.user.resolved_permissions.administrator):
            embed = FeedbackEmbed(
                "No permission to modify facilities", feedbackType.WARNING
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        facility = await self.bot.db.get_facility_id(id_)

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

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def remove(
        self,
        interaction: discord.Interaction,
        ids: app_commands.Transform[tuple, IdTransformer],
    ):
        """Remove facility

        Args:
            ids (app_commands.Transform[tuple, IdTransformer]): List of facility ID's to remove with a delimiter of ',' or a space ' ' Ex. 1,3 4 8
        """
        role_ids: list[int] = await self.bot.db.get_roles(interaction.user.guild.id)
        member_role_ids = [role.id for role in interaction.user.roles]
        similar_roles = list(set(role_ids).intersection(member_role_ids))
        if not (similar_roles or interaction.user.resolved_permissions.administrator):
            embed = FeedbackEmbed(
                "No permission to remove facilities", feedbackType.WARNING
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        author = interaction.user
        facilities = await self.bot.db.get_facility_ids(ids)

        if not facilities:
            embed = FeedbackEmbed("No facilities found", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(colour=Colour.blue())
        if len(facilities) < len(ids):
            embed.description = (
                f":warning: Only found {len(facilities)}/{len(ids)} facilities\n"
            )

        removed_facilities = None
        if self.bot.owner_id != author.id:
            removed_facilities = [
                facilities.pop(index)
                for index, facility in enumerate(facilities[:])
                if facility.can_modify(interaction) is False
            ]

        def format_facility(facility: list[Facility]) -> str:
            message = "```\n"
            for facilty in facility:
                previous_message = message
                message += f"{facilty.id_:3} - {facilty.name}\n"
                if len(message) > 1000:
                    message = previous_message
                    message += "Truncated entries..."
                    break
            message += "```"
            return message

        if removed_facilities:
            message = format_facility(removed_facilities)
            embed.add_field(
                name=":x: No permission to delete facilties:", value=message
            )
        if facilities:
            message = format_facility(facilities)
            embed.add_field(
                name=":white_check_mark: Permission to delete facilties:",
                value=message,
            )
        else:
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        view = RemoveFacilitiesView(
            original_author=author, bot=self.bot, facilities=facilities
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def remove_all(
        self,
        interaction: discord.Interaction,
    ):
        """Remove all facilities for the current guild"""
        role_ids: list[int] = await self.bot.db.get_roles(interaction.user.guild.id)
        member_role_ids = [role.id for role in interaction.user.roles]
        similar_roles = list(set(role_ids).intersection(member_role_ids))
        if not (similar_roles or interaction.user.resolved_permissions.administrator):
            embed = FeedbackEmbed(
                "No permission to remove facilities", feedbackType.WARNING
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        author = interaction.user
        if interaction.guild_id:
            search_dict = {"guild_id == ?": interaction.guild_id}
            facilities = await self.bot.db.get_facilities(search_dict)
        else:
            embed = FeedbackEmbed("No guild ID was set", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not facilities:
            embed = FeedbackEmbed("No facilities found", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(colour=Colour.blue())
        removed_facilities = None
        if self.bot.owner_id != author.id:
            removed_facilities = [
                facilities.pop(index)
                for index, facility in enumerate(facilities[:])
                if facility.can_modify(interaction) is False
            ]

        def format_facility(facility: list[Facility]) -> str:
            message = "```\n"
            for facilty in facility:
                previous_message = message
                message += f"{facilty.id_:3} - {facilty.name}\n"
                if len(message) > 1000:
                    message = previous_message
                    message += "Truncated entries..."
                    break
            message += "```"
            return message

        if facilities:
            message = format_facility(facilities)
            embed.add_field(
                name=":white_check_mark: Permission to delete facilties:",
                value=message,
            )
        else:
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        view = RemoveFacilitiesView(
            original_author=author, bot=self.bot, facilities=facilities
        )

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
            embed = FeedbackEmbed("No roles selected", feedbackType.INFO)

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.bot) -> None:
    await bot.add_cog(Modify(bot))
