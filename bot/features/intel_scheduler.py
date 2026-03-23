import asyncio
import logging
from datetime import datetime

import discord

from bot.app.settings import (
    EOD_SUMMARY_ENABLED,
    EOD_SUMMARY_TIME,
    EOD_TARGET_FORUM_ID,
    INTEL_API_RETRY_COUNT,
    INTEL_API_TIMEOUT_SECONDS,
    KIS_APP_KEY,
    KIS_APP_SECRET,
    MASSIVE_API_KEY,
    MARKETAUX_API_TOKEN,
    MARKETAUX_NEWS_COUNTRIES,
    MARKETAUX_NEWS_GLOBAL_QUERIES,
    MARKETAUX_NEWS_LANGUAGE,
    MARKET_DATA_PROVIDER_KIND,
    NAVER_NEWS_CLIENT_ID,
    NAVER_NEWS_CLIENT_SECRET,
    NAVER_NEWS_DOMESTIC_QUERIES,
    NAVER_NEWS_DOMESTIC_STOCK_QUERIES,
    NAVER_NEWS_GLOBAL_QUERY,
    NAVER_NEWS_GLOBAL_QUERIES,
    NAVER_NEWS_GLOBAL_STOCK_QUERIES,
    NAVER_NEWS_LIMIT_PER_REGION,
    NAVER_NEWS_MAX_AGE_HOURS,
    NEWS_BRIEFING_ENABLED,
    NEWS_BRIEFING_TIME,
    NEWS_BRIEFING_TRADING_DAYS_ONLY,
    NEWS_PROVIDER_KIND,
    NEWS_TARGET_FORUM_ID,
    WATCH_ALERT_CHANNEL_ID,
    WATCH_POLL_ENABLED,
    WATCH_POLL_INTERVAL_SECONDS,
)
from bot.common.clock import date_key, now_kst, timestamp_text
from bot.features.eod.policy import build_body as build_eod_body
from bot.features.eod.policy import build_post_title as build_eod_title
from bot.features.news.policy import build_region_body as build_news_region_body
from bot.features.news.policy import build_post_title as build_news_title
from bot.features.news.trend_policy import (
    build_trend_post_title,
    build_trend_region_messages,
    build_trend_starter_body,
)
from bot.forum.repository import (
    get_daily_posts_for_guild,
    get_guild_eod_forum_channel_id,
    get_guild_forum_channel_id,
    get_guild_last_auto_run_date,
    get_guild_last_auto_skip_date,
    get_guild_news_forum_channel_id,
    get_guild_watch_alert_channel_id,
    get_watch_baseline,
    list_guild_ids,
    list_watch_symbols,
    load_state,
    save_state,
    set_guild_last_auto_skip,
    set_guild_last_auto_run_date,
    set_job_last_run,
    set_provider_status,
    set_watch_baseline,
)
from bot.forum.service import upsert_daily_post
from bot.intel.instrument_registry import format_watch_symbol
from bot.intel.providers.market import (
    ErrorMarketDataProvider,
    KisMarketDataProvider,
    MassiveSnapshotMarketDataProvider,
    MockEodSummaryProvider,
    MockMarketDataProvider,
    RoutedMarketDataProvider,
)
from bot.intel.providers.news import (
    ErrorNewsProvider,
    HybridNewsProvider,
    MarketauxNewsProvider,
    MockNewsProvider,
    NaverNewsProvider,
    NewsAnalysis,
    NewsItem,
    NewsProvider,
    TrendThemeReport,
)
from bot.markets.trading_calendar import safe_check_krx_trading_day

logger = logging.getLogger(__name__)
NEWS_BRIEFING_COMMAND_KEY = "newsbriefing"
NEWS_BRIEFING_DOMESTIC_COMMAND_KEY = "newsbriefing-domestic"
NEWS_BRIEFING_GLOBAL_COMMAND_KEY = "newsbriefing-global"
TREND_BRIEFING_COMMAND_KEY = "trendbriefing"


