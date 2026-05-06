import asyncio
import copy
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from bot.features import intel_scheduler
from tests.state_store_adapter import patch_legacy_state_store
from bot.intel.instrument_registry import InstrumentRecord, InstrumentRegistry, ProviderIds
from bot.intel.providers.market import EodRow, EodSummary
from bot.intel.providers.news import CollectedNewsArticle

KST = ZoneInfo("Asia/Seoul")


def _article(now: datetime, *, url: str = "https://news.example.com/a") -> CollectedNewsArticle:
    return CollectedNewsArticle(
        provider="naver",
        region="domestic",
        title="수집 기사",
        description="설명",
        url=url,
        canonical_url=url,
        source="news.example.com",
        published_at=now,
        query="경제",
        raw_payload={"url": url},
    )


def _registry_record(
    canonical_symbol: str,
    *,
    market_code: str,
    ticker_or_code: str,
    display_name_ko: str = "",
    display_name_en: str = "",
) -> InstrumentRecord:
    return InstrumentRecord(
        canonical_symbol=canonical_symbol,
        market_code=market_code,
        ticker_or_code=ticker_or_code,
        display_name_ko=display_name_ko,
        display_name_en=display_name_en,
        aliases=(canonical_symbol, ticker_or_code),
        provider_ids=ProviderIds(kis_exchange_code=market_code),
        source="test",
    )


class FakeForumChannel:
    def __init__(self, guild_id: int):
        self.guild = SimpleNamespace(id=guild_id)


class FakeForumClient:
    def __init__(self, channel):
        self._channel = channel

    def get_channel(self, _channel_id: int):
        return self._channel

    async def fetch_channel(self, _channel_id: int):
        return self._channel


class FailingFetchForumClient:
    def get_channel(self, _channel_id: int):
        return None

    async def fetch_channel(self, _channel_id: int):
        raise RuntimeError("discord api down")


class MixedForumClient:
    def __init__(self, channels_by_id: dict[int, object], failing_ids: set[int]):
        self._channels_by_id = channels_by_id
        self._failing_ids = failing_ids

    def get_channel(self, channel_id: int):
        return self._channels_by_id.get(channel_id)

    async def fetch_channel(self, channel_id: int):
        if channel_id in self._failing_ids:
            raise RuntimeError("discord api down")
        return self._channels_by_id.get(channel_id)


@pytest.mark.asyncio
async def test_news_collection_records_provider_failure(monkeypatch):
    state = {"commands": {}, "guilds": {}}

    class FailingProvider:
        async def fetch(self, now):
            raise RuntimeError("boom")

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "news_provider", FailingProvider())

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_collection_job(now)

    runs = state["system"]["job_last_runs"]
    assert runs["news_collection"]["status"] == "failed"
    assert runs["news_collection"]["detail"].startswith("boom kis_news_ranking=disabled")
    assert "news_briefing" not in runs
    assert "trend_briefing" not in runs


@pytest.mark.asyncio
async def test_news_collection_stores_articles_without_news_forum_config(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    articles = [_article(now, url="https://news.example.com/a"), _article(now, url="https://news.example.com/b")]

    class Provider:
        last_fetch_stats = {"fetched": 3, "accepted": 2, "skipped": 1}

        async def fetch(self, now):
            return articles

    async def fail_post(**kwargs):
        raise AssertionError("news collection must not post to Discord")

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "NEWS_PROVIDER_KIND", "naver")
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", fail_post)

    await intel_scheduler._run_news_collection_job(now)

    articles_store = state["system"]["news_articles"]
    runs = state["system"]["job_last_runs"]
    assert len(articles_store) == 2
    assert runs["news_collection"]["status"] == "ok"
    assert runs["news_collection"]["detail"].startswith(
        "provider=naver fetched=3 inserted=2 updated=0 skipped=1 kis_news_ranking=disabled"
    )


@pytest.mark.asyncio
async def test_news_collection_upsert_counts_duplicate_article_key(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    duplicate = _article(now, url="https://news.example.com/duplicate")

    class Provider:
        last_fetch_stats = {"fetched": 2, "accepted": 2, "skipped": 0}

        async def fetch(self, now):
            return [duplicate, duplicate]

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "NEWS_PROVIDER_KIND", "naver")

    await intel_scheduler._run_news_collection_job(now)

    runs = state["system"]["job_last_runs"]
    assert runs["news_collection"]["detail"].startswith(
        "provider=naver fetched=2 inserted=1 updated=1 skipped=0 kis_news_ranking=disabled"
    )
    assert len(state["system"]["news_articles"]) == 1


