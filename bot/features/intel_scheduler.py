import asyncio
import logging
from datetime import datetime

import discord

from bot.app.settings import (
    EOD_SUMMARY_ENABLED,
    EOD_SUMMARY_TIME,
    EOD_TARGET_FORUM_ID,
    NEWS_BRIEFING_ENABLED,
    NEWS_BRIEFING_TIME,
    NEWS_BRIEFING_TRADING_DAYS_ONLY,
    NEWS_TARGET_FORUM_ID,
    WATCH_ALERT_CHANNEL_ID,
    WATCH_POLL_ENABLED,
    WATCH_POLL_INTERVAL_SECONDS,
)
from bot.common.clock import date_key, now_kst, timestamp_text
from bot.features.eod.policy import build_body as build_eod_body
from bot.features.eod.policy import build_post_title as build_eod_title
from bot.features.news.policy import build_body as build_news_body
from bot.features.news.policy import build_post_title as build_news_title
from bot.forum.repository import (
    get_guild_eod_forum_channel_id,
    get_guild_forum_channel_id,
    get_guild_last_auto_run_date,
    get_guild_news_forum_channel_id,
    get_guild_watch_alert_channel_id,
    get_watch_baseline,
    list_guild_ids,
    list_watch_symbols,
    load_state,
    save_state,
    set_guild_last_auto_run_date,
    set_job_last_run,
    set_provider_status,
    set_watch_baseline,
)
from bot.forum.service import upsert_daily_post
from bot.intel.providers.market import MockEodSummaryProvider, MockMarketDataProvider
from bot.intel.providers.news import MockNewsProvider, NewsItem
from bot.markets.trading_calendar import safe_check_krx_trading_day

logger = logging.getLogger(__name__)

news_provider = MockNewsProvider()
eod_provider = MockEodSummaryProvider()
quote_provider = MockMarketDataProvider()


def _parse_time(text: str, default_h: int, default_m: int) -> tuple[int, int]:
    try:
        h, m = text.split(":", maxsplit=1)
        return int(h), int(m)
    except Exception:
        return default_h, default_m


async def _run_news_job(client: discord.Client, now: datetime) -> None:
    state = load_state()
    run_date = date_key(now)
    pending_guilds: list[tuple[int, int]] = []
    missing_forum = 0

    for guild_id in list_guild_ids(state):
        if get_guild_last_auto_run_date(state, guild_id, "newsbriefing") == run_date:
            continue
        forum_channel_id = (
            get_guild_news_forum_channel_id(state, guild_id)
            or NEWS_TARGET_FORUM_ID
            or get_guild_forum_channel_id(state, guild_id)
        )
        if forum_channel_id is None:
            missing_forum += 1
            continue
        pending_guilds.append((guild_id, forum_channel_id))

    if not pending_guilds:
        if missing_forum > 0:
            set_job_last_run(state, "news_briefing", "skipped", f"no-target-forums missing_forum={missing_forum}")
            save_state(state)
        return

    if NEWS_BRIEFING_TRADING_DAYS_ONLY:
        is_trading_day, err = safe_check_krx_trading_day(now)
        if is_trading_day is not True:
            reason = "holiday" if is_trading_day is False else f"calendar-failed:{err}"
            set_job_last_run(state, "news_briefing", "skipped", reason)
            save_state(state)
            return

    try:
        items = await news_provider.fetch(now)
        set_provider_status(state, "news_provider", True, f"fetched={len(items)}")
    except Exception as exc:
        set_provider_status(state, "news_provider", False, str(exc))
        set_job_last_run(state, "news_briefing", "failed", str(exc))
        save_state(state)
        logger.exception("[intel] news fetch failed: %s", exc)
        return

    deduped: list[NewsItem] = []
    seen_keys: set[str] = set()
    for item in items:
        key = item.dedup_key()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(item)

    domestic = [x for x in deduped if x.region == "domestic"][:5]
    global_items = [x for x in deduped if x.region == "global"][:5]
    body = build_news_body(timestamp_text(now), domestic, global_items)
    posted = 0
    failed = 0

    for guild_id, forum_channel_id in pending_guilds:
        try:
            await upsert_daily_post(
                client=client,
                state=state,
                guild_id=guild_id,
                forum_channel_id=forum_channel_id,
                command_key="newsbriefing",
                post_title=build_news_title(),
                body_text=body,
                image_paths=[],
            )
            set_guild_last_auto_run_date(state, guild_id, "newsbriefing", run_date)
            posted += 1
        except Exception as exc:
            failed += 1
            logger.exception("[intel] news post failed guild=%s: %s", guild_id, exc)

    if posted > 0:
        set_job_last_run(
            state,
            "news_briefing",
            "ok",
            f"posted={posted} failed={failed} missing_forum={missing_forum} domestic={len(domestic)} global={len(global_items)}",
        )
    else:
        set_job_last_run(
            state,
            "news_briefing",
            "failed",
            f"posted=0 failed={failed} missing_forum={missing_forum}",
        )
    save_state(state)


