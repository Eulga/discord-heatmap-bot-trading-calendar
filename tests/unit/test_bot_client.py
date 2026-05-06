from types import SimpleNamespace

import pytest

from bot.app import bot_client


class FakeForumChannel:
    def __init__(self, channel_id: int, guild_id: int):
        self.id = channel_id
        self.guild = SimpleNamespace(id=guild_id)


class FakeClient:
    def __init__(self, channels_by_id: dict[int, object]):
        self._channels_by_id = channels_by_id

    def get_channel(self, channel_id: int):
        return self._channels_by_id.get(channel_id)

    async def fetch_channel(self, channel_id: int):
        return self._channels_by_id.get(channel_id)


def _patch_route_state(monkeypatch, state: dict, calls: list[tuple[str, int, int]]) -> None:
    def getter(key: str):
        def _get(guild_id: int) -> int | None:
            value = state.setdefault("guilds", {}).get(str(guild_id), {}).get(key)
            return value if isinstance(value, int) else None

        return _get

    def setter(key: str):
        def _set(guild_id: int, channel_id: int) -> None:
            state.setdefault("guilds", {}).setdefault(str(guild_id), {})[key] = channel_id
            calls.append((key, guild_id, channel_id))

        return _set

    monkeypatch.setattr(bot_client, "get_guild_forum_channel_id", getter("forum_channel_id"))
    monkeypatch.setattr(bot_client, "get_guild_eod_forum_channel_id", getter("eod_forum_channel_id"))
    monkeypatch.setattr(bot_client, "set_guild_forum_channel_id", setter("forum_channel_id"))
    monkeypatch.setattr(bot_client, "set_guild_eod_forum_channel_id", setter("eod_forum_channel_id"))


@pytest.mark.asyncio
async def test_bootstrap_guild_channel_routes_from_env_persists_missing_state(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    calls: list[tuple[str, int, int]] = []

    monkeypatch.setattr(bot_client.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(bot_client, "DEFAULT_FORUM_CHANNEL_ID", 101)
    monkeypatch.setattr(bot_client, "EOD_TARGET_FORUM_ID", 103)
    _patch_route_state(monkeypatch, state, calls)

    client = FakeClient(
        {
            101: FakeForumChannel(101, 1),
            103: FakeForumChannel(103, 1),
        }
    )

    await bot_client._bootstrap_guild_channel_routes_from_env(client)  # type: ignore[arg-type]

    guild = state["guilds"]["1"]
    assert guild["forum_channel_id"] == 101
    assert guild["eod_forum_channel_id"] == 103
    assert calls == [
        ("forum_channel_id", 1, 101),
        ("eod_forum_channel_id", 1, 103),
    ]


@pytest.mark.asyncio
async def test_bootstrap_guild_channel_routes_from_env_does_not_override_existing_state(monkeypatch):
    state = {
        "commands": {},
        "guilds": {
            "1": {
                "forum_channel_id": 201,
                "news_forum_channel_id": 202,
                "eod_forum_channel_id": 203,
            }
        },
    }
    calls: list[tuple[str, int, int]] = []

    monkeypatch.setattr(bot_client.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(bot_client, "DEFAULT_FORUM_CHANNEL_ID", 101)
    monkeypatch.setattr(bot_client, "EOD_TARGET_FORUM_ID", 103)
    _patch_route_state(monkeypatch, state, calls)

    client = FakeClient(
        {
            101: FakeForumChannel(101, 1),
            103: FakeForumChannel(103, 1),
        }
    )

    await bot_client._bootstrap_guild_channel_routes_from_env(client)  # type: ignore[arg-type]

    guild = state["guilds"]["1"]
    assert guild["forum_channel_id"] == 201
    assert guild["news_forum_channel_id"] == 202
    assert guild["eod_forum_channel_id"] == 203
    assert calls == []


def test_warn_legacy_watch_route_migration_needed_logs_missing_watch_forum(caplog, monkeypatch):
    monkeypatch.setattr(bot_client, "list_legacy_watch_route_migrations_needed", lambda: [(1, 460011902043553792)])

    with caplog.at_level("WARNING"):
        bot_client._warn_legacy_watch_route_migration_needed()

    assert "guild=1 legacy_watch_alert_channel_id=460011902043553792" in caplog.text
    assert "/setwatchforum-required" in caplog.text
    assert "guild=2" not in caplog.text
