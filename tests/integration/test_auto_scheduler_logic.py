from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from bot.features import auto_scheduler

KST = ZoneInfo("Asia/Seoul")


@pytest.mark.asyncio
async def test_scheduler_runs_when_trading_day(monkeypatch):
    state = {
        "commands": {"kheatmap": {"daily_posts_by_guild": {}, "last_images": {}}},
        "guilds": {"1": {"auto_screenshot_enabled": True}},
    }
    called = {"run": 0}

    def fake_jobs(_now):
        return [("kheatmap", {"kospi": "u"}, object(), object(), object(), 15, 35, lambda _dt: (True, None))]

    async def fake_execute(**kwargs):
        called["run"] += 1
        return True, "ok"

    monkeypatch.setattr(auto_scheduler, "_jobs_for_now", fake_jobs)
    monkeypatch.setattr(auto_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(auto_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(auto_scheduler, "execute_heatmap_for_guild", fake_execute)

    now = datetime(2026, 2, 13, 15, 35, tzinfo=KST)
    await auto_scheduler.process_auto_screenshot_tick(client=object(), now=now)

    assert called["run"] == 1
    assert state["guilds"]["1"]["last_auto_runs"]["kheatmap"] == "2026-02-13"


@pytest.mark.asyncio
async def test_scheduler_skips_on_holiday(monkeypatch, caplog):
    state = {
        "commands": {"kheatmap": {"daily_posts_by_guild": {}, "last_images": {}}},
        "guilds": {"1": {"auto_screenshot_enabled": True}},
    }
    called = {"run": 0}

    def fake_jobs(_now):
        return [("kheatmap", {"kospi": "u"}, object(), object(), object(), 15, 35, lambda _dt: (False, None))]

    async def fake_execute(**kwargs):
        called["run"] += 1
        return True, "ok"

    monkeypatch.setattr(auto_scheduler, "_jobs_for_now", fake_jobs)
    monkeypatch.setattr(auto_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(auto_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(auto_scheduler, "execute_heatmap_for_guild", fake_execute)
    caplog.set_level("INFO", logger=auto_scheduler.logger.name)

    now = datetime(2026, 2, 13, 15, 35, tzinfo=KST)
    await auto_scheduler.process_auto_screenshot_tick(client=object(), now=now)

    assert called["run"] == 0
    assert "reason=holiday" in caplog.text
    assert state["guilds"]["1"]["last_auto_skips"]["kheatmap"]["date"] == "2026-02-13"


@pytest.mark.asyncio
async def test_scheduler_skips_on_calendar_check_failure(monkeypatch, caplog):
    state = {
        "commands": {"usheatmap": {"daily_posts_by_guild": {}, "last_images": {}}},
        "guilds": {"1": {"auto_screenshot_enabled": True}},
    }

    def fake_jobs(_now):
        return [
            (
                "usheatmap",
                {"sp500": "u"},
                object(),
                object(),
                object(),
                6,
                5,
                lambda _dt: (None, "calendar unavailable"),
            )
        ]

    monkeypatch.setattr(auto_scheduler, "_jobs_for_now", fake_jobs)
    monkeypatch.setattr(auto_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(auto_scheduler, "save_state", lambda _state: None)
    caplog.set_level("WARNING", logger=auto_scheduler.logger.name)

    now = datetime(2026, 2, 13, 6, 5, tzinfo=KST)
    await auto_scheduler.process_auto_screenshot_tick(client=object(), now=now)

    assert "calendar-check-failed: calendar unavailable" in caplog.text
    assert state["guilds"]["1"]["last_auto_skips"]["usheatmap"]["reason"].startswith("calendar-check-failed")


@pytest.mark.asyncio
async def test_scheduler_respects_existing_last_auto_run(monkeypatch):
    state = {
        "commands": {"kheatmap": {"daily_posts_by_guild": {}, "last_images": {}}},
        "guilds": {
            "1": {
                "auto_screenshot_enabled": True,
                "last_auto_runs": {"kheatmap": "2026-02-13"},
            }
        },
    }
    called = {"run": 0}

    def fake_jobs(_now):
        return [("kheatmap", {"kospi": "u"}, object(), object(), object(), 15, 35, lambda _dt: (True, None))]

    async def fake_execute(**kwargs):
        called["run"] += 1
        return True, "ok"

    monkeypatch.setattr(auto_scheduler, "_jobs_for_now", fake_jobs)
    monkeypatch.setattr(auto_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(auto_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(auto_scheduler, "execute_heatmap_for_guild", fake_execute)

    now = datetime(2026, 2, 13, 15, 35, tzinfo=KST)
    await auto_scheduler.process_auto_screenshot_tick(client=object(), now=now)

    assert called["run"] == 0


@pytest.mark.asyncio
async def test_scheduler_preserves_runner_saved_daily_post_state(monkeypatch):
    disk = {
        "value": {
            "commands": {"kheatmap": {"daily_posts_by_guild": {}, "last_images": {}}},
            "guilds": {"1": {"auto_screenshot_enabled": True}},
        }
    }

    def load_state():
        return deepcopy(disk["value"])

    def save_state(state):
        disk["value"] = deepcopy(state)

    def fake_jobs(_now):
        return [("kheatmap", {"kospi": "u"}, object(), object(), object(), 15, 35, lambda _dt: (True, None))]

    async def fake_execute(**kwargs):
        inner_state = load_state()
        inner_state["commands"]["kheatmap"]["daily_posts_by_guild"] = {
            "1": {"2026-02-13": {"thread_id": 22, "starter_message_id": 11}}
        }
        save_state(inner_state)
        return True, "ok"

    monkeypatch.setattr(auto_scheduler, "_jobs_for_now", fake_jobs)
    monkeypatch.setattr(auto_scheduler, "load_state", load_state)
    monkeypatch.setattr(auto_scheduler, "save_state", save_state)
    monkeypatch.setattr(auto_scheduler, "execute_heatmap_for_guild", fake_execute)

    now = datetime(2026, 2, 13, 15, 35, tzinfo=KST)
    await auto_scheduler.process_auto_screenshot_tick(client=object(), now=now)

    assert disk["value"]["commands"]["kheatmap"]["daily_posts_by_guild"]["1"]["2026-02-13"] == {
        "thread_id": 22,
        "starter_message_id": 11,
    }
    assert disk["value"]["guilds"]["1"]["last_auto_runs"]["kheatmap"] == "2026-02-13"


@pytest.mark.asyncio
async def test_scheduler_skips_last_auto_run_save_when_refresh_returns_empty(monkeypatch, caplog):
    disk = {
        "value": {
            "commands": {"kheatmap": {"daily_posts_by_guild": {}, "last_images": {}}},
            "guilds": {"1": {"auto_screenshot_enabled": True}},
        }
    }
    calls = {"load": 0, "save": 0}

    def load_state():
        calls["load"] += 1
        if calls["load"] == 3:
            return {"commands": {}, "guilds": {}}
        return deepcopy(disk["value"])

    def save_state(state):
        calls["save"] += 1
        disk["value"] = deepcopy(state)

    def fake_jobs(_now):
        return [("kheatmap", {"kospi": "u"}, object(), object(), object(), 15, 35, lambda _dt: (True, None))]

    async def fake_execute(**kwargs):
        inner_state = load_state()
        inner_state["commands"]["kheatmap"]["daily_posts_by_guild"] = {
            "1": {"2026-02-13": {"thread_id": 22, "starter_message_id": 11}}
        }
        save_state(inner_state)
        return True, "ok"

    monkeypatch.setattr(auto_scheduler, "_jobs_for_now", fake_jobs)
    monkeypatch.setattr(auto_scheduler, "load_state", load_state)
    monkeypatch.setattr(auto_scheduler, "save_state", save_state)
    monkeypatch.setattr(auto_scheduler, "execute_heatmap_for_guild", fake_execute)
    caplog.set_level("WARNING", logger=auto_scheduler.logger.name)

    now = datetime(2026, 2, 13, 15, 35, tzinfo=KST)
    await auto_scheduler.process_auto_screenshot_tick(client=object(), now=now)

    assert disk["value"]["commands"]["kheatmap"]["daily_posts_by_guild"]["1"]["2026-02-13"] == {
        "thread_id": 22,
        "starter_message_id": 11,
    }
    assert "last_auto_runs" not in disk["value"]["guilds"]["1"]
    assert calls["save"] == 1
    assert "state refresh returned empty" in caplog.text
