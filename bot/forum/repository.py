import json
from typing import Any, cast

from bot.app.settings import LEGACY_STATE_FILE, STATE_FILE
from bot.app.types import AppState, CommandState, DailyPostEntry
from bot.common.fs import atomic_write_json
from bot.intel.instrument_registry import normalize_stored_watch_symbol


def _empty_state() -> AppState:
    return {"commands": {}, "guilds": {}}


def _migrate_legacy_state_file() -> None:
    if STATE_FILE == LEGACY_STATE_FILE:
        return
    if STATE_FILE.exists() or not LEGACY_STATE_FILE.exists():
        return
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LEGACY_STATE_FILE.replace(STATE_FILE)
    except OSError:
        return


def _get_state_file_for_read() -> Any:
    _migrate_legacy_state_file()
    if STATE_FILE.exists():
        return STATE_FILE
    if LEGACY_STATE_FILE.exists():
        return LEGACY_STATE_FILE
    return STATE_FILE


def load_state() -> AppState:
    state_file = _get_state_file_for_read()
    if not state_file.exists():
        return _empty_state()
    try:
        with state_file.open("r", encoding="utf-8") as f:
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
    if LEGACY_STATE_FILE != STATE_FILE and LEGACY_STATE_FILE.exists():
        try:
            LEGACY_STATE_FILE.unlink()
        except OSError:
            pass


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


def _get_guild_config(state: AppState, guild_id: int) -> dict[str, Any]:
    guilds = state.setdefault("guilds", {})
    cfg = guilds.setdefault(str(guild_id), {})
    if not isinstance(cfg, dict):
        cfg = {}
        guilds[str(guild_id)] = cfg
    return cast(dict[str, Any], cfg)


def set_guild_forum_channel_id(state: AppState, guild_id: int, channel_id: int) -> None:
    guild_cfg = _get_guild_config(state, guild_id)
    guild_cfg["forum_channel_id"] = channel_id


def get_guild_forum_channel_id(state: AppState, guild_id: int) -> int | None:
    guilds = state.get("guilds", {})
    guild_cfg = guilds.get(str(guild_id), {})
    channel_id = guild_cfg.get("forum_channel_id")
    if isinstance(channel_id, int):
        return channel_id
    return None


def set_guild_news_forum_channel_id(state: AppState, guild_id: int, channel_id: int) -> None:
    _get_guild_config(state, guild_id)["news_forum_channel_id"] = channel_id


def get_guild_news_forum_channel_id(state: AppState, guild_id: int) -> int | None:
    channel_id = _get_guild_config(state, guild_id).get("news_forum_channel_id")
    return channel_id if isinstance(channel_id, int) else None


def set_guild_eod_forum_channel_id(state: AppState, guild_id: int, channel_id: int) -> None:
    _get_guild_config(state, guild_id)["eod_forum_channel_id"] = channel_id


def get_guild_eod_forum_channel_id(state: AppState, guild_id: int) -> int | None:
    channel_id = _get_guild_config(state, guild_id).get("eod_forum_channel_id")
    return channel_id if isinstance(channel_id, int) else None


def set_guild_watch_alert_channel_id(state: AppState, guild_id: int, channel_id: int) -> None:
    _get_guild_config(state, guild_id)["watch_alert_channel_id"] = channel_id


def get_guild_watch_alert_channel_id(state: AppState, guild_id: int) -> int | None:
    channel_id = _get_guild_config(state, guild_id).get("watch_alert_channel_id")
    return channel_id if isinstance(channel_id, int) else None


def set_guild_auto_screenshot_enabled(state: AppState, guild_id: int, enabled: bool) -> None:
    _get_guild_config(state, guild_id)["auto_screenshot_enabled"] = enabled




def get_guild_auto_screenshot_enabled(state: AppState, guild_id: int) -> bool:
    value = _get_guild_config(state, guild_id).get("auto_screenshot_enabled")
    return value is True


