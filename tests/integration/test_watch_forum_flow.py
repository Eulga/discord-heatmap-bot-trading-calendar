from types import SimpleNamespace

import discord
import pytest

from bot.features.admin import command as admin_command
from bot.features.watch import command as watch_command
from bot.features.watch import thread_service


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
    def __init__(
        self,
        thread_id: int,
        starter_message: FakeMessage,
        *,
        guild_id: int = 1,
        parent_id: int | None = None,
        missing_starter: bool = False,
    ):
        self.id = thread_id
        self.guild = SimpleNamespace(id=guild_id)
        self.name = "old-title"
        self.parent = None
        self.parent_id = parent_id
        self._starter_message = starter_message
        self._missing_starter = missing_starter
        self._messages: dict[int, FakeMessage] = {starter_message.id: starter_message}
        self.sent_contents: list[str] = []

    async def fetch_message(self, message_id: int):
        if self._missing_starter and message_id == self._starter_message.id:
            raise FakeNotFound()
        message = self._messages.get(message_id)
        if message is None:
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
        for message in reversed(list(self._messages.values()))[:limit]:
            yield message


class FakeForumChannel:
    def __init__(self, channel_id: int, guild_id: int, *, existing_thread: FakeThread | None = None, created_thread: FakeThread | None = None):
        self.id = channel_id
        self.guild = SimpleNamespace(id=guild_id)
        self._existing_thread = existing_thread
        self._created_thread = created_thread or FakeThread(999, FakeMessage(555, "starter"))
        if self._existing_thread is not None and self._existing_thread.parent_id is None:
            self._existing_thread.parent = self
            self._existing_thread.parent_id = self.id
        if self._created_thread.parent_id is None:
            self._created_thread.parent = self
            self._created_thread.parent_id = self.id

    def get_thread(self, thread_id: int):
        if self._existing_thread and self._existing_thread.id == thread_id and self._existing_thread.parent_id == self.id:
            return self._existing_thread
        return None

    async def create_thread(self, name: str, content: str):
        self._created_thread.name = name
        self._created_thread.parent = self
        self._created_thread.parent_id = self.id
        self._created_thread._starter_message.content = content

        class Created:
            def __init__(self, thread, message):
                self.thread = thread
                self.message = message

        return Created(self._created_thread, self._created_thread._starter_message)


class FakeClient:
    def __init__(self, channels_by_id: dict[int, object]):
        self._channels_by_id = channels_by_id

    def get_channel(self, channel_id: int):
        return self._channels_by_id.get(channel_id)

    async def fetch_channel(self, channel_id: int):
        return self._channels_by_id.get(channel_id)


class FakeResponse:
    def __init__(self):
        self.messages: list[tuple[str, bool]] = []

    async def send_message(self, message: str, ephemeral: bool = False):
        self.messages.append((message, ephemeral))


class FakeInteraction:
    def __init__(self, *, guild_id: int, user_id: int, guild_owner_id: int = 99):
        self.guild_id = guild_id
        self.guild = SimpleNamespace(id=guild_id, owner_id=guild_owner_id)
        self.user = SimpleNamespace(id=user_id)
        self.response = FakeResponse()


def _tree():
    client = discord.Client(intents=discord.Intents.none())
    return discord.app_commands.CommandTree(client), client


def _command_by_name(tree: discord.app_commands.CommandTree, name: str):
    return next(command for command in tree.get_commands() if command.name == name)


