import asyncio
import logging
from datetime import datetime

import discord

from bot.app.settings import (
    DART_API_KEY,
    EOD_SUMMARY_ENABLED,
    EOD_SUMMARY_TIME,
    INSTRUMENT_REGISTRY_REFRESH_ENABLED,
    INSTRUMENT_REGISTRY_REFRESH_TIME,
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
from bot.features.watch.service import (
    calculate_change_pct,
    evaluate_band_event,
    render_band_comment,
    render_close_comment,
    render_watch_starter,
)
from bot.features.watch.session import get_watch_market_session
from bot.features.watch.thread_service import upsert_watch_thread
from bot.forum.repository import (
    get_daily_posts_for_guild,
    get_guild_eod_forum_channel_id,
    get_guild_forum_channel_id,
    get_guild_last_auto_run_date,
    get_guild_last_auto_skip_date,
    get_guild_news_forum_channel_id,
    get_guild_watch_forum_channel_id,
    get_job_last_runs,
    get_watch_reference_snapshot,
    get_watch_session_alert,
    list_guild_ids,
    list_watch_tracked_symbols,
    list_watch_symbols,
    load_state,
    save_state,
    set_guild_last_auto_skip,
    set_guild_last_auto_run_date,
    set_job_last_run,
    set_provider_status,
    set_watch_reference_snapshot,
    update_watch_session_alert,
)
from bot.forum.service import upsert_daily_post
from bot.intel.instrument_registry import (
    RUNTIME_REGISTRY_FILE,
    build_live_registry,
    load_registry,
    registry_status,
    save_registry,
)
from bot.intel.providers.market import (
    ErrorMarketDataProvider,
    KisMarketDataProvider,
    MassiveSnapshotMarketDataProvider,
    MockEodSummaryProvider,
    MockMarketDataProvider,
    RoutedMarketDataProvider,
    WatchSnapshot,
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


def _log_job_result(job_key: str, status: str, detail: str) -> None:
    if status == "failed":
        logger.warning("[intel] %s status=%s detail=%s", job_key, status, detail)
        return
    logger.info("[intel] %s status=%s detail=%s", job_key, status, detail)


def _job_status_on_date(state: dict, job_key: str, run_date: str) -> str | None:
    run = get_job_last_runs(state).get(job_key, {})
    if not str(run.get("run_at") or "").startswith(run_date):
        return None
    status = run.get("status")
    return str(status) if isinstance(status, str) else None


def _job_attempted_in_minute(state: dict, job_key: str, now: datetime) -> bool:
    run = get_job_last_runs(state).get(job_key, {})
    run_at = str(run.get("run_at") or "")
    return run_at.startswith(now.strftime("%Y-%m-%dT%H:%M"))


def _job_detail_on_date(state: dict, job_key: str, run_date: str) -> str:
    run = get_job_last_runs(state).get(job_key, {})
    if not str(run.get("run_at") or "").startswith(run_date):
        return ""
    detail = run.get("detail")
    return str(detail) if isinstance(detail, str) else ""


def _should_start_instrument_registry_refresh(
    state: dict,
    now: datetime,
    *,
    refresh_hour: int,
    refresh_minute: int,
) -> bool:
    run_date = date_key(now)
    if now.hour < refresh_hour or (now.hour == refresh_hour and now.minute < refresh_minute):
        return False

    status = _job_status_on_date(state, "instrument_registry_refresh", run_date)
    if status == "ok":
        return False
    if status is None:
        return True
    if _job_attempted_in_minute(state, "instrument_registry_refresh", now):
        return False
    detail = _job_detail_on_date(state, "instrument_registry_refresh", run_date)
    if "dart-api-key-missing" in detail:
        return False
    return True


def _refresh_instrument_registry_sync() -> dict[str, int | str]:
    previous_registry = load_registry()
    previous_symbols = {record.canonical_symbol for record in previous_registry.records}
    refreshed_registry = build_live_registry(dart_api_key=DART_API_KEY)
    refreshed_symbols = {record.canonical_symbol for record in refreshed_registry.records}
    save_registry(refreshed_registry, path=RUNTIME_REGISTRY_FILE)
    return {
        "source": "runtime",
        "loaded": len(refreshed_registry.records),
        "added": len(refreshed_symbols - previous_symbols),
        "removed": len(previous_symbols - refreshed_symbols),
    }


def _format_instrument_registry_refresh_detail(summary: dict[str, int | str]) -> str:
    return (
        f"source={summary['source']} loaded={summary['loaded']} "
        f"added={summary['added']} removed={summary['removed']}"
    )


def _record_instrument_registry_refresh_result(*, ok: bool, detail: str) -> None:
    state = load_state()
    status = "ok" if ok else "failed"
    set_job_last_run(state, "instrument_registry_refresh", status, detail)
    set_provider_status(state, "instrument_registry", ok, detail)
    save_state(state)
    _log_job_result("instrument_registry_refresh", status, detail)


async def _refresh_instrument_registry() -> dict[str, int | str]:
    return await asyncio.to_thread(_refresh_instrument_registry_sync)


async def _run_instrument_registry_refresh(now: datetime) -> None:
    try:
        summary = await _refresh_instrument_registry()
    except Exception as exc:
        active = registry_status()
        detail = f"{exc} active={active['message']}"
        _record_instrument_registry_refresh_result(ok=False, detail=detail)
        logger.exception("[intel] instrument registry refresh failed: %s", exc)
        return

    _record_instrument_registry_refresh_result(
        ok=True,
        detail=_format_instrument_registry_refresh_detail(summary),
    )


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
        forum_channel_id = get_guild_news_forum_channel_id(state, guild_id)
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
            _log_job_result("news_briefing", "failed", detail)
            _log_job_result("trend_briefing", "failed", detail)
            return
        if missing_forum > 0 and completed_guilds == 0:
            detail = f"no-target-forums missing_forum={missing_forum}"
            set_job_last_run(state, "news_briefing", "skipped", detail)
            set_job_last_run(state, "trend_briefing", "skipped", detail)
            save_state(state)
            _log_job_result("news_briefing", "skipped", detail)
            _log_job_result("trend_briefing", "skipped", detail)
        return

    if NEWS_BRIEFING_TRADING_DAYS_ONLY:
        is_trading_day, err = safe_check_krx_trading_day(now)
        if is_trading_day is not True:
            reason = "holiday" if is_trading_day is False else f"calendar-failed:{err}"
            set_job_last_run(state, "news_briefing", "skipped", reason)
            set_job_last_run(state, "trend_briefing", "skipped", reason)
            save_state(state)
            _log_job_result("news_briefing", "skipped", reason)
            _log_job_result("trend_briefing", "skipped", reason)
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
            _log_job_result("news_briefing", "failed", detail)
            _log_job_result("trend_briefing", "failed", detail)
            return
        if missing_forum > 0 and completed_guilds == 0:
            detail = f"no-target-forums missing_forum={missing_forum}"
            set_job_last_run(state, "news_briefing", "skipped", detail)
            set_job_last_run(state, "trend_briefing", "skipped", detail)
            save_state(state)
            _log_job_result("news_briefing", "skipped", detail)
            _log_job_result("trend_briefing", "skipped", detail)
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
        _log_job_result("news_briefing", "failed", str(exc))
        _log_job_result("trend_briefing", "failed", str(exc))
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
    news_detail = (
        f"posted={posted} failed={total_failures} missing_forum={missing_forum} "
        f"forum_resolution_failures={resolution_failures} domestic={len(domestic)} global={len(global_items)}"
    )
    set_job_last_run(
        state,
        "news_briefing",
        news_status,
        news_detail,
    )
    if trend_can_post:
        trend_total_failures = trend_failed + resolution_failures
        trend_status = "ok" if trend_posted > 0 and trend_total_failures == 0 else "failed"
        trend_detail = (
            f"posted={trend_posted} failed={trend_total_failures} missing_forum={missing_forum} "
            f"forum_resolution_failures={resolution_failures} "
            f"domestic_themes={len(trend_domestic)} global_themes={len(trend_global)}"
        )
        set_job_last_run(
            state,
            "trend_briefing",
            trend_status,
            trend_detail,
        )
    else:
        set_job_last_run(state, "trend_briefing", "skipped", trend_skip_reason)
    save_state(state)
    _log_job_result("news_briefing", news_status, news_detail)
    if trend_can_post:
        _log_job_result("trend_briefing", trend_status, trend_detail)
    else:
        _log_job_result("trend_briefing", "skipped", trend_skip_reason)


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
            or get_guild_forum_channel_id(state, guild_id)
        )
        if forum_channel_id is None:
            missing_forum += 1
            continue
        unresolved_pending_guilds.append((guild_id, forum_channel_id))

    if not unresolved_pending_guilds:
        if resolution_failures > 0:
            detail = f"forum-resolution-failed count={resolution_failures} missing_forum={missing_forum}"
            set_job_last_run(state, "eod_summary", "failed", detail)
            save_state(state)
            _log_job_result("eod_summary", "failed", detail)
            return
        if missing_forum > 0 and completed_guilds == 0:
            detail = f"no-target-forums missing_forum={missing_forum}"
            set_job_last_run(state, "eod_summary", "skipped", detail)
            save_state(state)
            _log_job_result("eod_summary", "skipped", detail)
        return

    is_trading_day, err = safe_check_krx_trading_day(now)
    if is_trading_day is not True:
        reason = "holiday" if is_trading_day is False else f"calendar-failed:{err}"
        set_job_last_run(state, "eod_summary", "skipped", reason)
        save_state(state)
        _log_job_result("eod_summary", "skipped", reason)
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
            detail = f"forum-resolution-failed count={resolution_failures} missing_forum={missing_forum}"
            set_job_last_run(state, "eod_summary", "failed", detail)
            save_state(state)
            _log_job_result("eod_summary", "failed", detail)
            return
        if missing_forum > 0 and completed_guilds == 0:
            detail = f"no-target-forums missing_forum={missing_forum}"
            set_job_last_run(state, "eod_summary", "skipped", detail)
            save_state(state)
            _log_job_result("eod_summary", "skipped", detail)
        return

    try:
        summary = await eod_provider.get_summary(now)
        set_provider_status(state, "eod_provider", True, "summary-ready")
    except Exception as exc:
        set_provider_status(state, "eod_provider", False, str(exc))
        set_job_last_run(state, "eod_summary", "failed", str(exc))
        save_state(state)
        _log_job_result("eod_summary", "failed", str(exc))
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
    detail = (
        f"posted={posted} failed={total_failures} missing_forum={missing_forum} "
        f"forum_resolution_failures={resolution_failures} date={summary.date_text}"
    )
    set_job_last_run(
        state,
        "eod_summary",
        status,
        detail,
    )
    save_state(state)
    _log_job_result("eod_summary", status, detail)


def _has_unfinalized_watch_session(alert_entry: dict[str, object]) -> bool:
    active_session_date = str(alert_entry.get("active_session_date") or "").strip()
    if not active_session_date:
        return False
    last_finalized_session_date = str(alert_entry.get("last_finalized_session_date") or "").strip()
    return active_session_date != last_finalized_session_date


def _watch_poll_target_symbols(state: dict, guild_id: int) -> tuple[list[str], list[str]]:
    active_symbols = list_watch_symbols(state, guild_id)
    tracked_symbols = list_watch_tracked_symbols(state, guild_id)
    active_set = set(active_symbols)
    targets = list(active_symbols)
    for symbol in tracked_symbols:
        if symbol in active_set:
            continue
        alert = get_watch_session_alert(state, guild_id, symbol)
        if _has_unfinalized_watch_session(alert):
            targets.append(symbol)
    return active_symbols, targets


def _resolve_watch_close_price(snapshot: WatchSnapshot, target_session_date: str) -> float | None:
    if snapshot.session_date == target_session_date and snapshot.session_close_price is not None:
        return snapshot.session_close_price
    if snapshot.session_date > target_session_date and snapshot.previous_close > 0:
        return snapshot.previous_close
    return None


async def _find_existing_close_comment(
    thread: discord.Thread,
    *,
    symbol: str,
    session_date: str,
) -> discord.Message | None:
    marker = f"[watch-close:{symbol}:{session_date}]"
    history = getattr(thread, "history", None)
    if not callable(history):
        return None
    try:
        async for message in history(limit=50):
            if marker in str(getattr(message, "content", "")):
                return message
    except Exception:
        return None
    return None


async def _finalize_watch_session(
    client: discord.Client,
    state: dict,
    *,
    now: datetime,
    guild_id: int,
    forum_channel_id: int,
    symbol: str,
    snapshot: WatchSnapshot,
    active: bool,
) -> bool:
    reference_snapshot = get_watch_reference_snapshot(state, guild_id, symbol)
    if reference_snapshot is None:
        return False
    reference_price = float(reference_snapshot.get("reference_price") or 0.0)
    target_session_date = str(reference_snapshot.get("session_date") or "")
    if reference_price <= 0 or not target_session_date:
        return False

    close_price = _resolve_watch_close_price(snapshot, target_session_date)
    if close_price is None:
        return False

    handle = await upsert_watch_thread(
        client=client,
        state=state,
        guild_id=guild_id,
        forum_channel_id=forum_channel_id,
        symbol=symbol,
        active=active,
        starter_text=None,
    )
    alert_entry = get_watch_session_alert(state, guild_id, symbol)
    intraday_comment_ids = [message_id for message_id in alert_entry.get("intraday_comment_ids", []) if isinstance(message_id, int)]
    remaining_intraday_comment_ids: list[int] = []

    for message_id in intraday_comment_ids:
        try:
            comment = await handle.thread.fetch_message(message_id)
            await comment.delete()
        except discord.NotFound:
            continue
        except (discord.Forbidden, discord.HTTPException):
            remaining_intraday_comment_ids.append(message_id)

    if remaining_intraday_comment_ids:
        update_watch_session_alert(
            state,
            guild_id,
            symbol,
            intraday_comment_ids=remaining_intraday_comment_ids,
            updated_at=now.isoformat(),
        )
        return False

    close_comment_ids_by_session = {
        str(date_text): int(message_id)
        for date_text, message_id in alert_entry.get("close_comment_ids_by_session", {}).items()
        if isinstance(date_text, str) and isinstance(message_id, int)
    }
    close_comment = None
    existing_close_comment_id = close_comment_ids_by_session.get(target_session_date)
    if isinstance(existing_close_comment_id, int):
        try:
            close_comment = await handle.thread.fetch_message(existing_close_comment_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            close_comment = None
    if close_comment is None:
        close_comment = await _find_existing_close_comment(handle.thread, symbol=symbol, session_date=target_session_date)

    close_text = render_close_comment(
        symbol,
        session_date=target_session_date,
        reference_price=reference_price,
        close_price=close_price,
    )
    if close_comment is None:
        close_comment = await handle.thread.send(close_text)
    else:
        await close_comment.edit(content=close_text)

    close_comment_ids_by_session[target_session_date] = close_comment.id
    update_watch_session_alert(
        state,
        guild_id,
        symbol,
        intraday_comment_ids=[],
        close_comment_ids_by_session=close_comment_ids_by_session,
        updated_at=now.isoformat(),
    )
    save_state(state)
    update_watch_session_alert(
        state,
        guild_id,
        symbol,
        last_finalized_session_date=target_session_date,
        updated_at=now.isoformat(),
    )
    save_state(state)
    return True


async def _run_watch_poll(client: discord.Client, now: datetime) -> None:
    state = load_state()
    active_symbols_count = 0
    updated_threads = 0
    finalized_sessions = 0
    missing_forum_guilds = 0
    thread_failures = 0
    snapshot_failures = 0
    comment_failures = 0
    total_target_symbols = 0
    pending_guilds: list[tuple[int, int, set[str], list[str]]] = []
    warm_symbols: set[str] = set()

    for guild_id in list_guild_ids(state):
        active_symbols, target_symbols = _watch_poll_target_symbols(state, guild_id)
        active_symbols_count += len(active_symbols)
        total_target_symbols += len(target_symbols)
        if not target_symbols:
            continue
        forum_channel_id = get_guild_watch_forum_channel_id(state, guild_id)
        if forum_channel_id is None:
            missing_forum_guilds += 1
            continue
        pending_guilds.append((guild_id, forum_channel_id, set(active_symbols), target_symbols))
        for symbol in target_symbols:
            market_session = get_watch_market_session(symbol, now)
            if market_session.is_regular_session_open or _has_unfinalized_watch_session(get_watch_session_alert(state, guild_id, symbol)):
                warm_symbols.add(symbol)

    warm_watch_snapshots = getattr(quote_provider, "warm_watch_snapshots", None)
    if warm_symbols and callable(warm_watch_snapshots):
        try:
            await warm_watch_snapshots(sorted(warm_symbols), now)
        except Exception as exc:
            logger.exception("[intel] watch warm snapshots failed: %s", exc)

    for guild_id, forum_channel_id, active_symbols, symbols in pending_guilds:
        for symbol in symbols:
            market_session = get_watch_market_session(symbol, now)
            alert_entry = get_watch_session_alert(state, guild_id, symbol)
            needs_finalization = _has_unfinalized_watch_session(alert_entry)
            if not market_session.is_regular_session_open and not needs_finalization:
                continue

            try:
                snapshot = await quote_provider.get_watch_snapshot(symbol, now)
                provider_key = getattr(snapshot, "provider", "") or "kis_quote"
                set_provider_status(state, provider_key, True, f"snapshot:{symbol}")
            except Exception as exc:
                provider_key = getattr(exc, "provider_key", "kis_quote")
                set_provider_status(state, provider_key, False, str(exc))
                snapshot_failures += 1
                continue

            if market_session.is_regular_session_open and symbol in active_symbols:
                try:
                    reference_snapshot = get_watch_reference_snapshot(state, guild_id, symbol)
                    active_session_date = str(alert_entry.get("active_session_date") or "")
                    reference_session_date = str(reference_snapshot.get("session_date") or "") if reference_snapshot is not None else ""
                    if needs_finalization and reference_session_date and reference_session_date < snapshot.session_date:
                        finalized = await _finalize_watch_session(
                            client,
                            state,
                            now=now,
                            guild_id=guild_id,
                            forum_channel_id=forum_channel_id,
                            symbol=symbol,
                            snapshot=snapshot,
                            active=True,
                        )
                        if not finalized:
                            comment_failures += 1
                            logger.warning(
                                "[intel] watch carry-forward finalization not completed guild=%s symbol=%s target_session=%s new_session=%s",
                                guild_id,
                                symbol,
                                reference_session_date,
                                snapshot.session_date,
                            )
                            continue
                        finalized_sessions += 1
                        alert_entry = get_watch_session_alert(state, guild_id, symbol)
                        reference_snapshot = get_watch_reference_snapshot(state, guild_id, symbol)
                        active_session_date = str(alert_entry.get("active_session_date") or "")
                    if (
                        reference_snapshot is None
                        or str(reference_snapshot.get("session_date") or "") != snapshot.session_date
                        or active_session_date != snapshot.session_date
                    ):
                        set_watch_reference_snapshot(
                            state,
                            guild_id,
                            symbol,
                            basis="previous_close",
                            reference_price=snapshot.previous_close,
                            session_date=snapshot.session_date,
                            checked_at=now.isoformat(),
                        )
                        update_watch_session_alert(
                            state,
                            guild_id,
                            symbol,
                            active_session_date=snapshot.session_date,
                            highest_up_band=0,
                            highest_down_band=0,
                            intraday_comment_ids=[],
                            updated_at=now.isoformat(),
                        )
                    else:
                        set_watch_reference_snapshot(
                            state,
                            guild_id,
                            symbol,
                            basis="previous_close",
                            reference_price=snapshot.previous_close,
                            session_date=snapshot.session_date,
                            checked_at=now.isoformat(),
                        )

                    alert_entry = get_watch_session_alert(state, guild_id, symbol)
                    current_highest_up_band = int(alert_entry.get("highest_up_band") or 0)
                    current_highest_down_band = int(alert_entry.get("highest_down_band") or 0)
                    change_pct = calculate_change_pct(snapshot.previous_close, snapshot.current_price)
                    event = evaluate_band_event(
                        highest_up_band=current_highest_up_band,
                        highest_down_band=current_highest_down_band,
                        change_pct=change_pct,
                    )
                    highest_up_band = current_highest_up_band
                    highest_down_band = current_highest_down_band
                    if event is not None:
                        if event.direction == "up":
                            highest_up_band = event.band
                        else:
                            highest_down_band = event.band

                    starter_text = render_watch_starter(
                        symbol,
                        reference_price=snapshot.previous_close,
                        current_price=snapshot.current_price,
                        change_pct=change_pct,
                        updated_at=snapshot.asof,
                    )
                    handle = await upsert_watch_thread(
                        client=client,
                        state=state,
                        guild_id=guild_id,
                        forum_channel_id=forum_channel_id,
                        symbol=symbol,
                        active=True,
                        starter_text=starter_text,
                    )
                    updated_threads += 1
                except Exception as exc:
                    logger.exception("[intel] watch thread update failed guild=%s symbol=%s: %s", guild_id, symbol, exc)
                    thread_failures += 1
                    continue

                try:
                    intraday_comment_ids = [
                        message_id
                        for message_id in alert_entry.get("intraday_comment_ids", [])
                        if isinstance(message_id, int)
                    ]
                    if event is not None:
                        comment = await handle.thread.send(
                            render_band_comment(
                                symbol,
                                direction=event.direction,
                                band=event.band,
                                change_pct=event.change_pct,
                                updated_at=snapshot.asof,
                            )
                        )
                        intraday_comment_ids.append(comment.id)
                    update_watch_session_alert(
                        state,
                        guild_id,
                        symbol,
                        highest_up_band=highest_up_band,
                        highest_down_band=highest_down_band,
                        intraday_comment_ids=intraday_comment_ids,
                        updated_at=now.isoformat(),
                    )
                    save_state(state)
                except Exception as exc:
                    logger.exception("[intel] watch comment/state update failed guild=%s symbol=%s: %s", guild_id, symbol, exc)
                    comment_failures += 1
                continue

            if needs_finalization:
                try:
                    finalized = await _finalize_watch_session(
                        client,
                        state,
                        now=now,
                        guild_id=guild_id,
                        forum_channel_id=forum_channel_id,
                        symbol=symbol,
                        snapshot=snapshot,
                        active=symbol in active_symbols,
                    )
                except Exception as exc:
                    logger.exception("[intel] watch finalization failed guild=%s symbol=%s: %s", guild_id, symbol, exc)
                    comment_failures += 1
                    continue
                if finalized:
                    finalized_sessions += 1

    detail = (
        f"active_symbols={active_symbols_count} updated_threads={updated_threads} finalized_sessions={finalized_sessions} "
        f"missing_forum_guilds={missing_forum_guilds} thread_failures={thread_failures} "
        f"snapshot_failures={snapshot_failures} comment_failures={comment_failures}"
    )
    if total_target_symbols == 0:
        status = "skipped"
        detail = "no-watch-symbols"
    elif not pending_guilds and missing_forum_guilds > 0:
        status = "skipped"
        detail = f"no-target-forums {detail}"
    elif snapshot_failures > 0 or thread_failures > 0 or comment_failures > 0:
        status = "failed"
    else:
        status = "ok"
    set_job_last_run(state, "watch_poll", status, detail)
    save_state(state)
    _log_job_result("watch_poll", status, detail)


async def intel_scheduler(client: discord.Client) -> None:
    news_h, news_m = _parse_time(NEWS_BRIEFING_TIME, 7, 30)
    eod_h, eod_m = _parse_time(EOD_SUMMARY_TIME, 16, 20)
    registry_h, registry_m = _parse_time(INSTRUMENT_REGISTRY_REFRESH_TIME, 6, 20)
    last_watch_run: datetime | None = None
    registry_refresh_task: asyncio.Task[dict[str, int | str]] | None = None

    while True:
        now = now_kst()
        try:
            if registry_refresh_task is not None and registry_refresh_task.done():
                try:
                    summary = registry_refresh_task.result()
                except Exception as exc:
                    active = registry_status()
                    detail = f"{exc} active={active['message']}"
                    _record_instrument_registry_refresh_result(ok=False, detail=detail)
                    logger.exception("[intel] instrument registry refresh failed: %s", exc)
                else:
                    _record_instrument_registry_refresh_result(
                        ok=True,
                        detail=_format_instrument_registry_refresh_detail(summary),
                    )
                registry_refresh_task = None
            if INSTRUMENT_REGISTRY_REFRESH_ENABLED:
                state = load_state()
                if registry_refresh_task is None and _should_start_instrument_registry_refresh(
                    state,
                    now,
                    refresh_hour=registry_h,
                    refresh_minute=registry_m,
                ):
                    logger.info("[intel] instrument_registry_refresh status=started scheduled_for=%02d:%02d", registry_h, registry_m)
                    registry_refresh_task = asyncio.create_task(_refresh_instrument_registry())
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