def _build_news_provider() -> NewsProvider:
    if NEWS_PROVIDER_KIND == "mock":
        return MockNewsProvider()
    if NEWS_PROVIDER_KIND == "naver":
        if not NAVER_NEWS_CLIENT_ID or not NAVER_NEWS_CLIENT_SECRET:
            return ErrorNewsProvider("naver-news-credentials-missing")
        return NaverNewsProvider(
            client_id=NAVER_NEWS_CLIENT_ID,
            client_secret=NAVER_NEWS_CLIENT_SECRET,
            domestic_query=NAVER_NEWS_DOMESTIC_QUERIES,
            global_query=NAVER_NEWS_GLOBAL_QUERIES,
            domestic_stock_query=NAVER_NEWS_DOMESTIC_STOCK_QUERIES,
            global_stock_query=NAVER_NEWS_GLOBAL_STOCK_QUERIES,
            limit_per_region=NAVER_NEWS_LIMIT_PER_REGION,
            max_age_hours=NAVER_NEWS_MAX_AGE_HOURS,
            timeout_seconds=INTEL_API_TIMEOUT_SECONDS,
            retry_count=INTEL_API_RETRY_COUNT,
        )
    if NEWS_PROVIDER_KIND == "marketaux":
        if not MARKETAUX_API_TOKEN:
            return ErrorNewsProvider("marketaux-api-token-missing")
        return MarketauxNewsProvider(
            api_token=MARKETAUX_API_TOKEN,
            global_query=MARKETAUX_NEWS_GLOBAL_QUERIES,
            countries=MARKETAUX_NEWS_COUNTRIES,
            language=MARKETAUX_NEWS_LANGUAGE,
            limit_per_region=NAVER_NEWS_LIMIT_PER_REGION,
            max_age_hours=NAVER_NEWS_MAX_AGE_HOURS,
            timeout_seconds=INTEL_API_TIMEOUT_SECONDS,
            retry_count=INTEL_API_RETRY_COUNT,
        )
    if NEWS_PROVIDER_KIND == "hybrid":
        if not NAVER_NEWS_CLIENT_ID or not NAVER_NEWS_CLIENT_SECRET:
            return ErrorNewsProvider("naver-news-credentials-missing")
        if not MARKETAUX_API_TOKEN:
            return ErrorNewsProvider("marketaux-api-token-missing")
        domestic_provider = NaverNewsProvider(
            client_id=NAVER_NEWS_CLIENT_ID,
            client_secret=NAVER_NEWS_CLIENT_SECRET,
            domestic_query=NAVER_NEWS_DOMESTIC_QUERIES,
            global_query=[],
            domestic_stock_query=NAVER_NEWS_DOMESTIC_STOCK_QUERIES,
            global_stock_query=[],
            limit_per_region=NAVER_NEWS_LIMIT_PER_REGION,
            max_age_hours=NAVER_NEWS_MAX_AGE_HOURS,
            timeout_seconds=INTEL_API_TIMEOUT_SECONDS,
            retry_count=INTEL_API_RETRY_COUNT,
        )
        global_provider = MarketauxNewsProvider(
            api_token=MARKETAUX_API_TOKEN,
            global_query=MARKETAUX_NEWS_GLOBAL_QUERIES,
            countries=MARKETAUX_NEWS_COUNTRIES,
            language=MARKETAUX_NEWS_LANGUAGE,
            limit_per_region=NAVER_NEWS_LIMIT_PER_REGION,
            max_age_hours=NAVER_NEWS_MAX_AGE_HOURS,
            timeout_seconds=INTEL_API_TIMEOUT_SECONDS,
            retry_count=INTEL_API_RETRY_COUNT,
        )
        return HybridNewsProvider(domestic_provider=domestic_provider, global_provider=global_provider)
    return ErrorNewsProvider(f"unsupported-news-provider:{NEWS_PROVIDER_KIND}")


def _build_market_data_provider():
    if MARKET_DATA_PROVIDER_KIND == "mock":
        return MockMarketDataProvider()
    if MARKET_DATA_PROVIDER_KIND == "kis":
        if not KIS_APP_KEY or not KIS_APP_SECRET:
            return ErrorMarketDataProvider("kis-credentials-missing", provider_key="kis_quote")
        primary_provider = KisMarketDataProvider(
            app_key=KIS_APP_KEY,
            app_secret=KIS_APP_SECRET,
            timeout_seconds=INTEL_API_TIMEOUT_SECONDS,
            retry_count=INTEL_API_RETRY_COUNT,
        )
        us_fallback_provider = None
        if MASSIVE_API_KEY:
            us_fallback_provider = MassiveSnapshotMarketDataProvider(
                api_key=MASSIVE_API_KEY,
                timeout_seconds=INTEL_API_TIMEOUT_SECONDS,
                retry_count=INTEL_API_RETRY_COUNT,
            )
        return RoutedMarketDataProvider(
            primary_provider=primary_provider,
            us_fallback_provider=us_fallback_provider,
        )
    return ErrorMarketDataProvider(
        f"unsupported-market-data-provider:{MARKET_DATA_PROVIDER_KIND}",
        provider_key="kis_quote",
    )