@pytest.mark.asyncio
async def test_news_collection_uses_watchlist_when_dynamic_ranking_credentials_missing(monkeypatch):
    state = {"commands": {}, "guilds": {}, "system": {"job_last_runs": {}}}
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    seen_universe = {}

    class Provider:
        last_fetch_stats = {"fetched": 0, "accepted": 0, "skipped": 0}

        async def fetch(self, now, *, query_universe=None):
            seen_universe["domestic"] = query_universe.domestic_stock_queries
            seen_universe["global"] = query_universe.global_stock_queries
            return []

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "NEWS_DYNAMIC_RANKING_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "NEWS_DYNAMIC_INCLUDE_OVERSEAS", True)
    monkeypatch.setattr(intel_scheduler, "kis_news_ranking_client", None)
    monkeypatch.setattr(intel_scheduler, "list_guild_ids", lambda: [1])
    monkeypatch.setattr(intel_scheduler, "list_watch_tracked_symbols", lambda guild_id: ["KRX:005930", "NAS:AAPL"])
    monkeypatch.setattr(
        intel_scheduler,
        "load_registry",
        lambda: InstrumentRegistry(
            generated_at="2026-02-13T00:00:00+09:00",
            records=[
                _registry_record("KRX:005930", market_code="KRX", ticker_or_code="005930", display_name_ko="삼성전자"),
                _registry_record("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", display_name_en="Apple"),
            ],
        ),
    )

    await intel_scheduler._run_news_collection_job(now)

    assert seen_universe == {"domestic": ("삼성전자",), "global": ("Apple OR AAPL",)}
    provider_status = state["system"]["provider_status"]["kis_news_ranking"]
    assert provider_status["ok"] is False
    assert provider_status["message"] == "kis-credentials-missing"
    assert "kis_news_ranking=false reason=kis-credentials-missing" in state["system"]["job_last_runs"]["news_collection"]["detail"]


@pytest.mark.asyncio
async def test_news_collection_skips_holiday_before_fetch(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    called = {"fetch": 0}

    class Provider:
        async def fetch(self, now):
            called["fetch"] += 1
            return []

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_TRADING_DAYS_ONLY", True)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (False, None))

    now = datetime(2026, 2, 14, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_collection_job(now)

    assert called["fetch"] == 0
    runs = state["system"]["job_last_runs"]
    assert runs["news_collection"]["status"] == "skipped"
    assert runs["news_collection"]["detail"] == "holiday"


@pytest.mark.asyncio
async def test_news_collection_db_write_failure_records_failed(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)

    class Provider:
        last_fetch_stats = {"fetched": 1, "accepted": 1, "skipped": 0}

        async def fetch(self, now):
            return [_article(now)]

    def fail_upsert(articles, collected_at):
        raise RuntimeError("db down")

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_news_articles", fail_upsert)

    await intel_scheduler._run_news_collection_job(now)

    runs = state["system"]["job_last_runs"]
    assert runs["news_collection"]["status"] == "failed"
    assert runs["news_collection"]["detail"] == "db-write-failed:db down"


@pytest.mark.asyncio
async def test_eod_job_skips_non_trading_day(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (False, None))

    now = datetime(2026, 2, 14, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=object(), now=now)  # type: ignore[arg-type]
    assert state["system"]["job_last_runs"]["eod_summary"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_eod_job_marks_failed_when_all_posts_fail(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    class Provider:
        async def get_summary(self, now):
            return EodSummary(
                date_text="2026-02-13",
                kospi_change_pct=0.82,
                kosdaq_change_pct=-0.27,
                top_gainers=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
                top_losers=[EodRow("068270", "셀트리온", -2.9, 250.1)],
                top_turnover=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
            )

    async def fail_post(**kwargs):
        raise RuntimeError("forum write failed")

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (True, None))
    monkeypatch.setattr(intel_scheduler, "eod_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", fail_post)

    now = datetime(2026, 2, 13, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=object(), now=now)  # type: ignore[arg-type]

    runs = state["system"]["job_last_runs"]
    assert runs["eod_summary"]["status"] == "failed"
    assert "posted=0" in runs["eod_summary"]["detail"]


@pytest.mark.asyncio
async def test_eod_job_marks_failed_when_any_guild_post_fails(monkeypatch):
    state = {
        "commands": {},
        "guilds": {
            "1": {"forum_channel_id": 123},
            "2": {"forum_channel_id": 456},
        },
    }

    class Provider:
        async def get_summary(self, now):
            return EodSummary(
                date_text="2026-02-13",
                kospi_change_pct=0.82,
                kosdaq_change_pct=-0.27,
                top_gainers=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
                top_losers=[EodRow("068270", "셀트리온", -2.9, 250.1)],
                top_turnover=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
            )

    async def flaky_post(**kwargs):
        if kwargs["guild_id"] == 2:
            raise RuntimeError("forum write failed")
        return None

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (True, None))
    monkeypatch.setattr(intel_scheduler, "eod_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", flaky_post)

    now = datetime(2026, 2, 13, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=object(), now=now)  # type: ignore[arg-type]

    runs = state["system"]["job_last_runs"]
    assert runs["eod_summary"]["status"] == "failed"
    assert "posted=1 failed=1" in runs["eod_summary"]["detail"]
    assert state["guilds"]["1"]["last_auto_runs"]["eodsummary"] == "2026-02-13"
    assert "last_auto_runs" not in state["guilds"]["2"]


@pytest.mark.asyncio
async def test_eod_job_keeps_ok_status_when_later_tick_has_only_missing_forums(monkeypatch):
    state = {
        "commands": {},
        "guilds": {
            "1": {"forum_channel_id": 123},
            "2": {},
        },
    }

    class Provider:
        async def get_summary(self, now):
            return EodSummary(
                date_text="2026-02-13",
                kospi_change_pct=0.82,
                kosdaq_change_pct=-0.27,
                top_gainers=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
                top_losers=[EodRow("068270", "셀트리온", -2.9, 250.1)],
                top_turnover=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
            )

    async def ok_post(**kwargs):
        return None

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (True, None))
    monkeypatch.setattr(intel_scheduler, "eod_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", ok_post)

    now = datetime(2026, 2, 13, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=object(), now=now)  # type: ignore[arg-type]

    first = state["system"]["job_last_runs"]["eod_summary"].copy()

    await intel_scheduler._run_eod_job(client=object(), now=now)  # type: ignore[arg-type]

    second = state["system"]["job_last_runs"]["eod_summary"]
    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert "no-target-forums" not in second["detail"]


@pytest.mark.asyncio
async def test_eod_job_skips_global_fallback_forum_from_other_guild(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {}}}
    called = {"summary": 0}

    class Provider:
        async def get_summary(self, now):
            called["summary"] += 1
            return EodSummary(
                date_text="2026-02-13",
                kospi_change_pct=0.82,
                kosdaq_change_pct=-0.27,
                top_gainers=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
                top_losers=[EodRow("068270", "셀트리온", -2.9, 250.1)],
                top_turnover=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
            )

    monkeypatch.setattr(intel_scheduler.discord, "ForumChannel", FakeForumChannel)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (True, None))
    monkeypatch.setattr(intel_scheduler, "eod_provider", Provider())

    now = datetime(2026, 2, 13, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=FakeForumClient(FakeForumChannel(guild_id=2)), now=now)

    assert called["summary"] == 0
    run = state["system"]["job_last_runs"]["eod_summary"]
    assert run["status"] == "skipped"
    assert "missing_forum=1" in run["detail"]


