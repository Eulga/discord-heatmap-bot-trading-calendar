from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.features.watch import service
from bot.forum import repository


KST = ZoneInfo("Asia/Seoul")


def test_watch_cooldown_separate_keys(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    now = datetime(2026, 2, 13, 9, 0, tzinfo=KST)

    monkeypatch.setattr(service, "now_kst", lambda: now)
    ok_up, direction_up, _ = service.evaluate_watch_signal(state, 1, "KRX:005930", 100.0, 104.0)
    assert ok_up is True
    assert direction_up == "up"

    monkeypatch.setattr(service, "now_kst", lambda: now + timedelta(minutes=1))
    ok_up_2, _, _ = service.evaluate_watch_signal(state, 1, "KRX:005930", 100.0, 104.5)
    assert ok_up_2 is False

    monkeypatch.setattr(service, "now_kst", lambda: now + timedelta(minutes=2))
    ok_down, direction_down, _ = service.evaluate_watch_signal(state, 1, "KRX:005930", 100.0, 95.0)
    assert ok_down is True
    assert direction_down == "down"


def test_watch_signal_same_direction_requires_rearm_inside_threshold(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    now = datetime(2026, 2, 13, 9, 0, tzinfo=KST)

    monkeypatch.setattr(service, "now_kst", lambda: now)
    ok_first, direction_first, _ = service.evaluate_watch_signal(state, 1, "KRX:005930", 100.0, 96.0)
    assert ok_first is True
    assert direction_first == "down"

    monkeypatch.setattr(service, "now_kst", lambda: now + timedelta(minutes=11))
    ok_repeat, direction_repeat, _ = service.evaluate_watch_signal(state, 1, "KRX:005930", 100.0, 96.5)
    assert ok_repeat is False
    assert direction_repeat == "down"

    monkeypatch.setattr(service, "now_kst", lambda: now + timedelta(minutes=12))
    ok_reset, direction_reset, _ = service.evaluate_watch_signal(state, 1, "KRX:005930", 100.0, 99.0)
    assert ok_reset is False
    assert direction_reset == ""

    monkeypatch.setattr(service, "now_kst", lambda: now + timedelta(minutes=13))
    ok_rearmed, direction_rearmed, _ = service.evaluate_watch_signal(state, 1, "KRX:005930", 100.0, 96.0)
    assert ok_rearmed is True
    assert direction_rearmed == "down"


def test_watch_signal_readd_starts_fresh_after_remove(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    now = datetime(2026, 2, 13, 9, 0, tzinfo=KST)

    assert repository.add_watch_symbol(state, 1, "005930") is True

    monkeypatch.setattr(service, "now_kst", lambda: now)
    ok_first, direction_first, _ = service.evaluate_watch_signal(state, 1, "KRX:005930", 100.0, 96.0)
    assert ok_first is True
    assert direction_first == "down"

    assert repository.remove_watch_symbol(state, 1, "005930") is True
    assert repository.add_watch_symbol(state, 1, "005930") is True

    monkeypatch.setattr(service, "now_kst", lambda: now + timedelta(minutes=20))
    ok_readded, direction_readded, _ = service.evaluate_watch_signal(state, 1, "KRX:005930", 100.0, 96.0)
    assert ok_readded is True
    assert direction_readded == "down"
