import discord
from discord import app_commands

from bot.forum.repository import load_state, save_state, set_guild_forum_channel_id


def register(tree: app_commands.CommandTree, client) -> None:
    @tree.command(name="setforumchannel", description="Set forum channel for this server.")
    async def set_forum_channel_command(
        interaction: discord.Interaction,
        forum_channel: discord.ForumChannel,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        is_owner = guild.owner_id == interaction.user.id
        is_admin = bool(member and member.guild_permissions.administrator)
        if not (is_owner or is_admin):
            await interaction.response.send_message(
                "서버 소유자 또는 관리자만 이 명령어를 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        if forum_channel.guild.id != guild.id:
            await interaction.response.send_message(
                "같은 서버의 포럼 채널만 설정할 수 있습니다.",
                ephemeral=True,
            )
            return

        state = load_state()
        set_guild_forum_channel_id(state, guild.id, forum_channel.id)
        save_state(state)

        await interaction.response.send_message(
            f"이 서버 포럼 채널을 <#{forum_channel.id}> 로 설정했습니다.",
            ephemeral=True,
        )