@pytest.mark.asyncio
async def test_eod_job_fails_when_forum_resolution_api_errors(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 999}}}
    called = {"summary": 0}

    class Provider:
        async def get_summary(self, now):
            called["summary"] += 1
            return EodSummary(
                date_text="2026-02-13",
                kospi_change_pct=0.82,
                kosdaq_change_pct=-0.27,
                top_gainers=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
                top_losers=[EodRow("068270", "셀트리온", -2.9, 250.1)],
                top_turnover=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
            )

    monkeypatch.setattr(intel_scheduler.discord, "ForumChannel", FakeForumChannel)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (True, None))
    monkeypatch.setattr(intel_scheduler, "eod_provider", Provider())

    now = datetime(2026, 2, 13, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=FailingFetchForumClient(), now=now)

    assert called["summary"] == 0
    run = state["system"]["job_last_runs"]["eod_summary"]
    assert run["status"] == "failed"
    assert run["detail"] == "forum-resolution-failed count=1 missing_forum=0"


@pytest.mark.asyncio
async def test_eod_job_skips_holiday_before_forum_resolution_errors(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 999}}}
    called = {"summary": 0}

    class Provider:
        async def get_summary(self, now):
            called["summary"] += 1
            return EodSummary(
                date_text="2026-02-13",
                kospi_change_pct=0.82,
                kosdaq_change_pct=-0.27,
                top_gainers=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
                top_losers=[EodRow("068270", "셀트리온", -2.9, 250.1)],
                top_turnover=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
            )

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (False, None))
    monkeypatch.setattr(intel_scheduler, "eod_provider", Provider())

    now = datetime(2026, 2, 14, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=FailingFetchForumClient(), now=now)

    assert called["summary"] == 0
    run = state["system"]["job_last_runs"]["eod_summary"]
    assert run["status"] == "skipped"
    assert run["detail"] == "holiday"


