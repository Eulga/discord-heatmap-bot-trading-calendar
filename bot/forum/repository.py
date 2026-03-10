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
    guild_cfg = guilds.setdefault(str(guild_id), {})
    guild_cfg["forum_channel_id"] = channel_id


def get_guild_forum_channel_id(state: AppState, guild_id: int) -> int | None:
    guilds = state.get("guilds", {})
    guild_cfg = guilds.get(str(guild_id), {})
    channel_id = guild_cfg.get("forum_channel_id")
    if isinstance(channel_id, int):
        return channel_id
    return None


def set_guild_auto_screenshot_enabled(state: AppState, guild_id: int, enabled: bool) -> None:
    guilds = state.setdefault("guilds", {})
    guild_cfg = guilds.setdefault(str(guild_id), {})
    guild_cfg["auto_screenshot_enabled"] = enabled


def get_guild_auto_screenshot_enabled(state: AppState, guild_id: int) -> bool:
    guilds = state.get("guilds", {})
    guild_cfg = guilds.get(str(guild_id), {})
    value = guild_cfg.get("auto_screenshot_enabled")
    return bool(value)


def get_auto_enabled_guild_ids(state: AppState) -> list[int]:
    result: list[int] = []
    for guild_id_str, guild_cfg in state.get("guilds", {}).items():
        if not isinstance(guild_cfg, dict):
            continue
        if guild_cfg.get("auto_screenshot_enabled") is True and guild_id_str.isdigit():
            result.append(int(guild_id_str))
    return result


def get_guild_last_auto_run_date(state: AppState, guild_id: int, command_key: str) -> str | None:
    guilds = state.get("guilds", {})
    guild_cfg = guilds.get(str(guild_id), {})
    last_auto_runs = guild_cfg.get("last_auto_runs")
    if isinstance(last_auto_runs, dict):
        value = last_auto_runs.get(command_key)
        if isinstance(value, str):
            return value
    return None


def set_guild_last_auto_run_date(state: AppState, guild_id: int, command_key: str, date_text: str) -> None:
    guilds = state.setdefault("guilds", {})
    guild_cfg = guilds.setdefault(str(guild_id), {})
    last_auto_runs = guild_cfg.setdefault("last_auto_runs", {})
    if isinstance(last_auto_runs, dict):
        last_auto_runs[command_key] = date_text


def get_guild_last_auto_skip_date(state: AppState, guild_id: int, command_key: str) -> str | None:
    guilds = state.get("guilds", {})
    guild_cfg = guilds.get(str(guild_id), {})
    last_auto_skips = guild_cfg.get("last_auto_skips")
    if not isinstance(last_auto_skips, dict):
        return None
    command_skip = last_auto_skips.get(command_key)
    if not isinstance(command_skip, dict):
        return None
    date_value = command_skip.get("date")
    if isinstance(date_value, str):
        return date_value
    return None


def set_guild_last_auto_skip(
    state: AppState,
    guild_id: int,
    command_key: str,
    date_text: str,
    reason: str,
) -> None:
    guilds = state.setdefault("guilds", {})
    guild_cfg = guilds.setdefault(str(guild_id), {})
    last_auto_skips = guild_cfg.setdefault("last_auto_skips", {})
    if isinstance(last_auto_skips, dict):
        last_auto_skips[command_key] = {"date": date_text, "reason": reason}
