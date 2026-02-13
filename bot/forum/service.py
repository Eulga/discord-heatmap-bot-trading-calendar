from pathlib import Path

import discord

from bot.app.types import AppState
from bot.common.clock import date_key
from bot.common.errors import ForumChannelTypeError
from bot.forum.repository import get_daily_posts_for_guild


async def upsert_daily_post(
    client: discord.Client,
    state: AppState,
    guild_id: int,
    forum_channel_id: int,
    command_key: str,
    post_title: str,
    body_text: str,
    image_paths: list[Path],
) -> tuple[discord.Thread, str]:
    channel = client.get_channel(forum_channel_id)
    if channel is None:
        channel = await client.fetch_channel(forum_channel_id)

    if not isinstance(channel, discord.ForumChannel):
        raise ForumChannelTypeError(f"Channel {forum_channel_id} is not a ForumChannel.")

    daily_posts = get_daily_posts_for_guild(state, command_key, guild_id)
    today = date_key()
    record = daily_posts.get(today, {})

    thread_id = record.get("thread_id")
    starter_message_id = record.get("starter_message_id")

    thread: discord.Thread | None = None
    starter_message: discord.Message | None = None

    if isinstance(thread_id, int) and isinstance(starter_message_id, int):
        try:
            candidate = channel.get_thread(thread_id)
            if candidate is None:
                fetched = await client.fetch_channel(thread_id)
                if isinstance(fetched, discord.Thread):
                    candidate = fetched
            if isinstance(candidate, discord.Thread):
                thread = candidate
                starter_message = await thread.fetch_message(starter_message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            thread = None
            starter_message = None

    files = [discord.File(path, filename=path.name) for path in image_paths]

    if thread is not None and starter_message is not None:
        await starter_message.edit(content=body_text, attachments=files)
        action = "updated"
        message = starter_message
    else:
        created = await channel.create_thread(name=post_title, content=body_text, files=files)
        thread = created.thread
        message = created.message
        action = "created"

    daily_posts[today] = {
        "thread_id": thread.id,
        "starter_message_id": message.id,
    }
    return thread, action