@pytest.mark.asyncio
async def test_eod_job_continues_after_one_forum_resolution_api_error(monkeypatch):
    state = {
        "commands": {},
        "guilds": {
            "1": {"forum_channel_id": 123},
            "2": {"forum_channel_id": 999},
        },
    }

    class Provider:
        async def get_summary(self, now):
            return EodSummary(
                date_text="2026-02-13",
                kospi_change_pct=0.82,
                kosdaq_change_pct=-0.27,
                top_gainers=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
                top_losers=[EodRow("068270", "셀트리온", -2.9, 250.1)],
                top_turnover=[EodRow("005930", "삼성전자", 4.2, 1300.5)],
            )

    async def ok_post(**kwargs):
        return None

    monkeypatch.setattr(intel_scheduler.discord, "ForumChannel", FakeForumChannel)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (True, None))
    monkeypatch.setattr(intel_scheduler, "eod_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", ok_post)

    client = MixedForumClient({123: FakeForumChannel(guild_id=1)}, {999})
    now = datetime(2026, 2, 13, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=client, now=now)

    run = state["system"]["job_last_runs"]["eod_summary"]
    assert run["status"] == "failed"
    assert "posted=1 failed=1" in run["detail"]
    assert "forum_resolution_failures=1" in run["detail"]
    assert state["guilds"]["1"]["last_auto_runs"]["eodsummary"] == "2026-02-13"
    assert "last_auto_runs" not in state["guilds"]["2"]


def test_build_market_data_provider_returns_error_provider_when_kis_credentials_missing(monkeypatch):
    monkeypatch.setattr(intel_scheduler, "MARKET_DATA_PROVIDER_KIND", "kis")
    monkeypatch.setattr(intel_scheduler, "KIS_APP_KEY", "")
    monkeypatch.setattr(intel_scheduler, "KIS_APP_SECRET", "")

    provider = intel_scheduler._build_market_data_provider()

    assert provider.__class__.__name__ == "ErrorMarketDataProvider"


def test_build_market_data_provider_wraps_kis_with_massive_fallback(monkeypatch):
    monkeypatch.setattr(intel_scheduler, "MARKET_DATA_PROVIDER_KIND", "kis")
    monkeypatch.setattr(intel_scheduler, "KIS_APP_KEY", "key")
    monkeypatch.setattr(intel_scheduler, "KIS_APP_SECRET", "secret")
    monkeypatch.setattr(intel_scheduler, "MASSIVE_API_KEY", "massive-key")

    provider = intel_scheduler._build_market_data_provider()

    assert provider.__class__.__name__ == "RoutedMarketDataProvider"
    assert provider.us_fallback_provider is not None


@pytest.mark.asyncio
async def test_instrument_registry_refresh_records_success_and_runtime_source(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    saved: dict[str, object] = {}

    previous_registry = InstrumentRegistry(
        generated_at="2026-03-22T00:00:00+00:00",
        records=(
            InstrumentRecord(
                canonical_symbol="KRX:005930",
                market_code="KRX",
                ticker_or_code="005930",
                display_name_ko="삼성전자",
                display_name_en="Samsung Electronics",
                aliases=("삼성전자", "Samsung Electronics", "005930", "KRX:005930"),
                provider_ids=ProviderIds(kis_exchange_code="KRX"),
                source="dart",
            ),
        ),
        metadata={"active_source": "bundled"},
    )
    refreshed_registry = InstrumentRegistry(
        generated_at="2026-03-23T00:00:00+00:00",
        records=(
            InstrumentRecord(
                canonical_symbol="KRX:005930",
                market_code="KRX",
                ticker_or_code="005930",
                display_name_ko="삼성전자",
                display_name_en="Samsung Electronics",
                aliases=("삼성전자", "Samsung Electronics", "005930", "KRX:005930"),
                provider_ids=ProviderIds(kis_exchange_code="KRX"),
                source="dart",
            ),
            InstrumentRecord(
                canonical_symbol="KRX:58L002",
                market_code="KRX",
                ticker_or_code="58L002",
                display_name_ko="KBL002삼성전자콜",
                display_name_en="",
                aliases=("KBL002삼성전자콜", "58L002", "KRX:58L002"),
                provider_ids=ProviderIds(kis_exchange_code="KRX"),
                source="krx-elw",
            ),
        ),
        metadata={"active_source": "runtime"},
    )

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "load_registry", lambda: previous_registry)
    monkeypatch.setattr(intel_scheduler, "build_live_registry", lambda dart_api_key: refreshed_registry)
    monkeypatch.setattr(intel_scheduler, "DART_API_KEY", "dart-key")

    def fake_save_registry(registry, path):
        saved["registry"] = registry
        saved["path"] = path

    monkeypatch.setattr(intel_scheduler, "save_registry", fake_save_registry)

    now = datetime(2026, 2, 13, 6, 20, tzinfo=KST)
    await intel_scheduler._run_instrument_registry_refresh(now)

    run = state["system"]["job_last_runs"]["instrument_registry_refresh"]
    assert run["status"] == "ok"
    assert run["detail"] == "source=runtime loaded=2 added=1 removed=0"
    provider = state["system"]["provider_status"]["instrument_registry"]
    assert provider["ok"] is True
    assert provider["message"] == "source=runtime loaded=2 added=1 removed=0"
    assert saved["path"] == intel_scheduler.RUNTIME_REGISTRY_FILE


