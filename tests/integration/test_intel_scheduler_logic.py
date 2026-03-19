from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from bot.features import intel_scheduler
from bot.intel.providers.market import EodRow, EodSummary
from bot.intel.providers.news import NewsAnalysis, NewsItem, ThemeBrief, TrendThemeReport

KST = ZoneInfo("Asia/Seoul")


def _theme_brief(region: str, name: str, now: datetime, base_url: str) -> ThemeBrief:
    return ThemeBrief(
        theme_name=name,
        region=region,
        score=44,
        reason_tags=("기사 4건", "3개 소스"),
        representative_items=(
            NewsItem(f"{name} 기사 1", f"{base_url}/1", f"{name.lower()}-source-1.com", now, region),
            NewsItem(f"{name} 기사 2", f"{base_url}/2", f"{name.lower()}-source-2.com", now, region),
        ),
        article_count=4,
        source_count=3,
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


@pytest.mark.asyncio
async def test_news_job_records_provider_failure(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    class FailingProvider:
        async def fetch(self, now):
            raise RuntimeError("boom")

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", FailingProvider())

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    runs = state["system"]["job_last_runs"]
    assert runs["news_briefing"]["status"] == "failed"


@pytest.mark.asyncio
async def test_eod_job_skips_non_trading_day(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (False, None))

    now = datetime(2026, 2, 14, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=object(), now=now)  # type: ignore[arg-type]
    assert state["system"]["job_last_runs"]["eod_summary"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_news_job_skips_when_no_target_forum(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {}}}
    called = {"fetch": 0}

    class Provider:
        async def fetch(self, now):
            called["fetch"] += 1
            return []

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "NEWS_TARGET_FORUM_ID", None)

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    assert called["fetch"] == 0
    runs = state["system"]["job_last_runs"]
    assert runs["news_briefing"]["status"] == "skipped"
    assert "no-target-forums" in runs["news_briefing"]["detail"]


@pytest.mark.asyncio
async def test_news_job_skips_global_fallback_forum_from_other_guild(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {}}}
    called = {"fetch": 0}

    class Provider:
        async def fetch(self, now):
            called["fetch"] += 1
            return []

    monkeypatch.setattr(intel_scheduler.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "NEWS_TARGET_FORUM_ID", 999)

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=FakeForumClient(FakeForumChannel(guild_id=2)), now=now)

    assert called["fetch"] == 0
    runs = state["system"]["job_last_runs"]
    assert runs["news_briefing"]["status"] == "skipped"
    assert "missing_forum=1" in runs["news_briefing"]["detail"]
    assert runs["trend_briefing"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_news_job_retries_same_items_after_post_failure(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    class Provider:
        async def fetch(self, now):
            return [
                NewsItem("한국 수출지표 개선 기대", "https://example.com/kr-export", "MockNewsKR", now, "domestic"),
                NewsItem("한국 수출지표 개선 기대", "https://example.com/kr-export", "MockNewsKR", now, "domestic"),
            ]

    captured: dict[str, str] = {}

    async def fail_post(**kwargs):
        raise RuntimeError("discord unavailable")

    async def ok_post(**kwargs):
        captured[kwargs["command_key"]] = kwargs["body_text"]

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", fail_post)

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    runs = state["system"]["job_last_runs"]
    assert runs["news_briefing"]["status"] == "failed"
    assert "newsbriefing" not in state["guilds"]["1"].get("last_auto_runs", {})

    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", ok_post)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    assert "한국 수출지표 개선 기대" in captured["newsbriefing-domestic"]
    assert captured["newsbriefing-domestic"].count("한국 수출지표 개선 기대") == 1
    assert "(데이터 없음)" in captured["newsbriefing-global"]
    assert state["guilds"]["1"]["last_auto_runs"]["newsbriefing"] == "2026-02-13"
    assert state["system"]["job_last_runs"]["news_briefing"]["status"] == "ok"


@pytest.mark.asyncio
async def test_news_job_keeps_ok_status_when_later_tick_has_only_missing_forums(monkeypatch):
    state = {
        "commands": {},
        "guilds": {
            "1": {"forum_channel_id": 123},
            "2": {},
        },
    }

    class Provider:
        async def fetch(self, now):
            return [NewsItem("한국 수출지표 개선 기대", "https://example.com/kr-export", "MockNewsKR", now, "domestic")]

    async def ok_post(**kwargs):
        return None

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", ok_post)

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    first = state["system"]["job_last_runs"]["news_briefing"].copy()

    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    second = state["system"]["job_last_runs"]["news_briefing"]
    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert "no-target-forums" not in second["detail"]


@pytest.mark.asyncio
async def test_news_job_uses_configured_limit_per_region(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    class Provider:
        async def fetch(self, now):
            domestic = [
                NewsItem(
                    f"D{index}",
                    f"https://e.co/d{index}",
                    f"d{index}.co",
                    now,
                    "domestic",
                )
                for index in range(25)
            ]
            global_items = [
                NewsItem(
                    f"G{index}",
                    f"https://e.co/g{index}",
                    f"g{index}.co",
                    now,
                    "global",
                )
                for index in range(23)
            ]
            return domestic + global_items

    captured: dict[str, str] = {}

    async def ok_post(**kwargs):
        captured[kwargs["command_key"]] = kwargs["body_text"]

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", ok_post)
    monkeypatch.setattr(intel_scheduler, "NAVER_NEWS_LIMIT_PER_REGION", 20)

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    assert state["system"]["job_last_runs"]["news_briefing"]["status"] == "ok"
    assert "domestic=20 global=20" in state["system"]["job_last_runs"]["news_briefing"]["detail"]

    domestic_body = captured["newsbriefing-domestic"]
    global_body = captured["newsbriefing-global"]
    assert "[국내]" in domestic_body
    assert "[해외]" not in domestic_body
    assert "[해외]" in global_body
    assert "[국내]" not in global_body
    assert domestic_body.count("\n- ") + domestic_body.startswith("- ") == 20
    assert global_body.count("\n- ") + global_body.startswith("- ") == 20


@pytest.mark.asyncio
async def test_news_job_dedups_same_story_across_regions(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    class Provider:
        async def fetch(self, now):
            return [
                NewsItem(
                    "엔비디아 수출 규제에 삼성전자·SK하이닉스 영향",
                    "https://example.com/story-1",
                    "example.com",
                    now,
                    "domestic",
                ),
                NewsItem(
                    "엔비디아 수출 규제에 삼성전자·SK하이닉스 영향",
                    "https://example.com/story-1",
                    "example.com",
                    now,
                    "global",
                ),
            ]

    captured: dict[str, str] = {}

    async def ok_post(**kwargs):
        captured[kwargs["command_key"]] = kwargs["body_text"]

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", ok_post)

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    combined = captured["newsbriefing-domestic"] + "\n" + captured["newsbriefing-global"]
    assert combined.count("엔비디아 수출 규제에 삼성전자·SK하이닉스 영향") == 1


@pytest.mark.asyncio
async def test_news_job_posts_domestic_and_global_threads_separately(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    class Provider:
        async def fetch(self, now):
            return [
                NewsItem("국내 기사", "https://example.com/domestic-1", "example.com", now, "domestic"),
                NewsItem("해외 기사", "https://example.com/global-1", "example.com", now, "global"),
            ]

    calls: list[tuple[str, str, str]] = []

    async def ok_post(**kwargs):
        calls.append((kwargs["command_key"], kwargs["post_title"], kwargs["body_text"]))

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", ok_post)

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    assert [call[0] for call in calls] == ["newsbriefing-domestic", "newsbriefing-global"]
    assert calls[0][1] == "[2026-02-13 국내 경제 뉴스 브리핑]"
    assert calls[1][1] == "[2026-02-13 해외 경제 뉴스 브리핑]"
    assert "[국내]" in calls[0][2]
    assert "[해외]" in calls[1][2]


@pytest.mark.asyncio
async def test_news_job_posts_trendbriefing_with_content_messages(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    class Provider:
        async def analyze(self, now):
            return NewsAnalysis(
                briefing_items=(
                    NewsItem("국내 기사", "https://example.com/domestic-1", "example.com", now, "domestic"),
                    NewsItem("해외 기사", "https://example.com/global-1", "example.com", now, "global"),
                ),
                trend_report=TrendThemeReport(
                    generated_at=now,
                    themes_by_region={
                        "domestic": (
                            _theme_brief("domestic", "반도체", now, "https://example.com/semi"),
                            _theme_brief("domestic", "건설/원전", now, "https://example.com/nuke"),
                            _theme_brief("domestic", "전력설비", now, "https://example.com/power"),
                        ),
                        "global": (
                            _theme_brief("global", "AI/반도체", now, "https://example.com/ai"),
                            _theme_brief("global", "금리/Fed", now, "https://example.com/fed"),
                            _theme_brief("global", "에너지/원유", now, "https://example.com/oil"),
                        ),
                    },
                ),
            )

    calls: list[dict] = []

    async def ok_post(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", ok_post)

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    assert [call["command_key"] for call in calls] == [
        "newsbriefing-domestic",
        "newsbriefing-global",
        "trendbriefing",
    ]
    trend_call = calls[2]
    assert trend_call["post_title"] == "[2026-02-13 트렌드 테마 뉴스]"
    assert "국내 테마 3개 | 해외 테마 3개" in trend_call["body_text"]
    assert len(trend_call["content_texts"]) == 2
    assert trend_call["content_texts"][0].startswith("[국내 트렌드 테마]")
    assert trend_call["content_texts"][1].startswith("[해외 트렌드 테마]")
    assert state["system"]["job_last_runs"]["trend_briefing"]["status"] == "ok"


@pytest.mark.asyncio
async def test_news_job_skips_trendbriefing_when_both_regions_are_below_minimum(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    class Provider:
        async def analyze(self, now):
            return NewsAnalysis(
                briefing_items=(
                    NewsItem("국내 기사", "https://example.com/domestic-1", "example.com", now, "domestic"),
                    NewsItem("해외 기사", "https://example.com/global-1", "example.com", now, "global"),
                ),
                trend_report=TrendThemeReport(
                    generated_at=now,
                    themes_by_region={
                        "domestic": (
                            _theme_brief("domestic", "반도체", now, "https://example.com/semi"),
                            _theme_brief("domestic", "건설/원전", now, "https://example.com/nuke"),
                        ),
                        "global": (
                            _theme_brief("global", "AI/반도체", now, "https://example.com/ai"),
                        ),
                    },
                ),
            )

    calls: list[dict] = []

    async def ok_post(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", ok_post)

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    assert [call["command_key"] for call in calls] == ["newsbriefing-domestic", "newsbriefing-global"]
    assert state["system"]["job_last_runs"]["trend_briefing"]["status"] == "skipped"
    assert state["guilds"]["1"]["last_auto_skips"]["trendbriefing"]["date"] == "2026-02-13"


@pytest.mark.asyncio
async def test_news_job_uses_placeholder_for_region_below_minimum_when_other_region_qualifies(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}

    class Provider:
        async def analyze(self, now):
            return NewsAnalysis(
                briefing_items=(
                    NewsItem("국내 기사", "https://example.com/domestic-1", "example.com", now, "domestic"),
                    NewsItem("해외 기사", "https://example.com/global-1", "example.com", now, "global"),
                ),
                trend_report=TrendThemeReport(
                    generated_at=now,
                    themes_by_region={
                        "domestic": (
                            _theme_brief("domestic", "반도체", now, "https://example.com/semi"),
                            _theme_brief("domestic", "자동차", now, "https://example.com/auto"),
                        ),
                        "global": (
                            _theme_brief("global", "AI/반도체", now, "https://example.com/ai"),
                            _theme_brief("global", "금리/Fed", now, "https://example.com/fed"),
                            _theme_brief("global", "에너지/원유", now, "https://example.com/oil"),
                        ),
                    },
                ),
            )

    calls: list[dict] = []

    async def ok_post(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "news_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", ok_post)

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    trend_call = calls[2]
    assert "국내 테마 0개 | 해외 테마 3개" in trend_call["body_text"]
    assert trend_call["content_texts"][0] == "[국내 트렌드 테마]\n- (유의미한 테마 부족)"
    assert trend_call["content_texts"][1].startswith("[해외 트렌드 테마]")


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

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (True, None))
    monkeypatch.setattr(intel_scheduler, "eod_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "upsert_daily_post", fail_post)

    now = datetime(2026, 2, 13, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=object(), now=now)  # type: ignore[arg-type]

    runs = state["system"]["job_last_runs"]
    assert runs["eod_summary"]["status"] == "failed"
    assert "posted=0" in runs["eod_summary"]["detail"]


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

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
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
    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "safe_check_krx_trading_day", lambda now: (True, None))
    monkeypatch.setattr(intel_scheduler, "eod_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "EOD_TARGET_FORUM_ID", 999)

    now = datetime(2026, 2, 13, 16, 20, tzinfo=KST)
    await intel_scheduler._run_eod_job(client=FakeForumClient(FakeForumChannel(guild_id=2)), now=now)

    assert called["summary"] == 0
    run = state["system"]["job_last_runs"]["eod_summary"]
    assert run["status"] == "skipped"
    assert "missing_forum=1" in run["detail"]


class FakeMessageable:
    async def send(self, message: str) -> None:
        raise NotImplementedError


class FakeWatchChannel(FakeMessageable):
    def __init__(self, guild_id: int):
        self.guild = SimpleNamespace(id=guild_id)
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


class FakeFailingWatchChannel(FakeMessageable):
    def __init__(self, guild_id: int):
        self.guild = SimpleNamespace(id=guild_id)

    async def send(self, message: str) -> None:
        raise RuntimeError("send denied")


class FakeWatchClient:
    def __init__(self, channel):
        self._channel = channel

    def get_channel(self, _channel_id: int):
        return self._channel

    async def fetch_channel(self, _channel_id: int):
        return self._channel


@pytest.mark.asyncio
async def test_watch_poll_fails_when_fallback_channel_belongs_to_other_guild(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"watchlist": ["005930"]}}}
    quote_calls = {"count": 0}

    class Provider:
        async def get_quote(self, symbol, now):
            quote_calls["count"] += 1
            return SimpleNamespace(price=73100.0)

    monkeypatch.setattr(intel_scheduler.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "WATCH_ALERT_CHANNEL_ID", 999)

    now = datetime(2026, 2, 13, 10, 0, tzinfo=KST)
    await intel_scheduler._run_watch_poll(client=FakeWatchClient(FakeWatchChannel(guild_id=2)), now=now)

    assert quote_calls["count"] == 0
    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "failed"
    assert "channel_failures=1" in run["detail"]


@pytest.mark.asyncio
async def test_watch_poll_marks_failed_when_all_quotes_fail(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"watchlist": ["005930"], "watch_alert_channel_id": 123}}}

    class Provider:
        async def get_quote(self, symbol, now):
            raise RuntimeError("quote provider down")

    monkeypatch.setattr(intel_scheduler.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "WATCH_ALERT_CHANNEL_ID", None)

    now = datetime(2026, 2, 13, 10, 0, tzinfo=KST)
    await intel_scheduler._run_watch_poll(client=FakeWatchClient(FakeWatchChannel(guild_id=1)), now=now)

    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "failed"
    assert "quote_failures=1" in run["detail"]
    provider = state["system"]["provider_status"]["market_data_provider"]
    assert provider["ok"] is False
    assert provider["message"] == "quote provider down"


@pytest.mark.asyncio
async def test_watch_poll_marks_failed_when_alert_delivery_fails(monkeypatch):
    now = datetime(2026, 2, 13, 10, 0, tzinfo=KST)
    state = {
        "commands": {},
        "guilds": {"1": {"watchlist": ["005930"], "watch_alert_channel_id": 123}},
        "system": {
            "watch_baselines": {
                "1": {
                    "005930": {
                        "price": 100.0,
                        "checked_at": now.isoformat(),
                    }
                }
            }
        },
    }

    class Provider:
        async def get_quote(self, symbol, now):
            return SimpleNamespace(price=110.0)

    monkeypatch.setattr(intel_scheduler.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "WATCH_ALERT_CHANNEL_ID", None)

    await intel_scheduler._run_watch_poll(client=FakeWatchClient(FakeFailingWatchChannel(guild_id=1)), now=now)

    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "failed"
    assert "alerts=0" in run["detail"]
    assert "alert_attempts=1" in run["detail"]
    assert "send_failures=1" in run["detail"]
    provider = state["system"]["provider_status"]["market_data_provider"]
    assert provider["ok"] is True
    assert provider["message"] == "quote:005930"


@pytest.mark.asyncio
async def test_watch_poll_marks_failed_when_quote_failure_happens_after_partial_success(monkeypatch):
    state = {
        "commands": {},
        "guilds": {"1": {"watchlist": ["005930", "000660"], "watch_alert_channel_id": 123}},
    }

    class Provider:
        async def get_quote(self, symbol, now):
            if symbol == "005930":
                return SimpleNamespace(price=73100.0)
            raise RuntimeError("quote provider down")

    monkeypatch.setattr(intel_scheduler.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "WATCH_ALERT_CHANNEL_ID", None)

    now = datetime(2026, 2, 13, 10, 0, tzinfo=KST)
    await intel_scheduler._run_watch_poll(client=FakeWatchClient(FakeWatchChannel(guild_id=1)), now=now)

    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "failed"
    assert "processed=1" in run["detail"]
    assert "quote_failures=1" in run["detail"]
