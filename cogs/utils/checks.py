from discord import Interaction, Member, app_commands

from .embeds import FeedbackEmbed, FeedbackType


def check_facility_permission():
    async def predicate(interaction: Interaction) -> bool:
        if not isinstance(interaction.user, Member):
            return True

        role_ids: list[int] = await interaction.client.db.get_roles(
            interaction.user.guild.id
        )
        if not role_ids:
            return True
        member_role_ids = [role.id for role in interaction.user.roles]
        similar_roles = list(set(role_ids).intersection(member_role_ids))
        if not (similar_roles or interaction.user.resolved_permissions.administrator):
            embed = FeedbackEmbed(
                "No permission to run this command", FeedbackType.WARNING
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False

        return True

    return app_commands.check(predicate)