@pytest.mark.asyncio
async def test_instrument_registry_refresh_keeps_active_registry_when_rebuild_fails(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    save_calls = {"count": 0}
    active_registry = InstrumentRegistry(
        generated_at="2026-03-23T00:00:00+00:00",
        records=(
            InstrumentRecord(
                canonical_symbol="KRX:005930",
                market_code="KRX",
                ticker_or_code="005930",
                display_name_ko="삼성전자",
                display_name_en="Samsung Electronics",
                aliases=("삼성전자", "Samsung Electronics", "005930", "KRX:005930"),
                provider_ids=ProviderIds(kis_exchange_code="KRX"),
                source="dart",
            ),
        ),
        metadata={"active_source": "bundled"},
    )

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "load_registry", lambda: active_registry)
    monkeypatch.setattr(
        intel_scheduler,
        "build_live_registry",
        lambda dart_api_key: (_ for _ in ()).throw(RuntimeError("dart-api-key-missing")),
    )
    monkeypatch.setattr(
        intel_scheduler,
        "registry_status",
        lambda: {
            "status": "ok",
            "message": "source=bundled loaded=15649 krx=8131 nas=4248 nys=3270 ams=0",
            "updated_at": "2026-03-23T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(intel_scheduler, "DART_API_KEY", "")

    def fake_save_registry(*args, **kwargs):
        save_calls["count"] += 1

    monkeypatch.setattr(intel_scheduler, "save_registry", fake_save_registry)

    now = datetime(2026, 2, 13, 6, 20, tzinfo=KST)
    await intel_scheduler._run_instrument_registry_refresh(now)

    assert save_calls["count"] == 0
    run = state["system"]["job_last_runs"]["instrument_registry_refresh"]
    assert run["status"] == "failed"
    assert "dart-api-key-missing" in run["detail"]
    assert "source=bundled loaded=15649" in run["detail"]
    provider = state["system"]["provider_status"]["instrument_registry"]
    assert provider["ok"] is False
    assert "source=bundled loaded=15649" in provider["message"]


def test_should_start_instrument_registry_refresh_retries_after_failed_same_day(monkeypatch):
    now = datetime(2026, 2, 13, 6, 21, tzinfo=KST)
    state = {
        "system": {
            "job_last_runs": {
                "instrument_registry_refresh": {
                    "status": "failed",
                    "detail": "temporary upstream outage",
                    "run_at": "2026-02-13T06:20:03+09:00",
                }
            }
        }
    }
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)

    should_run = intel_scheduler._should_start_instrument_registry_refresh(
        now,
        refresh_hour=6,
        refresh_minute=20,
    )

    assert should_run is True


def test_should_start_instrument_registry_refresh_catches_up_after_late_start(monkeypatch):
    patch_legacy_state_store(monkeypatch, intel_scheduler, {"system": {"job_last_runs": {}}})

    should_run = intel_scheduler._should_start_instrument_registry_refresh(
        datetime(2026, 2, 13, 6, 21, tzinfo=KST),
        refresh_hour=6,
        refresh_minute=20,
    )

    assert should_run is True


def test_should_start_instrument_registry_refresh_does_not_retry_same_minute_or_missing_dart_key(monkeypatch):
    same_minute = datetime(2026, 2, 13, 6, 20, 30, tzinfo=KST)
    state = {
        "system": {
            "job_last_runs": {
                "instrument_registry_refresh": {
                    "status": "failed",
                    "detail": "dart-api-key-missing",
                    "run_at": "2026-02-13T06:20:03+09:00",
                }
            }
        }
    }
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)

    should_run_same_minute = intel_scheduler._should_start_instrument_registry_refresh(
        same_minute,
        refresh_hour=6,
        refresh_minute=20,
    )
    should_run_missing_key_later = intel_scheduler._should_start_instrument_registry_refresh(
        datetime(2026, 2, 13, 6, 21, tzinfo=KST),
        refresh_hour=6,
        refresh_minute=20,
    )

    assert should_run_same_minute is False
    assert should_run_missing_key_later is False


def test_should_run_daily_job_catches_up_after_late_start(monkeypatch):
    patch_legacy_state_store(monkeypatch, intel_scheduler, {"system": {"job_last_runs": {}}})

    should_run = intel_scheduler._should_run_daily_job(
        datetime(2026, 2, 13, 7, 31, tzinfo=KST),
        job_key="news_collection",
        scheduled_hour=7,
        scheduled_minute=30,
    )

    assert should_run is True