news_provider = _build_news_provider()
eod_provider = MockEodSummaryProvider()
quote_provider = _build_market_data_provider()


def _parse_time(text: str, default_h: int, default_m: int) -> tuple[int, int]:
    try:
        h, m = text.split(":", maxsplit=1)
        return int(h), int(m)
    except Exception:
        return default_h, default_m


def _has_news_post_for_date(state: dict, command_key: str, guild_id: int, run_date: str) -> bool:
    return run_date in get_daily_posts_for_guild(state, command_key, guild_id)


def _is_trend_complete_for_date(state: dict, guild_id: int, run_date: str) -> bool:
    return _has_news_post_for_date(state, TREND_BRIEFING_COMMAND_KEY, guild_id, run_date) or (
        get_guild_last_auto_skip_date(state, guild_id, TREND_BRIEFING_COMMAND_KEY) == run_date
    )


def _migrate_legacy_news_post_if_needed(state: dict, guild_id: int, run_date: str) -> None:
    legacy_posts = get_daily_posts_for_guild(state, NEWS_BRIEFING_COMMAND_KEY, guild_id)
    if run_date not in legacy_posts:
        return
    domestic_posts = get_daily_posts_for_guild(state, NEWS_BRIEFING_DOMESTIC_COMMAND_KEY, guild_id)
    if run_date not in domestic_posts:
        domestic_posts[run_date] = legacy_posts[run_date]


async def _resolve_guild_forum_channel_id(
    client: discord.Client,
    guild_id: int,
    forum_channel_id: int,
) -> int | None:
    get_channel = getattr(client, "get_channel", None)
    fetch_channel = getattr(client, "fetch_channel", None)
    channel = get_channel(forum_channel_id) if callable(get_channel) else None
    if channel is None and callable(fetch_channel):
        try:
            channel = await fetch_channel(forum_channel_id)
        except discord.NotFound:
            return None
    if channel is None:
        return forum_channel_id
    channel_guild = getattr(channel, "guild", None)
    if not isinstance(channel, discord.ForumChannel) or getattr(channel_guild, "id", None) != guild_id:
        return None
    return forum_channel_id


