from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import re
import unicodedata
from typing import Any

import discord

from bot.app.settings import (
    STOCK_DASHBOARD_ROLE_CHANNEL_ID,
    STOCK_DASHBOARD_ROLE_PREFIX,
    STOCK_DASHBOARD_ROLE_SYNC_ENABLED,
    STOCK_DASHBOARD_ROLE_SYNC_INTERVAL_SECONDS,
)
from bot.features.quote.command import _fetch_dashboard_quotes, _fetch_dashboard_themes
from bot.forum.repository import (
    get_guild_stock_role_ids,
    get_guild_stock_role_message_id,
    get_guild_stock_role_targets,
    load_state,
    save_state,
    set_guild_stock_role_channel_id,
    set_guild_stock_role_id,
    set_guild_stock_role_message_id,
    set_guild_stock_role_targets,
    set_job_last_run,
)

logger = logging.getLogger(__name__)

MAX_SELECT_OPTIONS = 25
ROLE_SYNC_JOB_KEY = "stock_role_sync"


@dataclass(frozen=True)
class StockRoleTarget:
    key: str
    symbol: str
    name: str
    market: str
    category: str
    role_id: int | None = None

    def to_state(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "category": self.category,
        }
        if self.role_id is not None:
            payload["role_id"] = self.role_id
        return payload


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    return re.sub(r"\s+", "", normalized)


def _market_key(market: str) -> str:
    normalized = _normalize_text(market)
    if normalized in {"국장", "kr", "krx", "korea", "한국"}:
        return "KRX"
    if normalized in {"미장", "us", "usa", "nasdaq", "nyse", "amex"}:
        return "US"
    return "GEN"


def stock_role_key(symbol: str, market: str) -> str:
    cleaned_symbol = str(symbol or "").strip().upper()
    return f"{_market_key(market)}:{cleaned_symbol}"


