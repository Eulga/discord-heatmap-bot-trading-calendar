from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from bot.features import intel_scheduler
from bot.intel.providers.market import EodRow, EodSummary
from bot.intel.providers.news import NewsItem

KST = ZoneInfo("Asia/Seoul")


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

    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    await intel_scheduler._run_news_job(client=object(), now=now)  # type: ignore[arg-type]

    assert called["fetch"] == 0
    runs = state["system"]["job_last_runs"]
    assert runs["news_briefing"]["status"] == "skipped"
    assert "no-target-forums" in runs["news_briefing"]["detail"]


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
        captured["body_text"] = kwargs["body_text"]

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

    assert "한국 수출지표 개선 기대" in captured["body_text"]
    assert captured["body_text"].count("한국 수출지표 개선 기대") == 1
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
