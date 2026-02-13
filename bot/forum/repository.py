import json
from typing import cast

from bot.app.settings import STATE_FILE
from bot.app.types import AppState, CommandState, DailyPostEntry, GuildConfig
from bot.common.fs import atomic_write_json


def _empty_state() -> AppState:
    return {"commands": {}, "guilds": {}}


def load_state() -> AppState:
    if not STATE_FILE.exists():
        return _empty_state()
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_state()

    if not isinstance(data, dict):
        return _empty_state()

    commands = data.get("commands")
    if not isinstance(commands, dict):
        data["commands"] = {}
    guilds = data.get("guilds")
    if not isinstance(guilds, dict):
        data["guilds"] = {}

    return cast(AppState, data)


def save_state(state: AppState) -> None:
    atomic_write_json(STATE_FILE, state)


def get_command_state(state: AppState, command_key: str) -> CommandState:
    commands = state.setdefault("commands", {})
    command_state = commands.setdefault(command_key, {})
    command_state.setdefault("daily_posts_by_guild", {})
    command_state.setdefault("last_images", {})
    return cast(CommandState, command_state)


def get_daily_posts_for_guild(state: AppState, command_key: str, guild_id: int) -> dict[str, DailyPostEntry]:
    command_state = get_command_state(state, command_key)
    posts_by_guild = command_state.setdefault("daily_posts_by_guild", {})
    guild_key = str(guild_id)
    posts = posts_by_guild.setdefault(guild_key, {})
    return cast(dict[str, DailyPostEntry], posts)


def set_guild_forum_channel_id(state: AppState, guild_id: int, channel_id: int) -> None:
    guilds = state.setdefault("guilds", {})
    guilds[str(guild_id)] = cast(GuildConfig, {"forum_channel_id": channel_id})


def get_guild_forum_channel_id(state: AppState, guild_id: int) -> int | None:
    guilds = state.get("guilds", {})
    guild_cfg = guilds.get(str(guild_id), {})
    channel_id = guild_cfg.get("forum_channel_id")
    if isinstance(channel_id, int):
        return channel_id
    return None
