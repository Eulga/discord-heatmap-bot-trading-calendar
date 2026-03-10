import discord
from discord import app_commands

from bot.app.settings import DISCORD_GLOBAL_ADMIN_USER_IDS
from bot.forum.repository import (
    load_state,
    save_state,
    set_guild_auto_screenshot_enabled,
    set_guild_forum_channel_id,
)


def _is_authorized_admin(interaction: discord.Interaction) -> bool:
    guild = interaction.guild
    if guild is None:
        return False
    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    is_global_admin = interaction.user.id in DISCORD_GLOBAL_ADMIN_USER_IDS
    is_owner = guild.owner_id == interaction.user.id
    is_admin = bool(member and member.guild_permissions.administrator)
    return is_global_admin or is_owner or is_admin


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

        if not _is_authorized_admin(interaction):
            await interaction.response.send_message(
                "서버 소유자/관리자 또는 전역 허용 사용자만 이 명령어를 사용할 수 있습니다.",
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

    @tree.command(name="autoscreenshot", description="Toggle auto screenshot scheduler for this server.")
    @app_commands.describe(mode="on 또는 off")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="on", value="on"),
            app_commands.Choice(name="off", value="off"),
        ]
    )
    async def auto_screenshot_command(
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        if not _is_authorized_admin(interaction):
            await interaction.response.send_message(
                "서버 소유자/관리자 또는 전역 허용 사용자만 이 명령어를 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        enabled = mode.value == "on"
        state = load_state()
        set_guild_auto_screenshot_enabled(state, guild.id, enabled)
        save_state(state)

        if enabled:
            text = (
                "자동스크린샷을 켰습니다. KST 기준으로 15:35 `kheatmap`, "
                "06:05 `usheatmap` 자동 실행됩니다. (각 시장 거래일에만 실행)"
            )
        else:
            text = "자동스크린샷을 껐습니다."

        await interaction.response.send_message(text, ephemeral=True)
