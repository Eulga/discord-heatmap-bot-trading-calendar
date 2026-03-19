import pytest

from bot.forum import service
from bot.features import runner


class FakeMessage:
    def __init__(self, message_id: int):
        self.id = message_id
        self.edited = False
        self.deleted = False
        self.content = ""

    async def edit(self, content=None, attachments=None):
        self.edited = True
        if content is not None:
            self.content = content

    async def delete(self):
        self.deleted = True


class FakeThread:
    def __init__(self, thread_id: int, message: FakeMessage):
        self.id = thread_id
        self._message = message
        self.jump_url = f"https://discord.com/channels/thread/{thread_id}"
        self.name = "old-title"
        self.edited_name: str | None = None
        self._extra_messages: dict[int, FakeMessage] = {}
        self.sent_contents: list[str] = []

    async def fetch_message(self, message_id: int):
        if message_id != self._message.id:
            extra = self._extra_messages.get(message_id)
            if extra is None:
                raise RuntimeError("message mismatch")
            return extra
        return self._message

    async def edit(self, *, name: str):
        self.name = name
        self.edited_name = name

    async def send(self, content: str):
        message_id = max([self._message.id, *self._extra_messages.keys()], default=self._message.id) + 1
        message = FakeMessage(message_id)
        message.content = content
        self._extra_messages[message_id] = message
        self.sent_contents.append(content)
        return message


class FakeForumChannel:
    def __init__(self, existing_thread=None, created_thread=None):
        self._existing_thread = existing_thread
        self._created_thread = created_thread

    def get_thread(self, thread_id: int):
        if self._existing_thread and self._existing_thread.id == thread_id:
            return self._existing_thread
        return None

    async def create_thread(self, name, content, files):
        class Created:
            def __init__(self, thread, message):
                self.thread = thread
                self.message = message

        thread = self._created_thread or FakeThread(999, FakeMessage(555))
        return Created(thread, thread._message)


class FakeClient:
    def __init__(self, channel):
        self._channel = channel

    def get_channel(self, _):
        return self._channel

    async def fetch_channel(self, _):
        return self._channel


class FakeResponse:
    def __init__(self):
        self.deferred = False

    async def defer(self, thinking: bool):
        self.deferred = thinking


class FakeFollowup:
    def __init__(self):
        self.messages: list[str] = []

    async def send(self, message: str):
        self.messages.append(message)


class FakeInteraction:
    def __init__(self):
        self.response = FakeResponse()
        self.followup = FakeFollowup()
        self.guild_id = 1


