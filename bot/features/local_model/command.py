import logging

import discord
from discord import app_commands

from bot.app.settings import (
    DISCORD_GLOBAL_ADMIN_USER_IDS,
    LOCAL_MODEL_BASE_URL,
    LOCAL_MODEL_ENABLED,
    LOCAL_MODEL_MAX_PROMPT_CHARS,
    LOCAL_MODEL_MAX_RESPONSE_CHARS,
    LOCAL_MODEL_NAME,
    LOCAL_MODEL_PUBLIC_RESPONSES,
    LOCAL_MODEL_TIMEOUT_SECONDS,
)
from bot.features.local_model.client import LocalModelError, LocalModelTimeoutError, request_local_model

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


def _format_model_response(text: str, max_chars: int) -> str:
    stripped = text.strip()
    if not stripped:
        return "로컬 모델이 빈 응답을 반환했습니다."
    if len(stripped) <= max_chars:
        return stripped
    suffix = "\n\n... (응답이 길어 일부를 생략했습니다.)"
    return stripped[: max(0, max_chars - len(suffix))].rstrip() + suffix


def register(tree: app_commands.CommandTree, client) -> None:
    local = app_commands.Group(name="local", description="로컬 모델 명령")

    @local.command(name="ask", description="로컬 모델에 간단한 질문을 보냅니다.")
    @app_commands.describe(prompt="로컬 모델에 보낼 질문", public="응답을 채널에 공개")
    async def local_ask(interaction: discord.Interaction, prompt: str, public: bool = False) -> None:
        guild_id = interaction.guild_id
        user_id = _interaction_user_id(interaction)
        if guild_id is None or interaction.guild is None:
            logger.warning("[command] local.ask rejected reason=no-guild user=%s", user_id)
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return
        if not _is_authorized_admin(interaction):
            logger.warning("[command] local.ask rejected reason=unauthorized guild=%s user=%s", guild_id, user_id)
            await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
            return
        if not LOCAL_MODEL_ENABLED:
            logger.warning("[command] local.ask rejected reason=disabled guild=%s user=%s", guild_id, user_id)
            await interaction.response.send_message("로컬 모델 명령이 비활성화되어 있습니다.", ephemeral=True)
            return

        cleaned_prompt = prompt.strip()
        if not cleaned_prompt:
            await interaction.response.send_message("질문을 입력해주세요.", ephemeral=True)
            return
        if len(cleaned_prompt) > LOCAL_MODEL_MAX_PROMPT_CHARS:
            await interaction.response.send_message(
                f"질문이 너무 깁니다. 최대 {LOCAL_MODEL_MAX_PROMPT_CHARS}자까지 입력할 수 있습니다.",
                ephemeral=True,
            )
            return
        if public and not LOCAL_MODEL_PUBLIC_RESPONSES:
            await interaction.response.send_message("로컬 모델 공개 응답은 현재 비활성화되어 있습니다.", ephemeral=True)
            return

        ephemeral = not public
        await interaction.response.defer(thinking=True, ephemeral=ephemeral)
        try:
            text = await request_local_model(
                base_url=LOCAL_MODEL_BASE_URL,
                model=LOCAL_MODEL_NAME,
                prompt=cleaned_prompt,
                timeout_seconds=LOCAL_MODEL_TIMEOUT_SECONDS,
                max_tokens=LOCAL_MODEL_MAX_RESPONSE_CHARS,
            )
        except LocalModelTimeoutError:
            logger.warning("[command] local.ask result=failed guild=%s user=%s detail=timeout", guild_id, user_id)
            await interaction.followup.send("로컬 모델 응답 시간이 초과되었습니다.", ephemeral=ephemeral)
            return
        except LocalModelError as exc:
            logger.warning(
                "[command] local.ask result=failed guild=%s user=%s detail=%s",
                guild_id,
                user_id,
                exc.__class__.__name__,
            )
            await interaction.followup.send(
                "로컬 모델 호출에 실패했습니다. llama-server가 실행 중인지 확인해주세요.",
                ephemeral=ephemeral,
            )
            return

        response_text = _format_model_response(text, LOCAL_MODEL_MAX_RESPONSE_CHARS)
        logger.info(
            "[command] local.ask result=ok guild=%s user=%s response_chars=%s",
            guild_id,
            user_id,
            len(response_text),
        )
        await interaction.followup.send(response_text, ephemeral=ephemeral)

    tree.add_command(local)
