from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from bot.features import intel_scheduler
from bot.features.watch import thread_service
from bot.intel.providers import market as market_provider
from tests.state_store_adapter import patch_legacy_state_store


KST = ZoneInfo("Asia/Seoul")


class FakeNotFound(Exception):
    pass


class FakeHTTPException(Exception):
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


def _visible_messages(thread: FakeThread) -> list[FakeMessage]:
    return [message for message in sorted(thread._messages.values(), key=lambda item: item.id) if not message.deleted]


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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    now = datetime(2026, 3, 26, 10, 0, tzinfo=KST)
    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=now)

    thread = next(iter(forum._threads.values()))
    assert thread.starter_message.content == intel_scheduler.render_blank_watch_starter()
    assert len(thread.sent_contents) == 2
    assert thread.sent_contents[0] == "삼성전자 (KRX:005930) +6% 이상 상승 : +7.10% · 2026-03-26 10:00:00"
    assert "전일 종가: ₩100.00" in thread.sent_contents[1]
    assert "현재가: ₩107.10" in thread.sent_contents[1]
    assert "기준 세션" not in thread.sent_contents[1]
    assert "당일 최고 상승 band" not in thread.sent_contents[1]
    assert _visible_messages(thread)[-1].id == state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["current_comment_id"]
    assert state["system"]["provider_status"]["kis_quote"]["message"] == "snapshot:KRX:005930"
    assert state["system"]["job_last_runs"]["watch_poll"]["status"] == "ok"
    assert "updated_current_comments=1" in state["system"]["job_last_runs"]["watch_poll"]["detail"]


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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    client = FakeClient({456: forum})
    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 10, 0, tzinfo=KST))
    thread = next(iter(forum._threads.values()))
    first_current_comment_id = state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["current_comment_id"]

    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 10, 1, tzinfo=KST))
    second_current_comment_id = state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["current_comment_id"]
    assert second_current_comment_id == first_current_comment_id
    assert "현재가: ₩104.50" in thread._messages[first_current_comment_id].content

    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 10, 2, tzinfo=KST))

    third_current_comment_id = state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["current_comment_id"]
    assert third_current_comment_id != first_current_comment_id
    assert thread._messages[first_current_comment_id].deleted is True
    assert len(thread.sent_contents) == 4
    assert thread.sent_contents[0] == "삼성전자 (KRX:005930) +3% 이상 상승 : +4.00% · 2026-03-26 10:00:00"
    assert "현재가: ₩104.00" in thread.sent_contents[1]
    assert thread.sent_contents[2] == "삼성전자 (KRX:005930) -6% 이상 하락 : -6.20% · 2026-03-26 10:02:00"
    assert "현재가: ₩93.80" in thread.sent_contents[3]
    visible_contents = [message.content for message in _visible_messages(thread)]
    assert visible_contents[-2] == "삼성전자 (KRX:005930) -6% 이상 하락 : -6.20% · 2026-03-26 10:02:00"
    assert "현재가: ₩93.80" in visible_contents[-1]
    assert "당일 alert status" not in visible_contents[-1]


@pytest.mark.asyncio
async def test_watch_poll_updates_current_comment_when_band_comment_send_fails(monkeypatch):
    _patch_discord_types(monkeypatch)

    class BandFailThread(FakeThread):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.send_calls = 0

        async def send(self, content: str):
            self.send_calls += 1
            if self.send_calls == 1:
                raise RuntimeError("band-send-failed")
            return await super().send(content)

    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = BandFailThread(2001, starter, parent_id=456)
    forum._threads[thread.id] = thread
    state = {
        "commands": {
            "watchpoll": {
                "symbol_threads_by_guild": {
                    "1": {"KRX:005930": {"thread_id": 2001, "starter_message_id": 3001, "status": "active"}}
                },
            }
        },
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}},
    }

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            return _open_snapshot(now, 104.0)

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 26, 10, 0, tzinfo=KST))

    alert_entry = state["system"]["watch_session_alerts"]["1"]["KRX:005930"]
    assert thread.send_calls == 2
    assert len(thread.sent_contents) == 1
    assert "현재가: ₩104.00" in thread.sent_contents[0]
    assert alert_entry["highest_up_band"] == 0
    assert alert_entry["highest_down_band"] == 0
    assert alert_entry["intraday_comment_ids"] == []
    assert alert_entry["current_comment_id"] == _visible_messages(thread)[-1].id
    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "failed"
    assert "comment_failures=1" in run["detail"]
    assert "updated_current_comments=1" in run["detail"]


