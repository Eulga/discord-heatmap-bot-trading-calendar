import copy
import json

from bot.forum import repository


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