@pytest.mark.asyncio
async def test_upsert_updates_existing(monkeypatch, tmp_path):
    monkeypatch.setattr(service.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(service.discord, "Thread", FakeThread)

    msg = FakeMessage(11)
    thread = FakeThread(22, msg)
    channel = FakeForumChannel(existing_thread=thread)
    client = FakeClient(channel)

    state = {
        "commands": {
            "kheatmap": {
                "daily_posts_by_guild": {"1": {service.date_key(): {"thread_id": 22, "starter_message_id": 11}}},
                "last_images": {},
            }
        },
        "guilds": {},
    }

    image = tmp_path / "a.png"
    image.write_bytes(b"x" * 1024)

    _, action = await service.upsert_daily_post(client, state, 1, 123, "kheatmap", "title", "body", [image])
    assert action == "updated"
    assert msg.edited is True
    assert thread.edited_name == "title"


@pytest.mark.asyncio
async def test_upsert_creates_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(service.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(service.discord, "Thread", FakeThread)

    channel = FakeForumChannel(existing_thread=None, created_thread=FakeThread(77, FakeMessage(88)))
    client = FakeClient(channel)

    state = {"commands": {"kheatmap": {"daily_posts_by_guild": {}, "last_images": {}}}, "guilds": {}}
    image = tmp_path / "a.png"
    image.write_bytes(b"x" * 1024)

    thread, action = await service.upsert_daily_post(client, state, 1, 123, "kheatmap", "title", "body", [image])
    assert action == "created"
    assert thread.id == 77


@pytest.mark.asyncio
async def test_upsert_syncs_content_messages(monkeypatch):
    monkeypatch.setattr(service.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(service.discord, "Thread", FakeThread)

    starter = FakeMessage(11)
    thread = FakeThread(22, starter)
    old_message = FakeMessage(30)
    thread._extra_messages[30] = old_message
    channel = FakeForumChannel(existing_thread=thread)
    client = FakeClient(channel)

    state = {
        "commands": {
            "trendbriefing": {
                "daily_posts_by_guild": {
                    "1": {
                        service.date_key(): {
                            "thread_id": 22,
                            "starter_message_id": 11,
                            "content_message_ids": [30],
                        }
                    }
                },
                "last_images": {},
            }
        },
        "guilds": {},
    }

    await service.upsert_daily_post(
        client,
        state,
        1,
        123,
        "trendbriefing",
        "trend title",
        "starter body",
        [],
        content_texts=["domestic chunk", "global chunk"],
    )

    record = state["commands"]["trendbriefing"]["daily_posts_by_guild"]["1"][service.date_key()]
    assert starter.edited is True
    assert old_message.edited is True
    assert old_message.content == "domestic chunk"
    assert len(record["content_message_ids"]) == 2
    new_message_id = record["content_message_ids"][1]
    assert thread._extra_messages[new_message_id].content == "global chunk"


@pytest.mark.asyncio
async def test_upsert_deletes_extra_content_messages(monkeypatch):
    monkeypatch.setattr(service.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(service.discord, "Thread", FakeThread)

    starter = FakeMessage(11)
    thread = FakeThread(22, starter)
    first = FakeMessage(30)
    second = FakeMessage(31)
    thread._extra_messages[30] = first
    thread._extra_messages[31] = second
    channel = FakeForumChannel(existing_thread=thread)
    client = FakeClient(channel)

    state = {
        "commands": {
            "trendbriefing": {
                "daily_posts_by_guild": {
                    "1": {
                        service.date_key(): {
                            "thread_id": 22,
                            "starter_message_id": 11,
                            "content_message_ids": [30, 31],
                        }
                    }
                },
                "last_images": {},
            }
        },
        "guilds": {},
    }

    await service.upsert_daily_post(
        client,
        state,
        1,
        123,
        "trendbriefing",
        "trend title",
        "starter body",
        [],
        content_texts=["only one chunk"],
    )

    record = state["commands"]["trendbriefing"]["daily_posts_by_guild"]["1"][service.date_key()]
    assert record["content_message_ids"] == [30]
    assert second.deleted is True


@pytest.mark.asyncio
async def test_runner_includes_partial_failure_in_body(monkeypatch):
    interaction = FakeInteraction()
    client = object()

    state = {"commands": {"kheatmap": {"daily_posts_by_guild": {}, "last_images": {}}}, "guilds": {}}
    captured = {"body": ""}

    async def fake_get_or_capture_images(state, command_key, targets, capture_func):
        return [], ["kospi: timed out while rendering"], {}

    async def fake_upsert_daily_post(client, state, command_key, post_title, body_text, image_paths):
        captured["body"] = body_text
        class Thread:
            jump_url = "https://discord.com/channels/thread/1"
        return Thread(), "updated"

    monkeypatch.setattr(runner, "load_state", lambda: state)
    monkeypatch.setattr(runner, "save_state", lambda _: None)
    monkeypatch.setattr(runner, "get_or_capture_images", fake_get_or_capture_images)
    monkeypatch.setattr(runner, "upsert_daily_post", fake_upsert_daily_post)
    monkeypatch.setattr(runner, "get_guild_forum_channel_id", lambda _state, _gid: 123)

    def body_builder(ts, src_lines, failed):
        return "\n".join([ts, "Failed:", *[f"- {x}" for x in failed]])

    await runner.run_heatmap_command(
        interaction=interaction,
        client=client,  # type: ignore[arg-type]
        command_key="kheatmap",
        targets={"kospi": "x"},
        capture_func=lambda *_: None,  # type: ignore[arg-type]
        title_builder=lambda: "[2026-02-13 한국장 히트맵]",
        body_builder=body_builder,
    )

    # when all fail, it should notify and avoid upsert
    assert any("업데이트하지 못했습니다" in msg for msg in interaction.followup.messages)


@pytest.mark.asyncio
async def test_runner_upserts_with_partial_failure(monkeypatch, tmp_path):
    interaction = FakeInteraction()
    client = object()
    state = {"commands": {"kheatmap": {"daily_posts_by_guild": {}, "last_images": {}}}, "guilds": {}}

    image = tmp_path / "ok.png"
    image.write_bytes(b"x" * 1024)
    captured_body = {"value": ""}

    async def fake_get_or_capture_images(state, command_key, targets, capture_func):
        return [image], ["kosdaq: timed out while rendering"], {"kospi": "captured"}

    async def fake_upsert_daily_post(client, state, guild_id, forum_channel_id, command_key, post_title, body_text, image_paths):
        captured_body["value"] = body_text
        class Thread:
            jump_url = "https://discord.com/channels/thread/2"
        return Thread(), "updated"

    monkeypatch.setattr(runner, "load_state", lambda: state)
    monkeypatch.setattr(runner, "save_state", lambda _: None)
    monkeypatch.setattr(runner, "get_or_capture_images", fake_get_or_capture_images)
    monkeypatch.setattr(runner, "upsert_daily_post", fake_upsert_daily_post)
    monkeypatch.setattr(runner, "get_guild_forum_channel_id", lambda _state, _gid: 123)

    def body_builder(ts, src_lines, failed):
        return "\n".join([ts, *src_lines, "Failed:", *[f"- {x}" for x in failed]])

    await runner.run_heatmap_command(
        interaction=interaction,
        client=client,  # type: ignore[arg-type]
        command_key="kheatmap",
        targets={"kospi": "x", "kosdaq": "y"},
        capture_func=lambda *_: None,  # type: ignore[arg-type]
        title_builder=lambda: "[2026-02-13 한국장 히트맵]",
        body_builder=body_builder,
    )

    assert "Failed:" in captured_body["value"]
    assert "kosdaq: timed out while rendering" in captured_body["value"]
    assert any("포스트 수정 완료" in msg for msg in interaction.followup.messages)