async def _run_news_job(client: discord.Client, now: datetime) -> None:
    state = load_state()
    run_date = date_key(now)
    pending_guilds: list[tuple[int, int]] = []
    unresolved_pending_guilds: list[tuple[int, int]] = []
    completed_guilds = 0
    missing_forum = 0
    resolution_failures = 0

    for guild_id in list_guild_ids(state):
        _migrate_legacy_news_post_if_needed(state, guild_id, run_date)
        if (
            get_guild_last_auto_run_date(state, guild_id, NEWS_BRIEFING_COMMAND_KEY) == run_date
            and _has_news_post_for_date(state, NEWS_BRIEFING_DOMESTIC_COMMAND_KEY, guild_id, run_date)
            and _has_news_post_for_date(state, NEWS_BRIEFING_GLOBAL_COMMAND_KEY, guild_id, run_date)
            and _is_trend_complete_for_date(state, guild_id, run_date)
        ):
            completed_guilds += 1
            continue
        forum_channel_id = (
            get_guild_news_forum_channel_id(state, guild_id)
            or NEWS_TARGET_FORUM_ID
            or get_guild_forum_channel_id(state, guild_id)
        )
        if forum_channel_id is None:
            missing_forum += 1
            continue
        unresolved_pending_guilds.append((guild_id, forum_channel_id))

    if not unresolved_pending_guilds:
        if resolution_failures > 0:
            detail = f"forum-resolution-failed count={resolution_failures} missing_forum={missing_forum}"
            set_job_last_run(state, "news_briefing", "failed", detail)
            set_job_last_run(state, "trend_briefing", "failed", detail)
            save_state(state)
            return
        if missing_forum > 0 and completed_guilds == 0:
            set_job_last_run(state, "news_briefing", "skipped", f"no-target-forums missing_forum={missing_forum}")
            set_job_last_run(state, "trend_briefing", "skipped", f"no-target-forums missing_forum={missing_forum}")
            save_state(state)
        return

    if NEWS_BRIEFING_TRADING_DAYS_ONLY:
        is_trading_day, err = safe_check_krx_trading_day(now)
        if is_trading_day is not True:
            reason = "holiday" if is_trading_day is False else f"calendar-failed:{err}"
            set_job_last_run(state, "news_briefing", "skipped", reason)
            set_job_last_run(state, "trend_briefing", "skipped", reason)
            save_state(state)
            return

    for guild_id, forum_channel_id in unresolved_pending_guilds:
        try:
            resolved_forum_channel_id = await _resolve_guild_forum_channel_id(client, guild_id, forum_channel_id)
        except Exception as exc:
            resolution_failures += 1
            logger.exception("[intel] news forum resolution failed guild=%s: %s", guild_id, exc)
            continue
        if resolved_forum_channel_id is None:
            missing_forum += 1
            continue
        pending_guilds.append((guild_id, resolved_forum_channel_id))

    if not pending_guilds:
        if resolution_failures > 0:
            detail = f"forum-resolution-failed count={resolution_failures} missing_forum={missing_forum}"
            set_job_last_run(state, "news_briefing", "failed", detail)
            set_job_last_run(state, "trend_briefing", "failed", detail)
            save_state(state)
            return
        if missing_forum > 0 and completed_guilds == 0:
            set_job_last_run(state, "news_briefing", "skipped", f"no-target-forums missing_forum={missing_forum}")
            set_job_last_run(state, "trend_briefing", "skipped", f"no-target-forums missing_forum={missing_forum}")
            save_state(state)
        return

    try:
        analysis = await _analyze_news_provider(news_provider, now)
        items = list(analysis.briefing_items)
        set_provider_status(state, "news_provider", True, f"fetched={len(items)}")
        if NEWS_PROVIDER_KIND in {"naver", "hybrid"}:
            set_provider_status(state, "naver_news", True, f"fetched={len([item for item in items if item.region == 'domestic'])}")
        if NEWS_PROVIDER_KIND in {"marketaux", "hybrid"}:
            set_provider_status(state, "marketaux_news", True, f"fetched={len([item for item in items if item.region == 'global'])}")
    except Exception as exc:
        set_provider_status(state, "news_provider", False, str(exc))
        if "naver" in str(exc):
            set_provider_status(state, "naver_news", False, str(exc))
        if "marketaux" in str(exc):
            set_provider_status(state, "marketaux_news", False, str(exc))
        set_job_last_run(state, "news_briefing", "failed", str(exc))
        set_job_last_run(state, "trend_briefing", "failed", str(exc))
        save_state(state)
        logger.exception("[intel] news fetch failed: %s", exc)
        return

    deduped: list[NewsItem] = []
    seen_keys: set[str] = set()
    for item in items:
        key = item.story_key()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(item)

    domestic = [x for x in deduped if x.region == "domestic"][:NAVER_NEWS_LIMIT_PER_REGION]
    global_items = [x for x in deduped if x.region == "global"][:NAVER_NEWS_LIMIT_PER_REGION]
    domestic_body = build_news_region_body(timestamp_text(now), "domestic", domestic)
    global_body = build_news_region_body(timestamp_text(now), "global", global_items)
    trend_domestic = analysis.trend_report.for_region("domestic")
    trend_global = analysis.trend_report.for_region("global")
    trend_domestic_display = trend_domestic if len(trend_domestic) >= 3 else ()
    trend_global_display = trend_global if len(trend_global) >= 3 else ()
    trend_can_post = bool(trend_domestic_display or trend_global_display)
    trend_skip_reason = f"insufficient-themes domestic={len(trend_domestic)} global={len(trend_global)}"
    trend_display_report = TrendThemeReport(
        generated_at=analysis.trend_report.generated_at,
        themes_by_region={"domestic": trend_domestic_display, "global": trend_global_display},
    )
    trend_starter = build_trend_starter_body(timestamp_text(now), trend_display_report)
    trend_content_texts = [
        *build_trend_region_messages("domestic", trend_domestic_display),
        *build_trend_region_messages("global", trend_global_display),
    ]
    posted = 0
    failed = 0
    trend_posted = 0
    trend_failed = 0
    trend_skipped = 0

    for guild_id, forum_channel_id in pending_guilds:
        guild_failed = 0
        try:
            await upsert_daily_post(
                client=client,
                state=state,
                guild_id=guild_id,
                forum_channel_id=forum_channel_id,
                command_key=NEWS_BRIEFING_DOMESTIC_COMMAND_KEY,
                post_title=build_news_title("domestic", now),
                body_text=domestic_body,
                image_paths=[],
            )
            await upsert_daily_post(
                client=client,
                state=state,
                guild_id=guild_id,
                forum_channel_id=forum_channel_id,
                command_key=NEWS_BRIEFING_GLOBAL_COMMAND_KEY,
                post_title=build_news_title("global", now),
                body_text=global_body,
                image_paths=[],
            )
            set_guild_last_auto_run_date(state, guild_id, NEWS_BRIEFING_COMMAND_KEY, run_date)
            posted += 1
            if trend_can_post:
                try:
                    await upsert_daily_post(
                        client=client,
                        state=state,
                        guild_id=guild_id,
                        forum_channel_id=forum_channel_id,
                        command_key=TREND_BRIEFING_COMMAND_KEY,
                        post_title=build_trend_post_title(now),
                        body_text=trend_starter,
                        image_paths=[],
                        content_texts=trend_content_texts,
                    )
                    set_guild_last_auto_run_date(state, guild_id, TREND_BRIEFING_COMMAND_KEY, run_date)
                    trend_posted += 1
                except Exception as exc:
                    trend_failed += 1
                    logger.exception("[intel] trend post failed guild=%s: %s", guild_id, exc)
            else:
                set_guild_last_auto_skip(state, guild_id, TREND_BRIEFING_COMMAND_KEY, run_date, trend_skip_reason)
                trend_skipped += 1
        except Exception as exc:
            guild_failed += 1
            failed += 1
            logger.exception("[intel] news post failed guild=%s: %s", guild_id, exc)
        if guild_failed > 0:
            continue

    total_failures = failed + resolution_failures
    news_status = "ok" if posted > 0 and total_failures == 0 else "failed"
    set_job_last_run(
        state,
        "news_briefing",
        news_status,
        (
            f"posted={posted} failed={total_failures} missing_forum={missing_forum} "
            f"forum_resolution_failures={resolution_failures} domestic={len(domestic)} global={len(global_items)}"
        ),
    )
    if trend_can_post:
        trend_total_failures = trend_failed + resolution_failures
        trend_status = "ok" if trend_posted > 0 and trend_total_failures == 0 else "failed"
        set_job_last_run(
            state,
            "trend_briefing",
            trend_status,
            (
                f"posted={trend_posted} failed={trend_total_failures} missing_forum={missing_forum} "
                f"forum_resolution_failures={resolution_failures} "
                f"domestic_themes={len(trend_domestic)} global_themes={len(trend_global)}"
            ),
        )
    else:
        set_job_last_run(state, "trend_briefing", "skipped", trend_skip_reason)
    save_state(state)