def get_auto_enabled_guild_ids(state: AppState) -> list[int]:
    result: list[int] = []
    for guild_id_str, guild_cfg in state.get("guilds", {}).items():
        if not isinstance(guild_cfg, dict):
            continue
        if guild_cfg.get("auto_screenshot_enabled") is True and guild_id_str.isdigit():
            result.append(int(guild_id_str))
    return result


def get_guild_last_auto_run_date(state: AppState, guild_id: int, command_key: str) -> str | None:
    guild_cfg = _get_guild_config(state, guild_id)
    last_auto_runs = guild_cfg.get("last_auto_runs")
    if isinstance(last_auto_runs, dict):
        value = last_auto_runs.get(command_key)
        if isinstance(value, str):
            return value
    return None


def set_guild_last_auto_run_date(state: AppState, guild_id: int, command_key: str, date_text: str) -> None:
    guild_cfg = _get_guild_config(state, guild_id)
    last_auto_runs = guild_cfg.setdefault("last_auto_runs", {})
    if isinstance(last_auto_runs, dict):
        last_auto_runs[command_key] = date_text


def get_guild_last_auto_skip_date(state: AppState, guild_id: int, command_key: str) -> str | None:
    guild_cfg = _get_guild_config(state, guild_id)
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
    guild_cfg = _get_guild_config(state, guild_id)
    last_auto_skips = guild_cfg.setdefault("last_auto_skips", {})
    if isinstance(last_auto_skips, dict):
        last_auto_skips[command_key] = {"date": date_text, "reason": reason}


def list_guild_ids(state: AppState) -> list[int]:
    ids: list[int] = []
    for key in state.get("guilds", {}).keys():
        if key.isdigit():
            ids.append(int(key))
    return ids


def _normalize_watch_state(state: AppState, guild_id: int) -> list[str]:
    cfg = _get_guild_config(state, guild_id)
    watchlist = cfg.setdefault("watchlist", [])
    if not isinstance(watchlist, list):
        watchlist = []
        cfg["watchlist"] = watchlist

    normalized_list: list[str] = []
    seen: set[str] = set()
    migrated: dict[str, str] = {}

    for item in watchlist:
        if not isinstance(item, str):
            continue
        raw = item.strip().upper()
        if not raw:
            continue
        normalized, _warning = normalize_stored_watch_symbol(raw)
        target = normalized or raw
        if raw != target:
            migrated[raw] = target
        if target in seen:
            continue
        seen.add(target)
        normalized_list.append(target)

    normalized_list.sort()
    if watchlist != normalized_list:
        cfg["watchlist"] = normalized_list
    if migrated:
        _migrate_watch_baseline_keys(state, guild_id, migrated)
        _migrate_watch_cooldown_keys(state, guild_id, migrated)
        _migrate_watch_latch_keys(state, guild_id, migrated)
    return cast(list[str], cfg["watchlist"])


def _migrate_watch_baseline_keys(state: AppState, guild_id: int, migrated: dict[str, str]) -> None:
    watch_state = get_system_state(state).get("watch_baselines")
    if not isinstance(watch_state, dict):
        return
    guild_map = watch_state.get(str(guild_id))
    if not isinstance(guild_map, dict):
        return
    for old, new in migrated.items():
        value = guild_map.pop(old, None)
        if value is None or new in guild_map:
            continue
        guild_map[new] = value


def _migrate_watch_cooldown_keys(state: AppState, guild_id: int, migrated: dict[str, str]) -> None:
    cooldowns = _get_guild_config(state, guild_id).get("watch_alert_cooldowns")
    if not isinstance(cooldowns, dict):
        return
    moved: dict[str, str] = {}
    for key, hit_at in list(cooldowns.items()):
        if not isinstance(key, str) or not isinstance(hit_at, str):
            continue
        symbol, direction = key.rsplit(":", maxsplit=1) if ":" in key else (key, "")
        new_symbol = migrated.get(symbol.upper())
        if not new_symbol:
            continue
        new_key = f"{new_symbol}:{direction}" if direction else new_symbol
        if new_key not in cooldowns:
            moved[new_key] = hit_at
        cooldowns.pop(key, None)
    cooldowns.update(moved)


