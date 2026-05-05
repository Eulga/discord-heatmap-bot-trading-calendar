from collections.abc import Awaitable, Callable
import logging
from pathlib import Path

import discord

from bot.common.clock import timestamp_text
from bot.forum.state_store import get_guild_forum_channel_id
from bot.forum.service import upsert_daily_post
from bot.markets.capture_service import get_or_capture_images

CaptureFunc = Callable[[str, str], Awaitable[Path]]
BodyBuilder = Callable[[str, list[str], list[str]], str]
TitleBuilder = Callable[[], str]

logger = logging.getLogger(__name__)


def _interaction_user_id(interaction: discord.Interaction) -> int | None:
    return getattr(getattr(interaction, "user", None), "id", None)


async def _resolve_guild_forum_channel(
    client: discord.Client,
    guild_id: int,
    forum_channel_id: int,
) -> discord.ForumChannel | None:
    channel = client.get_channel(forum_channel_id)
    if channel is None:
        try:
            channel = await client.fetch_channel(forum_channel_id)
        except Exception:
            return None
    channel_guild = getattr(channel, "guild", None)
    if not isinstance(channel, discord.ForumChannel) or getattr(channel_guild, "id", None) != guild_id:
        return None
    return channel


async def execute_heatmap_for_guild(
    client: discord.Client,
    guild_id: int,
    command_key: str,
    targets: dict[str, str],
    capture_func: CaptureFunc,
    title_builder: TitleBuilder,
    body_builder: BodyBuilder,
) -> tuple[bool, str]:
    forum_channel_id = get_guild_forum_channel_id(guild_id)

    if forum_channel_id is None:
        return False, "이 서버의 포럼 채널이 설정되지 않았습니다. `/setforumchannel`로 먼저 설정해 주세요."

    resolved_forum = await _resolve_guild_forum_channel(client, guild_id, forum_channel_id)
    if resolved_forum is None:
        return False, "이 서버에 연결된 포럼 채널 설정이 유효하지 않습니다. `/setforumchannel`로 다시 설정해 주세요."

    image_paths, failed, source_map = await get_or_capture_images(
        state=None,
        command_key=command_key,
        targets=targets,
        capture_func=capture_func,
    )

    if not image_paths and failed:
        detail = "\n".join(f"- {line}" for line in failed)
        return False, f"이미지 생성에 실패해서 포럼 포스트를 업데이트하지 못했습니다.\n{detail}"

    src_lines: list[str] = []
    for market_label in targets.keys():
        source = source_map.get(market_label)
        if source == "cached":
            src_lines.append(f"- {market_label}: cached (<=1h)")
        elif source == "captured":
            src_lines.append(f"- {market_label}: captured")

    body = body_builder(timestamp_text(), src_lines, failed)
    title = title_builder()

    try:
        thread, action = await upsert_daily_post(
            client=client,
            state=None,
            guild_id=guild_id,
            forum_channel_id=resolved_forum.id,
            command_key=command_key,
            post_title=title,
            body_text=body,
            image_paths=image_paths,
        )
    except discord.Forbidden:
        return False, (
            "포럼 채널에 글 작성/수정 권한이 없습니다. "
            "봇에 forum posting, send messages, attach files 권한을 확인해 주세요."
        )
    except discord.HTTPException as exc:
        return False, f"포럼 포스트 업서트 중 Discord API 오류가 발생했습니다: {exc}"
    except Exception as exc:
        return False, f"포럼 포스트 업서트 중 오류가 발생했습니다: {exc}"

    action_text = "생성" if action == "created" else "수정"
    message = "\n".join(
        [
            f"{command_key} 포스트 {action_text} 완료: {thread.jump_url}",
            f"- 성공 이미지: {len(image_paths)}",
            f"- 실패 항목: {len(failed)}",
        ]
    )
    return True, message


async def run_heatmap_command(
    interaction: discord.Interaction,
    client: discord.Client,
    command_key: str,
    targets: dict[str, str],
    capture_func: CaptureFunc,
    title_builder: TitleBuilder,
    body_builder: BodyBuilder,
) -> None:
    await interaction.response.defer(thinking=True)
    guild_id = interaction.guild_id
    if guild_id is None:
        logger.warning("[command] %s rejected reason=no-guild user=%s", command_key, _interaction_user_id(interaction))
        await interaction.followup.send("이 명령어는 서버 채널에서만 사용할 수 있습니다.")
        return

    logger.info("[command] %s requested guild=%s user=%s", command_key, guild_id, _interaction_user_id(interaction))

    ok, message = await execute_heatmap_for_guild(
        client=client,
        guild_id=guild_id,
        command_key=command_key,
        targets=targets,
        capture_func=capture_func,
        title_builder=title_builder,
        body_builder=body_builder,
    )
    if ok:
        logger.info("[command] %s result=ok guild=%s detail=%s", command_key, guild_id, message)
    else:
        logger.warning("[command] %s result=failed guild=%s detail=%s", command_key, guild_id, message)
    await interaction.followup.send(message)