async def _analyze_news_provider(provider: NewsProvider, now: datetime) -> NewsAnalysis:
    analyze = getattr(provider, "analyze", None)
    if callable(analyze):
        return await analyze(now)
    items = await provider.fetch(now)
    return NewsAnalysis(
        briefing_items=tuple(items),
        trend_report=TrendThemeReport(
            generated_at=now,
            themes_by_region={"domestic": (), "global": ()},
        ),
    )


async def _run_eod_job(client: discord.Client, now: datetime) -> None:
    state = load_state()
    run_date = date_key(now)
    pending_guilds: list[tuple[int, int]] = []
    unresolved_pending_guilds: list[tuple[int, int]] = []
    completed_guilds = 0
    missing_forum = 0
    resolution_failures = 0

    for guild_id in list_guild_ids(state):
        if get_guild_last_auto_run_date(state, guild_id, "eodsummary") == run_date:
            completed_guilds += 1
            continue
        forum_channel_id = (
            get_guild_eod_forum_channel_id(state, guild_id)
            or EOD_TARGET_FORUM_ID
            or get_guild_forum_channel_id(state, guild_id)
        )
        if forum_channel_id is None:
            missing_forum += 1
            continue
        unresolved_pending_guilds.append((guild_id, forum_channel_id))

    if not unresolved_pending_guilds:
        if resolution_failures > 0:
            set_job_last_run(
                state,
                "eod_summary",
                "failed",
                f"forum-resolution-failed count={resolution_failures} missing_forum={missing_forum}",
            )
            save_state(state)
            return
        if missing_forum > 0 and completed_guilds == 0:
            set_job_last_run(state, "eod_summary", "skipped", f"no-target-forums missing_forum={missing_forum}")
            save_state(state)
        return

    is_trading_day, err = safe_check_krx_trading_day(now)
    if is_trading_day is not True:
        reason = "holiday" if is_trading_day is False else f"calendar-failed:{err}"
        set_job_last_run(state, "eod_summary", "skipped", reason)
        save_state(state)
        return

    for guild_id, forum_channel_id in unresolved_pending_guilds:
        try:
            resolved_forum_channel_id = await _resolve_guild_forum_channel_id(client, guild_id, forum_channel_id)
        except Exception as exc:
            resolution_failures += 1
            logger.exception("[intel] eod forum resolution failed guild=%s: %s", guild_id, exc)
            continue
        if resolved_forum_channel_id is None:
            missing_forum += 1
            continue
        pending_guilds.append((guild_id, resolved_forum_channel_id))

    if not pending_guilds:
        if resolution_failures > 0:
            set_job_last_run(
                state,
                "eod_summary",
                "failed",
                f"forum-resolution-failed count={resolution_failures} missing_forum={missing_forum}",
            )
            save_state(state)
            return
        if missing_forum > 0 and completed_guilds == 0:
            set_job_last_run(state, "eod_summary", "skipped", f"no-target-forums missing_forum={missing_forum}")
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

    total_failures = failed + resolution_failures
    status = "ok" if posted > 0 and total_failures == 0 else "failed"
    set_job_last_run(
        state,
        "eod_summary",
        status,
        (
            f"posted={posted} failed={total_failures} missing_forum={missing_forum} "
            f"forum_resolution_failures={resolution_failures} date={summary.date_text}"
        ),
    )
    save_state(state)


