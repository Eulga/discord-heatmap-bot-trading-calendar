from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import discord

from bot.app.settings import (
    INTEL_API_TIMEOUT_SECONDS,
    STOCK_DASHBOARD_ACCESS_ROLE_GUILD_ID,
    STOCK_DASHBOARD_ACCESS_ROLE_NAME,
    STOCK_DASHBOARD_ACCESS_ROLE_SYNC_ENABLED,
    STOCK_DASHBOARD_ACCESS_ROLE_SYNC_TIME,
    STOCK_DASHBOARD_API_BASE_URL,
    STOCK_DASHBOARD_INTERNAL_TOKEN,
    STOCK_DASHBOARD_LOGIN_CHANNEL_ID,
    STOCK_DASHBOARD_ROLE_CHANNEL_ID,
)
from bot.common.clock import now_kst
from bot.forum.repository import get_job_last_runs, load_state, save_state, set_job_last_run

logger = logging.getLogger(__name__)

DASHBOARD_ACCESS_ROLE_SYNC_JOB_KEY = "dashboard_access_role_sync"


class DashboardAccessRoleSyncError(RuntimeError):
    pass


def _parse_sync_time(value: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = value.split(":", maxsplit=1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (TypeError, ValueError):
        return 6, 10

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return 6, 10
    return hour, minute


def _has_success_today(state: dict[str, Any], now: datetime) -> bool:
    last_run = get_job_last_runs(state).get(DASHBOARD_ACCESS_ROLE_SYNC_JOB_KEY)
    if not isinstance(last_run, dict) or last_run.get("status") != "ok":
        return False
    run_at = str(last_run.get("run_at") or "")
    return run_at.startswith(now.strftime("%Y-%m-%d"))


def _is_due(now: datetime, state: dict[str, Any]) -> bool:
    if _has_success_today(state, now):
        return False
    hour, minute = _parse_sync_time(STOCK_DASHBOARD_ACCESS_ROLE_SYNC_TIME)
    due_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return now >= due_at


async def _fetch_channel(client: discord.Client, channel_id: int) -> discord.abc.GuildChannel | discord.Thread | None:
    channel = client.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await client.fetch_channel(channel_id)
    except Exception:
        return None


async def _resolve_guild(client: discord.Client) -> discord.Guild | None:
    if STOCK_DASHBOARD_ACCESS_ROLE_GUILD_ID is not None:
        guild = client.get_guild(STOCK_DASHBOARD_ACCESS_ROLE_GUILD_ID)
        if guild is not None:
            return guild

    for channel_id in [STOCK_DASHBOARD_LOGIN_CHANNEL_ID, STOCK_DASHBOARD_ROLE_CHANNEL_ID]:
        if channel_id is None:
            continue
        channel = await _fetch_channel(client, channel_id)
        guild = getattr(channel, "guild", None)
        if isinstance(guild, discord.Guild):
            return guild

    if len(client.guilds) == 1:
        return client.guilds[0]

    return None


async def _fetch_access_role_member_ids(guild: discord.Guild, role: discord.Role) -> set[int]:
    member_ids: set[int] = set()

    try:
        await guild.chunk(cache=True)
    except Exception as exc:
        logger.warning("[dashboard-access] guild member chunk 실패 guild=%s role=%s: %s", guild.id, role.id, exc)

    cached_role = guild.get_role(role.id) or role
    member_ids.update(member.id for member in cached_role.members)

    try:
        async for member in guild.fetch_members(limit=None):
            if any(member_role.id == role.id for member_role in member.roles):
                member_ids.add(member.id)
    except (discord.Forbidden, discord.HTTPException) as exc:
        if member_ids:
            logger.warning(
                "[dashboard-access] member fetch 실패로 캐시된 역할 멤버를 사용합니다. guild=%s role=%s count=%s",
                guild.id,
                role.id,
                len(member_ids),
            )
            return member_ids
        raise DashboardAccessRoleSyncError("Discord 멤버 목록을 읽을 수 없습니다. Server Members Intent와 봇 권한을 확인해주세요.") from exc

    return member_ids


def _request_dashboard_role_sync_sync(guild_id: int, role_name: str, active_discord_user_ids: set[int]) -> dict[str, Any]:
    if not STOCK_DASHBOARD_API_BASE_URL or not STOCK_DASHBOARD_INTERNAL_TOKEN:
        raise DashboardAccessRoleSyncError("대시보드 내부 API 설정이 없습니다.")

    request = Request(
        f"{STOCK_DASHBOARD_API_BASE_URL.rstrip('/')}/api/internal/auth/discord-role-sync",
        data=json.dumps(
            {
                "activeDiscordUserIds": [str(user_id) for user_id in sorted(active_discord_user_ids)],
                "guildId": str(guild_id),
                "roleName": role_name,
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "discord-heatmap-bot/1.0",
            "x-internal-token": STOCK_DASHBOARD_INTERNAL_TOKEN,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=INTEL_API_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            error_payload = {}
        message = error_payload.get("error") if isinstance(error_payload, dict) else None
        raise DashboardAccessRoleSyncError(str(message or f"대시보드 역할 동기화 API 오류가 발생했습니다. ({exc.code})")) from exc
    except URLError as exc:
        raise DashboardAccessRoleSyncError("대시보드 역할 동기화 API에 연결할 수 없습니다.") from exc

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise DashboardAccessRoleSyncError("대시보드 역할 동기화 응답이 올바르지 않습니다.")
    return data


async def sync_dashboard_access_role_once(client: discord.Client) -> None:
    if not STOCK_DASHBOARD_ACCESS_ROLE_SYNC_ENABLED:
        return

    state = load_state()
    guild = await _resolve_guild(client)
    if guild is None:
        set_job_last_run(state, DASHBOARD_ACCESS_ROLE_SYNC_JOB_KEY, "failed", "guild-unavailable")
        save_state(state)
        logger.warning("[dashboard-access] 접근 역할 동기화 실패: 대상 guild를 찾을 수 없습니다.")
        return

    role = discord.utils.get(guild.roles, name=STOCK_DASHBOARD_ACCESS_ROLE_NAME)
    if role is None:
        set_job_last_run(state, DASHBOARD_ACCESS_ROLE_SYNC_JOB_KEY, "failed", "role-unavailable")
        save_state(state)
        logger.warning(
            "[dashboard-access] 접근 역할 동기화 실패: 역할을 찾을 수 없습니다. guild=%s role=%s",
            guild.id,
            STOCK_DASHBOARD_ACCESS_ROLE_NAME,
        )
        return

    try:
        member_ids = await _fetch_access_role_member_ids(guild, role)
    except DashboardAccessRoleSyncError as exc:
        set_job_last_run(state, DASHBOARD_ACCESS_ROLE_SYNC_JOB_KEY, "failed", str(exc))
        save_state(state)
        logger.warning("[dashboard-access] 접근 역할 멤버 조회 실패 guild=%s role=%s reason=%s", guild.id, role.id, exc)
        return

    if not member_ids:
        set_job_last_run(state, DASHBOARD_ACCESS_ROLE_SYNC_JOB_KEY, "failed", "role-has-no-members")
        save_state(state)
        logger.warning(
            "[dashboard-access] 접근 역할 멤버가 0명이라 대시보드 계정 상태를 변경하지 않았습니다. guild=%s role=%s",
            guild.id,
            role.id,
        )
        return

    try:
        result = await asyncio.to_thread(_request_dashboard_role_sync_sync, guild.id, role.name, member_ids)
    except DashboardAccessRoleSyncError as exc:
        set_job_last_run(state, DASHBOARD_ACCESS_ROLE_SYNC_JOB_KEY, "failed", str(exc))
        save_state(state)
        logger.warning("[dashboard-access] 대시보드 역할 동기화 실패 guild=%s role=%s reason=%s", guild.id, role.id, exc)
        return

    detail = (
        f"role={role.name} active={result.get('activeDiscordUserCount')} "
        f"disabled={result.get('disabled')} reactivated={result.get('reactivated')}"
    )
    set_job_last_run(state, DASHBOARD_ACCESS_ROLE_SYNC_JOB_KEY, "ok", detail)
    save_state(state)
    logger.info("[dashboard-access] 접근 역할 동기화 완료 guild=%s %s", guild.id, detail)


async def dashboard_access_role_scheduler(client: discord.Client) -> None:
    while True:
        try:
            state = load_state()
            current_time = now_kst()
            if _is_due(current_time, state):
                await sync_dashboard_access_role_once(client)
        except Exception as exc:
            logger.exception("[dashboard-access] 접근 역할 동기화 루프 실패: %s", exc)
        await asyncio.sleep(300)
