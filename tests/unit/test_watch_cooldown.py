from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.features.watch import service


KST = ZoneInfo("Asia/Seoul")


def test_watch_cooldown_separate_keys(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    now = datetime(2026, 2, 13, 9, 0, tzinfo=KST)

    monkeypatch.setattr(service, "now_kst", lambda: now)
    ok_up, direction_up, _ = service.evaluate_watch_signal(state, 1, "005930", 100.0, 104.0)
    assert ok_up is True
    assert direction_up == "up"

    monkeypatch.setattr(service, "now_kst", lambda: now + timedelta(minutes=1))
    ok_up_2, _, _ = service.evaluate_watch_signal(state, 1, "005930", 100.0, 104.5)
    assert ok_up_2 is False

    monkeypatch.setattr(service, "now_kst", lambda: now + timedelta(minutes=2))
    ok_down, direction_down, _ = service.evaluate_watch_signal(state, 1, "005930", 100.0, 95.0)
    assert ok_down is True
    assert direction_down == "down"