@pytest.mark.asyncio
async def test_upsert_watch_thread_creates_and_reuses_existing_thread(monkeypatch):
    monkeypatch.setattr(thread_service.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(thread_service.discord, "Thread", FakeThread)
    monkeypatch.setattr(thread_service.discord, "NotFound", FakeNotFound)
    monkeypatch.setattr(thread_service.discord, "Forbidden", FakeNotFound)
    monkeypatch.setattr(thread_service.discord, "HTTPException", FakeNotFound)

    state = {"commands": {}, "guilds": {}}
    created_thread = FakeThread(2001, FakeMessage(3001, "before"))
    channel = FakeForumChannel(456, 1, created_thread=created_thread)
    client = FakeClient({456: channel, 2001: created_thread})

    created = await thread_service.upsert_watch_thread(
        client,
        state,
        guild_id=1,
        forum_channel_id=456,
        symbol="KRX:005930",
        active=True,
        starter_text="starter-v1",
    )
    assert created.action == "created"
    assert state["commands"]["watchpoll"]["symbol_threads_by_guild"]["1"]["KRX:005930"]["thread_id"] == 2001

    channel._existing_thread = created_thread
    updated = await thread_service.upsert_watch_thread(
        client,
        state,
        guild_id=1,
        forum_channel_id=456,
        symbol="KRX:005930",
        active=True,
        starter_text="starter-v2",
    )
    assert updated.action == "updated"
    assert created_thread._starter_message.content == "starter-v2"


@pytest.mark.asyncio
async def test_upsert_watch_thread_recreates_when_starter_message_is_missing(monkeypatch):
    monkeypatch.setattr(thread_service.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(thread_service.discord, "Thread", FakeThread)
    monkeypatch.setattr(thread_service.discord, "NotFound", FakeNotFound)
    monkeypatch.setattr(thread_service.discord, "Forbidden", FakeNotFound)
    monkeypatch.setattr(thread_service.discord, "HTTPException", FakeNotFound)

    old_thread = FakeThread(2001, FakeMessage(3001, "gone"), missing_starter=True)
    new_thread = FakeThread(2002, FakeMessage(3002, "fresh"))
    state = {
        "commands": {
            "watchpoll": {
                "daily_posts_by_guild": {},
                "last_images": {},
                "symbol_threads_by_guild": {"1": {"KRX:005930": {"thread_id": 2001, "starter_message_id": 3001, "status": "active"}}},
            }
        },
        "guilds": {},
    }
    channel = FakeForumChannel(456, 1, existing_thread=old_thread, created_thread=new_thread)
    client = FakeClient({456: channel, 2001: old_thread, 2002: new_thread})

    recreated = await thread_service.upsert_watch_thread(
        client,
        state,
        guild_id=1,
        forum_channel_id=456,
        symbol="KRX:005930",
        active=True,
        starter_text="starter-v2",
    )

    assert recreated.action == "created"
    assert state["commands"]["watchpoll"]["symbol_threads_by_guild"]["1"]["KRX:005930"]["thread_id"] == 2002


@pytest.mark.asyncio
async def test_upsert_watch_thread_recreates_when_existing_thread_belongs_to_other_forum(monkeypatch):
    monkeypatch.setattr(thread_service.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(thread_service.discord, "Thread", FakeThread)
    monkeypatch.setattr(thread_service.discord, "NotFound", FakeNotFound)
    monkeypatch.setattr(thread_service.discord, "Forbidden", FakeNotFound)
    monkeypatch.setattr(thread_service.discord, "HTTPException", FakeNotFound)

    old_thread = FakeThread(2001, FakeMessage(3001, "old"), parent_id=455)
    new_thread = FakeThread(2002, FakeMessage(3002, "fresh"))
    state = {
        "commands": {
            "watchpoll": {
                "daily_posts_by_guild": {},
                "last_images": {},
                "symbol_threads_by_guild": {"1": {"KRX:005930": {"thread_id": 2001, "starter_message_id": 3001, "status": "active"}}},
            }
        },
        "guilds": {},
    }
    channel = FakeForumChannel(456, 1, created_thread=new_thread)
    client = FakeClient({456: channel, 2001: old_thread, 2002: new_thread})

    recreated = await thread_service.upsert_watch_thread(
        client,
        state,
        guild_id=1,
        forum_channel_id=456,
        symbol="KRX:005930",
        active=True,
        starter_text="starter-v2",
    )

    assert recreated.action == "created"
    assert state["commands"]["watchpoll"]["symbol_threads_by_guild"]["1"]["KRX:005930"]["thread_id"] == 2002


@pytest.mark.asyncio
async def test_setwatchforum_command_handles_success_unauthorized_and_foreign_forum(monkeypatch):
    tree, client = _tree()
    admin_command.register(tree, client)
    command = _command_by_name(tree, "setwatchforum")

    state = {"commands": {}, "guilds": {}}
    monkeypatch.setattr(admin_command, "load_state", lambda: state)
    monkeypatch.setattr(admin_command, "save_state", lambda _state: None)
    monkeypatch.setattr(admin_command, "DISCORD_GLOBAL_ADMIN_USER_IDS", {10})

    success = FakeInteraction(guild_id=1, user_id=10)
    await command.callback(success, FakeForumChannel(456, 1))
    assert state["guilds"]["1"]["watch_forum_channel_id"] == 456
    assert success.response.messages[-1][0] == "watch 포럼을 <#456> 로 설정했습니다."

    unauthorized = FakeInteraction(guild_id=1, user_id=11)
    await command.callback(unauthorized, FakeForumChannel(457, 1))
    assert unauthorized.response.messages[-1][0] == "권한이 없습니다."

    foreign = FakeInteraction(guild_id=1, user_id=10)
    await command.callback(foreign, FakeForumChannel(458, 2))
    assert foreign.response.messages[-1][0] == "같은 서버의 포럼 채널만 설정할 수 있습니다."


@pytest.mark.asyncio
async def test_watch_add_rejects_when_watch_forum_is_missing(monkeypatch):
    tree, client = _tree()
    watch_command.register(tree, client)
    group = _command_by_name(tree, "watch")
    add_command = next(command for command in group.commands if command.name == "add")

    state = {"commands": {}, "guilds": {"1": {}}}
    monkeypatch.setattr(watch_command, "load_state", lambda: state)
    monkeypatch.setattr(watch_command, "save_state", lambda _state: None)

    interaction = FakeInteraction(guild_id=1, user_id=10)
    await add_command.callback(interaction, "005930")

    assert interaction.response.messages[-1][0] == "watch 포럼이 설정되지 않았습니다. 운영자에게 `/setwatchforum` 설정을 요청해주세요."


@pytest.mark.asyncio
async def test_watch_remove_marks_thread_inactive(monkeypatch):
    tree, client = _tree()
    watch_command.register(tree, client)
    group = _command_by_name(tree, "watch")
    remove_command = next(command for command in group.commands if command.name == "remove")

    state = {
        "commands": {
            "watchpoll": {
                "daily_posts_by_guild": {},
                "last_images": {},
                "symbol_threads_by_guild": {"1": {"KRX:005930": {"thread_id": 2001, "starter_message_id": 3001, "status": "active"}}},
            }
        },
        "guilds": {"1": {"watch_forum_channel_id": 456, "watchlist": ["KRX:005930"]}},
    }
    calls: list[tuple[str, bool]] = []

    async def fake_upsert_watch_thread(**kwargs):
        calls.append((kwargs["symbol"], kwargs["active"]))
        return SimpleNamespace(action="updated")

    monkeypatch.setattr(watch_command, "load_state", lambda: state)
    monkeypatch.setattr(watch_command, "save_state", lambda _state: None)
    monkeypatch.setattr(watch_command, "upsert_watch_thread", fake_upsert_watch_thread)

    interaction = FakeInteraction(guild_id=1, user_id=10)
    await remove_command.callback(interaction, "005930")

    assert state["guilds"]["1"]["watchlist"] == []
    assert state["commands"]["watchpoll"]["symbol_threads_by_guild"]["1"]["KRX:005930"]["status"] == "inactive"
    assert calls == [("KRX:005930", False)]
