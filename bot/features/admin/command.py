import logging

import discord
from discord import app_commands

from bot.app.settings import DISCORD_GLOBAL_ADMIN_USER_IDS
from bot.forum.state_store import (
    get_guild_watch_forum_channel_id,
    set_guild_auto_screenshot_enabled,
    set_guild_eod_forum_channel_id,
    set_guild_forum_channel_id,
    set_guild_news_forum_channel_id,
    set_guild_watch_forum_channel_id,
)

logger = logging.getLogger(__name__)


def _interaction_user_id(interaction: discord.Interaction) -> int | None:
    return getattr(getattr(interaction, "user", None), "id", None)


def _is_authorized_admin(interaction: discord.Interaction) -> bool:
    guild = interaction.guild
    if guild is None:
        return False
    user = getattr(interaction, "user", None)
    user_id = getattr(user, "id", None)
    member = user if isinstance(user, discord.Member) else None
    is_global_admin = isinstance(user_id, int) and user_id in DISCORD_GLOBAL_ADMIN_USER_IDS
    is_owner = isinstance(user_id, int) and guild.owner_id == user_id
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
            logger.warning("[command] setforumchannel rejected reason=no-guild user=%s", _interaction_user_id(interaction))
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        if not _is_authorized_admin(interaction):
            logger.warning("[command] setforumchannel rejected reason=unauthorized guild=%s user=%s", guild.id, _interaction_user_id(interaction))
            await interaction.response.send_message(
                "서버 소유자/관리자 또는 전역 허용 사용자만 이 명령어를 사용할 수 있습니다.", ephemeral=True
            )
            return
        if forum_channel.guild.id != guild.id:
            logger.warning(
                "[command] setforumchannel rejected reason=foreign-channel guild=%s user=%s channel=%s",
                guild.id,
                _interaction_user_id(interaction),
                forum_channel.id,
            )
            await interaction.response.send_message("같은 서버의 포럼 채널만 설정할 수 있습니다.", ephemeral=True)
            return

        set_guild_forum_channel_id(guild.id, forum_channel.id)
        logger.info("[command] setforumchannel result=ok guild=%s user=%s channel=%s", guild.id, _interaction_user_id(interaction), forum_channel.id)
        await interaction.response.send_message(f"기본 포럼 채널을 <#{forum_channel.id}> 로 설정했습니다.", ephemeral=True)

    @tree.command(name="setnewsforum", description="Set news briefing forum channel for this server.")
    async def set_news_forum_command(interaction: discord.Interaction, forum_channel: discord.ForumChannel) -> None:
        guild = interaction.guild
        if guild is None:
            logger.warning("[command] setnewsforum rejected reason=no-guild user=%s", _interaction_user_id(interaction))
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        if not _is_authorized_admin(interaction):
            logger.warning("[command] setnewsforum rejected reason=unauthorized guild=%s user=%s", guild.id, _interaction_user_id(interaction))
            await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
            return
        if forum_channel.guild.id != guild.id:
            logger.warning(
                "[command] setnewsforum rejected reason=foreign-channel guild=%s user=%s channel=%s",
                guild.id,
                _interaction_user_id(interaction),
                forum_channel.id,
            )
            await interaction.response.send_message("같은 서버의 포럼 채널만 설정할 수 있습니다.", ephemeral=True)
            return
        set_guild_news_forum_channel_id(guild.id, forum_channel.id)
        logger.info("[command] setnewsforum result=ok guild=%s user=%s channel=%s", guild.id, _interaction_user_id(interaction), forum_channel.id)
        await interaction.response.send_message(f"뉴스 브리핑 포럼을 <#{forum_channel.id}> 로 설정했습니다.", ephemeral=True)

    @tree.command(name="seteodforum", description="Set EOD summary forum channel for this server.")
    async def set_eod_forum_command(interaction: discord.Interaction, forum_channel: discord.ForumChannel) -> None:
        guild = interaction.guild
        if guild is None:
            logger.warning("[command] seteodforum rejected reason=no-guild user=%s", _interaction_user_id(interaction))
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        if not _is_authorized_admin(interaction):
            logger.warning("[command] seteodforum rejected reason=unauthorized guild=%s user=%s", guild.id, _interaction_user_id(interaction))
            await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
            return
        if forum_channel.guild.id != guild.id:
            logger.warning(
                "[command] seteodforum rejected reason=foreign-channel guild=%s user=%s channel=%s",
                guild.id,
                _interaction_user_id(interaction),
                forum_channel.id,
            )
            await interaction.response.send_message("같은 서버의 포럼 채널만 설정할 수 있습니다.", ephemeral=True)
            return
        set_guild_eod_forum_channel_id(guild.id, forum_channel.id)
        logger.info("[command] seteodforum result=ok guild=%s user=%s channel=%s", guild.id, _interaction_user_id(interaction), forum_channel.id)
        await interaction.response.send_message(f"장마감 요약 포럼을 <#{forum_channel.id}> 로 설정했습니다.", ephemeral=True)

    @tree.command(name="setwatchforum", description="Set watch forum channel for this server.")
    async def set_watch_forum_command(interaction: discord.Interaction, forum_channel: discord.ForumChannel) -> None:
        guild = interaction.guild
        if guild is None:
            logger.warning("[command] setwatchforum rejected reason=no-guild user=%s", _interaction_user_id(interaction))
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        if not _is_authorized_admin(interaction):
            logger.warning("[command] setwatchforum rejected reason=unauthorized guild=%s user=%s", guild.id, _interaction_user_id(interaction))
            await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
            return
        if forum_channel.guild.id != guild.id:
            logger.warning(
                "[command] setwatchforum rejected reason=foreign-channel guild=%s user=%s channel=%s",
                guild.id,
                _interaction_user_id(interaction),
                forum_channel.id,
            )
            await interaction.response.send_message("같은 서버의 포럼 채널만 설정할 수 있습니다.", ephemeral=True)
            return
        existing = get_guild_watch_forum_channel_id(guild.id)
        if existing == forum_channel.id:
            await interaction.response.send_message(f"watch 포럼은 이미 <#{forum_channel.id}> 로 설정되어 있습니다.", ephemeral=True)
            return
        set_guild_watch_forum_channel_id(guild.id, forum_channel.id)
        logger.info("[command] setwatchforum result=ok guild=%s user=%s channel=%s", guild.id, _interaction_user_id(interaction), forum_channel.id)
        await interaction.response.send_message(f"watch 포럼을 <#{forum_channel.id}> 로 설정했습니다.", ephemeral=True)

    @tree.command(name="autoscreenshot", description="Toggle auto screenshot scheduler for this server.")
    @app_commands.describe(mode="on 또는 off")
    @app_commands.choices(mode=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
    async def auto_screenshot_command(interaction: discord.Interaction, mode: app_commands.Choice[str]) -> None:
        guild = interaction.guild
        if guild is None:
            logger.warning("[command] autoscreenshot rejected reason=no-guild user=%s", _interaction_user_id(interaction))
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        if not _is_authorized_admin(interaction):
            logger.warning("[command] autoscreenshot rejected reason=unauthorized guild=%s user=%s", guild.id, _interaction_user_id(interaction))
            await interaction.response.send_message(
                "서버 소유자/관리자 또는 전역 허용 사용자만 이 명령어를 사용할 수 있습니다.", ephemeral=True
            )
            return

        enabled = mode.value == "on"
        set_guild_auto_screenshot_enabled(guild.id, enabled)
        logger.info(
            "[command] autoscreenshot result=ok guild=%s user=%s enabled=%s",
            guild.id,
            _interaction_user_id(interaction),
            enabled,
        )
        text = (
            "자동스크린샷을 켰습니다. KST 기준으로 16:00 `kheatmap`, 07:00 `usheatmap` 자동 실행됩니다."
            if enabled
            else "자동스크린샷을 껐습니다."
        )
        await interaction.response.send_message(text, ephemeral=True)
