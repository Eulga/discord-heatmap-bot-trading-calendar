from bot.forum import repository


def test_watchlist_add_remove_list():
    state = {"commands": {}, "guilds": {}}

    assert repository.add_watch_symbol(state, 1, "005930") is True
    assert repository.add_watch_symbol(state, 1, "005930") is False
    assert repository.list_watch_symbols(state, 1) == ["KRX:005930"]

    assert repository.remove_watch_symbol(state, 1, "005930") is True
    assert repository.remove_watch_symbol(state, 1, "005930") is False
    assert repository.list_watch_symbols(state, 1) == []


def test_watchlist_migrates_cooldown_and_baseline_keys_to_canonical():
    state = {
        "commands": {},
        "guilds": {
            "1": {
                "watchlist": ["005930"],
                "watch_alert_cooldowns": {"005930:up": "2026-02-13T09:00:00+09:00"},
            }
        },
        "system": {"watch_baselines": {"1": {"005930": {"price": 70000.0, "checked_at": "2026-02-13T09:00:00+09:00"}}}},
    }

    assert repository.list_watch_symbols(state, 1) == ["KRX:005930"]
    assert state["guilds"]["1"]["watch_alert_cooldowns"] == {"KRX:005930:up": "2026-02-13T09:00:00+09:00"}
    assert "KRX:005930" in state["system"]["watch_baselines"]["1"]


def test_watchlist_migrates_latch_keys_to_canonical():
    state = {
        "commands": {},
        "guilds": {
            "1": {
                "watchlist": ["005930"],
                "watch_alert_latches": {"005930": "down"},
            }
        },
    }

    assert repository.list_watch_symbols(state, 1) == ["KRX:005930"]
    assert state["guilds"]["1"]["watch_alert_latches"] == {"KRX:005930": "down"}


def test_watchlist_remove_clears_runtime_state():
    state = {
        "commands": {},
        "guilds": {
            "1": {
                "watchlist": ["KRX:005930"],
                "watch_alert_cooldowns": {
                    "KRX:005930:down": "2026-02-13T09:00:00+09:00",
                    "KRX:005930:up": "2026-02-13T09:05:00+09:00",
                    "NAS:AAPL:down": "2026-02-13T09:10:00+09:00",
                },
                "watch_alert_latches": {
                    "KRX:005930": "down",
                    "NAS:AAPL": "up",
                },
            }
        },
        "system": {
            "watch_baselines": {
                "1": {
                    "KRX:005930": {"price": 70000.0, "checked_at": "2026-02-13T09:00:00+09:00"},
                    "NAS:AAPL": {"price": 214.0, "checked_at": "2026-02-13T09:10:00+09:00"},
                }
            }
        },
    }

    assert repository.remove_watch_symbol(state, 1, "005930") is True
    assert repository.list_watch_symbols(state, 1) == []
    assert state["guilds"]["1"]["watch_alert_cooldowns"] == {"NAS:AAPL:down": "2026-02-13T09:10:00+09:00"}
    assert state["guilds"]["1"]["watch_alert_latches"] == {"NAS:AAPL": "up"}
    assert state["system"]["watch_baselines"]["1"] == {
        "NAS:AAPL": {"price": 214.0, "checked_at": "2026-02-13T09:10:00+09:00"}
    }