@pytest.mark.asyncio
async def test_watch_poll_recreates_current_comment_when_old_current_delete_fails(monkeypatch):
    _patch_discord_types(monkeypatch)
    monkeypatch.setattr(intel_scheduler.discord, "HTTPException", FakeHTTPException)

    class CurrentComment(FakeMessage):
        async def delete(self):
            raise FakeHTTPException("delete-failed")

    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    current_comment = CurrentComment(3002, "old current")
    thread = FakeThread(2001, starter, parent_id=456)
    thread.add_message(current_comment)
    forum._threads[thread.id] = thread
    state = {
        "commands": {
            "watchpoll": {
                "symbol_threads_by_guild": {
                    "1": {"KRX:005930": {"thread_id": 2001, "starter_message_id": 3001, "status": "active"}}
                },
            }
        },
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}},
        "system": {"watch_session_alerts": {"1": {"KRX:005930": {"current_comment_id": 3002}}}},
    }

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            return _open_snapshot(now, 104.0)

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 26, 10, 0, tzinfo=KST))

    alert_entry = state["system"]["watch_session_alerts"]["1"]["KRX:005930"]
    assert current_comment.deleted is False
    assert len(thread.sent_contents) == 2
    assert thread.sent_contents[0] == "삼성전자 (KRX:005930) +3% 이상 상승 : +4.00% · 2026-03-26 10:00:00"
    assert "현재가: ₩104.00" in thread.sent_contents[1]
    assert alert_entry["highest_up_band"] == 1
    assert alert_entry["intraday_comment_ids"] == [3003]
    assert alert_entry["current_comment_id"] == 3004
    assert _visible_messages(thread)[-1].id == 3004
    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "ok"
    assert "updated_current_comments=1" in run["detail"]


@pytest.mark.asyncio
async def test_watch_poll_defers_close_finalization_until_session_close_price_is_available(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = FakeThread(2001, starter)
    intraday_one = FakeMessage(3002, "band-1")
    intraday_two = FakeMessage(3003, "band-2")
    current_comment = FakeMessage(3004, "current")
    thread.add_message(intraday_one)
    thread.add_message(intraday_two)
    thread.add_message(current_comment)
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
                        "current_comment_id": 3004,
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
                asof=datetime(2026, 3, 26, 16, 0, tzinfo=KST),
                session_date="2026-03-26",
                provider="kis_quote",
            ),
            market_provider.WatchSnapshot(
                symbol="KRX:005930",
                current_price=99.0,
                previous_close=100.0,
                session_close_price=98.0,
                asof=datetime(2026, 3, 26, 16, 0, 30, tzinfo=KST),
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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    client = FakeClient({456: forum})
    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 16, 0, tzinfo=KST))
    assert intraday_one.deleted is False
    assert intraday_two.deleted is False
    assert current_comment.deleted is False
    assert "last_finalized_session_date" not in state["system"]["watch_session_alerts"]["1"]["KRX:005930"]

    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 16, 0, 30, tzinfo=KST))
    assert intraday_one.deleted is True
    assert intraday_two.deleted is True
    assert current_comment.deleted is True
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["last_finalized_session_date"] == "2026-03-26"
    assert "current_comment_id" not in state["system"]["watch_session_alerts"]["1"]["KRX:005930"]
    close_comments = [content for content in thread.sent_contents if "마감가 알림" in content]
    assert len(close_comments) == 1