def _migrate_watch_latch_keys(state: AppState, guild_id: int, migrated: dict[str, str]) -> None:
    latches = _get_guild_config(state, guild_id).get("watch_alert_latches")
    if not isinstance(latches, dict):
        return
    moved: dict[str, str] = {}
    for key, direction in list(latches.items()):
        if not isinstance(key, str) or not isinstance(direction, str):
            continue
        new_key = migrated.get(key.upper())
        if not new_key:
            continue
        if new_key not in latches:
            moved[new_key] = direction
        latches.pop(key, None)
    latches.update(moved)


def _clear_watch_runtime_state(state: AppState, guild_id: int, symbol: str) -> None:
    normalized, _warning = normalize_stored_watch_symbol(symbol)
    target = normalized or symbol.strip().upper()
    guild_cfg = _get_guild_config(state, guild_id)

    cooldowns = guild_cfg.get("watch_alert_cooldowns")
    if isinstance(cooldowns, dict):
        for key in list(cooldowns.keys()):
            if not isinstance(key, str):
                continue
            key_symbol, _direction = key.rsplit(":", maxsplit=1) if ":" in key else (key, "")
            if key_symbol == target:
                cooldowns.pop(key, None)

    latches = guild_cfg.get("watch_alert_latches")
    if isinstance(latches, dict):
        latches.pop(target, None)

    watch_state = get_system_state(state).get("watch_baselines")
    if not isinstance(watch_state, dict):
        return
    guild_map = watch_state.get(str(guild_id))
    if not isinstance(guild_map, dict):
        return
    guild_map.pop(target, None)


def add_watch_symbol(state: AppState, guild_id: int, symbol: str) -> bool:
    normalized, _warning = normalize_stored_watch_symbol(symbol)
    if not normalized:
        return False
    watchlist = _normalize_watch_state(state, guild_id)
    if normalized in watchlist:
        return False
    watchlist.append(normalized)
    watchlist.sort()
    return True


def remove_watch_symbol(state: AppState, guild_id: int, symbol: str) -> bool:
    normalized, _warning = normalize_stored_watch_symbol(symbol)
    watchlist = _normalize_watch_state(state, guild_id)
    raw = symbol.strip().upper()
    target = normalized or raw
    if target not in watchlist and raw not in watchlist:
        return False
    removed_symbol = target if target in watchlist else raw
    watchlist.remove(removed_symbol)
    _clear_watch_runtime_state(state, guild_id, removed_symbol)
    return True


def list_watch_symbols(state: AppState, guild_id: int) -> list[str]:
    return [x for x in _normalize_watch_state(state, guild_id) if isinstance(x, str)]


def get_system_state(state: AppState) -> dict[str, Any]:
    system = state.setdefault("system", {})
    if not isinstance(system, dict):
        system = {}
        state["system"] = system
    return cast(dict[str, Any], system)


def set_job_last_run(state: AppState, job_key: str, status: str, detail: str) -> None:
    runs = get_system_state(state).setdefault("job_last_runs", {})
    if isinstance(runs, dict):
        from bot.common.clock import now_kst

        runs[job_key] = {
            "status": status,
            "detail": detail,
            "run_at": now_kst().isoformat(),
        }


def get_job_last_runs(state: AppState) -> dict[str, dict[str, str]]:
    value = get_system_state(state).get("job_last_runs")
    if isinstance(value, dict):
        return cast(dict[str, dict[str, str]], value)
    return {}


def set_provider_status(state: AppState, provider_key: str, ok: bool, message: str) -> None:
    providers = get_system_state(state).setdefault("provider_status", {})
    if isinstance(providers, dict):
        from bot.common.clock import now_kst

        providers[provider_key] = {
            "ok": ok,
            "message": message,
            "updated_at": now_kst().isoformat(),
        }


def get_provider_statuses(state: AppState) -> dict[str, dict[str, Any]]:
    value = get_system_state(state).get("provider_status")
    if isinstance(value, dict):
        return cast(dict[str, dict[str, Any]], value)
    return {}


