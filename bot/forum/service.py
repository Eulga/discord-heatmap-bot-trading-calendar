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
    content_texts: list[str] | None = None,
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
    existing_content_ids = record.get("content_message_ids", [])
    content_message_ids = [message_id for message_id in existing_content_ids if isinstance(message_id, int)]
    desired_content_texts = content_texts or []

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
        if thread.name != post_title:
            await thread.edit(name=post_title)
        await starter_message.edit(content=body_text, attachments=files)
        action = "updated"
        message = starter_message
    else:
        created = await channel.create_thread(name=post_title, content=body_text, files=files)
        thread = created.thread
        message = created.message
        action = "created"

    persisted_content_ids = list(content_message_ids)

    def persist_record(current_content_ids: list[int]) -> None:
        daily_posts[today] = {
            "thread_id": thread.id,
            "starter_message_id": message.id,
        }
        cleaned_ids = [content_id for content_id in current_content_ids if isinstance(content_id, int)]
        if cleaned_ids:
            daily_posts[today]["content_message_ids"] = cleaned_ids

    # Persist the thread as soon as the starter message is available so retries reuse
    # the existing daily thread even if syncing follow-up content fails midway.
    persist_record(persisted_content_ids)

    for index, content_text in enumerate(desired_content_texts):
        if index < len(content_message_ids):
            try:
                content_message = await thread.fetch_message(content_message_ids[index])
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                content_message = await thread.send(content_text)
            else:
                await content_message.edit(content=content_text)
        else:
            content_message = await thread.send(content_text)
        if index < len(persisted_content_ids):
            persisted_content_ids[index] = content_message.id
        else:
            persisted_content_ids.append(content_message.id)
        persist_record(persisted_content_ids)

    for content_message_id in content_message_ids[len(desired_content_texts) :]:
        try:
            content_message = await thread.fetch_message(content_message_id)
            await content_message.delete()
        except discord.NotFound:
            if content_message_id in persisted_content_ids:
                persisted_content_ids.remove(content_message_id)
                persist_record(persisted_content_ids)
            continue
        except (discord.Forbidden, discord.HTTPException):
            continue
        if content_message_id in persisted_content_ids:
            persisted_content_ids.remove(content_message_id)
            persist_record(persisted_content_ids)

    persist_record(persisted_content_ids)
    return thread, action
