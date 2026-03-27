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


@pytest.mark.asyncio
async def test_bootstrap_guild_channel_routes_from_env_persists_missing_state(monkeypatch):
    state = {"commands": {}, "guilds": {}}
    saves = {"count": 0}

    monkeypatch.setattr(bot_client.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(bot_client, "DEFAULT_FORUM_CHANNEL_ID", 101)
    monkeypatch.setattr(bot_client, "NEWS_TARGET_FORUM_ID", 102)
    monkeypatch.setattr(bot_client, "EOD_TARGET_FORUM_ID", 103)
    monkeypatch.setattr(bot_client, "load_state", lambda: state)
    monkeypatch.setattr(bot_client, "save_state", lambda _state: saves.__setitem__("count", saves["count"] + 1))

    client = FakeClient(
        {
            101: FakeForumChannel(101, 1),
            102: FakeForumChannel(102, 1),
            103: FakeForumChannel(103, 1),
        }
    )

    await bot_client._bootstrap_guild_channel_routes_from_env(client)  # type: ignore[arg-type]

    guild = state["guilds"]["1"]
    assert guild["forum_channel_id"] == 101
    assert guild["news_forum_channel_id"] == 102
    assert guild["eod_forum_channel_id"] == 103
    assert saves["count"] == 1


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
    saves = {"count": 0}

    monkeypatch.setattr(bot_client.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(bot_client, "DEFAULT_FORUM_CHANNEL_ID", 101)
    monkeypatch.setattr(bot_client, "NEWS_TARGET_FORUM_ID", 102)
    monkeypatch.setattr(bot_client, "EOD_TARGET_FORUM_ID", 103)
    monkeypatch.setattr(bot_client, "load_state", lambda: state)
    monkeypatch.setattr(bot_client, "save_state", lambda _state: saves.__setitem__("count", saves["count"] + 1))

    client = FakeClient(
        {
            101: FakeForumChannel(101, 1),
            102: FakeForumChannel(102, 1),
            103: FakeForumChannel(103, 1),
        }
    )

    await bot_client._bootstrap_guild_channel_routes_from_env(client)  # type: ignore[arg-type]

    guild = state["guilds"]["1"]
    assert guild["forum_channel_id"] == 201
    assert guild["news_forum_channel_id"] == 202
    assert guild["eod_forum_channel_id"] == 203
    assert saves["count"] == 0


def test_warn_legacy_watch_route_migration_needed_logs_missing_watch_forum(caplog, monkeypatch):
    state = {
        "commands": {},
        "guilds": {
            "1": {"watch_alert_channel_id": 460011902043553792},
            "2": {"watch_alert_channel_id": 123, "watch_forum_channel_id": 456},
        },
    }

    monkeypatch.setattr(bot_client, "load_state", lambda: state)

    with caplog.at_level("WARNING"):
        bot_client._warn_legacy_watch_route_migration_needed()

    assert "guild=1 legacy_watch_alert_channel_id=460011902043553792" in caplog.text
    assert "/setwatchforum-required" in caplog.text
    assert "guild=2" not in caplog.text