@pytest.mark.asyncio
async def test_watch_poll_finalizes_krx_close_only_at_kst_1600(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = FakeThread(2001, starter)
    intraday = FakeMessage(3002, "band-1")
    current_comment = FakeMessage(3003, "current")
    thread.add_message(intraday)
    thread.add_message(current_comment)
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
                        "highest_up_band": 1,
                        "highest_down_band": 0,
                        "current_comment_id": 3003,
                        "intraday_comment_ids": [3002],
                        "close_comment_ids_by_session": {},
                    }
                }
            },
        },
    }
    snapshot_calls: list[datetime] = []

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            snapshot_calls.append(now)
            return market_provider.WatchSnapshot(
                symbol=symbol,
                current_price=99.0,
                previous_close=100.0,
                session_close_price=98.0,
                asof=now,
                session_date="2026-03-26",
                provider="kis_quote",
            )

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    client = FakeClient({456: forum})
    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 15, 59, tzinfo=KST))
    assert snapshot_calls == []
    assert intraday.deleted is False
    assert current_comment.deleted is False
    assert "last_finalized_session_date" not in state["system"]["watch_session_alerts"]["1"]["KRX:005930"]

    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 26, 16, 0, tzinfo=KST))
    assert snapshot_calls == [datetime(2026, 3, 26, 16, 0, tzinfo=KST)]
    assert intraday.deleted is True
    assert current_comment.deleted is True
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["last_finalized_session_date"] == "2026-03-26"
    close_comments = [content for content in thread.sent_contents if "마감가 알림" in content]
    assert len(close_comments) == 1


@pytest.mark.asyncio
async def test_watch_poll_finalizes_us_close_only_at_kst_0700(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = FakeThread(2001, starter)
    intraday = FakeMessage(3002, "band-1")
    current_comment = FakeMessage(3003, "current")
    thread.add_message(intraday)
    thread.add_message(current_comment)
    forum._threads[thread.id] = thread

    state = {
        "commands": {
            "watchpoll": {
                "daily_posts_by_guild": {},
                "last_images": {},
                "symbol_threads_by_guild": {"1": {"NAS:AAPL": {"thread_id": 2001, "starter_message_id": 3001, "status": "active"}}},
            }
        },
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["NAS:AAPL"]}},
        "system": {
            "watch_reference_snapshots": {
                "1": {
                    "NAS:AAPL": {
                        "basis": "previous_close",
                        "reference_price": 100.0,
                        "session_date": "2026-03-26",
                        "checked_at": "2026-03-26T10:00:00+09:00",
                    }
                }
            },
            "watch_session_alerts": {
                "1": {
                    "NAS:AAPL": {
                        "active_session_date": "2026-03-26",
                        "highest_up_band": 1,
                        "highest_down_band": 0,
                        "current_comment_id": 3003,
                        "intraday_comment_ids": [3002],
                        "close_comment_ids_by_session": {},
                    }
                }
            },
        },
    }
    snapshot_calls: list[datetime] = []

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            snapshot_calls.append(now)
            return market_provider.WatchSnapshot(
                symbol=symbol,
                current_price=101.0,
                previous_close=100.0,
                session_close_price=102.0,
                asof=now,
                session_date="2026-03-26",
                provider="kis_quote",
            )

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    client = FakeClient({456: forum})
    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 27, 6, 59, tzinfo=KST))
    assert snapshot_calls == []
    assert intraday.deleted is False
    assert current_comment.deleted is False
    assert "last_finalized_session_date" not in state["system"]["watch_session_alerts"]["1"]["NAS:AAPL"]

    await intel_scheduler._run_watch_poll(client=client, now=datetime(2026, 3, 27, 7, 0, tzinfo=KST))
    assert snapshot_calls == [datetime(2026, 3, 27, 7, 0, tzinfo=KST)]
    assert intraday.deleted is True
    assert current_comment.deleted is True
    assert state["system"]["watch_session_alerts"]["1"]["NAS:AAPL"]["last_finalized_session_date"] == "2026-03-26"
    close_comments = [content for content in thread.sent_contents if "마감가 알림" in content]
    assert len(close_comments) == 1