async def _run_eod_job(client: discord.Client, now: datetime) -> None:
    state = load_state()
    run_date = date_key(now)
    pending_guilds: list[tuple[int, int]] = []
    missing_forum = 0

    for guild_id in list_guild_ids(state):
        if get_guild_last_auto_run_date(state, guild_id, "eodsummary") == run_date:
            continue
        forum_channel_id = (
            get_guild_eod_forum_channel_id(state, guild_id)
            or EOD_TARGET_FORUM_ID
            or get_guild_forum_channel_id(state, guild_id)
        )
        if forum_channel_id is None:
            missing_forum += 1
            continue
        pending_guilds.append((guild_id, forum_channel_id))

    if not pending_guilds:
        if missing_forum > 0:
            set_job_last_run(state, "eod_summary", "skipped", f"no-target-forums missing_forum={missing_forum}")
            save_state(state)
        return

    is_trading_day, err = safe_check_krx_trading_day(now)
    if is_trading_day is not True:
        reason = "holiday" if is_trading_day is False else f"calendar-failed:{err}"
        set_job_last_run(state, "eod_summary", "skipped", reason)
        save_state(state)
        return

    try:
        summary = await eod_provider.get_summary(now)
        set_provider_status(state, "eod_provider", True, "summary-ready")
    except Exception as exc:
        set_provider_status(state, "eod_provider", False, str(exc))
        set_job_last_run(state, "eod_summary", "failed", str(exc))
        save_state(state)
        logger.exception("[intel] eod summary failed: %s", exc)
        return

    body = build_eod_body(timestamp_text(now), summary)
    posted = 0
    failed = 0

    for guild_id, forum_channel_id in pending_guilds:
        try:
            await upsert_daily_post(
                client=client,
                state=state,
                guild_id=guild_id,
                forum_channel_id=forum_channel_id,
                command_key="eodsummary",
                post_title=build_eod_title(),
                body_text=body,
                image_paths=[],
            )
            set_guild_last_auto_run_date(state, guild_id, "eodsummary", run_date)
            posted += 1
        except Exception as exc:
            failed += 1
            logger.exception("[intel] eod post failed guild=%s: %s", guild_id, exc)

    if posted > 0:
        set_job_last_run(
            state,
            "eod_summary",
            "ok",
            f"posted={posted} failed={failed} missing_forum={missing_forum} date={summary.date_text}",
        )
    else:
        set_job_last_run(
            state,
            "eod_summary",
            "failed",
            f"posted=0 failed={failed} missing_forum={missing_forum} date={summary.date_text}",
        )
    save_state(state)


async def _run_watch_poll(client: discord.Client, now: datetime) -> None:
    state = load_state()
    sent = 0
    for guild_id in list_guild_ids(state):
        symbols = list_watch_symbols(state, guild_id)
        if not symbols:
            continue
        alert_channel_id = get_guild_watch_alert_channel_id(state, guild_id) or WATCH_ALERT_CHANNEL_ID
        if alert_channel_id is None:
            continue
        channel = client.get_channel(alert_channel_id)
        if channel is None:
            try:
                channel = await client.fetch_channel(alert_channel_id)
            except Exception:
                continue
        if not isinstance(channel, discord.abc.Messageable):
            continue

        for symbol in symbols:
            try:
                quote = await quote_provider.get_quote(symbol, now)
                set_provider_status(state, "market_data_provider", True, f"quote:{symbol}")
            except Exception as exc:
                set_provider_status(state, "market_data_provider", False, str(exc))
                continue

            baseline = get_watch_baseline(state, guild_id, symbol) or quote.price
            from bot.features.watch.service import evaluate_watch_signal

            should_send, direction, change_pct = evaluate_watch_signal(
                state=state,
                guild_id=guild_id,
                symbol=symbol,
                base_price=baseline,
                current_price=quote.price,
            )
            set_watch_baseline(state, guild_id, symbol, baseline, now.isoformat())
            if should_send:
                emoji = "📈" if direction == "up" else "📉"
                await channel.send(
                    f"{emoji} `{symbol}` 변동 알림: 기준가 {baseline:,.2f} → 현재가 {quote.price:,.2f} ({change_pct:+.2f}%)"
                )
                sent += 1

    set_job_last_run(state, "watch_poll", "ok", f"alerts={sent}")
    save_state(state)


async def intel_scheduler(client: discord.Client) -> None:
    news_h, news_m = _parse_time(NEWS_BRIEFING_TIME, 7, 30)
    eod_h, eod_m = _parse_time(EOD_SUMMARY_TIME, 16, 20)
    last_watch_run: datetime | None = None

    while True:
        now = now_kst()
        try:
            if NEWS_BRIEFING_ENABLED and now.hour == news_h and now.minute == news_m:
                await _run_news_job(client, now)
            if EOD_SUMMARY_ENABLED and now.hour == eod_h and now.minute == eod_m:
                await _run_eod_job(client, now)

            if WATCH_POLL_ENABLED:
                if last_watch_run is None or (now - last_watch_run).total_seconds() >= WATCH_POLL_INTERVAL_SECONDS:
                    await _run_watch_poll(client, now)
                    last_watch_run = now
        except Exception as exc:
            state = load_state()
            set_job_last_run(state, "intel_scheduler", "failed", str(exc))
            save_state(state)
            logger.exception("[intel] scheduler error: %s", exc)
        await asyncio.sleep(15)