def test_should_run_daily_job_skips_before_time_and_after_same_day_attempt(monkeypatch):
    state = {
        "system": {
            "job_last_runs": {
                "news_collection": {
                    "status": "ok",
                    "detail": "provider=mock fetched=2 inserted=2 updated=0 skipped=0",
                    "run_at": "2026-02-13T07:31:05+09:00",
                }
            }
        }
    }
    patch_legacy_state_store(monkeypatch, intel_scheduler, {"system": {"job_last_runs": {}}})

    should_run_before_time = intel_scheduler._should_run_daily_job(
        datetime(2026, 2, 13, 7, 29, tzinfo=KST),
        job_key="news_collection",
        scheduled_hour=7,
        scheduled_minute=30,
    )
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    should_run_after_attempt = intel_scheduler._should_run_daily_job(
        datetime(2026, 2, 13, 7, 45, tzinfo=KST),
        job_key="news_collection",
        scheduled_hour=7,
        scheduled_minute=30,
    )

    assert should_run_before_time is False
    assert should_run_after_attempt is False


@pytest.mark.asyncio
async def test_intel_scheduler_runs_registry_refresh_once_at_configured_time(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    refresh_calls = {"count": 0}
    now = datetime(2026, 2, 13, 6, 20, tzinfo=KST)
    original_sleep = intel_scheduler.asyncio.sleep

    class StopLoop(BaseException):
        pass

    async def fake_refresh():
        refresh_calls["count"] += 1
        return {"source": "runtime", "loaded": 1, "added": 0, "removed": 0}

    async def stop_sleep(_seconds):
        await original_sleep(0)
        raise StopLoop()

    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_TIME", "06:20")
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "now_kst", lambda: now)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "_refresh_instrument_registry", fake_refresh)
    monkeypatch.setattr(intel_scheduler.asyncio, "sleep", stop_sleep)

    with pytest.raises(StopLoop):
        await intel_scheduler.intel_scheduler(client=object())  # type: ignore[arg-type]

    assert refresh_calls["count"] == 1


@pytest.mark.asyncio
async def test_intel_scheduler_does_not_restart_registry_refresh_after_same_day_success(monkeypatch):
    persisted_state = {"commands": {}, "guilds": {}, "system": {"job_last_runs": {}}}
    refresh_calls = {"count": 0}
    now = datetime(2026, 2, 13, 6, 20, tzinfo=KST)
    original_sleep = intel_scheduler.asyncio.sleep
    sleep_calls = {"count": 0}

    class StopLoop(BaseException):
        pass

    async def fake_refresh():
        refresh_calls["count"] += 1
        return {"source": "runtime", "loaded": 1, "added": 0, "removed": 0}

    def fake_load_state():
        return copy.deepcopy(persisted_state)

    def fake_save_state(state):
        persisted_state.clear()
        persisted_state.update(copy.deepcopy(state))

    async def stop_sleep(_seconds):
        sleep_calls["count"] += 1
        await original_sleep(0)
        if sleep_calls["count"] >= 2:
            raise StopLoop()

    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_TIME", "06:20")
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "now_kst", lambda: now)
    monkeypatch.setattr("bot.common.clock.now_kst", lambda: now)
    patch_legacy_state_store(monkeypatch, intel_scheduler, fake_load_state, fake_save_state)
    monkeypatch.setattr(intel_scheduler, "_refresh_instrument_registry", fake_refresh)
    monkeypatch.setattr(intel_scheduler.asyncio, "sleep", stop_sleep)

    with pytest.raises(StopLoop):
        await intel_scheduler.intel_scheduler(client=object())  # type: ignore[arg-type]

    assert refresh_calls["count"] == 1
    assert persisted_state["system"]["job_last_runs"]["instrument_registry_refresh"]["status"] == "ok"


@pytest.mark.asyncio
async def test_intel_scheduler_catches_up_news_collection_after_late_start(monkeypatch):
    state = {"commands": {}, "guilds": {}, "system": {"job_last_runs": {}}}
    news_calls: list[datetime] = []
    now = datetime(2026, 2, 13, 7, 31, tzinfo=KST)
    original_sleep = intel_scheduler.asyncio.sleep

    class StopLoop(BaseException):
        pass

    async def fake_news_job(run_now):
        news_calls.append(run_now)

    async def stop_sleep(_seconds):
        await original_sleep(0)
        raise StopLoop()

    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_TIME", "07:30")
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "now_kst", lambda: now)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "_run_news_collection_job", fake_news_job)
    monkeypatch.setattr(intel_scheduler.asyncio, "sleep", stop_sleep)

    with pytest.raises(StopLoop):
        await intel_scheduler.intel_scheduler(client=object())  # type: ignore[arg-type]

    assert news_calls == [now]


