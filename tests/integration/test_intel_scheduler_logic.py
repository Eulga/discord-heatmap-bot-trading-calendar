from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from bot.features import intel_scheduler

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
