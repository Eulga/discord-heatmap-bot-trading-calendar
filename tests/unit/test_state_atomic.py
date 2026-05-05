import copy
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.forum import repository, state_store


KST = ZoneInfo("Asia/Seoul")


class FakeCursor:
    def __init__(self, store: dict[str, dict], *, fail: bool = False):
        self.store = store
        self.fail = fail
        self.statements: list[tuple[str, tuple | None]] = []
        self._row = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, query: str, params: tuple | None = None):
        if self.fail:
            raise RuntimeError("database down")
        self.statements.append((query, params))
        self._row = None
        self.rowcount = 0
        normalized = " ".join(query.split()).upper()
        if normalized.startswith("SELECT STATE, VERSION FROM BOT_APP_STATE"):
            state_key = params[0]
            row = self.store.get(state_key)
            if row is not None:
                self._row = (copy.deepcopy(row["state"]), row["version"])
        elif normalized.startswith("SELECT VERSION FROM BOT_APP_STATE"):
            state_key = params[0]
            row = self.store.get(state_key)
            self._row = (row["version"],) if row is not None else None
        elif normalized.startswith("INSERT INTO BOT_APP_STATE"):
            state_key, state_json = params
            if state_key in self.store:
                self.rowcount = 0
                return
            self.store[state_key] = {"state": json.loads(state_json), "version": 1}
            self.rowcount = 1
        elif normalized.startswith("UPDATE BOT_APP_STATE"):
            state_json, state_key, expected_version = params
            row = self.store.get(state_key)
            if row is None or row["version"] != expected_version:
                self.rowcount = 0
                return
            row["state"] = json.loads(state_json)
            row["version"] = expected_version + 1
            self.rowcount = 1

    def fetchone(self):
        return self._row


class FakeConnection:
    def __init__(self, store: dict[str, dict], *, fail: bool = False):
        self.store = store
        self.fail = fail
        self.cursors: list[FakeCursor] = []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def cursor(self):
        cursor = FakeCursor(self.store, fail=self.fail)
        self.cursors.append(cursor)
        return cursor


class DdlCursor:
    def __init__(self):
        self.statements: list[str] = []

    def execute(self, query: str, params: tuple | None = None):
        self.statements.append(query)


