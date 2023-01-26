import rapidfuzz
from discord import Interaction, Embed, Member, Colour, TextChannel
from discord.ext import commands
from discord import app_commands
from facility import DynamicListConfirm
from utils import (
    Paginator,
    LocationTransformer,
    FacilityLocation,
    IdTransformer,
    FeedbackEmbed,
    feedbackType,
    check_facility_permission,
)
from data import VEHICLE_SERVICES, ITEM_SERVICES


class Query(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.rename(
        location="region",
        item_service="item-service",
        vehicle_service="vehicle-service",
    )
    @app_commands.choices(
        item_service=[
            app_commands.Choice(name=service, value=(1 << index))
            for index, service in enumerate(ITEM_SERVICES)
        ],
        vehicle_service=[
            app_commands.Choice(name=service, value=(1 << index))
            for index, service in enumerate(VEHICLE_SERVICES)
        ],
    )
    @check_facility_permission()
    async def locate(
        self,
        interaction: Interaction,
        location: app_commands.Transform[FacilityLocation, LocationTransformer] = None,
        item_service: int = None,
        vehicle_service: int = None,
        creator: Member = None,
        vehicle: str = None,
        ephemeral: bool = True,
    ) -> None:
        """Find a facility with optional search parameters

        Args:
            location (app_commands.Transform[FacilityLocation, LocationTransformer], optional): Region to search in
            item_service (int, optional): Item service to look for
            vehicle_service (int, optional): Vehicle service to look for
            creator (Member, optional): Filter by facility creator
            vehicle (str, optional): Vehicle upgrade/build facility to look for
            ephemeral (bool): Show results to only you (defaults to True)
        """
        if vehicle:
            for index, vehicles in enumerate(VEHICLE_SERVICES.values()):
                if vehicles and vehicle in vehicles:
                    vehicle_service = 1 << index
                    break
            else:
                embed = FeedbackEmbed("Invalid vehicle", feedbackType.WARNING)
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

        search_dict = {
            name: value
            for name, value in (
                (" region == ? ", location and location.region),
                (" item_services & ? ", item_service),
                (" vehicle_services & ? ", vehicle_service),
                (" author == ? ", creator and creator.id),
                (" guild_id == ? ", interaction.guild_id),
            )
            if value
        }

        facility_list = await self.bot.db.get_facilities(search_dict)

        if not facility_list:
            embed = FeedbackEmbed("No facilities found", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embeds = [facility.embed() for facility in facility_list]
        await Paginator(original_author=interaction.user).start(
            interaction, pages=embeds, ephemeral=ephemeral
        )

    @locate.autocomplete("vehicle")
    async def vehicle_autocomplete(
        self, _: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        choices = [
            vehicle
            for vehicles in VEHICLE_SERVICES.values()
            if vehicles
            for vehicle in vehicles
        ]
        sorted_choices = rapidfuzz.process.extract(current, choices, limit=25)
        return [
            app_commands.Choice(name=choice[0], value=choice[0])
            for choice in sorted_choices
        ]

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @check_facility_permission()
    async def view(
        self,
        interaction: Interaction,
        ids: app_commands.Transform[tuple, IdTransformer],
        ephemeral: bool = True,
    ):
        """View facilities based on their ID's

        Args:
            ids (app_commands.Transform[tuple, IdTransformer]): List of facility ID's to view with a delimiter of ',' or a space ' ' Ex. 1,3 4 8
            ephemeral (bool): Show results to only you (defaults to True)
        """
        facilities = await self.bot.db.get_facility_ids(ids)
        if not facilities:
            embed = FeedbackEmbed("No facilities found", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embeds = [
            facility.embed()
            for facility in facilities
            if facility.guild_id == interaction.guild_id
        ]
        await Paginator(original_author=interaction.user).start(
            interaction, pages=embeds, ephemeral=ephemeral
        )

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def logs(self, interaction: Interaction, ephemeral: bool = True) -> None:
        """View logs for the current guild

        Args:
            ephemeral (bool): Show results to only you (defaults to True)
        """
        logs = self.bot.guild_logs.get(interaction.guild_id, None)
        if not logs:
            embed = FeedbackEmbed("No logs found", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        embed = Embed(title=f"Logs for {interaction.guild.name}", colour=Colour.blue())

        formatted_logs = "> "
        formatted_logs += "\n> ".join(logs)
        embed.description = formatted_logs
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.default_permissions(administrator=True)
    async def set_list_channel(
        self, interaction: Interaction, channel: TextChannel | None
    ):
        """Sets list channel to post updates of facilities

        Args:
            channel (TextChannel): Channel to set, default to current channel
        """
        if not channel:
            if not isinstance(interaction.channel, TextChannel):
                embed = FeedbackEmbed("Channel is not supported", feedbackType.ERROR)
                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )
            channel = interaction.channel

        search_dict = {" guild_id == ? ": interaction.guild_id}

        facility_list: list = await self.bot.db.get_facilities(search_dict)

        embed = FeedbackEmbed(
            f"Confirm setting {channel.mention} as facility update channel",
            feedbackType.INFO,
        )
        view = DynamicListConfirm(
            original_author=interaction.user,
            bot=self.bot,
            selected_channel=channel,
            facilities=facility_list,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 4, key=lambda i: (i.guild_id, i.user.id))
    async def list(self, interaction: Interaction, ephemeral: bool = True):
        """Shows a list of all facilities for the current guild

        Args:
            ephemeral (bool): Show results to only you (defaults to True)
        """
        search_dict = {" guild_id == ? ": interaction.guild_id}

        facility_list: list = await self.bot.db.get_facilities(search_dict)

        if not facility_list:
            embed = FeedbackEmbed("No facilities found", feedbackType.ERROR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        from facility import create_list

        finished_embeds = create_list(facility_list, interaction.guild)

        await interaction.response.send_message(
            embed=finished_embeds.pop(0), ephemeral=ephemeral
        )

        for embed in finished_embeds:
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Query(bot))
