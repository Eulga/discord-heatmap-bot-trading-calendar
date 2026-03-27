from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from bot.features import intel_scheduler
from bot.features.watch import thread_service
from bot.intel.providers import market as market_provider


KST = ZoneInfo("Asia/Seoul")


class FakeNotFound(Exception):
    pass


class FakeMessage:
    def __init__(self, message_id: int, content: str = ""):
        self.id = message_id
        self.content = content
        self.deleted = False

    async def edit(self, content=None, attachments=None):
        if content is not None:
            self.content = content

    async def delete(self):
        self.deleted = True


class FakeThread:
    def __init__(self, thread_id: int, starter_message: FakeMessage, *, guild_id: int = 1, parent_id: int | None = None):
        self.id = thread_id
        self.guild = SimpleNamespace(id=guild_id)
        self.name = "old-title"
        self.parent = None
        self.parent_id = parent_id
        self._messages: dict[int, FakeMessage] = {starter_message.id: starter_message}
        self._starter_message_id = starter_message.id
        self.sent_contents: list[str] = []

    @property
    def starter_message(self) -> FakeMessage:
        return self._messages[self._starter_message_id]

    def add_message(self, message: FakeMessage) -> None:
        self._messages[message.id] = message

    async def fetch_message(self, message_id: int):
        message = self._messages.get(message_id)
        if message is None or message.deleted:
            raise FakeNotFound()
        return message

    async def edit(self, *, name: str):
        self.name = name

    async def send(self, content: str):
        message_id = max(self._messages) + 1
        message = FakeMessage(message_id, content)
        self._messages[message_id] = message
        self.sent_contents.append(content)
        return message

    async def history(self, limit: int = 50):
        visible_messages = [message for message in self._messages.values() if not message.deleted]
        for message in reversed(visible_messages[-limit:]):
            yield message


class FakeForumChannel:
    def __init__(self, channel_id: int, guild_id: int):
        self.id = channel_id
        self.guild = SimpleNamespace(id=guild_id)
        self._threads: dict[int, FakeThread] = {}
        self._next_thread_id = 2000
        self._next_message_id = 3000

    def get_thread(self, thread_id: int):
        thread = self._threads.get(thread_id)
        if thread is None:
            return None
        if thread.parent_id is None:
            thread.parent = self
            thread.parent_id = self.id
        if thread.parent_id != self.id:
            return None
        return thread

    async def create_thread(self, name: str, content: str):
        self._next_thread_id += 1
        self._next_message_id += 1
        starter = FakeMessage(self._next_message_id, content)
        thread = FakeThread(self._next_thread_id, starter, guild_id=self.guild.id)
        thread.name = name
        thread.parent = self
        thread.parent_id = self.id
        self._threads[thread.id] = thread

        class Created:
            def __init__(self, thread, message):
                self.thread = thread
                self.message = message

        return Created(thread, starter)


class FakeClient:
    def __init__(self, forums: dict[int, FakeForumChannel]):
        self._forums = forums

    def get_channel(self, channel_id: int):
        forum = self._forums.get(channel_id)
        if forum is not None:
            return forum
        for forum in self._forums.values():
            thread = forum.get_thread(channel_id)
            if thread is not None:
                return thread
        return None

    async def fetch_channel(self, channel_id: int):
        return self.get_channel(channel_id)


def _patch_discord_types(monkeypatch):
    for module in (thread_service, intel_scheduler):
        monkeypatch.setattr(module.discord, "ForumChannel", FakeForumChannel)
        monkeypatch.setattr(module.discord, "Thread", FakeThread)
        monkeypatch.setattr(module.discord, "NotFound", FakeNotFound)
        monkeypatch.setattr(module.discord, "Forbidden", FakeNotFound)
        monkeypatch.setattr(module.discord, "HTTPException", FakeNotFound)


def _open_snapshot(now: datetime, price: float) -> market_provider.WatchSnapshot:
    return market_provider.WatchSnapshot(
        symbol="KRX:005930",
        current_price=price,
        previous_close=100.0,
        session_close_price=None,
        asof=now,
        session_date="2026-03-26",
        provider="kis_quote",
    )


