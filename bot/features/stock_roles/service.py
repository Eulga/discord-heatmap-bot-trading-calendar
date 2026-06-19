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
    get_guild_stock_role_stale_targets,
    get_guild_stock_role_targets,
    load_state,
    remove_guild_stock_role_id,
    save_state,
    set_guild_stock_role_channel_id,
    set_guild_stock_role_id,
    set_guild_stock_role_message_id,
    set_guild_stock_role_stale_targets,
    set_guild_stock_role_targets,
    set_job_last_run,
)

logger = logging.getLogger(__name__)

MAX_SELECT_OPTIONS = 25
ROLE_SYNC_JOB_KEY = "stock_role_sync"
STALE_ROLE_PREFIX = "미사용 "
LEGACY_STOCK_ROLE_PREFIXES = ("종목",)


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


@dataclass(frozen=True)
class StockRoleCleanupResult:
    deleted: int
    missing: int
    failed: int
    names: list[str]


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
    if prefix:
        return f"{prefix} {name}"[:100].strip()
    return name[:100].strip()


def _strip_stock_role_prefix(role_name: str) -> str:
    cleaned_name = _safe_role_text(role_name)
    prefixes = [STOCK_DASHBOARD_ROLE_PREFIX, *LEGACY_STOCK_ROLE_PREFIXES]
    for raw_prefix in prefixes:
        prefix = _safe_role_text(raw_prefix)
        if prefix and cleaned_name.startswith(prefix + " "):
            return cleaned_name[len(prefix) :].strip()
    return cleaned_name


def unused_stock_role_name(role_name: str) -> str:
    cleaned_name = _safe_role_text(role_name)
    if cleaned_name.startswith(STALE_ROLE_PREFIX):
        body = cleaned_name[len(STALE_ROLE_PREFIX) :].strip()
    else:
        body = cleaned_name
    body = _strip_stock_role_prefix(body)
    return f"{STALE_ROLE_PREFIX}{body}"[:100].strip()


def legacy_unused_stock_role_names(role_name: str) -> list[str]:
    cleaned_name = _safe_role_text(role_name)
    names: list[str] = []
    for raw_prefix in LEGACY_STOCK_ROLE_PREFIXES:
        prefix = _safe_role_text(raw_prefix)
        if prefix:
            names.append(f"{STALE_ROLE_PREFIX}{prefix} {cleaned_name}"[:100].strip())
    return names


def stale_stock_role_targets(
    previous_targets: dict[str, dict[str, Any]],
    role_ids: dict[str, int],
    active_keys: set[str],
) -> dict[str, dict[str, Any]]:
    stale_targets: dict[str, dict[str, Any]] = {}
    candidate_keys = set(previous_targets) | set(role_ids)
    for target_key in sorted(candidate_keys - active_keys):
        payload = dict(previous_targets.get(target_key) or {})
        role_id = role_ids.get(target_key)
        if not isinstance(role_id, int):
            fallback_role_id = payload.get("role_id")
            role_id = fallback_role_id if isinstance(fallback_role_id, int) else None
        if isinstance(role_id, int):
            payload["role_id"] = role_id
            stale_targets[target_key] = payload
    return stale_targets


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


def _subscription_option_label(target: StockRoleTarget, subscribed: bool) -> str:
    prefix = "✅ " if subscribed else "▫ "
    return f"{prefix}{_option_label(target)}"[:100]


def _stock_role_targets_from_state(state: dict[str, Any], guild_id: int) -> list[StockRoleTarget]:
    raw_targets = get_guild_stock_role_targets(state, guild_id)
    targets: list[StockRoleTarget] = []
    for target_key, payload in raw_targets.items():
        role_id = payload.get("role_id")
        targets.append(
            StockRoleTarget(
                key=target_key,
                symbol=str(payload.get("symbol") or ""),
                name=str(payload.get("name") or payload.get("symbol") or target_key),
                market=str(payload.get("market") or ""),
                category=str(payload.get("category") or ""),
                role_id=role_id if isinstance(role_id, int) else None,
            )
        )
    return sorted(targets, key=lambda target: (target.category, target.market, target.name, target.symbol))


def _member_role_ids(member: discord.Member) -> set[int]:
    return {role.id for role in member.roles}