async def _run_watch_poll(client: discord.Client, now: datetime) -> None:
    state = load_state()
    sent = 0
    alert_attempts = 0
    processed = 0
    quote_failures = 0
    channel_failures = 0
    missing_channel_guilds = 0
    send_failures = 0
    watched_symbols = 0
    pending_guilds: list[tuple[int, discord.abc.Messageable, list[str]]] = []
    warm_symbols: set[str] = set()

    for guild_id in list_guild_ids(state):
        symbols = list_watch_symbols(state, guild_id)
        if not symbols:
            continue
        watched_symbols += len(symbols)
        alert_channel_id = get_guild_watch_alert_channel_id(state, guild_id) or WATCH_ALERT_CHANNEL_ID
        if alert_channel_id is None:
            missing_channel_guilds += 1
            continue
        channel = client.get_channel(alert_channel_id)
        if channel is None:
            try:
                channel = await client.fetch_channel(alert_channel_id)
            except Exception:
                channel_failures += 1
                continue
        channel_guild = getattr(channel, "guild", None)
        if not isinstance(channel, discord.abc.Messageable) or getattr(channel_guild, "id", None) != guild_id:
            channel_failures += 1
            continue
        pending_guilds.append((guild_id, channel, symbols))
        warm_symbols.update(symbols)

    warm_quotes = getattr(quote_provider, "warm_quotes", None)
    if pending_guilds and callable(warm_quotes):
        try:
            await warm_quotes(sorted(warm_symbols), now)
        except Exception as exc:
            logger.exception("[intel] watch warm quotes failed: %s", exc)

    for guild_id, channel, symbols in pending_guilds:
        for symbol in symbols:
            try:
                quote = await quote_provider.get_quote(symbol, now)
                provider_key = getattr(quote, "provider", "") or "kis_quote"
                set_provider_status(state, provider_key, True, f"quote:{symbol}")
            except Exception as exc:
                provider_key = getattr(exc, "provider_key", "kis_quote")
                set_provider_status(state, provider_key, False, str(exc))
                quote_failures += 1
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
            processed += 1
            if should_send:
                alert_attempts += 1
                emoji = "📈" if direction == "up" else "📉"
                display_symbol = format_watch_symbol(symbol)
                try:
                    await channel.send(
                        f"{emoji} {display_symbol} 변동 알림: 기준가 {baseline:,.2f} → 현재가 {quote.price:,.2f} ({change_pct:+.2f}%)"
                    )
                    sent += 1
                except Exception:
                    send_failures += 1

    detail = (
        "alerts="
        f"{sent} alert_attempts={alert_attempts} processed={processed} watched_symbols={watched_symbols} "
        f"quote_failures={quote_failures} channel_failures={channel_failures} "
        f"missing_channel_guilds={missing_channel_guilds} send_failures={send_failures}"
    )
    if watched_symbols == 0:
        set_job_last_run(state, "watch_poll", "skipped", "no-watch-symbols")
    elif quote_failures > 0 or channel_failures > 0 or send_failures > 0:
        set_job_last_run(state, "watch_poll", "failed", detail)
    elif processed > 0:
        set_job_last_run(state, "watch_poll", "ok", detail)
    else:
        set_job_last_run(state, "watch_poll", "skipped", f"no-target-channels {detail}")
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