@pytest.mark.asyncio
async def test_watch_poll_finalization_ignores_current_comment_cleanup_http_failure(monkeypatch):
    _patch_discord_types(monkeypatch)
    monkeypatch.setattr(intel_scheduler.discord, "HTTPException", FakeHTTPException)
    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = FakeThread(2001, starter)
    intraday = FakeMessage(3002, "band-1")

    class CurrentComment(FakeMessage):
        async def delete(self):
            raise FakeHTTPException("delete-failed")

    current_comment = CurrentComment(3003, "current")
    thread.add_message(intraday)
    thread.add_message(current_comment)
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
                        "highest_up_band": 1,
                        "highest_down_band": 0,
                        "current_comment_id": 3003,
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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 26, 16, 0, tzinfo=KST))

    alert_entry = state["system"]["watch_session_alerts"]["1"]["KRX:005930"]
    assert current_comment.deleted is False
    assert intraday.deleted is True
    assert "current_comment_id" not in alert_entry
    assert alert_entry["last_finalized_session_date"] == "2026-03-26"
    close_comments = [content for content in thread.sent_contents if "마감가 알림" in content]
    assert len(close_comments) == 1
    assert state["system"]["job_last_runs"]["watch_poll"]["status"] == "ok"


@pytest.mark.asyncio
async def test_watch_poll_finalizes_inactive_symbol_once_before_stopping(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = FakeThread(2001, starter)
    intraday = FakeMessage(3002, "band-1")
    current_comment = FakeMessage(3003, "current")
    thread.add_message(intraday)
    thread.add_message(current_comment)
    forum._threads[thread.id] = thread

    state = {
        "commands": {
            "watchpoll": {
                "daily_posts_by_guild": {},
                "last_images": {},
                "symbol_threads_by_guild": {"1": {"KRX:005930": {"thread_id": 2001, "starter_message_id": 3001, "status": "inactive"}}},
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
                        "highest_up_band": 1,
                        "highest_down_band": 0,
                        "current_comment_id": 3003,
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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 26, 16, 0, tzinfo=KST))

    assert intraday.deleted is True
    assert current_comment.deleted is True
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["last_finalized_session_date"] == "2026-03-26"
    assert "current_comment_id" not in state["system"]["watch_session_alerts"]["1"]["KRX:005930"]


@pytest.mark.asyncio
async def test_watch_poll_does_not_update_stopped_symbol_during_open_session(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    snapshot_calls = {"count": 0}
    state = {
        "commands": {
            "watchpoll": {
                "symbol_threads_by_guild": {"1": {"KRX:005930": {"status": "inactive"}}},
            }
        },
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}},
    }

    class Provider:
        async def get_watch_snapshot(self, symbol, now):
            snapshot_calls["count"] += 1
            return _open_snapshot(now, 104.0)

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 26, 10, 0, tzinfo=KST))

    assert snapshot_calls["count"] == 0
    assert forum._threads == {}
    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "skipped"
    assert run["detail"] == "no-watch-symbols"


@pytest.mark.asyncio
async def test_watch_poll_keeps_regular_updates_when_prior_session_missed_due_minute(monkeypatch):
    _patch_discord_types(monkeypatch)
    forum = FakeForumChannel(456, 1)
    starter = FakeMessage(3001, "starter")
    thread = FakeThread(2001, starter, parent_id=456)
    intraday = FakeMessage(3002, "band-1")
    current_comment = FakeMessage(3003, "current")
    thread.add_message(intraday)
    thread.add_message(current_comment)
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
                        "current_comment_id": 3003,
                        "intraday_comment_ids": [3002],
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
                current_price=98.4,
                previous_close=98.0,
                session_close_price=None,
                asof=datetime(2026, 3, 27, 10, 0, tzinfo=KST),
                session_date="2026-03-27",
                provider="kis_quote",
            ),
            market_provider.WatchSnapshot(
                symbol="KRX:005930",
                current_price=99.0,
                previous_close=98.0,
                session_close_price=99.0,
                asof=datetime(2026, 3, 27, 16, 0, tzinfo=KST),
                session_date="2026-03-27",
                provider="kis_quote",
            ),
        ]
    )
    snapshot_calls: list[datetime] = []

    class Provider:
        async def warm_watch_snapshots(self, symbols, now):
            return None

        async def get_watch_snapshot(self, symbol, now):
            snapshot_calls.append(now)
            return next(snapshots)

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 27, 10, 0, tzinfo=KST))

    assert snapshot_calls == [datetime(2026, 3, 27, 10, 0, tzinfo=KST)]
    assert intraday.deleted is False
    assert current_comment.deleted is False
    assert "last_finalized_session_date" not in state["system"]["watch_session_alerts"]["1"]["KRX:005930"]
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["active_session_date"] == "2026-03-27"
    assert state["system"]["watch_reference_snapshots"]["1"]["KRX:005930"]["session_date"] == "2026-03-27"
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["current_comment_id"] == 3003
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["pending_close_sessions"] == {
        "2026-03-26": {"reference_price": 100.0, "intraday_comment_ids": [3002], "updated_at": "2026-03-27T10:00:00+09:00"}
    }
    assert "현재가: ₩98.40" in current_comment.content
    close_comments = [content for content in thread.sent_contents if "마감가 알림" in content]
    assert len(close_comments) == 0
    assert thread.sent_contents == []

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 27, 16, 0, tzinfo=KST))

    assert snapshot_calls == [
        datetime(2026, 3, 27, 10, 0, tzinfo=KST),
        datetime(2026, 3, 27, 16, 0, tzinfo=KST),
    ]
    assert intraday.deleted is True
    assert current_comment.deleted is True
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["last_finalized_session_date"] == "2026-03-27"
    assert "pending_close_sessions" not in state["system"]["watch_session_alerts"]["1"]["KRX:005930"]
    close_comments = [content for content in thread.sent_contents if "마감가 알림" in content]
    assert len(close_comments) == 2
    assert "[watch-close:KRX:005930:2026-03-26]" in close_comments[0]
    assert "[watch-close:KRX:005930:2026-03-27]" in close_comments[1]