class PersonalStockRoleSelect(discord.ui.Select):
    def __init__(self, index: int, targets: list[StockRoleTarget], member_role_ids: set[int]) -> None:
        self.targets = targets
        options = [
            discord.SelectOption(
                label=_subscription_option_label(target, target.role_id in member_role_ids),
                value=target.key,
                description=_option_description(target),
                default=target.role_id in member_role_ids,
            )
            for target in targets
            if target.role_id is not None
        ]
        super().__init__(
            custom_id=f"stock-role-personal-select-{index}",
            placeholder=f"구독 종목 선택 {index + 1}",
            min_values=0,
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
        role_targets = get_guild_stock_role_targets(state, guild.id)

        added: list[str] = []
        removed: list[str] = []
        missing: list[str] = []
        selected_keys = set(self.values)

        for target in self.targets:
            role_id = target.role_id if isinstance(target.role_id, int) else role_ids.get(target.key)
            if not isinstance(role_id, int):
                role_target = role_targets.get(target.key)
                if isinstance(role_target, dict):
                    fallback_role_id = role_target.get("role_id")
                    role_id = fallback_role_id if isinstance(fallback_role_id, int) else None
            role = guild.get_role(role_id) if isinstance(role_id, int) else None
            if role is None:
                missing.append(target.key)
                continue

            is_selected = target.key in selected_keys
            has_role = role in member.roles
            if is_selected and not has_role:
                await member.add_roles(role, reason="관심종목 알림 역할 부여")
                added.append(role.name)
            elif not is_selected and has_role:
                await member.remove_roles(role, reason="관심종목 알림 역할 해제")
                removed.append(role.name)

        lines = []
        if added:
            lines.append("구독 추가: " + ", ".join(added))
        if removed:
            lines.append("구독 해제: " + ", ".join(removed))
        if missing:
            lines.append("역할을 찾지 못한 종목이 있습니다. 잠시 후 다시 시도해주세요.")

        await interaction.response.send_message("\n".join(lines) if lines else "변경된 구독이 없습니다.", ephemeral=True)


class PersonalStockRoleView(discord.ui.View):
    def __init__(self, targets: list[StockRoleTarget], member: discord.Member) -> None:
        super().__init__(timeout=300)
        member_role_ids = _member_role_ids(member)
        for index, chunk in enumerate(chunk_stock_role_targets(targets)):
            selectable = [target for target in chunk if target.role_id is not None]
            if selectable:
                self.add_item(PersonalStockRoleSelect(index, selectable, member_role_ids))


class StockRoleManageButton(discord.ui.Button):
    def __init__(self, disabled: bool = False) -> None:
        super().__init__(
            label="구독 관리",
            style=discord.ButtonStyle.primary,
            custom_id="stock-role-manage",
            disabled=disabled,
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
        targets = _stock_role_targets_from_state(state, guild.id)
        if not targets:
            await interaction.response.send_message("구독할 관심종목이 없습니다.", ephemeral=True)
            return

        view = PersonalStockRoleView(targets, member)
        await interaction.response.send_message(
            "체크된 종목은 현재 구독 중입니다. 구독할 종목만 선택한 뒤 저장하면 됩니다.",
            view=view,
            ephemeral=True,
        )


class StockRoleView(discord.ui.View):
    def __init__(self, target_count: int) -> None:
        super().__init__(timeout=None)
        self.add_item(StockRoleManageButton(disabled=target_count <= 0))


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
        role = discord.utils.get(guild.roles, name=unused_stock_role_name(desired_name))
    if role is None:
        for legacy_name in legacy_unused_stock_role_names(desired_name):
            role = discord.utils.get(guild.roles, name=legacy_name)
            if role is not None:
                break
    if role is None:
        return await guild.create_role(name=desired_name, mentionable=True, reason="관심종목 알림 역할 동기화")
    if role.name != desired_name or not role.mentionable:
        await role.edit(name=desired_name, mentionable=True, reason="관심종목 알림 역할 동기화")
    return role


async def _mark_stale_stock_roles(
    guild: discord.Guild,
    stale_targets: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    marked_targets: dict[str, dict[str, Any]] = {}
    for target_key, payload in stale_targets.items():
        role_id = payload.get("role_id")
        role = guild.get_role(role_id) if isinstance(role_id, int) else None
        if role is None:
            continue
        stale_name = unused_stock_role_name(role.name)
        if role.name != stale_name:
            try:
                await role.edit(name=stale_name, reason="관심종목 삭제로 미사용 역할 표시")
            except Exception as exc:
                logger.exception("[stock-role] 미사용 역할 표시 실패 guild=%s role=%s: %s", guild.id, role.id, exc)
                continue
        marked_payload = dict(payload)
        marked_payload["role_id"] = role.id
        marked_targets[target_key] = marked_payload
    return marked_targets


async def cleanup_stale_stock_roles(guild: discord.Guild) -> StockRoleCleanupResult:
    state = load_state()
    stale_targets = get_guild_stock_role_stale_targets(state, guild.id)
    role_ids = get_guild_stock_role_ids(state, guild.id)
    if not stale_targets:
        return StockRoleCleanupResult(deleted=0, missing=0, failed=0, names=[])

    deleted_names: list[str] = []
    missing = 0
    failed = 0
    for target_key, payload in list(stale_targets.items()):
        role_id = payload.get("role_id")
        if not isinstance(role_id, int):
            role_id = role_ids.get(target_key)
        role = guild.get_role(role_id) if isinstance(role_id, int) else None

        if role is None:
            missing += 1
            stale_targets.pop(target_key, None)
            remove_guild_stock_role_id(state, guild.id, target_key)
            continue

        try:
            deleted_names.append(role.name)
            await role.delete(reason="미사용 관심종목 역할 정리")
        except Exception as exc:
            failed += 1
            logger.exception("[stock-role] 미사용 역할 삭제 실패 guild=%s role=%s: %s", guild.id, role.id, exc)
            continue

        stale_targets.pop(target_key, None)
        remove_guild_stock_role_id(state, guild.id, target_key)

    set_guild_stock_role_stale_targets(state, guild.id, stale_targets)
    save_state(state)
    return StockRoleCleanupResult(deleted=len(deleted_names), missing=missing, failed=failed, names=deleted_names)


def _role_message_embed(target_count: int) -> discord.Embed:
    description = (
        "`구독 관리` 버튼을 누르면 본인에게만 보이는 종목 선택창이 열립니다.\n"
        "체크된 종목은 현재 구독 중이며, 관심종목 뉴스나 등락 알림이 올라올 때 해당 역할이 태그됩니다."
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
    bot_member = guild.me
    if bot_member is None and client.user is not None:
        try:
            bot_member = await guild.fetch_member(client.user.id)
        except Exception:
            bot_member = None
    if bot_member is None or not bot_member.guild_permissions.manage_roles:
        set_job_last_run(state, ROLE_SYNC_JOB_KEY, "failed", "missing-manage-roles-permission")
        save_state(state)
        logger.warning("[stock-role] 역할 동기화 중단: 봇에 역할 관리 권한이 없습니다 guild=%s", guild.id)
        return

    try:
        fetched_targets = await asyncio.to_thread(fetch_dashboard_stock_role_targets)
    except Exception as exc:
        set_job_last_run(state, ROLE_SYNC_JOB_KEY, "failed", str(exc))
        save_state(state)
        logger.exception("[stock-role] 관심종목 역할 동기화 대상 조회 실패: %s", exc)
        return

    role_ids = get_guild_stock_role_ids(state, guild.id)
    previous_targets = dict(get_guild_stock_role_targets(state, guild.id))
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

    active_keys = {target.key for target in synced_targets}
    stale_targets = stale_stock_role_targets(previous_targets, role_ids, active_keys)
    marked_stale_targets = await _mark_stale_stock_roles(guild, stale_targets)
    set_guild_stock_role_stale_targets(state, guild.id, marked_stale_targets)
    set_guild_stock_role_targets(
        state,
        guild.id,
        {target.key: target.to_state() for target in synced_targets},
    )

    view = StockRoleView(len(synced_targets))
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
    set_job_last_run(
        state,
        ROLE_SYNC_JOB_KEY,
        "ok",
        f"targets={len(synced_targets)} stale={len(marked_stale_targets)} channel={channel.id}",
    )
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