@pytest.mark.asyncio
async def test_watch_poll_updates_starter_and_posts_highest_new_band_comment(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    state = {"commands": {}, "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}}}

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            return _open_snapshot(now, 107.1)

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    now = datetime(2026, 3, 26, 10, 0, tzinfo=KST)
    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=now)

    thread = next(iter(forum._threads.values()))
    assert "전일 종가: ₩100.00" in thread.starter_message.content
    assert "현재가: ₩107.10" in thread.starter_message.content
    assert "기준 세션" not in thread.starter_message.content
    assert "당일 최고 상승 band" not in thread.starter_message.content
    assert len(thread.sent_contents) == 1
    assert thread.sent_contents[0] == "삼성전자 (KRX:005930) +6% 이상 상승 : +7.10% · 2026-03-26 10:00:00"
    assert state["system"]["provider_status"]["kis_quote"]["message"] == "snapshot:KRX:005930"
    assert state["system"]["job_last_runs"]["watch_poll"]["status"] == "ok"


@pytest.mark.asyncio
async def test_watch_poll_keeps_same_session_highest_band_and_supports_both_active(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    state = {"commands": {}, "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}}}
    snapshots = iter(
        [
            _open_snapshot(datetime(2026, 3, 26, 10, 0, tzinfo=KST), 104.0),
            _open_snapshot(datetime(2026, 3, 26, 10, 1, tzinfo=KST), 104.5),
            _open_snapshot(datetime(2026, 3, 26, 10, 2, tzinfo=KST), 93.8),
        ]
    )

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            return next(snapshots)

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    client = FakeClient({456: forum})
    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 10, 0, tzinfo=KST))
    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 10, 1, tzinfo=KST))
    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 10, 2, tzinfo=KST))

    thread = next(iter(forum._threads.values()))
    assert len(thread.sent_contents) == 2
    assert thread.sent_contents[0] == "삼성전자 (KRX:005930) +3% 이상 상승 : +4.00% · 2026-03-26 10:00:00"
    assert thread.sent_contents[1] == "삼성전자 (KRX:005930) -6% 이상 하락 : -6.20% · 2026-03-26 10:02:00"
    assert "당일 alert status" not in thread.starter_message.content


@pytest.mark.asyncio
async def test_watch_poll_defers_close_finalization_until_session_close_price_is_available(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = FakeThread(2001, starter)
    intraday_one = FakeMessage(3002, "band-1")
    intraday_two = FakeMessage(3003, "band-2")
    thread.add_message(intraday_one)
    thread.add_message(intraday_two)
    forum._threads[thread.id] = thread

    state = {
        "commands": {
            "watchpoll": {
                "daily_posts_by_guild": {},
                "last_images": {},
                "symbol_threads_by_guild": {"1": {"KRX:005930": {"thread_id": 2001, "starter_message_id": 3001, "status": "active"}}},
            }
        },
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}},
        "system": {
            "watch_reference_snapshots": {
                "1": {
                    "KRX:005930": {
                        "basis": "previous_close",
                        "reference_price": 100.0,
                        "session_date": "2026-03-26",
                        "checked_at": "2026-03-26T10:00:00+09:00",
                    }
                }
            },
            "watch_session_alerts": {
                "1": {
                    "KRX:005930": {
                        "active_session_date": "2026-03-26",
                        "highest_up_band": 2,
                        "highest_down_band": 0,
                        "intraday_comment_ids": [3002, 3003],
                        "close_comment_ids_by_session": {},
                    }
                }
            },
        },
    }
    snapshots = iter(
        [
            market_provider.WatchSnapshot(
                symbol="KRX:005930",
                current_price=99.0,
                previous_close=100.0,
                session_close_price=None,
                asof=datetime(2026, 3, 26, 16, 1, tzinfo=KST),
                session_date="2026-03-26",
                provider="kis_quote",
            ),
            market_provider.WatchSnapshot(
                symbol="KRX:005930",
                current_price=99.0,
                previous_close=100.0,
                session_close_price=98.0,
                asof=datetime(2026, 3, 26, 16, 2, tzinfo=KST),
                session_date="2026-03-26",
                provider="kis_quote",
            ),
        ]
    )

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            return next(snapshots)

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    client = FakeClient({456: forum})
    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 16, 1, tzinfo=KST))
    assert intraday_one.deleted is False
    assert intraday_two.deleted is False
    assert "last_finalized_session_date" not in state["system"]["watch_session_alerts"]["1"]["KRX:005930"]

    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 16, 2, tzinfo=KST))
    assert intraday_one.deleted is True
    assert intraday_two.deleted is True
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["last_finalized_session_date"] == "2026-03-26"
    close_comments = [content for content in thread.sent_contents if "마감가 알림" in content]
    assert len(close_comments) == 1