@pytest.mark.asyncio
async def test_watch_poll_drops_non_adjacent_pending_close_session(monkeypatch):
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
                        "reference_price": 98.0,
                        "session_date": "2026-03-27",
                        "checked_at": "2026-03-27T15:30:00+09:00",
                    }
                }
            },
            "watch_session_alerts": {
                "1": {
                    "KRX:005930": {
                        "active_session_date": "2026-03-27",
                        "last_finalized_session_date": "2026-03-27",
                        "highest_up_band": 0,
                        "highest_down_band": 0,
                        "intraday_comment_ids": [],
                        "pending_close_sessions": {
                            "2026-03-24": {
                                "reference_price": 100.0,
                                "intraday_comment_ids": [3002],
                                "updated_at": "2026-03-26T16:00:00+09:00",
                            }
                        },
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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=datetime(2026, 3, 27, 16, 0, tzinfo=KST))

    assert intraday.deleted is False
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["last_finalized_session_date"] == "2026-03-27"
    assert state["system"]["watch_session_alerts"]["1"]["KRX:005930"]["active_session_date"] == "2026-03-27"
    assert state["system"]["watch_reference_snapshots"]["1"]["KRX:005930"]["session_date"] == "2026-03-27"
    assert "pending_close_sessions" not in state["system"]["watch_session_alerts"]["1"]["KRX:005930"]
    assert thread.sent_contents == []
    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "ok"
    assert "finalized_sessions=0" in run["detail"]
    assert "dropped_pending_close_sessions=1" in run["detail"]


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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    now = datetime(2026, 3, 26, 10, 0, tzinfo=KST)
    await intel_scheduler._run_watch_poll(client=FakeClient({456: forum}), now=now)

    assert warm_calls == [["KRX:005930"]]
    assert snapshot_calls == ["KRX:005930"]
    thread = next(iter(forum._threads.values()))
    assert thread.starter_message.content == intel_scheduler.render_blank_watch_starter()
    assert "현재가: ₩104.00" in _visible_messages(thread)[-1].content
    run = state["system"]["job_last_runs"]["watch_poll"]
    assert run["status"] == "failed"
    assert "snapshot_failures=1" in run["detail"]
    assert "updated_threads=1" in run["detail"]
    assert "updated_current_comments=1" in run["detail"]


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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
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

    patch_legacy_state_store(monkeypatch, intel_scheduler, state)
    monkeypatch.setattr(intel_scheduler, "quote_provider", Provider())

    await intel_scheduler._run_watch_poll(client=FakeClient(forums), now=datetime(2026, 3, 26, 10, 0, tzinfo=KST))

    assert warmed == [("KRX:005930",)]
    assert snapshot_calls == ["KRX:005930", "KRX:005930"]
