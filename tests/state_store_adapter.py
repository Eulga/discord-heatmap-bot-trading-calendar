from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from bot.common.clock import date_key
from bot.forum import repository
from bot.forum.service import upsert_daily_post as real_upsert_daily_post
from bot.features.watch.thread_service import delete_watch_thread as real_delete_watch_thread
from bot.features.watch.thread_service import upsert_watch_thread as real_upsert_watch_thread
from bot.markets.capture_service import get_or_capture_images as real_get_or_capture_images


StateSource = dict[str, Any] | Callable[[], dict[str, Any]]
StateSink = Callable[[dict[str, Any]], None] | None


def patch_legacy_state_store(
    monkeypatch,
    module: Any,
    state_source: StateSource,
    save_state: StateSink = None,
) -> None:
    def load() -> dict[str, Any]:
        return state_source() if callable(state_source) else state_source

    def save(state: dict[str, Any]) -> None:
        if save_state is not None:
            save_state(state)

    def get(repo_func):
        return lambda *args, **kwargs: repo_func(load(), *args, **kwargs)

    def mutate(repo_func):
        def wrapper(*args, **kwargs):
            state = load()
            result = repo_func(state, *args, **kwargs)
            save(state)
            return result

        return wrapper

    def get_daily_post_record(command_key: str, guild_id: int, post_date: str | None = None):
        return repository.get_daily_posts_for_guild(load(), command_key, guild_id).get(post_date or date_key())

    def copy_daily_post_if_missing(source_command_key: str, target_command_key: str, guild_id: int, post_date: str) -> None:
        state = load()
        source = repository.get_daily_posts_for_guild(state, source_command_key, guild_id)
        target = repository.get_daily_posts_for_guild(state, target_command_key, guild_id)
        if post_date in source and post_date not in target:
            target[post_date] = source[post_date]
            save(state)

    def replace_watch_session_alert(guild_id: int, symbol: str, entry: dict[str, Any]):
        state = load()
        replacement = deepcopy(entry)
        current = repository.get_watch_session_alert(state, guild_id, symbol)
        current.clear()
        current.update(replacement)
        save(state)
        return current

    def mutate_watch_session_alert(guild_id: int, symbol: str, mutator: Callable[[dict[str, Any]], None]):
        state = load()
        current = repository.get_watch_session_alert(state, guild_id, symbol)
        mutator(current)
        save(state)
        return current

    def get_command_image_cache(command_key: str):
        return repository.get_command_state(load(), command_key).get("last_images", {})

    def upsert_command_image_cache(
        command_key: str,
        market_label: str,
        path: str,
        captured_at: str,
        *,
        last_run_at: str | None = None,
    ) -> None:
        state = load()
        command = repository.get_command_state(state, command_key)
        command.setdefault("last_images", {})[market_label] = {"path": path, "captured_at": captured_at}
        if last_run_at is not None:
            command["last_run_at"] = last_run_at
        save(state)

    def upsert_daily_post_record(
        command_key: str,
        guild_id: int,
        post_date: str,
        thread_id: int,
        starter_message_id: int,
        content_message_ids: list[int] | None = None,
    ) -> None:
        state = load()
        post = {"thread_id": int(thread_id), "starter_message_id": int(starter_message_id)}
        if content_message_ids:
            post["content_message_ids"] = [int(item) for item in content_message_ids]
        repository.get_daily_posts_for_guild(state, command_key, guild_id)[post_date] = post
        save(state)

    async def upsert_daily_post(**kwargs):
        kwargs["state"] = load()
        result = await real_upsert_daily_post(**kwargs)
        save(kwargs["state"])
        return result

    async def get_or_capture_images(**kwargs):
        kwargs["state"] = load()
        result = await real_get_or_capture_images(**kwargs)
        save(kwargs["state"])
        return result

    async def upsert_watch_thread(**kwargs):
        kwargs["state"] = load()
        result = await real_upsert_watch_thread(**kwargs)
        save(kwargs["state"])
        return result

    async def delete_watch_thread(**kwargs):
        kwargs["state"] = load()
        result = await real_delete_watch_thread(**kwargs)
        save(kwargs["state"])
        return result

    patches = {
        "load_state": load,
        "save_state": save,
        "get_guild_forum_channel_id": get(repository.get_guild_forum_channel_id),
        "get_guild_news_forum_channel_id": get(repository.get_guild_news_forum_channel_id),
        "get_guild_eod_forum_channel_id": get(repository.get_guild_eod_forum_channel_id),
        "get_guild_watch_forum_channel_id": get(repository.get_guild_watch_forum_channel_id),
        "set_guild_forum_channel_id": mutate(repository.set_guild_forum_channel_id),
        "set_guild_news_forum_channel_id": mutate(repository.set_guild_news_forum_channel_id),
        "set_guild_eod_forum_channel_id": mutate(repository.set_guild_eod_forum_channel_id),
        "set_guild_watch_forum_channel_id": mutate(repository.set_guild_watch_forum_channel_id),
        "set_guild_auto_screenshot_enabled": mutate(repository.set_guild_auto_screenshot_enabled),
        "get_auto_enabled_guild_ids": get(repository.get_auto_enabled_guild_ids),
        "get_guild_last_auto_attempt_date": get(repository.get_guild_last_auto_attempt_date),
        "get_guild_last_auto_run_date": get(repository.get_guild_last_auto_run_date),
        "get_guild_last_auto_skip_date": get(repository.get_guild_last_auto_skip_date),
        "set_guild_last_auto_attempt_date": mutate(repository.set_guild_last_auto_attempt_date),
        "set_guild_last_auto_run_date": mutate(repository.set_guild_last_auto_run_date),
        "set_guild_last_auto_skip": mutate(repository.set_guild_last_auto_skip),
        "list_guild_ids": get(repository.list_guild_ids),
        "get_daily_post_record": get_daily_post_record,
        "copy_daily_post_if_missing": copy_daily_post_if_missing,
        "get_command_image_cache": get_command_image_cache,
        "upsert_command_image_cache": upsert_command_image_cache,
        "upsert_daily_post_record": upsert_daily_post_record,
        "set_job_last_run": mutate(repository.set_job_last_run),
        "get_job_last_runs": get(repository.get_job_last_runs),
        "set_provider_status": mutate(repository.set_provider_status),
        "get_provider_statuses": get(repository.get_provider_statuses),
        "add_watch_symbol": mutate(repository.add_watch_symbol),
        "delete_watch_symbol": mutate(repository.delete_watch_symbol),
        "clear_watch_symbol_runtime_state": mutate(repository.clear_watch_symbol_runtime_state),
        "list_watch_symbols": get(repository.list_watch_symbols),
        "list_active_watch_symbols": get(repository.list_active_watch_symbols),
        "list_watch_tracked_symbols": get(repository.list_watch_tracked_symbols),
        "get_watch_symbol_status": get(repository.get_watch_symbol_status),
        "get_watch_symbol_thread": get(repository.get_watch_symbol_thread),
        "set_watch_symbol_thread": mutate(repository.set_watch_symbol_thread),
        "set_watch_symbol_thread_status": mutate(repository.set_watch_symbol_thread_status),
        "get_watch_reference_snapshot": get(repository.get_watch_reference_snapshot),
        "set_watch_reference_snapshot": mutate(repository.set_watch_reference_snapshot),
        "get_watch_session_alert": get(repository.get_watch_session_alert),
        "update_watch_session_alert": mutate(repository.update_watch_session_alert),
        "set_watch_current_comment_id": mutate(repository.set_watch_current_comment_id),
        "clear_watch_current_comment_id": mutate(repository.clear_watch_current_comment_id),
        "mutate_watch_session_alert": mutate_watch_session_alert,
        "replace_watch_session_alert": replace_watch_session_alert,
        "get_watch_cooldown_hit": get(repository.get_watch_cooldown_hit),
        "set_watch_cooldown_hit": mutate(repository.set_watch_cooldown_hit),
        "get_watch_alert_latch": get(repository.get_watch_alert_latch),
        "set_watch_alert_latch": mutate(repository.set_watch_alert_latch),
        "clear_watch_alert_latch": mutate(repository.clear_watch_alert_latch),
        "get_watch_baseline": get(repository.get_watch_baseline),
        "set_watch_baseline": mutate(repository.set_watch_baseline),
        "is_news_dedup_seen": get(repository.is_news_dedup_seen),
        "mark_news_dedup_seen": mutate(repository.mark_news_dedup_seen),
        "cleanup_news_dedup": mutate(repository.cleanup_news_dedup),
        "upsert_daily_post": upsert_daily_post,
        "get_or_capture_images": get_or_capture_images,
        "upsert_watch_thread": upsert_watch_thread,
        "delete_watch_thread": delete_watch_thread,
    }
    for name, value in patches.items():
        monkeypatch.setattr(module, name, value, raising=False)