def test_state_atomic_roundtrip(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(repository, "STATE_FILE", state_path)
    monkeypatch.setattr(repository, "STATE_BACKEND", "file")

    data = {"commands": {"kheatmap": {"daily_posts_by_guild": {}, "last_images": {}}}, "guilds": {}}
    repository.save_state(data)

    loaded = repository.load_state()
    assert "commands" in loaded
    assert "kheatmap" in loaded["commands"]
    assert "guilds" in loaded


def test_state_recover_on_invalid_json(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    state_path.write_text("{invalid", encoding="utf-8")
    monkeypatch.setattr(repository, "STATE_FILE", state_path)
    monkeypatch.setattr(repository, "STATE_BACKEND", "file")

    loaded = repository.load_state()
    assert loaded == {"commands": {}, "guilds": {}}


def test_state_migrates_legacy_state_file(tmp_path, monkeypatch):
    state_path = tmp_path / "state" / "state.json"
    legacy_path = tmp_path / "heatmaps" / "state.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text('{"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}', encoding="utf-8")
    monkeypatch.setattr(repository, "STATE_FILE", state_path)
    monkeypatch.setattr(repository, "LEGACY_STATE_FILE", legacy_path)
    monkeypatch.setattr(repository, "STATE_BACKEND", "file")

    loaded = repository.load_state()

    assert loaded["guilds"]["1"]["forum_channel_id"] == 123
    assert state_path.exists()
    assert not legacy_path.exists()


def test_postgres_backend_requires_database_url(monkeypatch):
    monkeypatch.setattr(repository, "STATE_BACKEND", "postgres")
    monkeypatch.setattr(repository, "DATABASE_URL", "")

    try:
        repository.load_state()
    except RuntimeError as exc:
        assert "DATABASE_URL is required" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_postgres_schema_migration_adds_version_column(monkeypatch):
    store: dict[str, dict] = {"prod-bot": {"state": {"commands": {}, "guilds": {}}, "version": 1}}
    connection = FakeConnection(store)

    monkeypatch.setattr(repository, "STATE_BACKEND", "postgres")
    monkeypatch.setattr(repository, "DATABASE_URL", "postgresql://example")
    monkeypatch.setattr(repository, "POSTGRES_STATE_KEY", "prod-bot")
    monkeypatch.setattr(repository, "_connect_postgres", lambda: connection)

    repository.load_state()

    executed = "\n".join(query for cursor in connection.cursors for query, _params in cursor.statements)
    assert "ALTER TABLE bot_app_state" in executed
    assert "ADD COLUMN IF NOT EXISTS version" in executed


def test_postgres_load_seeds_from_existing_file_state(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text('{"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}', encoding="utf-8")
    store: dict[str, dict] = {}
    connection = FakeConnection(store)

    monkeypatch.setattr(repository, "STATE_BACKEND", "postgres")
    monkeypatch.setattr(repository, "DATABASE_URL", "postgresql://example")
    monkeypatch.setattr(repository, "POSTGRES_STATE_KEY", "bot-1")
    monkeypatch.setattr(repository, "STATE_FILE", state_path)
    monkeypatch.setattr(repository, "LEGACY_STATE_FILE", tmp_path / "legacy-state.json")
    monkeypatch.setattr(repository, "_connect_postgres", lambda: connection)

    loaded = repository.load_state()

    assert loaded["guilds"]["1"]["forum_channel_id"] == 123
    assert store["bot-1"]["state"]["guilds"]["1"]["forum_channel_id"] == 123
    assert store["bot-1"]["version"] == 1
    assert state_path.exists()
    executed = "\n".join(query for cursor in connection.cursors for query, _params in cursor.statements)
    assert "ADD COLUMN IF NOT EXISTS version" in executed


def test_postgres_save_upserts_selected_state_key(monkeypatch):
    store: dict[str, dict] = {}
    connection = FakeConnection(store)

    monkeypatch.setattr(repository, "STATE_BACKEND", "postgres")
    monkeypatch.setattr(repository, "DATABASE_URL", "postgresql://example")
    monkeypatch.setattr(repository, "POSTGRES_STATE_KEY", "prod-bot")
    monkeypatch.setattr(repository, "_connect_postgres", lambda: connection)

    repository.save_state({"commands": {}, "guilds": {"9": {"forum_channel_id": 456}}})

    assert store == {"prod-bot": {"state": {"commands": {}, "guilds": {"9": {"forum_channel_id": 456}}}, "version": 1}}
    executed = "\n".join(query for cursor in connection.cursors for query, _params in cursor.statements)
    assert "bot_app_state" in executed
    assert "ON CONFLICT" in executed
    assert "ADD COLUMN IF NOT EXISTS version" in executed


def test_postgres_save_increments_loaded_state_version(monkeypatch):
    store: dict[str, dict] = {"prod-bot": {"state": {"commands": {}, "guilds": {}}, "version": 1}}
    connection = FakeConnection(store)

    monkeypatch.setattr(repository, "STATE_BACKEND", "postgres")
    monkeypatch.setattr(repository, "DATABASE_URL", "postgresql://example")
    monkeypatch.setattr(repository, "POSTGRES_STATE_KEY", "prod-bot")
    monkeypatch.setattr(repository, "_connect_postgres", lambda: connection)

    loaded = repository.load_state()
    loaded["guilds"]["9"] = {"forum_channel_id": 456}
    repository.save_state(loaded)

    assert store["prod-bot"]["state"]["guilds"]["9"]["forum_channel_id"] == 456
    assert store["prod-bot"]["version"] == 2


def test_postgres_stale_loaded_state_raises_without_overwrite(monkeypatch):
    store: dict[str, dict] = {
        "prod-bot": {"state": {"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}, "version": 1}
    }
    connection = FakeConnection(store)

    monkeypatch.setattr(repository, "STATE_BACKEND", "postgres")
    monkeypatch.setattr(repository, "DATABASE_URL", "postgresql://example")
    monkeypatch.setattr(repository, "POSTGRES_STATE_KEY", "prod-bot")
    monkeypatch.setattr(repository, "_connect_postgres", lambda: connection)

    loaded = repository.load_state()
    store["prod-bot"]["state"] = {"commands": {}, "guilds": {"2": {"forum_channel_id": 789}}}
    store["prod-bot"]["version"] = 2
    loaded["guilds"]["9"] = {"forum_channel_id": 456}

    try:
        repository.save_state(loaded)
    except RuntimeError as exc:
        assert str(exc) == "PostgreSQL state backend concurrent update conflict."
    else:
        raise AssertionError("expected RuntimeError")

    assert store["prod-bot"]["state"] == {"commands": {}, "guilds": {"2": {"forum_channel_id": 789}}}
    assert store["prod-bot"]["version"] == 2


def test_postgres_load_failure_does_not_return_empty_state(monkeypatch):
    connection = FakeConnection({}, fail=True)

    monkeypatch.setattr(repository, "STATE_BACKEND", "postgres")
    monkeypatch.setattr(repository, "DATABASE_URL", "postgresql://example")
    monkeypatch.setattr(repository, "_connect_postgres", lambda: connection)

    try:
        repository.load_state()
    except RuntimeError as exc:
        assert "PostgreSQL state backend load failed" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_split_state_schema_creates_watch_close_price_tables():
    cursor = DdlCursor()

    state_store._ensure_schema(cursor)

    executed = "\n".join(cursor.statements)
    assert "CREATE TABLE IF NOT EXISTS bot_watch_close_prices" in executed
    assert "PRIMARY KEY (state_key, symbol, session_date)" in executed
    assert "CREATE TABLE IF NOT EXISTS bot_watch_close_price_attempts" in executed
    assert "idx_bot_watch_close_prices_symbol_date" in executed
    assert "idx_bot_watch_close_prices_date" in executed


def test_watch_close_price_upsert_replaces_existing_symbol_session(monkeypatch):
    rows: dict[tuple[str, str, str], dict[str, object]] = {}

    def fake_execute(query: str, params: tuple):
        assert "ON CONFLICT (state_key, symbol, session_date) DO UPDATE" in query
        (
            state_key,
            symbol,
            market,
            session_date,
            close_price,
            reference_price,
            snapshot_session_date,
            snapshot_asof,
            provider,
            source,
            collection_reason,
            captured_at,
        ) = params
        rows[(state_key, symbol, session_date)] = {
            "market": market,
            "close_price": close_price,
            "reference_price": reference_price,
            "snapshot_session_date": snapshot_session_date,
            "snapshot_asof": snapshot_asof,
            "provider": provider,
            "source": source,
            "collection_reason": collection_reason,
            "captured_at": captured_at,
        }

    monkeypatch.setattr(state_store, "POSTGRES_STATE_KEY", "bot-1")
    monkeypatch.setattr(state_store, "_execute", fake_execute)

    now = datetime(2026, 3, 26, 16, 0, tzinfo=KST)
    state_store.upsert_watch_close_price(
        "krx:005930",
        session_date="2026-03-26",
        close_price=98.0,
        reference_price=100.0,
        snapshot_session_date="2026-03-26",
        snapshot_asof=now,
        provider="kis_quote",
        source="session_close_price",
        collection_reason="finalization",
        captured_at=now,
    )
    state_store.upsert_watch_close_price(
        "KRX:005930",
        session_date="2026-03-26",
        close_price=99.0,
        reference_price=100.0,
        snapshot_session_date="2026-03-26",
        snapshot_asof=now,
        provider="kis_quote",
        source="session_close_price",
        collection_reason="catchup",
        captured_at=now,
    )

    assert len(rows) == 1
    row = rows[("bot-1", "KRX:005930", "2026-03-26")]
    assert row["market"] == "KRX"
    assert row["close_price"] == 99.0
    assert row["collection_reason"] == "catchup"


def test_watch_close_price_attempt_throttle(monkeypatch):
    prices: set[tuple[str, str, str]] = set()
    attempts: dict[tuple[str, str, str], datetime] = {}
    now = datetime(2026, 3, 26, 16, 30, tzinfo=KST)

    def fake_fetchone(query: str, params: tuple):
        key = (params[0], params[1], params[2])
        if "FROM bot_watch_close_prices" in query:
            return (1,) if key in prices else None
        if "FROM bot_watch_close_price_attempts" in query:
            attempted_at = attempts.get(key)
            return (attempted_at,) if attempted_at is not None else None
        raise AssertionError(query)

    monkeypatch.setattr(state_store, "POSTGRES_STATE_KEY", "bot-1")
    monkeypatch.setattr(state_store, "_fetchone", fake_fetchone)

    assert state_store.should_attempt_watch_close_price("KRX:005930", "2026-03-26", now) is True

    attempts[("bot-1", "KRX:005930", "2026-03-26")] = now - timedelta(minutes=10)
    assert state_store.should_attempt_watch_close_price("KRX:005930", "2026-03-26", now) is False

    attempts[("bot-1", "KRX:005930", "2026-03-26")] = now - timedelta(minutes=16)
    assert state_store.should_attempt_watch_close_price("KRX:005930", "2026-03-26", now) is True

    prices.add(("bot-1", "KRX:005930", "2026-03-26"))
    assert state_store.should_attempt_watch_close_price("KRX:005930", "2026-03-26", now) is False


def test_split_state_maps_legacy_app_state_domains():
    state = {
        "commands": {
            "kheatmap": {
                "last_run_at": "2026-05-05T16:00:00+09:00",
                "last_images": {"kospi": {"path": "data/heatmaps/kospi.png", "captured_at": "2026-05-05T16:01:00+09:00"}},
                "daily_posts_by_guild": {
                    "1": {"2026-05-05": {"thread_id": 11, "starter_message_id": 12, "content_message_ids": [13, 14]}}
                },
            },
            "watchpoll": {
                "symbol_threads_by_guild": {"1": {"KRX:005930": {"thread_id": 21, "starter_message_id": 22, "status": "inactive"}}}
            },
        },
        "guilds": {
            "1": {
                "forum_channel_id": 101,
                "news_forum_channel_id": 102,
                "eod_forum_channel_id": 103,
                "watch_forum_channel_id": 104,
                "watch_alert_channel_id": 105,
                "auto_screenshot_enabled": True,
                "last_auto_attempts": {"kheatmap": "2026-05-05"},
                "last_auto_runs": {"kheatmap": "2026-05-05"},
                "last_auto_skips": {"usheatmap": {"date": "2026-05-04", "reason": "holiday"}},
                "watchlist": ["005930"],
                "watch_alert_cooldowns": {"KRX:005930:up": "2026-05-05T10:00:00+09:00"},
                "watch_alert_latches": {"KRX:005930": "up"},
            }
        },
        "system": {
            "watch_reference_snapshots": {
                "1": {
                    "KRX:005930": {
                        "basis": "previous_close",
                        "reference_price": 100.0,
                        "session_date": "2026-05-05",
                        "checked_at": "2026-05-05T10:00:00+09:00",
                    }
                }
            },
            "watch_session_alerts": {
                "1": {
                    "KRX:005930": {
                        "active_session_date": "2026-05-05",
                        "highest_up_band": 1,
                        "highest_down_band": 0,
                        "current_comment_id": 31,
                        "intraday_comment_ids": [32],
                        "close_comment_ids_by_session": {"2026-05-04": 33},
                        "pending_close_sessions": {
                            "2026-05-05": {"reference_price": 100.0, "intraday_comment_ids": [32]}
                        },
                        "last_finalized_session_date": "2026-05-04",
                    }
                }
            },
            "watch_baselines": {"1": {"KRX:005930": {"price": 100.0, "checked_at": "2026-05-05T09:00:00+09:00"}}},
            "job_last_runs": {"watch_poll": {"status": "ok", "detail": "done", "run_at": "2026-05-05T10:00:00+09:00"}},
            "provider_status": {"kis_quote": {"ok": True, "message": "ok", "updated_at": "2026-05-05T10:00:00+09:00"}},
            "news_dedup": {"2026-05-05": ["story-1"]},
        },
    }

    rows = state_store._split_state(state)

    assert rows["guild_config"] == [
        {
            "guild_id": 1,
            "forum_channel_id": 101,
            "news_forum_channel_id": 102,
            "eod_forum_channel_id": 103,
            "watch_forum_channel_id": 104,
            "legacy_watch_alert_channel_id": 105,
            "auto_screenshot_enabled": True,
        }
    ]
    assert {
        "guild_id": 1,
        "job_key": "kheatmap",
        "last_attempt_date": "2026-05-05",
        "last_run_date": "2026-05-05",
        "last_skip_date": None,
        "last_skip_reason": None,
    } in rows["guild_job_markers"]
    assert rows["daily_posts"] == [
        {
            "command_key": "kheatmap",
            "guild_id": 1,
            "post_date": "2026-05-05",
            "thread_id": 11,
            "starter_message_id": 12,
            "content_message_ids": [13, 14],
        }
    ]
    assert rows["command_image_cache"] == [
        {
            "command_key": "kheatmap",
            "market_label": "kospi",
            "path": "data/heatmaps/kospi.png",
            "captured_at": "2026-05-05T16:01:00+09:00",
            "last_run_at": "2026-05-05T16:00:00+09:00",
        }
    ]
    assert rows["watch_symbols"] == [
        {"guild_id": 1, "symbol": "KRX:005930", "status": "inactive", "thread_id": 21, "starter_message_id": 22}
    ]
    assert rows["watch_reference_snapshots"][0]["reference_price"] == 100.0
    assert rows["watch_session_alerts"][0]["pending_close_sessions"]["2026-05-05"]["intraday_comment_ids"] == [32]
    assert rows["watch_alert_cooldowns"] == [
        {"guild_id": 1, "alert_key": "KRX:005930:up", "hit_at": "2026-05-05T10:00:00+09:00"}
    ]
    assert rows["watch_alert_latches"] == [{"guild_id": 1, "symbol": "KRX:005930", "direction": "up"}]
    assert rows["watch_baselines"] == [
        {"guild_id": 1, "symbol": "KRX:005930", "price": 100.0, "checked_at": "2026-05-05T09:00:00+09:00"}
    ]
    assert rows["job_status"] == [
        {"job_key": "watch_poll", "status": "ok", "detail": "done", "run_at": "2026-05-05T10:00:00+09:00"}
    ]
    assert rows["provider_status"] == [
        {"provider_key": "kis_quote", "ok": True, "message": "ok", "updated_at": "2026-05-05T10:00:00+09:00"}
    ]
    assert rows["news_dedup"] == [{"date_text": "2026-05-05", "dedup_key": "story-1"}]
