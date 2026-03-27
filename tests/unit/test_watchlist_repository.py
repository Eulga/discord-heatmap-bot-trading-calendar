from bot.forum import repository


def test_watchlist_add_remove_list():
    state = {"commands": {}, "guilds": {}}

    assert repository.add_watch_symbol(state, 1, "005930") is True
    assert repository.add_watch_symbol(state, 1, "005930") is False
    assert repository.list_watch_symbols(state, 1) == ["KRX:005930"]
    assert repository.list_active_watch_symbols(state, 1) == ["KRX:005930"]

    repository.set_watch_symbol_thread_status(state, 1, "005930", "inactive")
    assert repository.get_watch_symbol_status(state, 1, "005930") == "inactive"
    assert repository.list_active_watch_symbols(state, 1) == []

    assert repository.delete_watch_symbol(state, 1, "005930") is True
    assert repository.delete_watch_symbol(state, 1, "005930") is False
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


def test_watch_delete_clears_runtime_state_and_watch_state():
    state = {
        "commands": {
            "watchpoll": {
                "symbol_threads_by_guild": {
                    "1": {
                        "KRX:005930": {"thread_id": 1001, "starter_message_id": 1002, "status": "inactive"},
                    }
                }
            }
        },
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
            },
            "watch_reference_snapshots": {
                "1": {
                    "KRX:005930": {
                        "basis": "previous_close",
                        "reference_price": 70000.0,
                        "session_date": "2026-03-27",
                        "checked_at": "2026-03-27T09:00:00+09:00",
                    }
                }
            },
            "watch_session_alerts": {
                "1": {
                    "KRX:005930": {
                        "active_session_date": "2026-03-27",
                        "highest_up_band": 1,
                        "intraday_comment_ids": [2001],
                        "close_comment_ids_by_session": {},
                    }
                }
            },
        },
    }

    assert repository.delete_watch_symbol(state, 1, "005930") is True
    assert repository.list_watch_symbols(state, 1) == []
    assert state["guilds"]["1"]["watch_alert_cooldowns"] == {"NAS:AAPL:down": "2026-02-13T09:10:00+09:00"}
    assert state["guilds"]["1"]["watch_alert_latches"] == {"NAS:AAPL": "up"}
    assert state["system"]["watch_baselines"]["1"] == {
        "NAS:AAPL": {"price": 214.0, "checked_at": "2026-02-13T09:10:00+09:00"}
    }
    assert state["commands"]["watchpoll"]["symbol_threads_by_guild"]["1"] == {}
    assert state["system"]["watch_reference_snapshots"]["1"] == {}
    assert state["system"]["watch_session_alerts"]["1"] == {}


def test_watch_state_stores_watch_forum_and_symbol_thread_registry():
    state = {"commands": {}, "guilds": {}}

    repository.set_guild_watch_forum_channel_id(state, 1, 456)
    repository.set_watch_symbol_thread(
        state,
        1,
        "005930",
        thread_id=1001,
        starter_message_id=1002,
        status="active",
    )

    assert repository.get_guild_watch_forum_channel_id(state, 1) == 456
    assert repository.get_watch_symbol_thread(state, 1, "KRX:005930") == {
        "thread_id": 1001,
        "starter_message_id": 1002,
        "status": "active",
    }
    assert repository.list_watch_tracked_symbols(state, 1) == ["KRX:005930"]


def test_watch_thread_status_can_exist_without_thread_ids():
    state = {"commands": {}, "guilds": {"1": {"watchlist": ["KRX:005930"]}}}

    repository.set_watch_symbol_thread_status(state, 1, "005930", "inactive")

    assert repository.get_watch_symbol_thread(state, 1, "KRX:005930") == {"status": "inactive"}
    assert repository.get_watch_symbol_status(state, 1, "KRX:005930") == "inactive"
    assert repository.list_active_watch_symbols(state, 1) == []


def test_watch_state_stores_reference_snapshot_and_session_alerts_without_seeding_from_legacy_state():
    state = {
        "commands": {},
        "guilds": {
            "1": {
                "watch_alert_cooldowns": {"KRX:005930:down": "2026-02-13T09:00:00+09:00"},
                "watch_alert_latches": {"KRX:005930": "down"},
            }
        },
        "system": {
            "watch_baselines": {
                "1": {
                    "KRX:005930": {"price": 70000.0, "checked_at": "2026-02-13T09:00:00+09:00"},
                }
            }
        },
    }

    repository.set_watch_reference_snapshot(
        state,
        1,
        "KRX:005930",
        basis="previous_close",
        reference_price=73100.0,
        session_date="2026-03-26",
        checked_at="2026-03-26T09:01:00+09:00",
    )
    repository.update_watch_session_alert(
        state,
        1,
        "KRX:005930",
        active_session_date="2026-03-26",
        highest_up_band=2,
        intraday_comment_ids=[2001],
        close_comment_ids_by_session={"2026-03-25": 1901},
        updated_at="2026-03-26T10:11:00+09:00",
    )

    assert repository.get_watch_reference_snapshot(state, 1, "005930") == {
        "basis": "previous_close",
        "reference_price": 73100.0,
        "session_date": "2026-03-26",
        "checked_at": "2026-03-26T09:01:00+09:00",
    }
    assert repository.get_watch_session_alert(state, 1, "005930") == {
        "active_session_date": "2026-03-26",
        "highest_up_band": 2,
        "highest_down_band": 0,
        "intraday_comment_ids": [2001],
        "close_comment_ids_by_session": {"2026-03-25": 1901},
        "updated_at": "2026-03-26T10:11:00+09:00",
    }