def _safe_role_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = re.sub(r"[@#:`\r\n]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def stock_role_name(target: StockRoleTarget) -> str:
    name = _safe_role_text(target.name or target.symbol)
    symbol = _safe_role_text(target.symbol)
    prefix = _safe_role_text(STOCK_DASHBOARD_ROLE_PREFIX)
    if symbol and symbol not in name:
        name = f"{name} {symbol}"
    return f"{prefix} {name}"[:100].strip()


def _stock_target_from_item(item: dict[str, Any], fallback_category: str = "") -> StockRoleTarget | None:
    symbol = str(item.get("symbol") or "").strip()
    if not symbol:
        return None

    name = str(item.get("name") or symbol).strip()
    market = str(item.get("market") or "").strip()
    category = str(item.get("category") or item.get("theme") or fallback_category or "").strip()
    return StockRoleTarget(
        key=stock_role_key(symbol, market),
        symbol=symbol,
        name=name,
        market=market,
        category=category,
    )


def _dashboard_targets_from_payload(payload: dict[str, Any]) -> dict[str, StockRoleTarget]:
    raw_items = payload.get("items")
    fallback_category = str(payload.get("theme") or "").strip()
    targets: dict[str, StockRoleTarget] = {}
    if not isinstance(raw_items, list):
        return targets

    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        target = _stock_target_from_item(raw_item, fallback_category)
        if target is not None:
            targets[target.key] = target
    return targets


def fetch_dashboard_stock_role_targets() -> list[StockRoleTarget]:
    targets = _dashboard_targets_from_payload(_fetch_dashboard_quotes(""))

    if not targets:
        theme_payload = _fetch_dashboard_themes()
        raw_themes = theme_payload.get("themes")
        if isinstance(raw_themes, list):
            for raw_theme in raw_themes:
                if not isinstance(raw_theme, dict):
                    continue
                theme_name = str(raw_theme.get("name") or "").strip()
                if not theme_name:
                    continue
                targets.update(_dashboard_targets_from_payload(_fetch_dashboard_quotes(theme_name)))

    return sorted(targets.values(), key=lambda target: (target.category, target.market, target.name, target.symbol))


def chunk_stock_role_targets(targets: list[StockRoleTarget]) -> list[list[StockRoleTarget]]:
    return [targets[index : index + MAX_SELECT_OPTIONS] for index in range(0, len(targets), MAX_SELECT_OPTIONS)]


def _option_label(target: StockRoleTarget) -> str:
    if target.symbol and target.symbol not in target.name:
        return f"{target.name} · {target.symbol}"[:100]
    return target.name[:100]


def _option_description(target: StockRoleTarget) -> str | None:
    parts = [part for part in [target.category, target.market] if part]
    return " · ".join(parts)[:100] if parts else None


class StockRoleSelect(discord.ui.Select):
    def __init__(self, index: int, targets: list[StockRoleTarget]) -> None:
        options = [
            discord.SelectOption(
                label=_option_label(target),
                value=target.key,
                description=_option_description(target),
            )
            for target in targets
            if target.role_id is not None
        ]
        super().__init__(
            custom_id=f"stock-role-select-{index}",
            placeholder=f"관심종목 선택 {index + 1}",
            min_values=1,
            max_values=max(1, min(len(options), MAX_SELECT_OPTIONS)),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("서버 안에서만 사용할 수 있습니다.", ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await guild.fetch_member(interaction.user.id)

        state = load_state()
        role_ids = get_guild_stock_role_ids(state, guild.id)

        added: list[str] = []
        removed: list[str] = []
        missing: list[str] = []

        for target_key in self.values:
            role_id = role_ids.get(target_key)
            role = guild.get_role(role_id) if isinstance(role_id, int) else None
            if role is None:
                missing.append(target_key)
                continue

            if role in member.roles:
                await member.remove_roles(role, reason="관심종목 알림 역할 해제")
                removed.append(role.name)
            else:
                await member.add_roles(role, reason="관심종목 알림 역할 부여")
                added.append(role.name)

        lines = []
        if added:
            lines.append("추가: " + ", ".join(added))
        if removed:
            lines.append("해제: " + ", ".join(removed))
        if missing:
            lines.append("역할을 찾지 못한 종목이 있습니다. 잠시 후 다시 시도해주세요.")

        await interaction.response.send_message("\n".join(lines) if lines else "변경된 역할이 없습니다.", ephemeral=True)


class StockRoleView(discord.ui.View):
    def __init__(self, targets: list[StockRoleTarget]) -> None:
        super().__init__(timeout=None)
        for index, chunk in enumerate(chunk_stock_role_targets(targets)):
            selectable = [target for target in chunk if target.role_id is not None]
            if selectable:
                self.add_item(StockRoleSelect(index, selectable))


async def _fetch_text_channel(client: discord.Client, channel_id: int) -> discord.TextChannel | None:
    channel = client.get_channel(channel_id)
    if channel is None:
        try:
            channel = await client.fetch_channel(channel_id)
        except Exception:
            return None
    return channel if isinstance(channel, discord.TextChannel) else None


async def _ensure_role(guild: discord.Guild, target: StockRoleTarget, role_id: int | None) -> discord.Role:
    role = guild.get_role(role_id) if isinstance(role_id, int) else None
    desired_name = stock_role_name(target)
    if role is None:
        role = discord.utils.get(guild.roles, name=desired_name)
    if role is None:
        return await guild.create_role(name=desired_name, mentionable=True, reason="관심종목 알림 역할 동기화")
    if not role.mentionable:
        await role.edit(mentionable=True, reason="관심종목 알림 역할 멘션 허용")
    return role


def _role_message_embed(target_count: int) -> discord.Embed:
    description = (
        "아래 목록에서 종목을 선택하면 해당 종목 알림 역할을 받거나 해제합니다.\n"
        "관심종목 뉴스나 등락 알림이 올라올 때 선택한 종목 역할이 함께 태그됩니다."
    )
    embed = discord.Embed(title="관심종목 알림 구독", description=description, color=0x14B8A6)
    embed.set_footer(text=f"현재 {target_count}개 종목")
    return embed


async def sync_stock_roles_once(client: discord.Client) -> None:
    if not STOCK_DASHBOARD_ROLE_SYNC_ENABLED:
        return
    if STOCK_DASHBOARD_ROLE_CHANNEL_ID is None:
        return

    state = load_state()
    channel = await _fetch_text_channel(client, STOCK_DASHBOARD_ROLE_CHANNEL_ID)
    if channel is None:
        set_job_last_run(state, ROLE_SYNC_JOB_KEY, "failed", "role-channel-unavailable")
        save_state(state)
        logger.warning("[stock-role] 역할 부여 채널을 찾지 못했습니다 channel=%s", STOCK_DASHBOARD_ROLE_CHANNEL_ID)
        return

    guild = channel.guild
    set_guild_stock_role_channel_id(state, guild.id, channel.id)

    try:
        fetched_targets = await asyncio.to_thread(fetch_dashboard_stock_role_targets)
    except Exception as exc:
        set_job_last_run(state, ROLE_SYNC_JOB_KEY, "failed", str(exc))
        save_state(state)
        logger.exception("[stock-role] 관심종목 역할 동기화 대상 조회 실패: %s", exc)
        return

    role_ids = get_guild_stock_role_ids(state, guild.id)
    synced_targets: list[StockRoleTarget] = []
    for target in fetched_targets:
        try:
            role = await _ensure_role(guild, target, role_ids.get(target.key))
        except Exception as exc:
            logger.exception("[stock-role] 역할 생성 실패 guild=%s symbol=%s: %s", guild.id, target.symbol, exc)
            continue
        set_guild_stock_role_id(state, guild.id, target.key, role.id)
        synced_targets.append(
            StockRoleTarget(
                key=target.key,
                symbol=target.symbol,
                name=target.name,
                market=target.market,
                category=target.category,
                role_id=role.id,
            )
        )

    set_guild_stock_role_targets(
        state,
        guild.id,
        {target.key: target.to_state() for target in synced_targets},
    )

    view = StockRoleView(synced_targets)
    embed = _role_message_embed(len(synced_targets))
    message_id = get_guild_stock_role_message_id(state, guild.id)
    message: discord.Message | None = None
    if message_id is not None:
        try:
            message = await channel.fetch_message(message_id)
        except Exception:
            message = None

    if message is None:
        message = await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())
    else:
        await message.edit(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())

    set_guild_stock_role_message_id(state, guild.id, message.id)
    set_job_last_run(state, ROLE_SYNC_JOB_KEY, "ok", f"targets={len(synced_targets)} channel={channel.id}")
    save_state(state)
    logger.info("[stock-role] 관심종목 역할 동기화 완료 guild=%s targets=%s", guild.id, len(synced_targets))


async def stock_role_scheduler(client: discord.Client) -> None:
    while True:
        try:
            await sync_stock_roles_once(client)
        except Exception as exc:
            logger.exception("[stock-role] 관심종목 역할 동기화 루프 실패: %s", exc)
        await asyncio.sleep(STOCK_DASHBOARD_ROLE_SYNC_INTERVAL_SECONDS)


def stock_role_mentions_for_text(state: dict[str, Any], guild_id: int, text: str, *, limit: int = 5) -> str:
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return ""

    targets = get_guild_stock_role_targets(state, guild_id)
    mentions: list[str] = []
    seen_role_ids: set[int] = set()
    for target in targets.values():
        role_id = target.get("role_id")
        if not isinstance(role_id, int) or role_id in seen_role_ids:
            continue

        terms = [
            str(target.get("symbol") or "").strip(),
            str(target.get("name") or "").strip(),
        ]
        if any(_normalize_text(term) and _normalize_text(term) in normalized_text for term in terms):
            mentions.append(f"<@&{role_id}>")
            seen_role_ids.add(role_id)
        if len(mentions) >= limit:
            break

    return " ".join(mentions)


def stock_role_mentions_for_items(state: dict[str, Any], guild_id: int, items: list[dict[str, Any]], *, limit: int = 5) -> str:
    texts: list[str] = []
    for item in items:
        texts.extend(
            [
                str(item.get("symbol") or ""),
                str(item.get("ticker") or ""),
                str(item.get("name") or ""),
                str(item.get("title") or ""),
                str(item.get("summary") or ""),
                str(item.get("description") or ""),
            ]
        )
    return stock_role_mentions_for_text(state, guild_id, "\n".join(texts), limit=limit)