@pytest.mark.asyncio
async def test_intel_scheduler_runs_news_collection_close_slot(monkeypatch):
    state = {
        "commands": {},
        "guilds": {},
        "system": {
            "job_last_runs": {
                "news_collection": {
                    "status": "ok",
                    "detail": "morning",
                    "run_at": "2026-02-13T07:31:00+09:00",
                }
            }
        },
    }
    calls: list[str] = []
    now = datetime(2026, 2, 13, 16, 11, tzinfo=KST)
    original_sleep = intel_scheduler.asyncio.sleep

    class StopLoop(BaseException):
        pass

    async def fake_news_job(run_now, *, job_key=intel_scheduler.NEWS_COLLECTION_JOB_KEY):
        calls.append(job_key)

    async def stop_sleep(_seconds):
        await original_sleep(0)
        raise StopLoop()

    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_TIME", "07:30")
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_CLOSE_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_CLOSE_TIME", "16:10")
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "now_kst", lambda: now)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "_run_news_collection_job", fake_news_job)
    monkeypatch.setattr(intel_scheduler.asyncio, "sleep", stop_sleep)

    with pytest.raises(StopLoop):
        await intel_scheduler.intel_scheduler(client=object())  # type: ignore[arg-type]

    assert calls == [intel_scheduler.NEWS_COLLECTION_CLOSE_JOB_KEY]


@pytest.mark.asyncio
async def test_intel_scheduler_does_not_rerun_same_day_news_collection_close_success(monkeypatch):
    state = {
        "commands": {},
        "guilds": {},
        "system": {
            "job_last_runs": {
                "news_collection": {
                    "status": "ok",
                    "detail": "morning",
                    "run_at": "2026-02-13T07:31:00+09:00",
                },
                "news_collection_close": {
                    "status": "ok",
                    "detail": "close",
                    "run_at": "2026-02-13T16:11:00+09:00",
                },
            }
        },
    }
    calls: list[str] = []
    now = datetime(2026, 2, 13, 16, 12, tzinfo=KST)
    original_sleep = intel_scheduler.asyncio.sleep

    class StopLoop(BaseException):
        pass

    async def fake_news_job(run_now, *, job_key=intel_scheduler.NEWS_COLLECTION_JOB_KEY):
        calls.append(job_key)

    async def stop_sleep(_seconds):
        await original_sleep(0)
        raise StopLoop()

    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_TIME", "07:30")
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_CLOSE_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_CLOSE_TIME", "16:10")
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "now_kst", lambda: now)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "_run_news_collection_job", fake_news_job)
    monkeypatch.setattr(intel_scheduler.asyncio, "sleep", stop_sleep)

    with pytest.raises(StopLoop):
        await intel_scheduler.intel_scheduler(client=object())  # type: ignore[arg-type]

    assert calls == []


@pytest.mark.asyncio
async def test_intel_scheduler_catches_up_eod_job_after_late_start(monkeypatch):
    state = {"commands": {}, "guilds": {}, "system": {"job_last_runs": {}}}
    eod_calls: list[datetime] = []
    now = datetime(2026, 2, 13, 16, 21, tzinfo=KST)
    original_sleep = intel_scheduler.asyncio.sleep

    class StopLoop(BaseException):
        pass

    async def fake_eod_job(_client, run_now):
        eod_calls.append(run_now)

    async def stop_sleep(_seconds):
        await original_sleep(0)
        raise StopLoop()

    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_TIME", "16:20")
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "now_kst", lambda: now)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "_run_eod_job", fake_eod_job)
    monkeypatch.setattr(intel_scheduler.asyncio, "sleep", stop_sleep)

    with pytest.raises(StopLoop):
        await intel_scheduler.intel_scheduler(client=object())  # type: ignore[arg-type]

    assert eod_calls == [now]


@pytest.mark.asyncio
async def test_intel_scheduler_keeps_watch_poll_running_while_registry_refresh_is_in_flight(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    watch_calls: list[datetime] = []
    refresh_started = asyncio.Event()
    release_refresh = asyncio.Event()
    now = datetime(2026, 2, 13, 6, 20, tzinfo=KST)
    original_sleep = intel_scheduler.asyncio.sleep

    class StopLoop(BaseException):
        pass

    async def fake_refresh():
        refresh_started.set()
        await release_refresh.wait()
        return {"source": "runtime", "loaded": 1, "added": 0, "removed": 0}

    async def fake_watch_poll(_client, run_now):
        watch_calls.append(run_now)

    async def stop_sleep(_seconds):
        await original_sleep(0)
        assert refresh_started.is_set() is True
        assert watch_calls == [now]
        release_refresh.set()
        await original_sleep(0)
        raise StopLoop()

    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_TIME", "06:20")
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_INTERVAL_SECONDS", 60)
    monkeypatch.setattr(intel_scheduler, "now_kst", lambda: now)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "_refresh_instrument_registry", fake_refresh)
    monkeypatch.setattr(intel_scheduler, "_run_watch_poll", fake_watch_poll)
    monkeypatch.setattr(intel_scheduler.asyncio, "sleep", stop_sleep)

    with pytest.raises(StopLoop):
        await intel_scheduler.intel_scheduler(client=object())  # type: ignore[arg-type]

    assert watch_calls == [now]


