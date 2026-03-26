from __future__ import annotations

from dataclasses import dataclass

import discord

from bot.app.types import AppState
from bot.common.errors import ForumChannelTypeError
from bot.features.watch.service import render_watch_placeholder
from bot.forum.repository import get_watch_symbol_thread, set_watch_symbol_thread
from bot.intel.instrument_registry import format_watch_symbol


@dataclass(frozen=True)
class WatchThreadHandle:
    thread: discord.Thread
    starter_message: discord.Message
    action: str


def _watch_thread_title(symbol: str) -> str:
    return format_watch_symbol(symbol)


async def _resolve_forum_channel(
    client: discord.Client,
    *,
    guild_id: int,
    forum_channel_id: int,
) -> discord.ForumChannel:
    channel = client.get_channel(forum_channel_id)
    if channel is None:
        channel = await client.fetch_channel(forum_channel_id)
    channel_guild = getattr(channel, "guild", None)
    if not isinstance(channel, discord.ForumChannel) or getattr(channel_guild, "id", None) != guild_id:
        raise ForumChannelTypeError(f"Channel {forum_channel_id} is not a ForumChannel for guild {guild_id}.")
    return channel


async def _resolve_existing_thread(
    client: discord.Client,
    *,
    forum_channel: discord.ForumChannel,
    thread_id: int,
    starter_message_id: int,
) -> tuple[discord.Thread, discord.Message] | None:
    try:
        thread = forum_channel.get_thread(thread_id)
        if thread is None:
            fetched = await client.fetch_channel(thread_id)
            if isinstance(fetched, discord.Thread):
                thread = fetched
        if not isinstance(thread, discord.Thread):
            return None
        thread_guild = getattr(thread, "guild", None)
        if getattr(thread_guild, "id", None) != getattr(forum_channel.guild, "id", None):
            return None
        parent = getattr(thread, "parent", None)
        parent_id = getattr(thread, "parent_id", None)
        if parent_id is None and parent is not None:
            parent_id = getattr(parent, "id", None)
        if parent_id != forum_channel.id:
            return None
        starter_message = await thread.fetch_message(starter_message_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None
    return thread, starter_message


async def upsert_watch_thread(
    client: discord.Client,
    state: AppState,
    *,
    guild_id: int,
    forum_channel_id: int,
    symbol: str,
    active: bool,
    starter_text: str | None = None,
) -> WatchThreadHandle:
    forum_channel = await _resolve_forum_channel(client, guild_id=guild_id, forum_channel_id=forum_channel_id)
    desired_title = _watch_thread_title(symbol)
    desired_starter = starter_text
    existing = get_watch_symbol_thread(state, guild_id, symbol)

    if existing is not None:
        thread_id = existing.get("thread_id")
        starter_message_id = existing.get("starter_message_id")
        if isinstance(thread_id, int) and isinstance(starter_message_id, int):
            resolved = await _resolve_existing_thread(
                client,
                forum_channel=forum_channel,
                thread_id=thread_id,
                starter_message_id=starter_message_id,
            )
            if resolved is not None:
                thread, starter_message = resolved
                if thread.name != desired_title:
                    await thread.edit(name=desired_title)
                if desired_starter is not None:
                    await starter_message.edit(content=desired_starter)
                set_watch_symbol_thread(
                    state,
                    guild_id,
                    symbol,
                    thread_id=thread.id,
                    starter_message_id=starter_message.id,
                    status="active" if active else "inactive",
                )
                return WatchThreadHandle(thread=thread, starter_message=starter_message, action="updated")

    created = await forum_channel.create_thread(
        name=desired_title,
        content=desired_starter or render_watch_placeholder(symbol, active=active),
    )
    thread = created.thread
    starter_message = created.message
    set_watch_symbol_thread(
        state,
        guild_id,
        symbol,
        thread_id=thread.id,
        starter_message_id=starter_message.id,
        status="active" if active else "inactive",
    )
    return WatchThreadHandle(thread=thread, starter_message=starter_message, action="created")