@pytest.mark.asyncio
async def test_watch_poll_finalizes_inactive_symbol_once_before_stopping(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = FakeThread(2001, starter)
    intraday = FakeMessage(3002, "band-1")
    thread.add_message(intraday)
    forum._threads[thread.id] = thread

    state = {
        "commands": {
            "watchpoll": {
                "daily_posts_by_guild": {},
                "last_images": {},
                "symbol_threads_by_guild": {"1": {"KRX:005930": {"thread_id": 2001, "starter_message_id": 3001, "status": "inactive"}}},
            }
        },
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": []}},
        "system": {
            "watch_reference_snapshots": {
                "1": {
                    "KRX:005930": {
                        "basis": "previous_close",
                        "reference_price": 100.0,
                        "session_date": "2026-03-26",
                        "checked_at": "2026-03-26T10:00:00+09:00",
                    }
                }
            },
            "watch_session_alerts": {
                "1": {
                    "KRX:005930": {
                        "active_session_date": "2026-03-26",
                        "highest_up_band": 1,
                        "highest_down_band": 0,
                        "intraday_comment_ids": [3002],
                        "close_comment_ids_by_session": {},
                    }
                }
            },
        },
    }

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            return market_provider.WatchSnapshot(
                symbol="KRX:005930",
                current_price=99.0,
                previous_close=100.0,
                session_close_price=98.0,
                asof=now,
                session_date="2026-03-26",
                provider="kis_quote",
            )

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 26, 16, 5, tzinfo=KST))

    assert intraday.deleted is True
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["last_finalized_session_date"] == "2026-03-26"


@pytest.mark.asyncio
async def test_watch_poll_finalizes_prior_session_before_rotating_to_new_open_session(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = FakeThread(2001, starter, parent_id=456)
    intraday = FakeMessage(3002, "band-1")
    thread.add_message(intraday)
    forum._threads[thread.id] = thread

    state = {
        "commands": {
            "watchpoll": {
                "daily_posts_by_guild": {},
                "last_images": {},
                "symbol_threads_by_guild": {"1": {"KRX:005930": {"thread_id": 2001, "starter_message_id": 3001, "status": "active"}}},
            }
        },
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}},
        "system": {
            "watch_reference_snapshots": {
                "1": {
                    "KRX:005930": {
                        "basis": "previous_close",
                        "reference_price": 100.0,
                        "session_date": "2026-03-26",
                        "checked_at": "2026-03-26T15:30:00+09:00",
                    }
                }
            },
            "watch_session_alerts": {
                "1": {
                    "KRX:005930": {
                        "active_session_date": "2026-03-26",
                        "highest_up_band": 1,
                        "highest_down_band": 0,
                        "intraday_comment_ids": [3002],
                        "close_comment_ids_by_session": {},
                    }
                }
            },
        },
    }

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            return market_provider.WatchSnapshot(
                symbol="KRX:005930",
                current_price=98.4,
                previous_close=98.0,
                session_close_price=None,
                asof=now,
                session_date="2026-03-27",
                provider="kis_quote",
            )

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 27, 10, 0, tzinfo=KST))

    assert intraday.deleted is True
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["last_finalized_session_date"] == "2026-03-26"
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["active_session_date"] == "2026-03-27"
    assert state["system"]["watch_reference_snapshots"]["1"]["KRX:005930"]["session_date"] == "2026-03-27"
    close_comments = [content for content in thread.sent_contents if "마감가 알림" in content]
    assert len(close_comments) == 1
    assert "전일 종가: ₩98.00" in thread.starter_message.content


@pytest.mark.asyncio
async def test_watch_poll_keeps_non_adjacent_unfinalized_session_open(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = FakeThread(2001, starter, parent_id=456)
    intraday = FakeMessage(3002, "band-1")
    thread.add_message(intraday)
    forum._threads[thread.id] = thread

    state = {
        "commands": {
            "watchpoll": {
                "daily_posts_by_guild": {},
                "last_images": {},
                "symbol_threads_by_guild": {"1": {"KRX:005930": {"thread_id": 2001, "starter_message_id": 3001, "status": "active"}}},
            }
        },
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}},
        "system": {
            "watch_reference_snapshots": {
                "1": {
                    "KRX:005930": {
                        "basis": "previous_close",
                        "reference_price": 100.0,
                        "session_date": "2026-03-24",
                        "checked_at": "2026-03-24T15:30:00+09:00",
                    }
                }
            },
            "watch_session_alerts": {
                "1": {
                    "KRX:005930": {
                        "active_session_date": "2026-03-24",
                        "highest_up_band": 1,
                        "highest_down_band": 0,
                        "intraday_comment_ids": [3002],
                        "close_comment_ids_by_session": {},
                    }
                }
            },
        },
    }

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            return market_provider.WatchSnapshot(
                symbol="KRX:005930",
                current_price=98.4,
                previous_close=98.0,
                session_close_price=None,
                asof=now,
                session_date="2026-03-27",
                provider="kis_quote",
            )

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 27, 10, 0, tzinfo=KST))

    assert intraday.deleted is False
    assert "last_finalized_session_date" not in state["system"]["watch_session_alerts"]["1"]["KRX:005930"]
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["active_session_date"] == "2026-03-24"
    assert state["system"]["watch_reference_snapshots"]["1"]["KRX:005930"]["session_date"] == "2026-03-24"
    assert thread.sent_contents == []
    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "failed"
    assert "comment_failures=1" in run["detail"]