@pytest.mark.asyncio
async def test_intel_scheduler_runs_us_watch_close_job_during_grace_window(monkeypatch):
    state = {"commands": {}, "guilds": {}, "system": {"job_last_runs": {}}}
    now = datetime(2026, 3, 27, 7, 10, tzinfo=KST)
    close_calls: list[tuple[str, frozenset[str], datetime]] = []
    original_sleep = intel_scheduler.asyncio.sleep

    class StopLoop(BaseException):
        pass

    async def fake_close_job(_client, run_now, *, job_key, market_prefixes):
        close_calls.append((job_key, market_prefixes, run_now))

    async def fake_watch_poll(_client, _run_now):
        return None

    async def stop_sleep(_seconds):
        await original_sleep(0)
        raise StopLoop()

    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "now_kst", lambda: now)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "_run_watch_close_finalization_job", fake_close_job)
    monkeypatch.setattr(intel_scheduler, "_run_watch_poll", fake_watch_poll)
    monkeypatch.setattr(intel_scheduler.asyncio, "sleep", stop_sleep)

    with pytest.raises(StopLoop):
        await intel_scheduler.intel_scheduler(client=object())  # type: ignore[arg-type]

    assert close_calls == [(intel_scheduler.WATCH_CLOSE_US_JOB_KEY, intel_scheduler.WATCH_CLOSE_US_MARKET_PREFIXES, now)]


@pytest.mark.asyncio
async def test_intel_scheduler_runs_krx_watch_close_job_during_grace_window(monkeypatch):
    state = {"commands": {}, "guilds": {}, "system": {"job_last_runs": {}}}
    now = datetime(2026, 3, 26, 16, 10, tzinfo=KST)
    close_calls: list[tuple[str, frozenset[str], datetime]] = []
    original_sleep = intel_scheduler.asyncio.sleep

    class StopLoop(BaseException):
        pass

    async def fake_close_job(_client, run_now, *, job_key, market_prefixes):
        close_calls.append((job_key, market_prefixes, run_now))

    async def fake_watch_poll(_client, _run_now):
        return None

    async def stop_sleep(_seconds):
        await original_sleep(0)
        raise StopLoop()

    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "now_kst", lambda: now)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "_run_watch_close_finalization_job", fake_close_job)
    monkeypatch.setattr(intel_scheduler, "_run_watch_poll", fake_watch_poll)
    monkeypatch.setattr(intel_scheduler.asyncio, "sleep", stop_sleep)

    with pytest.raises(StopLoop):
        await intel_scheduler.intel_scheduler(client=object())  # type: ignore[arg-type]

    assert close_calls == [(intel_scheduler.WATCH_CLOSE_KRX_JOB_KEY, intel_scheduler.WATCH_CLOSE_KRX_MARKET_PREFIXES, now)]


@pytest.mark.asyncio
async def test_intel_scheduler_skips_watch_close_job_after_grace_window(monkeypatch):
    state = {"commands": {}, "guilds": {}, "system": {"job_last_runs": {}}}
    now = datetime(2026, 3, 27, 7, 31, tzinfo=KST)
    close_calls: list[str] = []
    original_sleep = intel_scheduler.asyncio.sleep

    class StopLoop(BaseException):
        pass

    async def fake_close_job(_client, _run_now, *, job_key, market_prefixes):
        close_calls.append(job_key)

    async def fake_watch_poll(_client, _run_now):
        return None

    async def stop_sleep(_seconds):
        await original_sleep(0)
        raise StopLoop()

    monkeypatch.setattr(intel_scheduler, "INSTRUMENT_REGISTRY_REFRESH_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "NEWS_COLLECTION_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "EOD_SUMMARY_ENABLED", False)
    monkeypatch.setattr(intel_scheduler, "WATCH_POLL_ENABLED", True)
    monkeypatch.setattr(intel_scheduler, "now_kst", lambda: now)
    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "_run_watch_close_finalization_job", fake_close_job)
    monkeypatch.setattr(intel_scheduler, "_run_watch_poll", fake_watch_poll)
    monkeypatch.setattr(intel_scheduler.asyncio, "sleep", stop_sleep)

    with pytest.raises(StopLoop):
        await intel_scheduler.intel_scheduler(client=object())  # type: ignore[arg-type]

    assert close_calls == []
