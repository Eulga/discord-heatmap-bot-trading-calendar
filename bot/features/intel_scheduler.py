import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

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
    STOCK_DASHBOARD_ALERT_DELIVERY_ENABLED,
    STOCK_DASHBOARD_ALERT_POLL_INTERVAL_SECONDS,
    STOCK_DASHBOARD_API_BASE_URL,
    STOCK_DASHBOARD_INTERNAL_TOKEN,
    STOCK_DASHBOARD_NEWS_DELIVERY_ENABLED,
    STOCK_DASHBOARD_NEWS_MAX_PER_BATCH,
    STOCK_DASHBOARD_NEWS_POLL_INTERVAL_SECONDS,
    STOCK_DASHBOARD_MARKET_REPORT_FORUM_ID,
    STOCK_DASHBOARD_REPORT_DELIVERY_ENABLED,
    STOCK_DASHBOARD_REPORT_POLL_INTERVAL_SECONDS,
    STOCK_DASHBOARD_WATCHLIST_REPORT_FORUM_ID,
    STOCK_DASHBOARD_WEB_BASE_URL,
    WATCH_FEATURE_ENABLED,
    WATCH_POLL_ENABLED,
    WATCH_POLL_INTERVAL_SECONDS,
)
from bot.app.dashboard_delivery import record_dashboard_delivery_results
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
from bot.features.dashboard_session import dashboard_market_session, schedule_icon
from bot.features.stock_roles.service import stock_role_mentions_for_items, stock_role_mentions_for_text
from bot.features.watch.service import (
    calculate_change_pct,
    evaluate_band_event,
    render_band_comment,
    render_blank_watch_starter,
    render_close_comment,
    render_watch_current_comment,
)
from bot.features.watch.session import get_watch_market_session, is_adjacent_watch_session_date
from bot.features.watch.thread_service import upsert_watch_thread
from bot.forum.repository import (
    clear_watch_current_comment_id,
    cleanup_news_dedup,
    get_daily_posts_for_guild,
    get_guild_eod_forum_channel_id,
    get_guild_forum_channel_id,
    get_guild_last_auto_run_date,
    get_guild_last_auto_skip_date,
    get_guild_news_forum_channel_id,
    get_guild_schedule_alert_channel_id,
    get_guild_watch_forum_channel_id,
    get_job_last_runs,
    get_watch_reference_snapshot,
    get_watch_session_alert,
    is_news_dedup_seen,
    list_guild_ids,
    list_active_watch_symbols,
    list_watch_tracked_symbols,
    load_state,
    mark_news_dedup_seen,
    save_state,
    set_guild_last_auto_skip,
    set_guild_last_auto_run_date,
    set_job_last_run,
    set_provider_status,
    set_watch_current_comment_id,
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
    DashboardNewsProvider,
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
DASHBOARD_ALERT_DELIVERY_COMMAND_KEY = "dashboard-alerts"
DASHBOARD_NEWS_DELIVERY_COMMAND_KEY = "dashboard-news-delivery"
DASHBOARD_REPORT_DELIVERY_COMMAND_KEY_PREFIX = "dashboard-report-delivery"
DASHBOARD_ALERT_SENT_IDS_KEY = "dashboard_alert_sent_ids_by_guild"
DASHBOARD_ALERT_SENT_ID_LIMIT = 300
DASHBOARD_NEWS_COLOR = 0x22D3EE
DASHBOARD_REPORT_MARKET_COLOR = 0x38BDF8
DASHBOARD_REPORT_WATCHLIST_COLOR = 0xA78BFA
DASHBOARD_ALERT_COLOR_KR_UP = 0xFF5A52
DASHBOARD_ALERT_COLOR_KR_DOWN = 0x2F80ED
DASHBOARD_ALERT_COLOR_US_UP = 0x30D158
DASHBOARD_ALERT_COLOR_US_DOWN = 0xFF5A52
DASHBOARD_ALERT_COLOR_NEUTRAL = 0x8B95A1
WATCH_CLOSE_FINALIZATION_TIMEZONE = ZoneInfo("Asia/Seoul")
WATCH_PENDING_CLOSE_SESSIONS_KEY = "pending_close_sessions"
WATCH_CLOSE_FINALIZATION_DUE_TIMES = {
    "KRX": (16, 0),
    "NAS": (7, 0),
    "NYS": (7, 0),
    "AMS": (7, 0),
}


def _build_news_provider() -> NewsProvider:
    if NEWS_PROVIDER_KIND == "mock":
        return MockNewsProvider()
    if NEWS_PROVIDER_KIND == "dashboard":
        if not STOCK_DASHBOARD_API_BASE_URL or not STOCK_DASHBOARD_INTERNAL_TOKEN:
            return ErrorNewsProvider("dashboard-news-config-missing")
        return DashboardNewsProvider(
            base_url=STOCK_DASHBOARD_API_BASE_URL,
            internal_token=STOCK_DASHBOARD_INTERNAL_TOKEN,
            limit_per_region=NAVER_NEWS_LIMIT_PER_REGION,
            timeout_seconds=INTEL_API_TIMEOUT_SECONDS,
            retry_count=INTEL_API_RETRY_COUNT,
        )
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


def _should_run_daily_job(
    state: dict,
    now: datetime,
    *,
    job_key: str,
    scheduled_hour: int,
    scheduled_minute: int,
) -> bool:
    if now.hour < scheduled_hour or (now.hour == scheduled_hour and now.minute < scheduled_minute):
        return False
    return _job_status_on_date(state, job_key, date_key(now)) is None


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


def _fetch_dashboard_alert_deliveries_sync() -> list[dict[str, Any]]:
    if not STOCK_DASHBOARD_API_BASE_URL or not STOCK_DASHBOARD_INTERNAL_TOKEN:
        raise RuntimeError("dashboard-alert-config-missing")

    request = Request(
        f"{STOCK_DASHBOARD_API_BASE_URL.rstrip('/')}/api/discord/deliveries/alerts",
        headers={
            "Accept": "application/json",
            "User-Agent": "discord-heatmap-bot/1.0",
            "x-internal-token": STOCK_DASHBOARD_INTERNAL_TOKEN,
        },
    )

    try:
        with urlopen(request, timeout=INTEL_API_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise RuntimeError(f"dashboard-alert-auth-failed:{exc.code}") from exc
        raise RuntimeError(f"dashboard-alert-upstream-error:{exc.code}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("dashboard-alert-invalid-response") from exc
    except URLError as exc:
        raise RuntimeError("dashboard-alert-unreachable") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("dashboard-alert-invalid-response")

    alerts: list[dict[str, Any]] = []
    for item in payload["data"]:
        if not isinstance(item, dict):
            continue
        alert_id = str(item.get("id") or "").strip()
        title = str(item.get("title") or "").strip()
        if not alert_id or not title:
            continue
        alerts.append(item)
    return alerts


async def _fetch_dashboard_alert_deliveries() -> list[dict[str, Any]]:
    return await asyncio.to_thread(_fetch_dashboard_alert_deliveries_sync)


def _fetch_dashboard_news_deliveries_sync() -> list[dict[str, Any]]:
    if not STOCK_DASHBOARD_API_BASE_URL or not STOCK_DASHBOARD_INTERNAL_TOKEN:
        raise RuntimeError("dashboard-news-config-missing")

    request = Request(
        f"{STOCK_DASHBOARD_API_BASE_URL.rstrip('/')}/api/discord/deliveries/news",
        headers={
            "Accept": "application/json",
            "User-Agent": "discord-heatmap-bot/1.0",
            "x-internal-token": STOCK_DASHBOARD_INTERNAL_TOKEN,
        },
    )

    try:
        with urlopen(request, timeout=INTEL_API_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise RuntimeError(f"dashboard-news-auth-failed:{exc.code}") from exc
        raise RuntimeError(f"dashboard-news-upstream-error:{exc.code}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("dashboard-news-invalid-response") from exc
    except URLError as exc:
        raise RuntimeError("dashboard-news-unreachable") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("dashboard-news-invalid-response")

    news_items: list[dict[str, Any]] = []
    for item in payload["data"]:
        if not isinstance(item, dict):
            continue
        delivery_id = str(item.get("id") or item.get("articleKey") or "").strip()
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or item.get("link") or "").strip()
        if not delivery_id or not title or not url:
            continue
        news_items.append(item)
    return news_items


async def _fetch_dashboard_news_deliveries() -> list[dict[str, Any]]:
    return await asyncio.to_thread(_fetch_dashboard_news_deliveries_sync)


def _fetch_dashboard_report_deliveries_sync() -> list[dict[str, Any]]:
    if not STOCK_DASHBOARD_API_BASE_URL or not STOCK_DASHBOARD_INTERNAL_TOKEN:
        raise RuntimeError("dashboard-report-config-missing")

    request = Request(
        f"{STOCK_DASHBOARD_API_BASE_URL.rstrip('/')}/api/discord/deliveries/reports",
        headers={
            "Accept": "application/json",
            "User-Agent": "discord-heatmap-bot/1.0",
            "x-internal-token": STOCK_DASHBOARD_INTERNAL_TOKEN,
        },
    )

    try:
        with urlopen(request, timeout=INTEL_API_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise RuntimeError(f"dashboard-report-auth-failed:{exc.code}") from exc
        raise RuntimeError(f"dashboard-report-upstream-error:{exc.code}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("dashboard-report-invalid-response") from exc
    except URLError as exc:
        raise RuntimeError("dashboard-report-unreachable") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("dashboard-report-invalid-response")

    reports: list[dict[str, Any]] = []
    for item in payload["data"]:
        if not isinstance(item, dict):
            continue
        delivery_id = str(item.get("id") or "").strip()
        kind = str(item.get("kind") or "").strip()
        title = str(item.get("title") or "").strip()
        body = str(item.get("body") or "").strip()
        if not delivery_id or kind not in {"market", "watchlist"} or not title or not body:
            continue
        reports.append(item)
    return reports


async def _fetch_dashboard_report_deliveries() -> list[dict[str, Any]]:
    return await asyncio.to_thread(_fetch_dashboard_report_deliveries_sync)


def _post_dashboard_alert_delivery_results_sync(results: list[dict[str, Any]]) -> None:
    if not results or not STOCK_DASHBOARD_API_BASE_URL or not STOCK_DASHBOARD_INTERNAL_TOKEN:
        return

    request = Request(
        f"{STOCK_DASHBOARD_API_BASE_URL.rstrip('/')}/api/discord/deliveries/alerts",
        data=json.dumps({"results": results}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "discord-heatmap-bot/1.0",
            "x-internal-token": STOCK_DASHBOARD_INTERNAL_TOKEN,
        },
        method="POST",
    )

    with urlopen(request, timeout=INTEL_API_TIMEOUT_SECONDS) as response:
        if response.status >= 400:
            raise RuntimeError(f"dashboard-alert-result-save-failed:{response.status}")


async def _record_dashboard_alert_delivery_results(results: list[dict[str, Any]]) -> None:
    if not results:
        return

    try:
        await asyncio.to_thread(_post_dashboard_alert_delivery_results_sync, results)
    except Exception as exc:
        logger.warning("[intel] dashboard alert delivery result save failed: %s", exc)


def _dashboard_alert_sent_ids(state: dict, guild_id: int) -> list[str]:
    system = state.setdefault("system", {})
    if not isinstance(system, dict):
        state["system"] = {}
        system = state["system"]
    store = system.setdefault(DASHBOARD_ALERT_SENT_IDS_KEY, {})
    if not isinstance(store, dict):
        store = {}
        system[DASHBOARD_ALERT_SENT_IDS_KEY] = store
    ids = store.setdefault(str(guild_id), [])
    if not isinstance(ids, list):
        ids = []
        store[str(guild_id)] = ids
    cleaned = [str(item) for item in ids if isinstance(item, str) and item.strip()]
    if cleaned != ids:
        store[str(guild_id)] = cleaned
        return cleaned
    return ids


def _mark_dashboard_alerts_sent(state: dict, guild_id: int, alert_ids: list[str]) -> None:
    sent_ids = _dashboard_alert_sent_ids(state, guild_id)
    for alert_id in alert_ids:
        if alert_id not in sent_ids:
            sent_ids.append(alert_id)
    if len(sent_ids) > DASHBOARD_ALERT_SENT_ID_LIMIT:
        del sent_ids[: len(sent_ids) - DASHBOARD_ALERT_SENT_ID_LIMIT]


def _dashboard_alert_canonical_symbol(alert: dict[str, Any]) -> str:
    alert_id = str(alert.get("id") or "").strip()
    if not alert_id.startswith("price-"):
        return ""
    canonical_symbol = alert_id.removeprefix("price-").strip()
    for suffix in ("-up", "-down"):
        marker_index = canonical_symbol.rfind(suffix)
        if marker_index == -1:
            continue
        band = canonical_symbol[marker_index + len(suffix) + 1 :]
        if band.isdigit():
            return canonical_symbol[:marker_index].strip()
    return canonical_symbol


def _dashboard_alert_ticker(alert: dict[str, Any]) -> str:
    explicit_ticker = str(alert.get("ticker") or "").strip()
    if explicit_ticker:
        return explicit_ticker

    canonical_symbol = _dashboard_alert_canonical_symbol(alert)
    if not canonical_symbol:
        return ""
    if ":" in canonical_symbol:
        return canonical_symbol.split(":", 1)[1].strip()
    return canonical_symbol


def _dashboard_alert_stock_name(alert: dict[str, Any]) -> str:
    title = str(alert.get("title") or "").strip()
    description = str(alert.get("description") or "").strip()
    if description:
        return description.rsplit(" ", 1)[0].strip()
    return title.replace("변동성 확대", "").strip() or title or "관심종목"


def _dashboard_alert_category(alert: dict[str, Any]) -> str:
    category = str(alert.get("category") or "").strip()
    return "" if category == "직접 추가" else category


def _dashboard_alert_change_text(alert: dict[str, Any]) -> str:
    description = str(alert.get("description") or "").strip()
    if not description:
        return ""
    return description.rsplit(" ", 1)[-1].strip()


def _dashboard_alert_direction_key(alert: dict[str, Any]) -> str:
    status = str(alert.get("status") or "").strip()
    if status in {"상승", "up"}:
        return "up"
    if status in {"하락", "down"}:
        return "down"
    return "neutral"


def _dashboard_alert_color(alert: dict[str, Any], direction_key: str) -> int:
    market = str(alert.get("market") or "").strip()
    is_kr_market = market in {"국장", "KR", "KRX"}
    if direction_key == "up":
        return DASHBOARD_ALERT_COLOR_KR_UP if is_kr_market else DASHBOARD_ALERT_COLOR_US_UP
    if direction_key == "down":
        return DASHBOARD_ALERT_COLOR_KR_DOWN if is_kr_market else DASHBOARD_ALERT_COLOR_US_DOWN
    return DASHBOARD_ALERT_COLOR_NEUTRAL


def _dashboard_alert_marker(alert: dict[str, Any], direction_key: str) -> str:
    market = str(alert.get("market") or "").strip()
    is_kr_market = market in {"국장", "KR", "KRX"}
    if direction_key == "up":
        return "🔴" if is_kr_market else "🟢"
    if direction_key == "down":
        return "🔵" if is_kr_market else "🔴"
    return "⚪"


def _format_dashboard_stock_alert_title(alert: dict[str, Any]) -> str:
    category = _dashboard_alert_category(alert)
    stock_name = _dashboard_alert_stock_name(alert)
    ticker = _dashboard_alert_ticker(alert)
    category_prefix = f"[{category}] " if category else ""
    prefix = f"({ticker}) " if ticker else ""
    return f"{category_prefix}{prefix}{stock_name}".strip()


def _format_dashboard_schedule_alert_title(alert: dict[str, Any]) -> str:
    title = str(alert.get("title") or "일정 알림").strip()
    status = str(alert.get("status") or "").strip()
    description = str(alert.get("description") or "").strip()
    icon = schedule_icon(str(alert.get("market") or ""), str(alert.get("eventType") or ""), f"{title} {description}")
    if status and status not in title:
        return f"{icon} {title} {status}".strip()
    return f"{icon} {title}".strip()


def _is_dashboard_alert_date_part(value: str) -> bool:
    return len(value) == 10 and value[4] == "-" and value[7] == "-" and value.replace("-", "").isdigit()


def _is_dashboard_alert_time_part(value: str) -> bool:
    hour, separator, minute = value.partition(":")
    return bool(separator) and hour.isdigit() and minute.isdigit() and len(minute) == 2


def _format_dashboard_schedule_alert_description(alert: dict[str, Any]) -> str:
    raw_description = str(alert.get("description") or "").strip()
    if not raw_description:
        return ""

    public_lines = []
    for line in raw_description.splitlines():
        text = line.strip()
        if not text or text.startswith("출처:") or text.startswith("http://") or text.startswith("https://"):
            continue
        public_lines.append(text)

    compact = " ".join(public_lines).strip()
    if not compact:
        return ""

    parts = [part.strip() for part in compact.split("·") if part.strip()]
    if len(parts) >= 3 and _is_dashboard_alert_date_part(parts[0]) and _is_dashboard_alert_time_part(parts[1]):
        return f"**{parts[1]}** · {' · '.join(parts[2:])}"
    if len(parts) >= 2 and _is_dashboard_alert_date_part(parts[0]):
        return " · ".join(parts[1:])
    return compact


def _build_dashboard_stock_alert_embed(alert: dict[str, Any], now: datetime | None = None) -> discord.Embed | None:
    if str(alert.get("type") or "").strip() != "stock":
        return None

    direction_key = _dashboard_alert_direction_key(alert)
    change_text = _dashboard_alert_change_text(alert)
    marker = _dashboard_alert_marker(alert, direction_key)
    session = dashboard_market_session(str(alert.get("market") or ""), now)
    description = f"{marker} {session.basis_label} **{change_text}**" if change_text else ""
    embed = discord.Embed(
        title=_format_dashboard_stock_alert_title(alert),
        description=description,
        color=_dashboard_alert_color(alert, direction_key),
    )
    embed.set_footer(text=session.footer_text)
    return embed


def _build_dashboard_schedule_alert_embed(alert: dict[str, Any], now: datetime | None = None) -> discord.Embed | None:
    if str(alert.get("type") or "").strip() != "event":
        return None

    priority = str(alert.get("priority") or "").strip()
    color = 0xF59E0B if priority == "높음" else 0x22D3EE
    embed = discord.Embed(
        title=_format_dashboard_schedule_alert_title(alert),
        description=_format_dashboard_schedule_alert_description(alert),
        color=color,
    )
    embed.set_footer(text="일정 알림 · KST 기준")
    return embed


def _format_dashboard_alert_message(alert: dict[str, Any], now: datetime | None = None) -> str:
    title = str(alert.get("title") or "관심종목 알림").strip()
    status = str(alert.get("status") or "").strip()
    priority = str(alert.get("priority") or "").strip()
    market = str(alert.get("market") or "").strip()
    source = str(alert.get("source") or "").strip()
    description = str(alert.get("description") or "").strip()
    alert_type = str(alert.get("type") or "").strip()
    url = str(alert.get("url") or "").strip()

    if alert_type == "stock":
        direction_key = _dashboard_alert_direction_key(alert)
        marker = _dashboard_alert_marker(alert, direction_key)
        session = dashboard_market_session(market, now)
        lines = [f"**{_format_dashboard_stock_alert_title(alert)}**"]
        if description:
            lines.append(f"{marker} {session.basis_label} **{_dashboard_alert_change_text(alert)}**")
        lines.append(session.footer_text)
        return "\n".join(lines)[:1900]

    if alert_type == "event":
        lines = [f"**{_format_dashboard_schedule_alert_title(alert)}**"]
        compact_description = _format_dashboard_schedule_alert_description(alert)
        if compact_description:
            lines.append(compact_description)
        return "\n".join(lines)[:1900]

    meta = " · ".join(part for part in [market, status, priority] if part)
    lines = [f"**{title}**"]
    if meta:
        lines.append(meta)
    if description:
        lines.append(description)
    if source and source != "collector_projection":
        lines.append(f"출처: {source}")
    if url:
        lines.append(url)
    return "\n".join(lines)[:1900]


def _is_dashboard_stock_alert(alert: dict[str, Any]) -> bool:
    return str(alert.get("type") or "").strip() == "stock"


def _is_dashboard_schedule_alert(alert: dict[str, Any]) -> bool:
    return str(alert.get("type") or "").strip() == "event"


async def _resolve_guild_message_channel(
    client: discord.Client,
    guild_id: int,
    channel_id: int,
) -> Any | None:
    get_channel = getattr(client, "get_channel", None)
    fetch_channel = getattr(client, "fetch_channel", None)
    channel = get_channel(channel_id) if callable(get_channel) else None
    if channel is None and callable(fetch_channel):
        try:
            channel = await fetch_channel(channel_id)
        except discord.NotFound:
            return None
    if channel is None:
        return None
    channel_guild = getattr(channel, "guild", None)
    if getattr(channel_guild, "id", None) != guild_id:
        return None
    if not callable(getattr(channel, "send", None)):
        return None
    return channel


def _dashboard_alert_post_title(now: datetime) -> str:
    return f"관심종목 알림 {date_key(now)}"


def _dashboard_alert_starter_body(now: datetime, alert_count: int) -> str:
    return f"{timestamp_text(now)} 기준 대시보드 주요 알림 {alert_count}건"


def _dashboard_delivery_result(
    alert: dict[str, Any],
    *,
    guild_id: int,
    status: str,
    target: str,
    channel_id: int | str | None = None,
    message_id: int | str | None = None,
    reason: str | None = None,
    thread_id: int | str | None = None,
) -> dict[str, Any]:
    title = (
        _format_dashboard_schedule_alert_title(alert)
        if target == "schedule"
        else _format_dashboard_stock_alert_title(alert)
    )
    return {
        "alertId": str(alert.get("id") or ""),
        "channelId": str(channel_id or ""),
        "guildId": str(guild_id),
        "messageId": str(message_id or ""),
        "reason": reason or "",
        "status": status,
        "target": target,
        "threadId": str(thread_id or ""),
        "title": title,
    }


def _dashboard_content_delivery_result(
    *,
    channel_id: int | str | None,
    delivery_id: str,
    guild_id: int,
    message_id: int | str | None = None,
    reason: str | None = None,
    status: str,
    target: str,
    thread_id: int | str | None = None,
    title: str,
) -> dict[str, Any]:
    return {
        "channelId": str(channel_id or ""),
        "deliveryId": delivery_id,
        "guildId": str(guild_id),
        "messageId": str(message_id or ""),
        "reason": reason or "",
        "status": status,
        "target": target,
        "threadId": str(thread_id or ""),
        "title": title,
    }


def _short_text(text: str, max_chars: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max(0, max_chars - 1)].rstrip()}…"


def _dashboard_news_delivery_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("articleKey") or item.get("url") or "").strip()


def _is_dashboard_news_sendable(item: dict[str, Any]) -> bool:
    importance = str(item.get("importance") or "").strip().lower()
    return importance != "low"


def _dashboard_news_region_label(item: dict[str, Any]) -> str:
    region = str(item.get("region") or "").strip().lower()
    market = str(item.get("market") or "").strip()
    if region == "domestic" or market == "국장":
        return "국내"
    if region == "global" or market == "미장":
        return "해외"
    return "시장"


def _dashboard_news_time_text(item: dict[str, Any]) -> str:
    published_at_text = str(item.get("publishedAt") or "").strip()
    if not published_at_text:
        return ""
    try:
        published_at = datetime.fromisoformat(published_at_text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=ZoneInfo("UTC"))
    return published_at.astimezone(ZoneInfo("Asia/Seoul")).strftime("%H:%M")


def _dashboard_news_source_text(item: dict[str, Any]) -> str:
    source = str(item.get("source") or "").strip()
    time_text = _dashboard_news_time_text(item)
    return " · ".join(part for part in [source, time_text] if part)


def _dashboard_news_card_prefix(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    importance = str(item.get("importance") or "").strip().lower()
    category = str(item.get("category") or item.get("topic") or item.get("theme") or "").strip().lower()
    region_label = _dashboard_news_region_label(item)
    has_symbols = bool(item.get("symbols") or item.get("tickers") or item.get("relatedSymbols"))

    if "속보" in title or importance in {"breaking", "critical", "urgent"}:
        return "🔊 [속보]"
    if any(keyword in category for keyword in ["macro", "econom", "금리", "환율", "물가", "원자재"]):
        return "📊 [매크로]"
    if has_symbols or any(keyword in category for keyword in ["stock", "company", "기업", "종목"]):
        return "🏢 [기업]"
    if region_label == "해외":
        return "🌐 [해외]"
    return "📌 [중요]"


def _dashboard_news_summary_lines(item: dict[str, Any], *, max_lines: int = 3) -> list[str]:
    summary = str(item.get("summary") or item.get("marketReason") or "").strip()
    if not summary:
        return []

    normalized = " ".join(summary.split())
    sentences = [
        part.strip(" -")
        for part in re.split(r"(?<=[.!?。])\s+|(?<=다\.)\s+|(?<=요\.)\s+|(?<=음\.)\s+", normalized)
        if part.strip(" -")
    ]
    if not sentences:
        sentences = [normalized]

    return [_short_text(sentence, 170) for sentence in sentences[:max_lines]]


def _dashboard_news_delivery_post_title(now: datetime) -> str:
    return f"📰 {date_key(now)} 뉴스"


def _dashboard_news_delivery_starter_body(now: datetime) -> str:
    return f"{timestamp_text(now)} 기준"


def _build_dashboard_news_delivery_embed(items: list[dict[str, Any]], now: datetime) -> discord.Embed:
    embed = discord.Embed(
        title="시장 뉴스",
        description=f"{timestamp_text(now)} 기준 새 중요 뉴스 {len(items)}건",
        color=DASHBOARD_NEWS_COLOR,
    )
    for item in items:
        title = _short_text(str(item.get("title") or "뉴스").strip(), 220)
        field_name = _short_text(f"{_dashboard_news_card_prefix(item)} {title}", 256)
        summary_lines = _dashboard_news_summary_lines(item)
        source_text = _dashboard_news_source_text(item)
        url = str(item.get("url") or item.get("link") or "").strip()
        lines = []
        for index, summary_line in enumerate(summary_lines, start=1):
            lines.append(f"{index}. {summary_line}")
        if source_text:
            lines.append(source_text)
        if url:
            lines.append(f"[원문 보기]({url})")
        embed.add_field(name=field_name, value="\n".join(lines)[:1024] or "원문 링크를 확인하세요.", inline=False)
    return embed


async def _upsert_daily_post_lenient(**kwargs: Any) -> tuple[Any | None, str]:
    result = await upsert_daily_post(**kwargs)
    if isinstance(result, tuple):
        thread = result[0] if len(result) >= 1 else None
        action = str(result[1]) if len(result) >= 2 else ""
        return thread, action
    return None, ""


async def _run_dashboard_news_delivery(client: discord.Client, now: datetime) -> None:
    state = load_state()
    pending_guilds: list[tuple[int, int]] = []
    missing_forum = 0

    for guild_id in list_guild_ids(state):
        forum_channel_id = get_guild_news_forum_channel_id(state, guild_id)
        if forum_channel_id is None:
            missing_forum += 1
            continue
        pending_guilds.append((guild_id, forum_channel_id))

    if not pending_guilds:
        detail = f"no-target-forums missing_forum={missing_forum}"
        set_job_last_run(state, "dashboard_news_delivery", "skipped", detail)
        save_state(state)
        _log_job_result("dashboard_news_delivery", "skipped", detail)
        return

    try:
        news_items = await _fetch_dashboard_news_deliveries()
    except Exception as exc:
        set_job_last_run(state, "dashboard_news_delivery", "failed", str(exc))
        set_provider_status(state, "dashboard_news", False, str(exc))
        save_state(state)
        _log_job_result("dashboard_news_delivery", "failed", str(exc))
        logger.exception("[intel] dashboard news delivery fetch failed: %s", exc)
        return

    sendable_items = [item for item in news_items if _is_dashboard_news_sendable(item)]
    set_provider_status(state, "dashboard_news", True, f"fetched={len(news_items)} sendable={len(sendable_items)}")
    cleanup_news_dedup(state, keep_recent_days=7)

    if not sendable_items:
        set_job_last_run(state, "dashboard_news_delivery", "skipped", "no-news")
        save_state(state)
        _log_job_result("dashboard_news_delivery", "skipped", "no-news")
        return

    run_date = date_key(now)
    posted = 0
    failed = 0
    skipped = 0
    delivery_results: list[dict[str, Any]] = []

    for guild_id, forum_channel_id in pending_guilds:
        new_items = []
        for item in sendable_items:
            delivery_id = _dashboard_news_delivery_id(item)
            if not delivery_id:
                continue
            dedup_key = f"{guild_id}:{delivery_id}"
            if is_news_dedup_seen(state, dedup_key, run_date):
                continue
            new_items.append(item)
            if len(new_items) >= STOCK_DASHBOARD_NEWS_MAX_PER_BATCH:
                break

        if not new_items:
            skipped += 1
            continue

        try:
            thread, _action = await upsert_daily_post(
                client=client,
                state=state,
                guild_id=guild_id,
                forum_channel_id=forum_channel_id,
                command_key=DASHBOARD_NEWS_DELIVERY_COMMAND_KEY,
                post_title=_dashboard_news_delivery_post_title(now),
                body_text=_dashboard_news_delivery_starter_body(now),
                image_paths=[],
            )
            embed = _build_dashboard_news_delivery_embed(new_items, now)
            role_mentions = stock_role_mentions_for_items(state, guild_id, new_items)
            if role_mentions:
                message = await thread.send(
                    content=role_mentions,
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(roles=True, users=False, everyone=False),
                )
            else:
                message = await thread.send(embed=embed)
            for item in new_items:
                delivery_id = _dashboard_news_delivery_id(item)
                mark_news_dedup_seen(state, f"{guild_id}:{delivery_id}", run_date)
                delivery_results.append(
                    _dashboard_content_delivery_result(
                        channel_id=getattr(thread, "id", None),
                        delivery_id=delivery_id,
                        guild_id=guild_id,
                        message_id=getattr(message, "id", None),
                        status="sent",
                        target="news",
                        thread_id=getattr(thread, "id", None),
                        title=str(item.get("title") or "뉴스"),
                    )
                )
            posted += len(new_items)
        except Exception as exc:
            failed += 1
            for item in new_items:
                delivery_id = _dashboard_news_delivery_id(item)
                delivery_results.append(
                    _dashboard_content_delivery_result(
                        channel_id=forum_channel_id,
                        delivery_id=delivery_id,
                        guild_id=guild_id,
                        reason=str(exc),
                        status="failed",
                        target="news",
                        title=str(item.get("title") or "뉴스"),
                    )
                )
            logger.exception("[intel] dashboard news delivery post failed guild=%s: %s", guild_id, exc)

    status = "ok" if posted > 0 and failed == 0 else "failed" if failed > 0 else "skipped"
    detail = (
        f"news={len(news_items)} sendable={len(sendable_items)} posted={posted} "
        f"skipped_guilds={skipped} failed_guilds={failed} missing_forum={missing_forum}"
    )
    set_job_last_run(state, "dashboard_news_delivery", status, detail)
    save_state(state)
    await record_dashboard_delivery_results("news", delivery_results)
    _log_job_result("dashboard_news_delivery", status, detail)


def _dashboard_report_delivery_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("reportId") or "").strip()


def _dashboard_report_kind(item: dict[str, Any]) -> str:
    kind = str(item.get("kind") or "").strip().lower()
    return kind if kind in {"market", "watchlist"} else ""


def _dashboard_report_kind_label(kind: str) -> str:
    return "시장" if kind == "market" else "관종"


def _dashboard_report_forum_id(kind: str) -> int | None:
    if kind == "market":
        return STOCK_DASHBOARD_MARKET_REPORT_FORUM_ID
    if kind == "watchlist":
        return STOCK_DASHBOARD_WATCHLIST_REPORT_FORUM_ID
    return None


def _dashboard_report_color(kind: str) -> int:
    return DASHBOARD_REPORT_MARKET_COLOR if kind == "market" else DASHBOARD_REPORT_WATCHLIST_COLOR


def _dashboard_report_url(item: dict[str, Any]) -> str:
    path = str(item.get("urlPath") or "").strip()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path and STOCK_DASHBOARD_WEB_BASE_URL:
        return f"{STOCK_DASHBOARD_WEB_BASE_URL}{path if path.startswith('/') else f'/{path}'}"
    return ""


def _dashboard_report_post_title(kind: str, report_date: str) -> str:
    date_text = report_date or date_key(now_kst())
    return f"{date_text} {_dashboard_report_kind_label(kind)} 리포트"


def _dashboard_report_starter_body(kind: str, report_date: str) -> str:
    return f"{report_date or date_key(now_kst())} 기준 {_dashboard_report_kind_label(kind)} 리포트"


def _dashboard_report_body_lines(item: dict[str, Any], *, max_lines: int = 6) -> list[str]:
    body = str(item.get("body") or "").strip()
    lines = []
    for raw_line in body.splitlines():
        normalized = " ".join(raw_line.strip(" -").split())
        if not normalized:
            continue
        lines.append(_short_text(normalized, 180))
        if len(lines) >= max_lines:
            break
    return lines


def _build_dashboard_report_delivery_embed(item: dict[str, Any]) -> discord.Embed:
    kind = _dashboard_report_kind(item)
    title = _short_text(str(item.get("title") or _dashboard_report_post_title(kind, "")).strip(), 220)
    summary = _short_text(str(item.get("summary") or "").strip(), 260)
    url = _dashboard_report_url(item)
    embed = discord.Embed(
        title=title,
        description=summary or None,
        color=_dashboard_report_color(kind),
    )

    body_lines = _dashboard_report_body_lines(item)
    if body_lines:
        embed.add_field(name="핵심 요약", value="\n".join(f"{index}. {line}" for index, line in enumerate(body_lines, start=1))[:1024], inline=False)
    if url:
        embed.add_field(name="전체 보기", value=f"[웹에서 열기]({url})", inline=False)
    embed.set_footer(text=f"{_dashboard_report_kind_label(kind)} 리포트")
    return embed


async def _resolve_report_forum_channel(client: discord.Client, channel_id: int) -> Any | None:
    get_channel = getattr(client, "get_channel", None)
    fetch_channel = getattr(client, "fetch_channel", None)
    channel = get_channel(channel_id) if callable(get_channel) else None
    if channel is None and callable(fetch_channel):
        try:
            channel = await fetch_channel(channel_id)
        except discord.NotFound:
            return None
    if channel is None:
        return None
    if not isinstance(channel, discord.ForumChannel):
        return None
    return channel


async def _run_dashboard_report_delivery(client: discord.Client, now: datetime) -> None:
    configured_forums = {
        "market": STOCK_DASHBOARD_MARKET_REPORT_FORUM_ID,
        "watchlist": STOCK_DASHBOARD_WATCHLIST_REPORT_FORUM_ID,
    }
    if not any(configured_forums.values()):
        detail = "no-report-forums"
        state = load_state()
        set_job_last_run(state, "dashboard_report_delivery", "skipped", detail)
        save_state(state)
        _log_job_result("dashboard_report_delivery", "skipped", detail)
        return

    try:
        report_items = await _fetch_dashboard_report_deliveries()
    except Exception as exc:
        state = load_state()
        set_job_last_run(state, "dashboard_report_delivery", "failed", str(exc))
        set_provider_status(state, "dashboard_reports", False, str(exc))
        save_state(state)
        _log_job_result("dashboard_report_delivery", "failed", str(exc))
        logger.exception("[intel] dashboard report delivery fetch failed: %s", exc)
        return

    state = load_state()
    set_provider_status(state, "dashboard_reports", True, f"fetched={len(report_items)}")

    if not report_items:
        set_job_last_run(state, "dashboard_report_delivery", "skipped", "no-reports")
        save_state(state)
        _log_job_result("dashboard_report_delivery", "skipped", "no-reports")
        return

    posted = 0
    failed = 0
    skipped = 0
    delivery_results: list[dict[str, Any]] = []

    for item in report_items:
        kind = _dashboard_report_kind(item)
        delivery_id = _dashboard_report_delivery_id(item)
        forum_channel_id = _dashboard_report_forum_id(kind)
        title = str(item.get("title") or _dashboard_report_post_title(kind, "")).strip()
        if not kind or not delivery_id or forum_channel_id is None:
            skipped += 1
            delivery_results.append(
                _dashboard_content_delivery_result(
                    channel_id=forum_channel_id,
                    delivery_id=delivery_id or "unknown-report",
                    guild_id=0,
                    reason="report-forum-missing",
                    status="skipped",
                    target=f"{kind or 'unknown'}-report",
                    title=title or "리포트",
                )
            )
            continue

        channel = await _resolve_report_forum_channel(client, forum_channel_id)
        if channel is None:
            failed += 1
            delivery_results.append(
                _dashboard_content_delivery_result(
                    channel_id=forum_channel_id,
                    delivery_id=delivery_id,
                    guild_id=0,
                    reason="report-forum-not-found",
                    status="failed",
                    target=f"{kind}-report",
                    title=title,
                )
            )
            continue

        guild_id = int(getattr(getattr(channel, "guild", None), "id", 0) or 0)
        try:
            report_date = str(item.get("reportDate") or date_key(now)).strip()
            thread, _action = await upsert_daily_post(
                client=client,
                state=state,
                guild_id=guild_id,
                forum_channel_id=forum_channel_id,
                command_key=f"{DASHBOARD_REPORT_DELIVERY_COMMAND_KEY_PREFIX}-{kind}",
                post_title=_dashboard_report_post_title(kind, report_date),
                body_text=_dashboard_report_starter_body(kind, report_date),
                image_paths=[],
            )
            message = await thread.send(embed=_build_dashboard_report_delivery_embed(item))
            delivery_results.append(
                _dashboard_content_delivery_result(
                    channel_id=forum_channel_id,
                    delivery_id=delivery_id,
                    guild_id=guild_id,
                    message_id=getattr(message, "id", None),
                    status="sent",
                    target=f"{kind}-report",
                    thread_id=getattr(thread, "id", None),
                    title=title,
                )
            )
            posted += 1
        except Exception as exc:
            failed += 1
            delivery_results.append(
                _dashboard_content_delivery_result(
                    channel_id=forum_channel_id,
                    delivery_id=delivery_id,
                    guild_id=guild_id,
                    reason=str(exc),
                    status="failed",
                    target=f"{kind}-report",
                    title=title,
                )
            )
            logger.exception("[intel] dashboard report delivery post failed kind=%s delivery_id=%s: %s", kind, delivery_id, exc)

    status = "ok" if posted > 0 and failed == 0 else "failed" if failed > 0 else "skipped"
    detail = f"reports={len(report_items)} posted={posted} skipped={skipped} failed={failed}"
    set_job_last_run(state, "dashboard_report_delivery", status, detail)
    save_state(state)
    await record_dashboard_delivery_results("reports", delivery_results)
    _log_job_result("dashboard_report_delivery", status, detail)


async def _run_dashboard_alert_delivery(client: discord.Client, now: datetime) -> None:
    state = load_state()
    pending_guilds: list[tuple[int, int | None, int | None]] = []
    missing_forum = 0
    missing_schedule_channel = 0

    for guild_id in list_guild_ids(state):
        forum_channel_id = get_guild_watch_forum_channel_id(state, guild_id)
        schedule_channel_id = get_guild_schedule_alert_channel_id(state, guild_id)
        if forum_channel_id is None:
            missing_forum += 1
        if schedule_channel_id is None:
            missing_schedule_channel += 1
        if forum_channel_id is None and schedule_channel_id is None:
            continue
        pending_guilds.append((guild_id, forum_channel_id, schedule_channel_id))

    if not pending_guilds:
        detail = f"no-target-channels missing_forum={missing_forum} missing_schedule_channel={missing_schedule_channel}"
        set_job_last_run(state, "dashboard_alert_delivery", "skipped", detail)
        save_state(state)
        _log_job_result("dashboard_alert_delivery", "skipped", detail)
        return

    try:
        alerts = await _fetch_dashboard_alert_deliveries()
    except Exception as exc:
        set_job_last_run(state, "dashboard_alert_delivery", "failed", str(exc))
        set_provider_status(state, "dashboard_alerts", False, str(exc))
        save_state(state)
        _log_job_result("dashboard_alert_delivery", "failed", str(exc))
        logger.exception("[intel] dashboard alert delivery fetch failed: %s", exc)
        return

    set_provider_status(state, "dashboard_alerts", True, f"fetched={len(alerts)}")

    if not alerts:
        set_job_last_run(state, "dashboard_alert_delivery", "skipped", "no-alerts")
        save_state(state)
        _log_job_result("dashboard_alert_delivery", "skipped", "no-alerts")
        return

    posted = 0
    failed = 0
    skipped = 0
    no_route = 0
    delivery_results: list[dict[str, Any]] = []

    for guild_id, forum_channel_id, schedule_channel_id in pending_guilds:
        sent_ids = set(_dashboard_alert_sent_ids(state, guild_id))
        new_alerts = [alert for alert in alerts if str(alert.get("id") or "") not in sent_ids]
        if not new_alerts:
            skipped += 1
            continue

        stock_alerts = [alert for alert in new_alerts if _is_dashboard_stock_alert(alert)]
        schedule_alerts = [alert for alert in new_alerts if _is_dashboard_schedule_alert(alert)]

        if stock_alerts:
            if forum_channel_id is None:
                no_route += len(stock_alerts)
                _mark_dashboard_alerts_sent(
                    state,
                    guild_id,
                    [str(alert.get("id") or "") for alert in stock_alerts if str(alert.get("id") or "")],
                )
                delivery_results.extend(
                    _dashboard_delivery_result(
                        alert,
                        guild_id=guild_id,
                        reason="watch-forum-not-configured",
                        status="skipped",
                        target="stock",
                    )
                    for alert in stock_alerts
                    if str(alert.get("id") or "")
                )
            else:
                try:
                    thread, _action = await upsert_daily_post(
                        client=client,
                        state=state,
                        guild_id=guild_id,
                        forum_channel_id=forum_channel_id,
                        command_key=DASHBOARD_ALERT_DELIVERY_COMMAND_KEY,
                        post_title=_dashboard_alert_post_title(now),
                        body_text=_dashboard_alert_starter_body(now, len(stock_alerts)),
                        image_paths=[],
                    )
                    sent_now: list[str] = []
                    for alert in stock_alerts:
                        embed = _build_dashboard_stock_alert_embed(alert, now)
                        role_mentions = stock_role_mentions_for_text(
                            state,
                            guild_id,
                            "\n".join(
                                [
                                    str(alert.get("ticker") or ""),
                                    str(alert.get("title") or ""),
                                    str(alert.get("description") or ""),
                                    str(alert.get("category") or ""),
                                ]
                            ),
                            limit=1,
                        )
                        allowed_mentions = (
                            discord.AllowedMentions(roles=True, users=False, everyone=False)
                            if role_mentions
                            else None
                        )
                        if embed is None:
                            content = _format_dashboard_alert_message(alert, now)
                            if role_mentions:
                                content = f"{role_mentions}\n{content}"
                                message = await thread.send(content, allowed_mentions=allowed_mentions)
                            else:
                                message = await thread.send(content)
                        else:
                            if role_mentions:
                                message = await thread.send(
                                    content=role_mentions,
                                    embed=embed,
                                    allowed_mentions=allowed_mentions,
                                )
                            else:
                                message = await thread.send(embed=embed)
                        alert_id = str(alert.get("id") or "")
                        sent_now.append(alert_id)
                        _mark_dashboard_alerts_sent(state, guild_id, [alert_id])
                        delivery_results.append(
                            _dashboard_delivery_result(
                                alert,
                                channel_id=getattr(thread, "id", None),
                                guild_id=guild_id,
                                message_id=getattr(message, "id", None),
                                status="sent",
                                target="stock",
                                thread_id=getattr(thread, "id", None),
                            )
                        )
                    posted += len(sent_now)
                except Exception as exc:
                    failed += 1
                    delivery_results.extend(
                        _dashboard_delivery_result(
                            alert,
                            channel_id=forum_channel_id,
                            guild_id=guild_id,
                            reason=str(exc),
                            status="failed",
                            target="stock",
                        )
                        for alert in stock_alerts
                        if str(alert.get("id") or "")
                    )
                    logger.exception("[intel] dashboard alert delivery post failed guild=%s: %s", guild_id, exc)

        if schedule_alerts:
            if schedule_channel_id is None:
                no_route += len(schedule_alerts)
                _mark_dashboard_alerts_sent(
                    state,
                    guild_id,
                    [str(alert.get("id") or "") for alert in schedule_alerts if str(alert.get("id") or "")],
                )
                delivery_results.extend(
                    _dashboard_delivery_result(
                        alert,
                        guild_id=guild_id,
                        reason="schedule-channel-not-configured",
                        status="skipped",
                        target="schedule",
                    )
                    for alert in schedule_alerts
                    if str(alert.get("id") or "")
                )
            else:
                try:
                    channel = await _resolve_guild_message_channel(client, guild_id, schedule_channel_id)
                    if channel is None:
                        raise RuntimeError("schedule-channel-unavailable")
                    sent_now = []
                    for alert in schedule_alerts:
                        embed = _build_dashboard_schedule_alert_embed(alert, now)
                        if embed is None:
                            message = await channel.send(_format_dashboard_alert_message(alert, now))
                        else:
                            message = await channel.send(embed=embed)
                        alert_id = str(alert.get("id") or "")
                        sent_now.append(alert_id)
                        _mark_dashboard_alerts_sent(state, guild_id, [alert_id])
                        delivery_results.append(
                            _dashboard_delivery_result(
                                alert,
                                channel_id=getattr(channel, "id", None) or schedule_channel_id,
                                guild_id=guild_id,
                                message_id=getattr(message, "id", None),
                                status="sent",
                                target="schedule",
                            )
                        )
                    posted += len(sent_now)
                except Exception as exc:
                    failed += 1
                    delivery_results.extend(
                        _dashboard_delivery_result(
                            alert,
                            channel_id=schedule_channel_id,
                            guild_id=guild_id,
                            reason=str(exc),
                            status="failed",
                            target="schedule",
                        )
                        for alert in schedule_alerts
                        if str(alert.get("id") or "")
                    )
                    logger.exception("[intel] dashboard schedule alert delivery failed guild=%s: %s", guild_id, exc)

    status = "ok" if posted > 0 and failed == 0 else "failed" if failed > 0 else "skipped"
    detail = (
        f"alerts={len(alerts)} posted={posted} skipped_guilds={skipped} failed_guilds={failed} "
        f"no_route={no_route} missing_forum={missing_forum} missing_schedule_channel={missing_schedule_channel}"
    )
    set_job_last_run(state, "dashboard_alert_delivery", status, detail)
    save_state(state)
    await _record_dashboard_alert_delivery_results(delivery_results)
    _log_job_result("dashboard_alert_delivery", status, detail)


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
    delivery_results: list[dict[str, Any]] = []

    for guild_id, forum_channel_id in pending_guilds:
        guild_failed = 0
        try:
            domestic_thread, _domestic_action = await _upsert_daily_post_lenient(
                client=client,
                state=state,
                guild_id=guild_id,
                forum_channel_id=forum_channel_id,
                command_key=NEWS_BRIEFING_DOMESTIC_COMMAND_KEY,
                post_title=build_news_title("domestic", now),
                body_text=domestic_body,
                image_paths=[],
            )
            delivery_results.append(
                _dashboard_content_delivery_result(
                    channel_id=forum_channel_id,
                    delivery_id=f"news-domestic:{guild_id}:{run_date}",
                    guild_id=guild_id,
                    status="sent",
                    target="domestic",
                    thread_id=getattr(domestic_thread, "id", None),
                    title=build_news_title("domestic", now),
                )
            )
            global_thread, _global_action = await _upsert_daily_post_lenient(
                client=client,
                state=state,
                guild_id=guild_id,
                forum_channel_id=forum_channel_id,
                command_key=NEWS_BRIEFING_GLOBAL_COMMAND_KEY,
                post_title=build_news_title("global", now),
                body_text=global_body,
                image_paths=[],
            )
            delivery_results.append(
                _dashboard_content_delivery_result(
                    channel_id=forum_channel_id,
                    delivery_id=f"news-global:{guild_id}:{run_date}",
                    guild_id=guild_id,
                    status="sent",
                    target="global",
                    thread_id=getattr(global_thread, "id", None),
                    title=build_news_title("global", now),
                )
            )
            set_guild_last_auto_run_date(state, guild_id, NEWS_BRIEFING_COMMAND_KEY, run_date)
            posted += 1
            if trend_can_post:
                try:
                    trend_thread, _trend_action = await _upsert_daily_post_lenient(
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
                    delivery_results.append(
                        _dashboard_content_delivery_result(
                            channel_id=forum_channel_id,
                            delivery_id=f"news-trend:{guild_id}:{run_date}",
                            guild_id=guild_id,
                            status="sent",
                            target="trend",
                            thread_id=getattr(trend_thread, "id", None),
                            title=build_trend_post_title(now),
                        )
                    )
                    set_guild_last_auto_run_date(state, guild_id, TREND_BRIEFING_COMMAND_KEY, run_date)
                    trend_posted += 1
                except Exception as exc:
                    delivery_results.append(
                        _dashboard_content_delivery_result(
                            channel_id=forum_channel_id,
                            delivery_id=f"news-trend:{guild_id}:{run_date}",
                            guild_id=guild_id,
                            reason=str(exc),
                            status="failed",
                            target="trend",
                            title=build_trend_post_title(now),
                        )
                    )
                    trend_failed += 1
                    logger.exception("[intel] trend post failed guild=%s: %s", guild_id, exc)
            else:
                set_guild_last_auto_skip(state, guild_id, TREND_BRIEFING_COMMAND_KEY, run_date, trend_skip_reason)
                trend_skipped += 1
        except Exception as exc:
            guild_failed += 1
            failed += 1
            delivery_results.append(
                _dashboard_content_delivery_result(
                    channel_id=forum_channel_id,
                    delivery_id=f"news:{guild_id}:{run_date}",
                    guild_id=guild_id,
                    reason=str(exc),
                    status="failed",
                    target="news",
                    title="뉴스 브리핑",
                )
            )
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
    await record_dashboard_delivery_results("news", delivery_results)


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
    if _pending_watch_close_sessions(alert_entry):
        return True
    active_session_date = str(alert_entry.get("active_session_date") or "").strip()
    if not active_session_date:
        return False
    last_finalized_session_date = str(alert_entry.get("last_finalized_session_date") or "").strip()
    return active_session_date != last_finalized_session_date


def _pending_watch_close_sessions(alert_entry: dict[str, object]) -> dict[str, dict[str, object]]:
    raw_pending = alert_entry.get(WATCH_PENDING_CLOSE_SESSIONS_KEY)
    if not isinstance(raw_pending, dict):
        return {}
    pending: dict[str, dict[str, object]] = {}
    for session_date, raw_entry in raw_pending.items():
        date_text = str(session_date or "").strip()
        if not date_text or not isinstance(raw_entry, dict):
            continue
        try:
            reference_price = float(raw_entry.get("reference_price") or 0.0)
        except (TypeError, ValueError):
            reference_price = 0.0
        if reference_price <= 0:
            continue
        intraday_comment_ids = [
            int(message_id)
            for message_id in raw_entry.get("intraday_comment_ids", [])
            if isinstance(message_id, int)
        ]
        pending_entry: dict[str, object] = {
            "reference_price": reference_price,
            "intraday_comment_ids": intraday_comment_ids,
        }
        updated_at = raw_entry.get("updated_at")
        if isinstance(updated_at, str) and updated_at.strip():
            pending_entry["updated_at"] = updated_at
        pending[date_text] = pending_entry
    return pending


def _store_pending_watch_close_session(
    state: dict,
    guild_id: int,
    symbol: str,
    *,
    session_date: str,
    reference_price: float,
    intraday_comment_ids: list[int],
    updated_at: str,
) -> None:
    if reference_price <= 0 or not session_date:
        return
    alert_entry = get_watch_session_alert(state, guild_id, symbol)
    pending = _pending_watch_close_sessions(alert_entry)
    existing_entry = pending.get(session_date, {})
    existing_intraday_ids = {
        int(message_id)
        for message_id in existing_entry.get("intraday_comment_ids", [])
        if isinstance(message_id, int)
    }
    merged_intraday_ids = sorted(existing_intraday_ids | {int(message_id) for message_id in intraday_comment_ids})
    pending[session_date] = {
        "reference_price": float(reference_price),
        "intraday_comment_ids": merged_intraday_ids,
        "updated_at": updated_at,
    }
    alert_entry[WATCH_PENDING_CLOSE_SESSIONS_KEY] = pending


def _clear_pending_watch_close_session(
    state: dict,
    guild_id: int,
    symbol: str,
    session_date: str,
    *,
    updated_at: str | None = None,
) -> None:
    alert_entry = get_watch_session_alert(state, guild_id, symbol)
    pending = _pending_watch_close_sessions(alert_entry)
    pending.pop(session_date, None)
    if pending:
        alert_entry[WATCH_PENDING_CLOSE_SESSIONS_KEY] = pending
    else:
        alert_entry.pop(WATCH_PENDING_CLOSE_SESSIONS_KEY, None)
    if updated_at is not None:
        alert_entry["updated_at"] = updated_at


def _is_stale_pending_watch_close_session(symbol: str, snapshot: WatchSnapshot, target_session_date: str) -> bool:
    if snapshot.session_date <= target_session_date:
        return False
    return not is_adjacent_watch_session_date(
        symbol,
        previous_session_date=target_session_date,
        next_session_date=snapshot.session_date,
    )


def _current_watch_close_target(
    state: dict,
    guild_id: int,
    symbol: str,
    alert_entry: dict[str, object],
) -> tuple[str, float, list[int]] | None:
    active_session_date = str(alert_entry.get("active_session_date") or "").strip()
    last_finalized_session_date = str(alert_entry.get("last_finalized_session_date") or "").strip()
    if not active_session_date or active_session_date == last_finalized_session_date:
        return None
    reference_snapshot = get_watch_reference_snapshot(state, guild_id, symbol)
    if reference_snapshot is None:
        return None
    target_session_date = str(reference_snapshot.get("session_date") or "")
    if target_session_date != active_session_date:
        return None
    reference_price = float(reference_snapshot.get("reference_price") or 0.0)
    if reference_price <= 0:
        return None
    intraday_comment_ids = [
        int(message_id)
        for message_id in alert_entry.get("intraday_comment_ids", [])
        if isinstance(message_id, int)
    ]
    return active_session_date, reference_price, intraday_comment_ids


def _watch_close_finalization_due_time(symbol: str) -> tuple[int, int] | None:
    market_prefix = symbol.split(":", maxsplit=1)[0].upper()
    return WATCH_CLOSE_FINALIZATION_DUE_TIMES.get(market_prefix)


def _is_watch_close_finalization_due(symbol: str, now: datetime) -> bool:
    due_time = _watch_close_finalization_due_time(symbol)
    if due_time is None:
        return False
    kst_now = now.astimezone(WATCH_CLOSE_FINALIZATION_TIMEZONE)
    return (kst_now.hour, kst_now.minute) == due_time


def _watch_poll_target_symbols(state: dict, guild_id: int) -> tuple[list[str], list[str]]:
    active_symbols = list_active_watch_symbols(state, guild_id)
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


def _is_invalid_watch_symbol_error(exc: RuntimeError) -> bool:
    message = str(exc)
    return message.startswith("unsupported-market:")


def _resolve_watch_close_price(symbol: str, snapshot: WatchSnapshot, target_session_date: str) -> float | None:
    if snapshot.session_date == target_session_date and snapshot.session_close_price is not None:
        return snapshot.session_close_price
    if (
        snapshot.session_date > target_session_date
        and snapshot.previous_close > 0
        and is_adjacent_watch_session_date(
            symbol,
            previous_session_date=target_session_date,
            next_session_date=snapshot.session_date,
        )
    ):
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


async def _delete_watch_current_comment(
    thread: discord.Thread,
    state: dict,
    *,
    guild_id: int,
    symbol: str,
) -> None:
    alert_entry = get_watch_session_alert(state, guild_id, symbol)
    current_comment_id = alert_entry.get("current_comment_id")
    if not isinstance(current_comment_id, int):
        return
    try:
        current_comment = await thread.fetch_message(current_comment_id)
        await current_comment.delete()
    except discord.NotFound:
        pass
    except (discord.Forbidden, discord.HTTPException) as exc:
        logger.warning(
            "[intel] watch current comment cleanup skipped guild=%s symbol=%s message_id=%s detail=%s",
            guild_id,
            symbol,
            current_comment_id,
            exc,
        )
    clear_watch_current_comment_id(state, guild_id, symbol)


async def _upsert_watch_current_comment(
    thread: discord.Thread,
    state: dict,
    *,
    guild_id: int,
    symbol: str,
    content: str,
    force_recreate: bool,
) -> discord.Message:
    alert_entry = get_watch_session_alert(state, guild_id, symbol)
    current_comment_id = alert_entry.get("current_comment_id")
    current_comment = None

    if isinstance(current_comment_id, int):
        try:
            current_comment = await thread.fetch_message(current_comment_id)
        except discord.NotFound:
            clear_watch_current_comment_id(state, guild_id, symbol)
            current_comment = None

    if current_comment is not None and force_recreate:
        try:
            await current_comment.delete()
        except discord.NotFound:
            pass
        except (discord.Forbidden, discord.HTTPException) as exc:
            logger.warning(
                "[intel] watch current comment recreate cleanup skipped guild=%s symbol=%s message_id=%s detail=%s",
                guild_id,
                symbol,
                current_comment_id,
                exc,
            )
        clear_watch_current_comment_id(state, guild_id, symbol)
        current_comment = None

    if current_comment is None:
        current_comment = await thread.send(content)
    else:
        await current_comment.edit(content=content)

    set_watch_current_comment_id(state, guild_id, symbol, current_comment.id)
    return current_comment


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
    target_session_date: str | None = None,
    reference_price: float | None = None,
    intraday_comment_ids: list[int] | None = None,
    delete_current_comment: bool = True,
    clear_current_intraday_ids: bool = True,
) -> bool:
    if target_session_date is None or reference_price is None:
        reference_snapshot = get_watch_reference_snapshot(state, guild_id, symbol)
        if reference_snapshot is None:
            return False
        reference_price = float(reference_snapshot.get("reference_price") or 0.0)
        target_session_date = str(reference_snapshot.get("session_date") or "")
    if reference_price <= 0 or not target_session_date:
        return False

    close_price = _resolve_watch_close_price(symbol, snapshot, target_session_date)
    if close_price is None:
        return False

    handle = await upsert_watch_thread(
        client=client,
        state=state,
        guild_id=guild_id,
        forum_channel_id=forum_channel_id,
        symbol=symbol,
        active=active,
        starter_text=render_blank_watch_starter(),
    )
    if delete_current_comment:
        await _delete_watch_current_comment(handle.thread, state, guild_id=guild_id, symbol=symbol)
    alert_entry = get_watch_session_alert(state, guild_id, symbol)
    if intraday_comment_ids is None:
        intraday_comment_ids = [
            message_id
            for message_id in alert_entry.get("intraday_comment_ids", [])
            if isinstance(message_id, int)
        ]
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
        if clear_current_intraday_ids:
            update_watch_session_alert(
                state,
                guild_id,
                symbol,
                intraday_comment_ids=remaining_intraday_comment_ids,
                updated_at=now.isoformat(),
            )
        else:
            _store_pending_watch_close_session(
                state,
                guild_id,
                symbol,
                session_date=target_session_date,
                reference_price=reference_price,
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
    if clear_current_intraday_ids:
        update_watch_session_alert(
            state,
            guild_id,
            symbol,
            intraday_comment_ids=[],
            close_comment_ids_by_session=close_comment_ids_by_session,
            updated_at=now.isoformat(),
        )
    else:
        update_watch_session_alert(
            state,
            guild_id,
            symbol,
            close_comment_ids_by_session=close_comment_ids_by_session,
            updated_at=now.isoformat(),
        )
        _clear_pending_watch_close_session(state, guild_id, symbol, target_session_date)
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


async def _finalize_pending_watch_close_sessions(
    client: discord.Client,
    state: dict,
    *,
    now: datetime,
    guild_id: int,
    forum_channel_id: int,
    symbol: str,
    snapshot: WatchSnapshot,
    active: bool,
    alert_entry: dict[str, object],
) -> tuple[int, int]:
    finalized_count = 0
    dropped_count = 0
    pending_close_sessions = _pending_watch_close_sessions(alert_entry)
    for target_session_date, pending_entry in sorted(pending_close_sessions.items()):
        if _is_stale_pending_watch_close_session(symbol, snapshot, target_session_date):
            logger.warning(
                "[intel] watch pending close dropped after adjacency lost guild=%s symbol=%s target_session=%s snapshot_session=%s",
                guild_id,
                symbol,
                target_session_date,
                snapshot.session_date,
            )
            _clear_pending_watch_close_session(
                state,
                guild_id,
                symbol,
                target_session_date,
                updated_at=now.isoformat(),
            )
            save_state(state)
            dropped_count += 1
            continue
        if await _finalize_watch_session(
            client,
            state,
            now=now,
            guild_id=guild_id,
            forum_channel_id=forum_channel_id,
            symbol=symbol,
            snapshot=snapshot,
            active=active,
            target_session_date=target_session_date,
            reference_price=float(pending_entry.get("reference_price") or 0.0),
            intraday_comment_ids=[
                int(message_id)
                for message_id in pending_entry.get("intraday_comment_ids", [])
                if isinstance(message_id, int)
            ],
            delete_current_comment=False,
            clear_current_intraday_ids=False,
        ):
            finalized_count += 1
    return finalized_count, dropped_count


async def _run_watch_poll(client: discord.Client, now: datetime) -> None:
    state = load_state()
    active_symbols_count = 0
    updated_threads = 0
    updated_current_comments = 0
    finalized_sessions = 0
    dropped_pending_close_sessions = 0
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
            try:
                market_session = get_watch_market_session(symbol, now)
            except RuntimeError as exc:
                if not _is_invalid_watch_symbol_error(exc):
                    raise
                logger.debug(
                    "[intel] watch warm skipped invalid symbol guild=%s symbol=%s detail=%s",
                    guild_id,
                    symbol,
                    exc,
                )
                continue
            alert_entry = get_watch_session_alert(state, guild_id, symbol)
            needs_finalization = _has_unfinalized_watch_session(alert_entry)
            close_finalization_due = _is_watch_close_finalization_due(symbol, now)
            if market_session.is_regular_session_open and symbol in active_symbols:
                warm_symbols.add(symbol)
            elif needs_finalization and close_finalization_due:
                warm_symbols.add(symbol)

    warm_watch_snapshots = getattr(quote_provider, "warm_watch_snapshots", None)
    if warm_symbols and callable(warm_watch_snapshots):
        try:
            await warm_watch_snapshots(sorted(warm_symbols), now)
        except Exception as exc:
            logger.exception("[intel] watch warm snapshots failed: %s", exc)

    for guild_id, forum_channel_id, active_symbols, symbols in pending_guilds:
        for symbol in symbols:
            try:
                market_session = get_watch_market_session(symbol, now)
            except RuntimeError as exc:
                if not _is_invalid_watch_symbol_error(exc):
                    raise
                logger.warning(
                    "[intel] watch symbol skipped guild=%s symbol=%s detail=%s",
                    guild_id,
                    symbol,
                    exc,
                )
                snapshot_failures += 1
                continue
            alert_entry = get_watch_session_alert(state, guild_id, symbol)
            needs_finalization = _has_unfinalized_watch_session(alert_entry)
            close_finalization_due = _is_watch_close_finalization_due(symbol, now)
            if market_session.is_regular_session_open and symbol in active_symbols:
                pass
            else:
                if not needs_finalization or not close_finalization_due:
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
                        if not close_finalization_due:
                            _store_pending_watch_close_session(
                                state,
                                guild_id,
                                symbol,
                                session_date=reference_session_date,
                                reference_price=float(reference_snapshot.get("reference_price") or 0.0),
                                intraday_comment_ids=[
                                    message_id
                                    for message_id in alert_entry.get("intraday_comment_ids", [])
                                    if isinstance(message_id, int)
                                ],
                                updated_at=now.isoformat(),
                            )
                        else:
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

                    current_comment_text = render_watch_current_comment(
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
                        starter_text=render_blank_watch_starter(),
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
                    persisted_highest_up_band = current_highest_up_band
                    persisted_highest_down_band = current_highest_down_band
                    band_comment_posted = False
                    if event is not None:
                        try:
                            comment = await handle.thread.send(
                                render_band_comment(
                                    symbol,
                                    direction=event.direction,
                                    band=event.band,
                                    change_pct=event.change_pct,
                                    updated_at=snapshot.asof,
                                )
                            )
                        except Exception as exc:
                            logger.exception("[intel] watch band comment failed guild=%s symbol=%s: %s", guild_id, symbol, exc)
                            comment_failures += 1
                        else:
                            intraday_comment_ids.append(comment.id)
                            persisted_highest_up_band = highest_up_band
                            persisted_highest_down_band = highest_down_band
                            band_comment_posted = True
                            update_watch_session_alert(
                                state,
                                guild_id,
                                symbol,
                                highest_up_band=persisted_highest_up_band,
                                highest_down_band=persisted_highest_down_band,
                                intraday_comment_ids=intraday_comment_ids,
                                updated_at=now.isoformat(),
                            )
                            save_state(state)
                    try:
                        await _upsert_watch_current_comment(
                            handle.thread,
                            state,
                            guild_id=guild_id,
                            symbol=symbol,
                            content=current_comment_text,
                            force_recreate=band_comment_posted,
                        )
                    except Exception as exc:
                        logger.exception("[intel] watch current comment update failed guild=%s symbol=%s: %s", guild_id, symbol, exc)
                        comment_failures += 1
                    else:
                        updated_current_comments += 1
                        update_watch_session_alert(
                            state,
                            guild_id,
                            symbol,
                            highest_up_band=persisted_highest_up_band,
                            highest_down_band=persisted_highest_down_band,
                            intraday_comment_ids=intraday_comment_ids,
                            updated_at=now.isoformat(),
                        )
                        save_state(state)
                except Exception as exc:
                    logger.exception("[intel] watch comment/state update failed guild=%s symbol=%s: %s", guild_id, symbol, exc)
                    comment_failures += 1
                continue

            if needs_finalization:
                if not close_finalization_due:
                    continue
                try:
                    pending_finalized, pending_dropped = await _finalize_pending_watch_close_sessions(
                        client,
                        state,
                        now=now,
                        guild_id=guild_id,
                        forum_channel_id=forum_channel_id,
                        symbol=symbol,
                        snapshot=snapshot,
                        active=symbol in active_symbols,
                        alert_entry=alert_entry,
                    )
                    finalized_sessions += pending_finalized
                    dropped_pending_close_sessions += pending_dropped
                    alert_entry = get_watch_session_alert(state, guild_id, symbol)
                    current_target = _current_watch_close_target(state, guild_id, symbol, alert_entry)
                    if current_target is None:
                        continue
                    target_session_date, reference_price, intraday_comment_ids = current_target
                    finalized = await _finalize_watch_session(
                        client,
                        state,
                        now=now,
                        guild_id=guild_id,
                        forum_channel_id=forum_channel_id,
                        symbol=symbol,
                        snapshot=snapshot,
                        active=symbol in active_symbols,
                        target_session_date=target_session_date,
                        reference_price=reference_price,
                        intraday_comment_ids=intraday_comment_ids,
                    )
                except Exception as exc:
                    logger.exception("[intel] watch finalization failed guild=%s symbol=%s: %s", guild_id, symbol, exc)
                    comment_failures += 1
                    continue
                if finalized:
                    finalized_sessions += 1

    detail = (
        f"active_symbols={active_symbols_count} updated_threads={updated_threads} "
        f"updated_current_comments={updated_current_comments} finalized_sessions={finalized_sessions} "
        f"dropped_pending_close_sessions={dropped_pending_close_sessions} "
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
    last_dashboard_alert_run: datetime | None = None
    last_dashboard_news_run: datetime | None = None
    last_dashboard_report_run: datetime | None = None
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
            state = load_state()
            if INSTRUMENT_REGISTRY_REFRESH_ENABLED:
                if registry_refresh_task is None and _should_start_instrument_registry_refresh(
                    state,
                    now,
                    refresh_hour=registry_h,
                    refresh_minute=registry_m,
                ):
                    logger.info("[intel] instrument_registry_refresh status=started scheduled_for=%02d:%02d", registry_h, registry_m)
                    registry_refresh_task = asyncio.create_task(_refresh_instrument_registry())
            if NEWS_BRIEFING_ENABLED and _should_run_daily_job(
                state,
                now,
                job_key="news_briefing",
                scheduled_hour=news_h,
                scheduled_minute=news_m,
            ):
                await _run_news_job(client, now)
            if EOD_SUMMARY_ENABLED and _should_run_daily_job(
                state,
                now,
                job_key="eod_summary",
                scheduled_hour=eod_h,
                scheduled_minute=eod_m,
            ):
                await _run_eod_job(client, now)

            if STOCK_DASHBOARD_ALERT_DELIVERY_ENABLED:
                if (
                    last_dashboard_alert_run is None
                    or (now - last_dashboard_alert_run).total_seconds() >= STOCK_DASHBOARD_ALERT_POLL_INTERVAL_SECONDS
                ):
                    await _run_dashboard_alert_delivery(client, now)
                    last_dashboard_alert_run = now

            if STOCK_DASHBOARD_NEWS_DELIVERY_ENABLED:
                if (
                    last_dashboard_news_run is None
                    or (now - last_dashboard_news_run).total_seconds() >= STOCK_DASHBOARD_NEWS_POLL_INTERVAL_SECONDS
                ):
                    await _run_dashboard_news_delivery(client, now)
                    last_dashboard_news_run = now

            if STOCK_DASHBOARD_REPORT_DELIVERY_ENABLED:
                if (
                    last_dashboard_report_run is None
                    or (now - last_dashboard_report_run).total_seconds() >= STOCK_DASHBOARD_REPORT_POLL_INTERVAL_SECONDS
                ):
                    await _run_dashboard_report_delivery(client, now)
                    last_dashboard_report_run = now

            if WATCH_FEATURE_ENABLED and WATCH_POLL_ENABLED:
                if last_watch_run is None or (now - last_watch_run).total_seconds() >= WATCH_POLL_INTERVAL_SECONDS:
                    await _run_watch_poll(client, now)
                    last_watch_run = now
        except Exception as exc:
            state = load_state()
            set_job_last_run(state, "intel_scheduler", "failed", str(exc))
            save_state(state)
            logger.exception("[intel] scheduler error: %s", exc)
        await asyncio.sleep(15)