@pytest.mark.asyncio
async def test_watch_poll_invalid_symbol_does_not_abort_other_symbols(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    warm_calls: list[list[str]] = []
    snapshot_calls: list[str] = []
    state = {
        "commands": {},
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["BAD:123", "KRX:005930"]}},
    }

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            warm_calls.append(list(symbols))

        async def get_watch_snapshot(self, symbol, now):
            snapshot_calls.append(symbol)
            return _open_snapshot(now, 104.0)

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    now = datetime(2026, 3, 26, 10, 0, tzinfo=KST)
    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=now)

    assert warm_calls == [["KRX:005930"]]
    assert snapshot_calls == ["KRX:005930"]
    thread = next(iter(forum._threads.values()))
    assert "현재가: ₩104.00" in thread.starter_message.content
    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "failed"
    assert "snapshot_failures=1" in run["detail"]
    assert "updated_threads=1" in run["detail"]


@pytest.mark.asyncio
async def test_watch_poll_re_raises_unexpected_market_session_failure(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    state = {
        "commands": {},
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}},
    }

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

    original_get_watch_market_session = intel_scheduler.get_watch_market_session

    def broken_get_watch_market_session(symbol, now):
        if symbol == "KRX:005930":
            raise RuntimeError("calendar-broken")
        return original_get_watch_market_session(symbol, now)

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())
    monkeypatch.setattr(intel_scheduler, "get_watch_market_session", broken_get_watch_market_session)

    with pytest.raises(RuntimeError, match="calendar-broken"):
        await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 26, 10, 0, tzinfo=KST))


@pytest.mark.asyncio
async def test_watch_poll_skips_when_only_missing_watch_forum_routes_exist(monkeypatch):
    state = {"commands": {}, "guilds": {"1": {"watchlist": ["KRX:005930"]}}}
    called = {"count": 0}

    class Provider:
        async def get_watch_snapshot(self, symbol, now):
            called["count"] += 1
            return _open_snapshot(now, 104.0)

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({}), now=datetime(2026, 3, 26, 10, 0, tzinfo=KST))

    assert called["count"] == 0
    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "skipped"
    assert "missing_forum_guilds=1" in run["detail"]


@pytest.mark.asyncio
async def test_watch_poll_records_snapshot_provider_failure(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    state = {"commands": {}, "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}}}

    class Provider:
        async def get_watch_snapshot(self, symbol, now):
            raise market_provider.MarketDataProviderError("quote provider down", provider_key="kis_quote")

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 26, 10, 0, tzinfo=KST))

    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "failed"
    assert "snapshot_failures=1" in run["detail"]
    assert state["system"]["provider_status"]["kis_quote"]["message"] == "quote provider down"


@pytest.mark.asyncio
async def test_watch_poll_warms_unique_symbols_once(monkeypatch):
    _patch_discord_types(monkeypatch)
    forums = {456: FakeForumChannel(456, 1), 457: FakeForumChannel(457, 2)}
    state = {
        "commands": {},
        "guilds": {
            "1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]},
            "2": {"watch_forum_channel_id": 457, "watchlist": ["KRX:005930"]},
        },
    }
    warmed: list[tuple[str, ...]] = []
    snapshot_calls: list[str] = []

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            warmed.append(tuple(symbols))

        async def get_watch_snapshot(self, symbol, now):
            snapshot_calls.append(symbol)
            return _open_snapshot(now, 104.0)

    monkeypatch.setattr(intel_scheduler, "load_state", lambda: state)
    monkeypatch.setattr(intel_scheduler, "save_state", lambda _state: None)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient(forums), now=datetime(2026, 3, 26, 10, 0, tzinfo=KST))

    assert warmed == [("KRX:005930",)]
    assert snapshot_calls == ["KRX:005930", "KRX:005930"]
