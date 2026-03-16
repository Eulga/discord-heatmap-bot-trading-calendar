import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

from bot.app.settings import KOREA_MARKET_URLS, US_MARKET_URLS
from bot.common.clock import date_key, now_kst
from bot.features.kheatmap.policy import build_body as build_k_body
from bot.features.kheatmap.policy import build_post_title as build_k_title
from bot.features.runner import execute_heatmap_for_guild
from bot.features.usheatmap.policy import build_body as build_us_body
from bot.features.usheatmap.policy import build_post_title as build_us_title
from bot.forum.repository import (
    get_auto_enabled_guild_ids,
    get_guild_last_auto_run_date,
    get_guild_last_auto_skip_date,
    load_state,
    save_state,
    set_guild_last_auto_run_date,
    set_guild_last_auto_skip,
)
from bot.markets.providers.korea import capture as capture_korea
from bot.markets.providers.us import capture as capture_us
from bot.markets.trading_calendar import safe_check_krx_trading_day, safe_check_nyse_trading_day

logger = logging.getLogger(__name__)

TradingDayCheck = Callable[[datetime], tuple[bool | None, str | None]]


def _jobs_for_now(now: datetime) -> list[tuple[str, dict[str, str], object, object, object, int, int, TradingDayCheck]]:
    jobs: list[tuple[str, dict[str, str], object, object, object, int, int, TradingDayCheck]] = []
    if now.hour == 15 and now.minute == 35:
        jobs.append(
            (
                "kheatmap",
                KOREA_MARKET_URLS,
                capture_korea,
                build_k_title,
                build_k_body,
                15,
                35,
                safe_check_krx_trading_day,
            )
        )
    if now.hour == 6 and now.minute == 5:
        jobs.append(
            (
                "usheatmap",
                US_MARKET_URLS,
                capture_us,
                build_us_title,
                build_us_body,
                6,
                5,
                safe_check_nyse_trading_day,
            )
        )
    return jobs


async def process_auto_screenshot_tick(client, now: datetime | None = None) -> None:
    tick_now = now or now_kst()
    current_date = date_key(tick_now)
    jobs = _jobs_for_now(tick_now)
    if not jobs:
        return

    state = load_state()
    guild_ids = get_auto_enabled_guild_ids(state)

    for guild_id in guild_ids:
        for command_key, targets, capture_func, title_builder, body_builder, h, m, trading_day_check in jobs:
            last_run = get_guild_last_auto_run_date(state, guild_id, command_key)
            if last_run == current_date:
                continue

            is_trading_day, check_error = trading_day_check(tick_now)
            if is_trading_day is None:
                reason = f"calendar-check-failed: {check_error}"
                last_skip_date = get_guild_last_auto_skip_date(state, guild_id, command_key)
                if last_skip_date != current_date:
                    set_guild_last_auto_skip(state, guild_id, command_key, current_date, reason)
                    save_state(state)
                logger.warning(
                    "[auto-screenshot] skipped guild=%s command=%s at=%02d:%02d reason=%s",
                    guild_id,
                    command_key,
                    h,
                    m,
                    reason,
                )
                continue

            if is_trading_day is False:
                reason = "holiday"
                last_skip_date = get_guild_last_auto_skip_date(state, guild_id, command_key)
                if last_skip_date != current_date:
                    set_guild_last_auto_skip(state, guild_id, command_key, current_date, reason)
                    save_state(state)
                logger.info(
                    "[auto-screenshot] skipped guild=%s command=%s at=%02d:%02d reason=%s",
                    guild_id,
                    command_key,
                    h,
                    m,
                    reason,
                )
                continue

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
                set_guild_last_auto_run_date(state, guild_id, command_key, current_date)
                save_state(state)
                logger.info(
                    "[auto-screenshot] success guild=%s command=%s at=%02d:%02d msg=%s",
                    guild_id,
                    command_key,
                    h,
                    m,
                    message,
                )
            else:
                logger.error(
                    "[auto-screenshot] failed guild=%s command=%s at=%02d:%02d reason=%s",
                    guild_id,
                    command_key,
                    h,
                    m,
                    message,
                )


async def auto_screenshot_scheduler(client) -> None:
    while True:
        try:
            await process_auto_screenshot_tick(client=client)
            await asyncio.sleep(30)
        except Exception as exc:
            logger.exception("[auto-screenshot] scheduler error: %s", exc)
            await asyncio.sleep(30)
