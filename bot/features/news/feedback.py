import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import discord

from bot.app.settings import (
    INTEL_API_TIMEOUT_SECONDS,
    STOCK_DATA_CONTROLLER_API_BASE_URL,
    STOCK_DATA_CONTROLLER_INTERNAL_TOKEN,
)

logger = logging.getLogger(__name__)

NEWS_FEEDBACK_VIEW_TIMEOUT_SECONDS = 3 * 24 * 60 * 60
NEWS_FEEDBACK_EPHEMERAL_DELETE_AFTER_SECONDS = 60
MAX_NEWS_FEEDBACK_OPTIONS = 25
NEWS_FEEDBACK_ACTIONS = {
    "useful": "유용함",
    "noise": "불필요",
    "duplicate": "중복",
}


class NewsFeedbackError(RuntimeError):
    pass


@dataclass(frozen=True)
class NewsFeedbackOption:
    article_key: str
    label: str
    description: str


async def _send_ephemeral(interaction: discord.Interaction, *args: Any, **kwargs: Any) -> None:
    try:
        message = await interaction.followup.send(
            *args,
            ephemeral=True,
            wait=True,
            **kwargs,
        )
    except discord.HTTPException:
        raise

    try:
        await message.delete(delay=NEWS_FEEDBACK_EPHEMERAL_DELETE_AFTER_SECONDS)
    except discord.HTTPException:
        logger.debug("[news-feedback] ephemeral message delete scheduling failed", exc_info=True)


def _short_text(text: str, max_chars: int) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max(0, max_chars - 1)].rstrip()}…"


def _article_key(item: dict[str, Any]) -> str:
    return str(item.get("articleKey") or item.get("article_key") or "").strip()


def _feedback_options(items: list[dict[str, Any]]) -> list[NewsFeedbackOption]:
    options: list[NewsFeedbackOption] = []
    for index, item in enumerate(items, start=1):
        article_key = _article_key(item)
        if not article_key or len(article_key) > 100:
            continue
        title = str(item.get("title") or "뉴스").strip()
        source = str(item.get("source") or "").strip()
        options.append(
            NewsFeedbackOption(
                article_key=article_key,
                label=_short_text(f"{index}. {title}", 100),
                description=_short_text(source or article_key, 100),
            )
        )
        if len(options) >= MAX_NEWS_FEEDBACK_OPTIONS:
            break
    return options


def record_news_feedback_sync(
    *,
    article_key: str,
    discord_user_id: str,
    action: str,
    guild_id: str = "",
    channel_id: str = "",
    thread_id: str = "",
    message_id: str = "",
) -> None:
    if not STOCK_DATA_CONTROLLER_API_BASE_URL or not STOCK_DATA_CONTROLLER_INTERNAL_TOKEN:
        raise NewsFeedbackError("collector-feedback-config-missing")

    payload = {
        "action": action,
        "article_key": article_key,
        "channel_id": channel_id,
        "discord_user_id": discord_user_id,
        "guild_id": guild_id,
        "message_id": message_id,
        "thread_id": thread_id,
    }
    request = Request(
        f"{STOCK_DATA_CONTROLLER_API_BASE_URL.rstrip('/')}/news/feedback",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "discord-heatmap-bot/1.0",
            "X-Internal-Token": STOCK_DATA_CONTROLLER_INTERNAL_TOKEN,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=INTEL_API_TIMEOUT_SECONDS) as response:
            if response.status >= 400:
                raise NewsFeedbackError(f"collector-feedback-save-failed:{response.status}")
    except HTTPError as exc:
        raise NewsFeedbackError(f"collector-feedback-save-failed:{exc.code}") from exc
    except URLError as exc:
        raise NewsFeedbackError("collector-feedback-unreachable") from exc


class NewsFeedbackSelect(discord.ui.Select):
    def __init__(self, action: str, options: list[NewsFeedbackOption], max_values: int | None = None) -> None:
        self.feedback_action = action
        select_options = [
            discord.SelectOption(
                label=option.label,
                value=option.article_key,
                description=option.description,
            )
            for option in options
        ]
        super().__init__(
            custom_id=f"news-feedback:{action}",
            placeholder=NEWS_FEEDBACK_ACTIONS[action],
            min_values=1,
            max_values=max_values or max(1, min(len(select_options), MAX_NEWS_FEEDBACK_OPTIONS)),
            options=select_options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild_id = str(getattr(interaction.guild, "id", "") or "")
        channel_id = str(getattr(interaction.channel, "id", "") or "")
        message_id = str(getattr(interaction.message, "id", "") or "")
        thread_id = channel_id
        user_id = str(getattr(interaction.user, "id", "") or "")

        saved = 0
        failed = 0
        for article_key in self.values:
            try:
                await asyncio.to_thread(
                    record_news_feedback_sync,
                    article_key=article_key,
                    discord_user_id=user_id,
                    action=self.feedback_action,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    thread_id=thread_id,
                    message_id=message_id,
                )
            except Exception as exc:
                failed += 1
                logger.warning(
                    "[news-feedback] 저장 실패 user=%s article_key=%s action=%s reason=%s",
                    user_id,
                    article_key,
                    self.feedback_action,
                    exc,
                )
            else:
                saved += 1

        if saved and not failed:
            await _send_ephemeral(interaction, f"피드백을 저장했습니다. ({saved}건)")
            return
        if saved and failed:
            await _send_ephemeral(interaction, f"일부만 저장했습니다. 성공 {saved}건, 실패 {failed}건")
            return
        await _send_ephemeral(interaction, "피드백을 저장하지 못했습니다. 잠시 후 다시 시도해주세요.")


def build_news_feedback_view(items: list[dict[str, Any]]) -> discord.ui.View | None:
    options = _feedback_options(items)
    if not options:
        return None

    view = discord.ui.View(timeout=NEWS_FEEDBACK_VIEW_TIMEOUT_SECONDS)
    for action in NEWS_FEEDBACK_ACTIONS:
        view.add_item(NewsFeedbackSelect(action, options))
    return view


def register_persistent_news_feedback_view(client: discord.Client) -> None:
    placeholder_options = [
        NewsFeedbackOption(
            article_key=f"placeholder-{index}",
            label=f"최근 뉴스 카드 {index}",
            description="재기동 후 기존 뉴스 피드백을 처리하기 위한 등록값",
        )
        for index in range(1, MAX_NEWS_FEEDBACK_OPTIONS + 1)
    ]
    view = discord.ui.View(timeout=None)
    for action in NEWS_FEEDBACK_ACTIONS:
        view.add_item(NewsFeedbackSelect(action, placeholder_options, max_values=MAX_NEWS_FEEDBACK_OPTIONS))
    client.add_view(view)
