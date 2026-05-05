from types import SimpleNamespace

import discord
import pytest

from bot.features.local_model import command as local_command
from bot.features.local_model.client import LocalModelError


class FakeResponse:
    def __init__(self):
        self.messages: list[tuple[str, bool]] = []
        self.deferred = False
        self.deferred_ephemeral: bool | None = None

    async def send_message(self, message: str, ephemeral: bool = False):
        self.messages.append((message, ephemeral))

    async def defer(self, thinking: bool, ephemeral: bool = False):
        self.deferred = thinking
        self.deferred_ephemeral = ephemeral


class FakeFollowup:
    def __init__(self):
        self.messages: list[tuple[str, bool]] = []

    async def send(self, message: str, ephemeral: bool = False):
        self.messages.append((message, ephemeral))


class FakeInteraction:
    def __init__(self, *, guild_id: int | None, user_id: int, guild_owner_id: int = 99):
        self.guild_id = guild_id
        self.guild = SimpleNamespace(id=guild_id, owner_id=guild_owner_id) if guild_id is not None else None
        self.user = SimpleNamespace(id=user_id)
        self.response = FakeResponse()
        self.followup = FakeFollowup()


def _tree():
    client = discord.Client(intents=discord.Intents.none())
    return discord.app_commands.CommandTree(client), client


def _command_by_name(tree: discord.app_commands.CommandTree, name: str):
    return next(command for command in tree.get_commands() if command.name == name)


def _local_ask_command(tree: discord.app_commands.CommandTree):
    group = _command_by_name(tree, "local")
    return next(command for command in group.commands if command.name == "ask")


@pytest.mark.asyncio
async def test_local_ask_rejects_when_disabled(monkeypatch):
    tree, client = _tree()
    local_command.register(tree, client)
    ask_command = _local_ask_command(tree)
    monkeypatch.setattr(local_command, "LOCAL_MODEL_ENABLED", False)

    interaction = FakeInteraction(guild_id=1, user_id=99, guild_owner_id=99)
    await ask_command.callback(interaction, "안녕")

    assert interaction.response.messages[-1] == ("로컬 모델 명령이 비활성화되어 있습니다.", True)
    assert interaction.response.deferred is False


@pytest.mark.asyncio
async def test_local_ask_rejects_unauthorized_user(monkeypatch):
    tree, client = _tree()
    local_command.register(tree, client)
    ask_command = _local_ask_command(tree)
    monkeypatch.setattr(local_command, "LOCAL_MODEL_ENABLED", True)
    monkeypatch.setattr(local_command, "DISCORD_GLOBAL_ADMIN_USER_IDS", set())

    interaction = FakeInteraction(guild_id=1, user_id=10, guild_owner_id=99)
    await ask_command.callback(interaction, "안녕")

    assert interaction.response.messages[-1] == ("권한이 없습니다.", True)
    assert interaction.response.deferred is False


@pytest.mark.asyncio
async def test_local_ask_calls_client_for_admin(monkeypatch):
    tree, client = _tree()
    local_command.register(tree, client)
    ask_command = _local_ask_command(tree)
    calls = {}

    async def fake_request_local_model(**kwargs):
        calls.update(kwargs)
        return "모델 응답"

    monkeypatch.setattr(local_command, "LOCAL_MODEL_ENABLED", True)
    monkeypatch.setattr(local_command, "LOCAL_MODEL_BASE_URL", "http://host.docker.internal:8081/v1")
    monkeypatch.setattr(local_command, "LOCAL_MODEL_NAME", "gemma-e4b")
    monkeypatch.setattr(local_command, "LOCAL_MODEL_TIMEOUT_SECONDS", 45)
    monkeypatch.setattr(local_command, "LOCAL_MODEL_MAX_PROMPT_CHARS", 2000)
    monkeypatch.setattr(local_command, "LOCAL_MODEL_MAX_RESPONSE_CHARS", 1800)
    monkeypatch.setattr(local_command, "DISCORD_GLOBAL_ADMIN_USER_IDS", {10})
    monkeypatch.setattr(local_command, "request_local_model", fake_request_local_model)

    interaction = FakeInteraction(guild_id=1, user_id=10, guild_owner_id=99)
    await ask_command.callback(interaction, " 안녕 ")

    assert interaction.response.deferred is True
    assert interaction.response.deferred_ephemeral is True
    assert interaction.followup.messages[-1] == ("모델 응답", True)
    assert calls["base_url"] == "http://host.docker.internal:8081/v1"
    assert calls["model"] == "gemma-e4b"
    assert calls["prompt"] == "안녕"


@pytest.mark.asyncio
async def test_local_ask_rejects_public_response_when_disabled(monkeypatch):
    tree, client = _tree()
    local_command.register(tree, client)
    ask_command = _local_ask_command(tree)
    monkeypatch.setattr(local_command, "LOCAL_MODEL_ENABLED", True)
    monkeypatch.setattr(local_command, "LOCAL_MODEL_PUBLIC_RESPONSES", False)

    interaction = FakeInteraction(guild_id=1, user_id=99, guild_owner_id=99)
    await ask_command.callback(interaction, "안녕", True)

    assert interaction.response.messages[-1] == ("로컬 모델 공개 응답은 현재 비활성화되어 있습니다.", True)
    assert interaction.response.deferred is False


@pytest.mark.asyncio
async def test_local_ask_handles_client_failure(monkeypatch):
    tree, client = _tree()
    local_command.register(tree, client)
    ask_command = _local_ask_command(tree)

    async def fake_request_local_model(**_kwargs):
        raise LocalModelError("bad response")

    monkeypatch.setattr(local_command, "LOCAL_MODEL_ENABLED", True)
    monkeypatch.setattr(local_command, "request_local_model", fake_request_local_model)

    interaction = FakeInteraction(guild_id=1, user_id=99, guild_owner_id=99)
    await ask_command.callback(interaction, "안녕")

    assert interaction.response.deferred is True
    assert "로컬 모델 호출에 실패했습니다" in interaction.followup.messages[-1][0]
    assert interaction.followup.messages[-1][1] is True