def is_news_dedup_seen(state: AppState, dedup_key: str, date_text: str) -> bool:
    news_dedup = get_system_state(state).setdefault("news_dedup", {})
    if not isinstance(news_dedup, dict):
        return False
    keys = news_dedup.setdefault(date_text, [])
    if not isinstance(keys, list):
        return False
    return dedup_key in keys


def mark_news_dedup_seen(state: AppState, dedup_key: str, date_text: str) -> None:
    news_dedup = get_system_state(state).setdefault("news_dedup", {})
    if not isinstance(news_dedup, dict):
        return
    keys = news_dedup.setdefault(date_text, [])
    if not isinstance(keys, list):
        return
    if dedup_key not in keys:
        keys.append(dedup_key)


def get_watch_cooldown_hit(state: AppState, guild_id: int, key: str) -> str | None:
    cooldowns = _get_guild_config(state, guild_id).get("watch_alert_cooldowns")
    if not isinstance(cooldowns, dict):
        return None
    value = cooldowns.get(key)
    return value if isinstance(value, str) else None


def set_watch_cooldown_hit(state: AppState, guild_id: int, key: str, hit_at: str) -> None:
    cfg = _get_guild_config(state, guild_id)
    cooldowns = cfg.setdefault("watch_alert_cooldowns", {})
    if isinstance(cooldowns, dict):
        cooldowns[key] = hit_at


def get_watch_alert_latch(state: AppState, guild_id: int, symbol: str) -> str | None:
    latches = _get_guild_config(state, guild_id).get("watch_alert_latches")
    if not isinstance(latches, dict):
        return None
    normalized, _warning = normalize_stored_watch_symbol(symbol)
    value = latches.get(normalized or symbol.strip().upper())
    return value if isinstance(value, str) else None


def set_watch_alert_latch(state: AppState, guild_id: int, symbol: str, direction: str) -> None:
    cfg = _get_guild_config(state, guild_id)
    latches = cfg.setdefault("watch_alert_latches", {})
    if not isinstance(latches, dict):
        return
    normalized, _warning = normalize_stored_watch_symbol(symbol)
    latches[normalized or symbol.strip().upper()] = direction


def clear_watch_alert_latch(state: AppState, guild_id: int, symbol: str) -> None:
    latches = _get_guild_config(state, guild_id).get("watch_alert_latches")
    if not isinstance(latches, dict):
        return
    normalized, _warning = normalize_stored_watch_symbol(symbol)
    latches.pop(normalized or symbol.strip().upper(), None)


def get_watch_baseline(state: AppState, guild_id: int, symbol: str) -> float | None:
    watch_state = get_system_state(state).setdefault("watch_baselines", {})
    if not isinstance(watch_state, dict):
        return None
    guild_map = watch_state.get(str(guild_id))
    if not isinstance(guild_map, dict):
        return None
    normalized, _warning = normalize_stored_watch_symbol(symbol)
    value = guild_map.get((normalized or symbol.strip().upper()))
    if not isinstance(value, dict):
        return None
    price = value.get("price")
    return float(price) if isinstance(price, (int, float)) else None


def set_watch_baseline(state: AppState, guild_id: int, symbol: str, price: float, checked_at: str) -> None:
    watch_state = get_system_state(state).setdefault("watch_baselines", {})
    if not isinstance(watch_state, dict):
        return
    guild_map = watch_state.setdefault(str(guild_id), {})
    if not isinstance(guild_map, dict):
        return
    normalized, _warning = normalize_stored_watch_symbol(symbol)
    guild_map[(normalized or symbol.strip().upper())] = {"price": float(price), "checked_at": checked_at}


def cleanup_news_dedup(state: AppState, keep_recent_days: int = 7) -> None:
    news_dedup = get_system_state(state).get("news_dedup")
    if not isinstance(news_dedup, dict):
        return
    keys = sorted([k for k in news_dedup.keys() if isinstance(k, str)])
    if len(keys) <= keep_recent_days:
        return
    for old in keys[:-keep_recent_days]:
        news_dedup.pop(old, None)
