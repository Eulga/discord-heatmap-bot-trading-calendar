from __future__ import annotations

import json
import zlib
from collections.abc import Callable, Iterable
from typing import Any, cast

from bot.app.settings import DATABASE_URL, POSTGRES_STATE_KEY, STATE_BACKEND
from bot.app.types import AppState, DailyPostEntry, WatchReferenceSnapshotEntry, WatchSessionAlertEntry, WatchThreadEntry
from bot.common.clock import date_key, now_kst
from bot.forum import repository as legacy_repository
from bot.intel.instrument_registry import normalize_stored_watch_symbol

MIGRATION_SPLIT_STATE_V1 = "split_state_v1"

_SCHEMA_READY = False
_UNSET = object()


def _state_key() -> str:
    return POSTGRES_STATE_KEY


def _require_postgres_backend() -> None:
    backend = (STATE_BACKEND or "").strip().lower()
    if backend not in {"postgres", "postgresql"}:
        raise RuntimeError("PostgreSQL state store requires STATE_BACKEND=postgres.")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required for the PostgreSQL state store.")


def _import_psycopg() -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required for the PostgreSQL state store.") from exc
    return psycopg


def _connect() -> Any:
    _require_postgres_backend()
    return _import_psycopg().connect(DATABASE_URL)


def reset_schema_cache_for_tests() -> None:
    global _SCHEMA_READY
    _SCHEMA_READY = False


def _normalize_symbol(symbol: str) -> str:
    normalized, _warning = normalize_stored_watch_symbol(symbol)
    return normalized or symbol.strip().upper()


def _int_or_none(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _float_or_none(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return [int(item) for item in value if isinstance(item, int) and not isinstance(item, bool)]


def _split_state(state: AppState) -> dict[str, list[dict[str, Any]]]:
    state = legacy_repository._normalize_state(state)
    rows: dict[str, list[dict[str, Any]]] = {
        "guild_config": [],
        "guild_job_markers": [],
        "daily_posts": [],
        "command_image_cache": [],
        "watch_symbols": [],
        "watch_reference_snapshots": [],
        "watch_session_alerts": [],
        "watch_alert_cooldowns": [],
        "watch_alert_latches": [],
        "watch_baselines": [],
        "job_status": [],
        "provider_status": [],
        "news_dedup": [],
    }

    guilds = state.get("guilds", {})
    if isinstance(guilds, dict):
        for guild_key, raw_cfg in guilds.items():
            if not str(guild_key).isdigit() or not isinstance(raw_cfg, dict):
                continue
            guild_id = int(guild_key)
            rows["guild_config"].append(
                {
                    "guild_id": guild_id,
                    "forum_channel_id": _int_or_none(raw_cfg.get("forum_channel_id")),
                    "news_forum_channel_id": _int_or_none(raw_cfg.get("news_forum_channel_id")),
                    "eod_forum_channel_id": _int_or_none(raw_cfg.get("eod_forum_channel_id")),
                    "watch_forum_channel_id": _int_or_none(raw_cfg.get("watch_forum_channel_id")),
                    "legacy_watch_alert_channel_id": _int_or_none(raw_cfg.get("watch_alert_channel_id")),
                    "auto_screenshot_enabled": raw_cfg.get("auto_screenshot_enabled") is True,
                }
            )
            marker_keys: set[str] = set()
            for key in ("last_auto_attempts", "last_auto_runs", "last_auto_skips"):
                value = raw_cfg.get(key)
                if isinstance(value, dict):
                    marker_keys.update(str(item) for item in value.keys() if isinstance(item, str))
            for job_key in sorted(marker_keys):
                skips = raw_cfg.get("last_auto_skips")
                skip_entry = skips.get(job_key) if isinstance(skips, dict) else None
                skip_date = skip_entry.get("date") if isinstance(skip_entry, dict) else None
                skip_reason = skip_entry.get("reason") if isinstance(skip_entry, dict) else None
                rows["guild_job_markers"].append(
                    {
                        "guild_id": guild_id,
                        "job_key": job_key,
                        "last_attempt_date": (raw_cfg.get("last_auto_attempts") or {}).get(job_key)
                        if isinstance(raw_cfg.get("last_auto_attempts"), dict)
                        else None,
                        "last_run_date": (raw_cfg.get("last_auto_runs") or {}).get(job_key)
                        if isinstance(raw_cfg.get("last_auto_runs"), dict)
                        else None,
                        "last_skip_date": skip_date,
                        "last_skip_reason": skip_reason,
                    }
                )
            watchlist = raw_cfg.get("watchlist")
            if isinstance(watchlist, list):
                for item in watchlist:
                    if isinstance(item, str):
                        symbol = _normalize_symbol(item)
                        if symbol:
                            rows["watch_symbols"].append({"guild_id": guild_id, "symbol": symbol, "status": "active"})
            cooldowns = raw_cfg.get("watch_alert_cooldowns")
            if isinstance(cooldowns, dict):
                for key, hit_at in cooldowns.items():
                    if isinstance(key, str) and isinstance(hit_at, str):
                        rows["watch_alert_cooldowns"].append({"guild_id": guild_id, "alert_key": key, "hit_at": hit_at})
            latches = raw_cfg.get("watch_alert_latches")
            if isinstance(latches, dict):
                for symbol, direction in latches.items():
                    if isinstance(symbol, str) and isinstance(direction, str):
                        rows["watch_alert_latches"].append(
                            {"guild_id": guild_id, "symbol": _normalize_symbol(symbol), "direction": direction}
                        )

    commands = state.get("commands", {})
    if isinstance(commands, dict):
        for command_key, raw_command in commands.items():
            if not isinstance(command_key, str) or not isinstance(raw_command, dict):
                continue
            last_run_at = raw_command.get("last_run_at") if isinstance(raw_command.get("last_run_at"), str) else None
            last_images = raw_command.get("last_images")
            if isinstance(last_images, dict):
                for market_label, raw_cache in last_images.items():
                    if not isinstance(market_label, str) or not isinstance(raw_cache, dict):
                        continue
                    rows["command_image_cache"].append(
                        {
                            "command_key": command_key,
                            "market_label": market_label,
                            "path": raw_cache.get("path") if isinstance(raw_cache.get("path"), str) else None,
                            "captured_at": raw_cache.get("captured_at")
                            if isinstance(raw_cache.get("captured_at"), str)
                            else None,
                            "last_run_at": last_run_at,
                        }
                    )
            daily_posts = raw_command.get("daily_posts_by_guild")
            if isinstance(daily_posts, dict):
                for guild_key, posts_by_date in daily_posts.items():
                    if not str(guild_key).isdigit() or not isinstance(posts_by_date, dict):
                        continue
                    for post_date, raw_post in posts_by_date.items():
                        if not isinstance(post_date, str) or not isinstance(raw_post, dict):
                            continue
                        thread_id = _int_or_none(raw_post.get("thread_id"))
                        starter_message_id = _int_or_none(raw_post.get("starter_message_id"))
                        if thread_id is None or starter_message_id is None:
                            continue
                        rows["daily_posts"].append(
                            {
                                "command_key": command_key,
                                "guild_id": int(guild_key),
                                "post_date": post_date,
                                "thread_id": thread_id,
                                "starter_message_id": starter_message_id,
                                "content_message_ids": _int_list(raw_post.get("content_message_ids")),
                            }
                        )
            if command_key == "watchpoll":
                symbols_by_guild = raw_command.get("symbol_threads_by_guild")
                if isinstance(symbols_by_guild, dict):
                    for guild_key, raw_symbols in symbols_by_guild.items():
                        if not str(guild_key).isdigit() or not isinstance(raw_symbols, dict):
                            continue
                        guild_id = int(guild_key)
                        for symbol, raw_entry in raw_symbols.items():
                            if not isinstance(symbol, str) or not isinstance(raw_entry, dict):
                                continue
                            status = str(raw_entry.get("status") or "active").lower()
                            rows["watch_symbols"].append(
                                {
                                    "guild_id": guild_id,
                                    "symbol": _normalize_symbol(symbol),
                                    "status": "inactive" if status == "inactive" else "active",
                                    "thread_id": _int_or_none(raw_entry.get("thread_id")),
                                    "starter_message_id": _int_or_none(raw_entry.get("starter_message_id")),
                                }
                            )

    system = state.get("system", {})
    if isinstance(system, dict):
        baselines = system.get("watch_baselines")
        if isinstance(baselines, dict):
            for guild_key, raw_symbols in baselines.items():
                if not str(guild_key).isdigit() or not isinstance(raw_symbols, dict):
                    continue
                for symbol, raw_entry in raw_symbols.items():
                    if not isinstance(symbol, str) or not isinstance(raw_entry, dict):
                        continue
                    price = _float_or_none(raw_entry.get("price"))
                    checked_at = _str_or_none(raw_entry.get("checked_at"))
                    if price is not None and checked_at is not None:
                        rows["watch_baselines"].append(
                            {"guild_id": int(guild_key), "symbol": _normalize_symbol(symbol), "price": price, "checked_at": checked_at}
                        )
        refs = system.get("watch_reference_snapshots")
        if isinstance(refs, dict):
            for guild_key, raw_symbols in refs.items():
                if not str(guild_key).isdigit() or not isinstance(raw_symbols, dict):
                    continue
                for symbol, raw_entry in raw_symbols.items():
                    if not isinstance(symbol, str) or not isinstance(raw_entry, dict):
                        continue
                    reference_price = _float_or_none(raw_entry.get("reference_price"))
                    if reference_price is None:
                        continue
                    rows["watch_reference_snapshots"].append(
                        {
                            "guild_id": int(guild_key),
                            "symbol": _normalize_symbol(symbol),
                            "basis": str(raw_entry.get("basis") or ""),
                            "reference_price": reference_price,
                            "session_date": str(raw_entry.get("session_date") or ""),
                            "checked_at": str(raw_entry.get("checked_at") or ""),
                        }
                    )
        alerts = system.get("watch_session_alerts")
        if isinstance(alerts, dict):
            for guild_key, raw_symbols in alerts.items():
                if not str(guild_key).isdigit() or not isinstance(raw_symbols, dict):
                    continue
                for symbol, raw_entry in raw_symbols.items():
                    if not isinstance(symbol, str) or not isinstance(raw_entry, dict):
                        continue
                    rows["watch_session_alerts"].append(_watch_alert_row_from_entry(int(guild_key), symbol, raw_entry))
        runs = system.get("job_last_runs")
        if isinstance(runs, dict):
            for job_key, raw_entry in runs.items():
                if isinstance(job_key, str) and isinstance(raw_entry, dict):
                    rows["job_status"].append(
                        {
                            "job_key": job_key,
                            "status": str(raw_entry.get("status") or ""),
                            "detail": str(raw_entry.get("detail") or ""),
                            "run_at": str(raw_entry.get("run_at") or ""),
                        }
                    )
        providers = system.get("provider_status")
        if isinstance(providers, dict):
            for provider_key, raw_entry in providers.items():
                if isinstance(provider_key, str) and isinstance(raw_entry, dict):
                    rows["provider_status"].append(
                        {
                            "provider_key": provider_key,
                            "ok": raw_entry.get("ok") is True,
                            "message": str(raw_entry.get("message") or ""),
                            "updated_at": str(raw_entry.get("updated_at") or ""),
                        }
                    )
        dedup = system.get("news_dedup")
        if isinstance(dedup, dict):
            for dedup_date, keys in dedup.items():
                if isinstance(dedup_date, str) and isinstance(keys, list):
                    for dedup_key in keys:
                        if isinstance(dedup_key, str):
                            rows["news_dedup"].append({"date_text": dedup_date, "dedup_key": dedup_key})

    rows["watch_symbols"] = list(_dedupe_rows(rows["watch_symbols"], ("guild_id", "symbol")))
    return rows


def _dedupe_rows(rows: Iterable[dict[str, Any]], key_fields: tuple[str, ...]) -> Iterable[dict[str, Any]]:
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(row.get(field) for field in key_fields)
        current = merged.get(key)
        if current is None:
            merged[key] = dict(row)
            continue
        current.update({field: value for field, value in row.items() if value is not None})
        if row.get("status") == "inactive":
            current["status"] = "inactive"
    return merged.values()


def _watch_alert_row_from_entry(guild_id: int, symbol: str, entry: dict[str, Any]) -> dict[str, Any]:
    close_ids = entry.get("close_comment_ids_by_session")
    pending = entry.get("pending_close_sessions")
    return {
        "guild_id": guild_id,
        "symbol": _normalize_symbol(symbol),
        "active_session_date": _str_or_none(entry.get("active_session_date")),
        "highest_up_band": int(entry.get("highest_up_band") or 0),
        "highest_down_band": int(entry.get("highest_down_band") or 0),
        "current_comment_id": _int_or_none(entry.get("current_comment_id")),
        "intraday_comment_ids": _int_list(entry.get("intraday_comment_ids")),
        "close_comment_ids_by_session": close_ids if isinstance(close_ids, dict) else {},
        "pending_close_sessions": pending if isinstance(pending, dict) else {},
        "last_finalized_session_date": _str_or_none(entry.get("last_finalized_session_date")),
        "updated_at": _str_or_none(entry.get("updated_at")),
    }


def _ensure_schema(cursor: Any) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_app_state (
            state_key TEXT PRIMARY KEY,
            state JSONB NOT NULL,
            version BIGINT NOT NULL DEFAULT 1,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    cursor.execute("ALTER TABLE bot_app_state ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_state_migrations (
            state_key TEXT NOT NULL,
            migration_id TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, migration_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_guild_config (
            state_key TEXT NOT NULL,
            guild_id BIGINT NOT NULL,
            forum_channel_id BIGINT,
            news_forum_channel_id BIGINT,
            eod_forum_channel_id BIGINT,
            watch_forum_channel_id BIGINT,
            legacy_watch_alert_channel_id BIGINT,
            auto_screenshot_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, guild_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_guild_job_markers (
            state_key TEXT NOT NULL,
            guild_id BIGINT NOT NULL,
            job_key TEXT NOT NULL,
            last_attempt_date TEXT,
            last_run_date TEXT,
            last_skip_date TEXT,
            last_skip_reason TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, guild_id, job_key)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_daily_posts (
            state_key TEXT NOT NULL,
            command_key TEXT NOT NULL,
            guild_id BIGINT NOT NULL,
            post_date TEXT NOT NULL,
            thread_id BIGINT NOT NULL,
            starter_message_id BIGINT NOT NULL,
            content_message_ids BIGINT[] NOT NULL DEFAULT '{}',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, command_key, guild_id, post_date)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_command_image_cache (
            state_key TEXT NOT NULL,
            command_key TEXT NOT NULL,
            market_label TEXT NOT NULL,
            path TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            last_run_at TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, command_key, market_label)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_watch_symbols (
            state_key TEXT NOT NULL,
            guild_id BIGINT NOT NULL,
            symbol TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            thread_id BIGINT,
            starter_message_id BIGINT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, guild_id, symbol)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_watch_reference_snapshots (
            state_key TEXT NOT NULL,
            guild_id BIGINT NOT NULL,
            symbol TEXT NOT NULL,
            basis TEXT NOT NULL,
            reference_price DOUBLE PRECISION NOT NULL,
            session_date TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, guild_id, symbol)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_watch_session_alerts (
            state_key TEXT NOT NULL,
            guild_id BIGINT NOT NULL,
            symbol TEXT NOT NULL,
            active_session_date TEXT,
            highest_up_band INTEGER NOT NULL DEFAULT 0,
            highest_down_band INTEGER NOT NULL DEFAULT 0,
            current_comment_id BIGINT,
            intraday_comment_ids BIGINT[] NOT NULL DEFAULT '{}',
            close_comment_ids_by_session JSONB NOT NULL DEFAULT '{}'::jsonb,
            pending_close_sessions JSONB NOT NULL DEFAULT '{}'::jsonb,
            last_finalized_session_date TEXT,
            updated_at TEXT,
            row_updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, guild_id, symbol)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_watch_alert_cooldowns (
            state_key TEXT NOT NULL,
            guild_id BIGINT NOT NULL,
            alert_key TEXT NOT NULL,
            hit_at TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, guild_id, alert_key)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_watch_alert_latches (
            state_key TEXT NOT NULL,
            guild_id BIGINT NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, guild_id, symbol)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_watch_baselines (
            state_key TEXT NOT NULL,
            guild_id BIGINT NOT NULL,
            symbol TEXT NOT NULL,
            price DOUBLE PRECISION NOT NULL,
            checked_at TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, guild_id, symbol)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_job_status (
            state_key TEXT NOT NULL,
            job_key TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT NOT NULL,
            run_at TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, job_key)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_provider_status (
            state_key TEXT NOT NULL,
            provider_key TEXT NOT NULL,
            ok BOOLEAN NOT NULL,
            message TEXT NOT NULL,
            updated_at_text TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, provider_key)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_news_dedup (
            state_key TEXT NOT NULL,
            date_text TEXT NOT NULL,
            dedup_key TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (state_key, date_text, dedup_key)
        )
        """
    )


def _clear_split_rows(cursor: Any, state_key: str) -> None:
    for table in (
        "bot_news_dedup",
        "bot_provider_status",
        "bot_job_status",
        "bot_watch_baselines",
        "bot_watch_alert_latches",
        "bot_watch_alert_cooldowns",
        "bot_watch_session_alerts",
        "bot_watch_reference_snapshots",
        "bot_watch_symbols",
        "bot_command_image_cache",
        "bot_daily_posts",
        "bot_guild_job_markers",
        "bot_guild_config",
    ):
        cursor.execute(f"DELETE FROM {table} WHERE state_key = %s", (state_key,))


def _insert_split_rows(cursor: Any, state: AppState, state_key: str) -> None:
    rows = _split_state(state)
    for row in rows["guild_config"]:
        cursor.execute(
            """
            INSERT INTO bot_guild_config (
                state_key, guild_id, forum_channel_id, news_forum_channel_id, eod_forum_channel_id,
                watch_forum_channel_id, legacy_watch_alert_channel_id, auto_screenshot_enabled
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (state_key, guild_id) DO UPDATE SET
                forum_channel_id = EXCLUDED.forum_channel_id,
                news_forum_channel_id = EXCLUDED.news_forum_channel_id,
                eod_forum_channel_id = EXCLUDED.eod_forum_channel_id,
                watch_forum_channel_id = EXCLUDED.watch_forum_channel_id,
                legacy_watch_alert_channel_id = EXCLUDED.legacy_watch_alert_channel_id,
                auto_screenshot_enabled = EXCLUDED.auto_screenshot_enabled,
                updated_at = now()
            """,
            (
                state_key,
                row["guild_id"],
                row["forum_channel_id"],
                row["news_forum_channel_id"],
                row["eod_forum_channel_id"],
                row["watch_forum_channel_id"],
                row["legacy_watch_alert_channel_id"],
                row["auto_screenshot_enabled"],
            ),
        )
    for row in rows["guild_job_markers"]:
        cursor.execute(
            """
            INSERT INTO bot_guild_job_markers (
                state_key, guild_id, job_key, last_attempt_date, last_run_date, last_skip_date, last_skip_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (state_key, guild_id, job_key) DO UPDATE SET
                last_attempt_date = EXCLUDED.last_attempt_date,
                last_run_date = EXCLUDED.last_run_date,
                last_skip_date = EXCLUDED.last_skip_date,
                last_skip_reason = EXCLUDED.last_skip_reason,
                updated_at = now()
            """,
            (
                state_key,
                row["guild_id"],
                row["job_key"],
                row["last_attempt_date"],
                row["last_run_date"],
                row["last_skip_date"],
                row["last_skip_reason"],
            ),
        )
    for row in rows["daily_posts"]:
        upsert_daily_post_record(
            row["command_key"],
            row["guild_id"],
            row["post_date"],
            row["thread_id"],
            row["starter_message_id"],
            row["content_message_ids"],
            cursor=cursor,
            state_key=state_key,
        )
    for row in rows["command_image_cache"]:
        if row["path"] and row["captured_at"]:
            upsert_command_image_cache(
                row["command_key"],
                row["market_label"],
                row["path"],
                row["captured_at"],
                last_run_at=row["last_run_at"],
                cursor=cursor,
                state_key=state_key,
            )
    for row in rows["watch_symbols"]:
        _upsert_watch_symbol_row(cursor, state_key=state_key, **row)
    for row in rows["watch_reference_snapshots"]:
        set_watch_reference_snapshot(
            row["guild_id"],
            row["symbol"],
            basis=row["basis"],
            reference_price=row["reference_price"],
            session_date=row["session_date"],
            checked_at=row["checked_at"],
            cursor=cursor,
            state_key=state_key,
        )
    for row in rows["watch_session_alerts"]:
        _upsert_watch_session_alert_row(cursor, state_key, row)
    for row in rows["watch_alert_cooldowns"]:
        set_watch_cooldown_hit(row["guild_id"], row["alert_key"], row["hit_at"], cursor=cursor, state_key=state_key)
    for row in rows["watch_alert_latches"]:
        set_watch_alert_latch(row["guild_id"], row["symbol"], row["direction"], cursor=cursor, state_key=state_key)
    for row in rows["watch_baselines"]:
        set_watch_baseline(row["guild_id"], row["symbol"], row["price"], row["checked_at"], cursor=cursor, state_key=state_key)
    for row in rows["job_status"]:
        _set_job_last_run_values(row["job_key"], row["status"], row["detail"], row["run_at"], cursor=cursor, state_key=state_key)
    for row in rows["provider_status"]:
        _set_provider_status_values(row["provider_key"], row["ok"], row["message"], row["updated_at"], cursor=cursor, state_key=state_key)
    for row in rows["news_dedup"]:
        cursor.execute(
            """
            INSERT INTO bot_news_dedup (state_key, date_text, dedup_key)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (state_key, row["date_text"], row["dedup_key"]),
        )


def _load_migration_source(cursor: Any, state_key: str) -> AppState:
    cursor.execute("SELECT state FROM bot_app_state WHERE state_key = %s", (state_key,))
    row = cursor.fetchone()
    if row is not None:
        return legacy_repository._coerce_postgres_state(row[0])
    return legacy_repository._load_file_state(migrate_legacy=False)


def ensure_schema_and_migrate() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    state_key = _state_key()
    with _connect() as conn:
        with conn.cursor() as cursor:
            _ensure_schema(cursor)
            lock_key = zlib.crc32(f"bot-state-split:{state_key}".encode("utf-8"))
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", (lock_key,))
            cursor.execute(
                "SELECT 1 FROM bot_state_migrations WHERE state_key = %s AND migration_id = %s",
                (state_key, MIGRATION_SPLIT_STATE_V1),
            )
            if cursor.fetchone() is None:
                source = _load_migration_source(cursor, state_key)
                _clear_split_rows(cursor, state_key)
                _insert_split_rows(cursor, source, state_key)
                cursor.execute(
                    """
                    INSERT INTO bot_state_migrations (state_key, migration_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (state_key, MIGRATION_SPLIT_STATE_V1),
                )
    _SCHEMA_READY = True


def _fetchone(query: str, params: tuple[Any, ...]) -> Any:
    ensure_schema_and_migrate()
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()


def _fetchall(query: str, params: tuple[Any, ...]) -> list[Any]:
    ensure_schema_and_migrate()
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return list(cursor.fetchall())


def _execute(query: str, params: tuple[Any, ...]) -> None:
    ensure_schema_and_migrate()
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)


def load_state_snapshot() -> AppState:
    ensure_schema_and_migrate()
    state: AppState = {"commands": {}, "guilds": {}}
    state_key = _state_key()
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT guild_id, forum_channel_id, news_forum_channel_id, eod_forum_channel_id,
                       watch_forum_channel_id, legacy_watch_alert_channel_id, auto_screenshot_enabled
                FROM bot_guild_config
                WHERE state_key = %s
                """,
                (state_key,),
            )
            for row in cursor.fetchall():
                guild_id = str(row[0])
                cfg: dict[str, Any] = {}
                for key, value in (
                    ("forum_channel_id", row[1]),
                    ("news_forum_channel_id", row[2]),
                    ("eod_forum_channel_id", row[3]),
                    ("watch_forum_channel_id", row[4]),
                    ("watch_alert_channel_id", row[5]),
                ):
                    if value is not None:
                        cfg[key] = int(value)
                if row[6] is True:
                    cfg["auto_screenshot_enabled"] = True
                state["guilds"][guild_id] = cfg
            cursor.execute(
                """
                SELECT guild_id, job_key, last_attempt_date, last_run_date, last_skip_date, last_skip_reason
                FROM bot_guild_job_markers
                WHERE state_key = %s
                """,
                (state_key,),
            )
            for guild_id, job_key, attempt, run, skip_date, skip_reason in cursor.fetchall():
                cfg = state["guilds"].setdefault(str(guild_id), {})
                if attempt:
                    cfg.setdefault("last_auto_attempts", {})[job_key] = attempt
                if run:
                    cfg.setdefault("last_auto_runs", {})[job_key] = run
                if skip_date:
                    cfg.setdefault("last_auto_skips", {})[job_key] = {"date": skip_date, "reason": skip_reason or ""}
            cursor.execute(
                """
                SELECT command_key, guild_id, post_date, thread_id, starter_message_id, content_message_ids
                FROM bot_daily_posts
                WHERE state_key = %s
                """,
                (state_key,),
            )
            for command_key, guild_id, post_date, thread_id, starter_message_id, content_ids in cursor.fetchall():
                command = state["commands"].setdefault(command_key, {"daily_posts_by_guild": {}, "last_images": {}})
                posts = command.setdefault("daily_posts_by_guild", {}).setdefault(str(guild_id), {})
                post: DailyPostEntry = {"thread_id": int(thread_id), "starter_message_id": int(starter_message_id)}
                ids = [int(item) for item in (content_ids or [])]
                if ids:
                    post["content_message_ids"] = ids
                posts[post_date] = post
            cursor.execute(
                """
                SELECT command_key, market_label, path, captured_at, last_run_at
                FROM bot_command_image_cache
                WHERE state_key = %s
                """,
                (state_key,),
            )
            for command_key, market_label, path, captured_at, last_run_at in cursor.fetchall():
                command = state["commands"].setdefault(command_key, {"daily_posts_by_guild": {}, "last_images": {}})
                command.setdefault("last_images", {})[market_label] = {"path": path, "captured_at": captured_at}
                if last_run_at:
                    command["last_run_at"] = last_run_at
            cursor.execute(
                "SELECT guild_id, symbol, status, thread_id, starter_message_id FROM bot_watch_symbols WHERE state_key = %s",
                (state_key,),
            )
            for guild_id, symbol, status, thread_id, starter_message_id in cursor.fetchall():
                cfg = state["guilds"].setdefault(str(guild_id), {})
                cfg.setdefault("watchlist", [])
                if symbol not in cfg["watchlist"]:
                    cfg["watchlist"].append(symbol)
                command = state["commands"].setdefault("watchpoll", {"daily_posts_by_guild": {}, "last_images": {}})
                entries = command.setdefault("symbol_threads_by_guild", {}).setdefault(str(guild_id), {})
                entry: WatchThreadEntry = {"status": status}
                if thread_id is not None:
                    entry["thread_id"] = int(thread_id)
                if starter_message_id is not None:
                    entry["starter_message_id"] = int(starter_message_id)
                entries[symbol] = entry
            _load_snapshot_system_rows(cursor, state, state_key)
    return state


def _load_snapshot_system_rows(cursor: Any, state: AppState, state_key: str) -> None:
    system = state.setdefault("system", {})
    cursor.execute(
        "SELECT guild_id, symbol, basis, reference_price, session_date, checked_at FROM bot_watch_reference_snapshots WHERE state_key = %s",
        (state_key,),
    )
    for guild_id, symbol, basis, reference_price, session_date, checked_at in cursor.fetchall():
        system.setdefault("watch_reference_snapshots", {}).setdefault(str(guild_id), {})[symbol] = {
            "basis": basis,
            "reference_price": float(reference_price),
            "session_date": session_date,
            "checked_at": checked_at,
        }
    cursor.execute(
        """
        SELECT guild_id, symbol, active_session_date, highest_up_band, highest_down_band, current_comment_id,
               intraday_comment_ids, close_comment_ids_by_session, pending_close_sessions,
               last_finalized_session_date, updated_at
        FROM bot_watch_session_alerts
        WHERE state_key = %s
        """,
        (state_key,),
    )
    for row in cursor.fetchall():
        guild_id, symbol = row[0], row[1]
        entry = _watch_alert_entry_from_row(row[2:])
        system.setdefault("watch_session_alerts", {}).setdefault(str(guild_id), {})[symbol] = entry
    cursor.execute("SELECT guild_id, symbol, price, checked_at FROM bot_watch_baselines WHERE state_key = %s", (state_key,))
    for guild_id, symbol, price, checked_at in cursor.fetchall():
        system.setdefault("watch_baselines", {}).setdefault(str(guild_id), {})[symbol] = {"price": float(price), "checked_at": checked_at}
    cursor.execute("SELECT guild_id, alert_key, hit_at FROM bot_watch_alert_cooldowns WHERE state_key = %s", (state_key,))
    for guild_id, alert_key, hit_at in cursor.fetchall():
        state["guilds"].setdefault(str(guild_id), {}).setdefault("watch_alert_cooldowns", {})[alert_key] = hit_at
    cursor.execute("SELECT guild_id, symbol, direction FROM bot_watch_alert_latches WHERE state_key = %s", (state_key,))
    for guild_id, symbol, direction in cursor.fetchall():
        state["guilds"].setdefault(str(guild_id), {}).setdefault("watch_alert_latches", {})[symbol] = direction
    cursor.execute("SELECT job_key, status, detail, run_at FROM bot_job_status WHERE state_key = %s", (state_key,))
    for job_key, status, detail, run_at in cursor.fetchall():
        system.setdefault("job_last_runs", {})[job_key] = {"status": status, "detail": detail, "run_at": run_at}
    cursor.execute("SELECT provider_key, ok, message, updated_at_text FROM bot_provider_status WHERE state_key = %s", (state_key,))
    for provider_key, ok, message, updated_at_text in cursor.fetchall():
        system.setdefault("provider_status", {})[provider_key] = {"ok": bool(ok), "message": message, "updated_at": updated_at_text}
    cursor.execute("SELECT date_text, dedup_key FROM bot_news_dedup WHERE state_key = %s", (state_key,))
    for dedup_date, dedup_key in cursor.fetchall():
        system.setdefault("news_dedup", {}).setdefault(dedup_date, []).append(dedup_key)


def _watch_alert_entry_from_row(row: tuple[Any, ...]) -> WatchSessionAlertEntry:
    (
        active_session_date,
        highest_up_band,
        highest_down_band,
        current_comment_id,
        intraday_comment_ids,
        close_ids,
        pending,
        last_finalized_session_date,
        updated_at,
    ) = row
    entry: WatchSessionAlertEntry = {
        "highest_up_band": int(highest_up_band or 0),
        "highest_down_band": int(highest_down_band or 0),
        "intraday_comment_ids": [int(item) for item in (intraday_comment_ids or [])],
        "close_comment_ids_by_session": {str(k): int(v) for k, v in _json_dict(close_ids).items() if isinstance(v, int)},
    }
    if active_session_date:
        entry["active_session_date"] = active_session_date
    if current_comment_id is not None:
        entry["current_comment_id"] = int(current_comment_id)
    pending_dict = _json_dict(pending)
    if pending_dict:
        entry["pending_close_sessions"] = pending_dict
    if last_finalized_session_date:
        entry["last_finalized_session_date"] = last_finalized_session_date
    if updated_at:
        entry["updated_at"] = updated_at
    return entry


def get_guild_forum_channel_id(guild_id: int) -> int | None:
    return _get_guild_channel(guild_id, "forum_channel_id")


def get_guild_news_forum_channel_id(guild_id: int) -> int | None:
    return _get_guild_channel(guild_id, "news_forum_channel_id")


def get_guild_eod_forum_channel_id(guild_id: int) -> int | None:
    return _get_guild_channel(guild_id, "eod_forum_channel_id")


def get_guild_watch_forum_channel_id(guild_id: int) -> int | None:
    return _get_guild_channel(guild_id, "watch_forum_channel_id")


def _get_guild_channel(guild_id: int, column: str) -> int | None:
    if column not in {"forum_channel_id", "news_forum_channel_id", "eod_forum_channel_id", "watch_forum_channel_id"}:
        raise ValueError(f"unsupported guild channel column: {column}")
    row = _fetchone(f"SELECT {column} FROM bot_guild_config WHERE state_key = %s AND guild_id = %s", (_state_key(), guild_id))
    return int(row[0]) if row and row[0] is not None else None


def _set_guild_channel(guild_id: int, channel_id: int, column: str) -> None:
    if column not in {"forum_channel_id", "news_forum_channel_id", "eod_forum_channel_id", "watch_forum_channel_id"}:
        raise ValueError(f"unsupported guild channel column: {column}")
    _execute(
        f"""
        INSERT INTO bot_guild_config (state_key, guild_id, {column})
        VALUES (%s, %s, %s)
        ON CONFLICT (state_key, guild_id) DO UPDATE SET {column} = EXCLUDED.{column}, updated_at = now()
        """,
        (_state_key(), guild_id, channel_id),
    )


def set_guild_forum_channel_id(guild_id: int, channel_id: int) -> None:
    _set_guild_channel(guild_id, channel_id, "forum_channel_id")


def set_guild_news_forum_channel_id(guild_id: int, channel_id: int) -> None:
    _set_guild_channel(guild_id, channel_id, "news_forum_channel_id")


def set_guild_eod_forum_channel_id(guild_id: int, channel_id: int) -> None:
    _set_guild_channel(guild_id, channel_id, "eod_forum_channel_id")


def set_guild_watch_forum_channel_id(guild_id: int, channel_id: int) -> None:
    _set_guild_channel(guild_id, channel_id, "watch_forum_channel_id")


def set_guild_auto_screenshot_enabled(guild_id: int, enabled: bool) -> None:
    _execute(
        """
        INSERT INTO bot_guild_config (state_key, guild_id, auto_screenshot_enabled)
        VALUES (%s, %s, %s)
        ON CONFLICT (state_key, guild_id) DO UPDATE SET
            auto_screenshot_enabled = EXCLUDED.auto_screenshot_enabled,
            updated_at = now()
        """,
        (_state_key(), guild_id, enabled),
    )


def get_auto_enabled_guild_ids() -> list[int]:
    return [
        int(row[0])
        for row in _fetchall(
            """
            SELECT guild_id FROM bot_guild_config
            WHERE state_key = %s AND auto_screenshot_enabled IS TRUE
            ORDER BY guild_id
            """,
            (_state_key(),),
        )
    ]


def list_guild_ids() -> list[int]:
    rows = _fetchall(
        """
        SELECT DISTINCT guild_id FROM (
            SELECT guild_id FROM bot_guild_config WHERE state_key = %s
            UNION SELECT guild_id FROM bot_guild_job_markers WHERE state_key = %s
            UNION SELECT guild_id FROM bot_daily_posts WHERE state_key = %s
            UNION SELECT guild_id FROM bot_watch_symbols WHERE state_key = %s
            UNION SELECT guild_id FROM bot_watch_reference_snapshots WHERE state_key = %s
            UNION SELECT guild_id FROM bot_watch_session_alerts WHERE state_key = %s
        ) AS guilds
        ORDER BY guild_id
        """,
        (_state_key(), _state_key(), _state_key(), _state_key(), _state_key(), _state_key()),
    )
    return [int(row[0]) for row in rows]


def list_legacy_watch_route_migrations_needed() -> list[tuple[int, int]]:
    rows = _fetchall(
        """
        SELECT guild_id, legacy_watch_alert_channel_id
        FROM bot_guild_config
        WHERE state_key = %s
          AND watch_forum_channel_id IS NULL
          AND legacy_watch_alert_channel_id IS NOT NULL
        ORDER BY guild_id
        """,
        (_state_key(),),
    )
    return [(int(row[0]), int(row[1])) for row in rows]


def get_guild_last_auto_run_date(guild_id: int, command_key: str) -> str | None:
    return _get_guild_job_marker(guild_id, command_key, "last_run_date")


def get_guild_last_auto_attempt_date(guild_id: int, command_key: str) -> str | None:
    return _get_guild_job_marker(guild_id, command_key, "last_attempt_date")


def get_guild_last_auto_skip_date(guild_id: int, command_key: str) -> str | None:
    return _get_guild_job_marker(guild_id, command_key, "last_skip_date")


def _get_guild_job_marker(guild_id: int, job_key: str, column: str) -> str | None:
    if column not in {"last_attempt_date", "last_run_date", "last_skip_date"}:
        raise ValueError(f"unsupported marker column: {column}")
    row = _fetchone(
        f"SELECT {column} FROM bot_guild_job_markers WHERE state_key = %s AND guild_id = %s AND job_key = %s",
        (_state_key(), guild_id, job_key),
    )
    return row[0] if row and isinstance(row[0], str) else None


def set_guild_last_auto_run_date(guild_id: int, command_key: str, date_text: str) -> None:
    _upsert_guild_job_marker(guild_id, command_key, last_run_date=date_text)


def set_guild_last_auto_attempt_date(guild_id: int, command_key: str, date_text: str) -> None:
    _upsert_guild_job_marker(guild_id, command_key, last_attempt_date=date_text)


def set_guild_last_auto_skip(guild_id: int, command_key: str, date_text: str, reason: str) -> None:
    _upsert_guild_job_marker(guild_id, command_key, last_skip_date=date_text, last_skip_reason=reason)


def _upsert_guild_job_marker(
    guild_id: int,
    job_key: str,
    *,
    last_attempt_date: str | None = None,
    last_run_date: str | None = None,
    last_skip_date: str | None = None,
    last_skip_reason: str | None = None,
) -> None:
    _execute(
        """
        INSERT INTO bot_guild_job_markers (
            state_key, guild_id, job_key, last_attempt_date, last_run_date, last_skip_date, last_skip_reason
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (state_key, guild_id, job_key) DO UPDATE SET
            last_attempt_date = COALESCE(EXCLUDED.last_attempt_date, bot_guild_job_markers.last_attempt_date),
            last_run_date = COALESCE(EXCLUDED.last_run_date, bot_guild_job_markers.last_run_date),
            last_skip_date = COALESCE(EXCLUDED.last_skip_date, bot_guild_job_markers.last_skip_date),
            last_skip_reason = COALESCE(EXCLUDED.last_skip_reason, bot_guild_job_markers.last_skip_reason),
            updated_at = now()
        """,
        (_state_key(), guild_id, job_key, last_attempt_date, last_run_date, last_skip_date, last_skip_reason),
    )


def get_daily_post_record(command_key: str, guild_id: int, post_date: str | None = None) -> DailyPostEntry | None:
    row = _fetchone(
        """
        SELECT thread_id, starter_message_id, content_message_ids
        FROM bot_daily_posts
        WHERE state_key = %s AND command_key = %s AND guild_id = %s AND post_date = %s
        """,
        (_state_key(), command_key, guild_id, post_date or date_key()),
    )
    if row is None:
        return None
    record: DailyPostEntry = {"thread_id": int(row[0]), "starter_message_id": int(row[1])}
    content_ids = [int(item) for item in (row[2] or [])]
    if content_ids:
        record["content_message_ids"] = content_ids
    return record


def upsert_daily_post_record(
    command_key: str,
    guild_id: int,
    post_date: str,
    thread_id: int,
    starter_message_id: int,
    content_message_ids: list[int] | None = None,
    *,
    cursor: Any | None = None,
    state_key: str | None = None,
) -> None:
    params = (state_key or _state_key(), command_key, guild_id, post_date, thread_id, starter_message_id, content_message_ids or [])
    query = """
        INSERT INTO bot_daily_posts (
            state_key, command_key, guild_id, post_date, thread_id, starter_message_id, content_message_ids
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (state_key, command_key, guild_id, post_date) DO UPDATE SET
            thread_id = EXCLUDED.thread_id,
            starter_message_id = EXCLUDED.starter_message_id,
            content_message_ids = EXCLUDED.content_message_ids,
            updated_at = now()
        """
    if cursor is not None:
        cursor.execute(query, params)
        return
    _execute(query, params)


def copy_daily_post_if_missing(source_command_key: str, target_command_key: str, guild_id: int, post_date: str) -> None:
    ensure_schema_and_migrate()
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO bot_daily_posts (
                    state_key, command_key, guild_id, post_date, thread_id, starter_message_id, content_message_ids
                )
                SELECT state_key, %s, guild_id, post_date, thread_id, starter_message_id, content_message_ids
                FROM bot_daily_posts
                WHERE state_key = %s AND command_key = %s AND guild_id = %s AND post_date = %s
                ON CONFLICT DO NOTHING
                """,
                (target_command_key, _state_key(), source_command_key, guild_id, post_date),
            )


def get_command_image_cache(command_key: str) -> dict[str, dict[str, str]]:
    rows = _fetchall(
        """
        SELECT market_label, path, captured_at
        FROM bot_command_image_cache
        WHERE state_key = %s AND command_key = %s
        """,
        (_state_key(), command_key),
    )
    return {row[0]: {"path": row[1], "captured_at": row[2]} for row in rows}


def upsert_command_image_cache(
    command_key: str,
    market_label: str,
    path: str,
    captured_at: str,
    *,
    last_run_at: str | None = None,
    cursor: Any | None = None,
    state_key: str | None = None,
) -> None:
    query = """
        INSERT INTO bot_command_image_cache (state_key, command_key, market_label, path, captured_at, last_run_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (state_key, command_key, market_label) DO UPDATE SET
            path = EXCLUDED.path,
            captured_at = EXCLUDED.captured_at,
            last_run_at = COALESCE(EXCLUDED.last_run_at, bot_command_image_cache.last_run_at),
            updated_at = now()
        """
    params = (state_key or _state_key(), command_key, market_label, path, captured_at, last_run_at)
    if cursor is not None:
        cursor.execute(query, params)
        return
    _execute(query, params)


def set_job_last_run(job_key: str, status: str, detail: str) -> None:
    _set_job_last_run_values(job_key, status, detail, now_kst().isoformat())


def _set_job_last_run_values(
    job_key: str,
    status: str,
    detail: str,
    run_at: str,
    *,
    cursor: Any | None = None,
    state_key: str | None = None,
) -> None:
    query = """
        INSERT INTO bot_job_status (state_key, job_key, status, detail, run_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (state_key, job_key) DO UPDATE SET
            status = EXCLUDED.status,
            detail = EXCLUDED.detail,
            run_at = EXCLUDED.run_at,
            updated_at = now()
        """
    params = (state_key or _state_key(), job_key, status, detail, run_at)
    if cursor is not None:
        cursor.execute(query, params)
        return
    _execute(query, params)


def get_job_last_runs() -> dict[str, dict[str, str]]:
    rows = _fetchall("SELECT job_key, status, detail, run_at FROM bot_job_status WHERE state_key = %s", (_state_key(),))
    return {row[0]: {"status": row[1], "detail": row[2], "run_at": row[3]} for row in rows}


def set_provider_status(provider_key: str, ok: bool, message: str) -> None:
    _set_provider_status_values(provider_key, ok, message, now_kst().isoformat())


def _set_provider_status_values(
    provider_key: str,
    ok: bool,
    message: str,
    updated_at: str,
    *,
    cursor: Any | None = None,
    state_key: str | None = None,
) -> None:
    query = """
        INSERT INTO bot_provider_status (state_key, provider_key, ok, message, updated_at_text)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (state_key, provider_key) DO UPDATE SET
            ok = EXCLUDED.ok,
            message = EXCLUDED.message,
            updated_at_text = EXCLUDED.updated_at_text,
            updated_at = now()
        """
    params = (state_key or _state_key(), provider_key, ok, message, updated_at)
    if cursor is not None:
        cursor.execute(query, params)
        return
    _execute(query, params)


def get_provider_statuses() -> dict[str, dict[str, Any]]:
    rows = _fetchall(
        "SELECT provider_key, ok, message, updated_at_text FROM bot_provider_status WHERE state_key = %s",
        (_state_key(),),
    )
    return {row[0]: {"ok": bool(row[1]), "message": row[2], "updated_at": row[3]} for row in rows}


def add_watch_symbol(guild_id: int, symbol: str) -> bool:
    normalized = _normalize_symbol(symbol)
    ensure_schema_and_migrate()
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO bot_watch_symbols (state_key, guild_id, symbol, status)
                VALUES (%s, %s, %s, 'active')
                ON CONFLICT DO NOTHING
                """,
                (_state_key(), guild_id, normalized),
            )
            return cursor.rowcount == 1


def _upsert_watch_symbol_row(
    cursor: Any,
    *,
    state_key: str,
    guild_id: int,
    symbol: str,
    status: str = "active",
    thread_id: int | None = None,
    starter_message_id: int | None = None,
) -> None:
    cursor.execute(
        """
        INSERT INTO bot_watch_symbols (state_key, guild_id, symbol, status, thread_id, starter_message_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (state_key, guild_id, symbol) DO UPDATE SET
            status = EXCLUDED.status,
            thread_id = COALESCE(EXCLUDED.thread_id, bot_watch_symbols.thread_id),
            starter_message_id = COALESCE(EXCLUDED.starter_message_id, bot_watch_symbols.starter_message_id),
            updated_at = now()
        """,
        (state_key, guild_id, _normalize_symbol(symbol), status, thread_id, starter_message_id),
    )


def delete_watch_symbol(guild_id: int, symbol: str) -> bool:
    normalized = _normalize_symbol(symbol)
    ensure_schema_and_migrate()
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM bot_watch_symbols WHERE state_key = %s AND guild_id = %s AND symbol = %s",
                (_state_key(), guild_id, normalized),
            )
            changed = cursor.rowcount > 0
            for table in ("bot_watch_reference_snapshots", "bot_watch_session_alerts", "bot_watch_baselines", "bot_watch_alert_latches"):
                cursor.execute(
                    f"DELETE FROM {table} WHERE state_key = %s AND guild_id = %s AND symbol = %s",
                    (_state_key(), guild_id, normalized),
                )
                changed = changed or cursor.rowcount > 0
            cursor.execute(
                """
                DELETE FROM bot_watch_alert_cooldowns
                WHERE state_key = %s AND guild_id = %s AND (alert_key = %s OR alert_key LIKE %s)
                """,
                (_state_key(), guild_id, normalized, f"{normalized}:%"),
            )
            return changed or cursor.rowcount > 0


def clear_watch_symbol_runtime_state(guild_id: int, symbol: str) -> None:
    normalized = _normalize_symbol(symbol)
    ensure_schema_and_migrate()
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM bot_watch_alert_cooldowns
                WHERE state_key = %s AND guild_id = %s AND (alert_key = %s OR alert_key LIKE %s)
                """,
                (_state_key(), guild_id, normalized, f"{normalized}:%"),
            )
            cursor.execute(
                "DELETE FROM bot_watch_alert_latches WHERE state_key = %s AND guild_id = %s AND symbol = %s",
                (_state_key(), guild_id, normalized),
            )
            cursor.execute(
                "DELETE FROM bot_watch_baselines WHERE state_key = %s AND guild_id = %s AND symbol = %s",
                (_state_key(), guild_id, normalized),
            )


def list_watch_symbols(guild_id: int) -> list[str]:
    rows = _fetchall(
        """
        SELECT symbol FROM bot_watch_symbols
        WHERE state_key = %s AND guild_id = %s
        ORDER BY symbol
        """,
        (_state_key(), guild_id),
    )
    return [row[0] for row in rows]


def list_active_watch_symbols(guild_id: int) -> list[str]:
    rows = _fetchall(
        """
        SELECT symbol FROM bot_watch_symbols
        WHERE state_key = %s AND guild_id = %s AND status <> 'inactive'
        ORDER BY symbol
        """,
        (_state_key(), guild_id),
    )
    return [row[0] for row in rows]


def list_watch_tracked_symbols(guild_id: int) -> list[str]:
    return list_watch_symbols(guild_id)


def get_watch_symbol_status(guild_id: int, symbol: str) -> str:
    row = _fetchone(
        "SELECT status FROM bot_watch_symbols WHERE state_key = %s AND guild_id = %s AND symbol = %s",
        (_state_key(), guild_id, _normalize_symbol(symbol)),
    )
    return "inactive" if row and row[0] == "inactive" else "active"


def get_watch_symbol_thread(guild_id: int, symbol: str) -> WatchThreadEntry | None:
    row = _fetchone(
        """
        SELECT status, thread_id, starter_message_id
        FROM bot_watch_symbols
        WHERE state_key = %s AND guild_id = %s AND symbol = %s
        """,
        (_state_key(), guild_id, _normalize_symbol(symbol)),
    )
    if row is None:
        return None
    entry: WatchThreadEntry = {"status": row[0]}
    if row[1] is not None:
        entry["thread_id"] = int(row[1])
    if row[2] is not None:
        entry["starter_message_id"] = int(row[2])
    return entry


def set_watch_symbol_thread(
    guild_id: int,
    symbol: str,
    *,
    thread_id: int,
    starter_message_id: int,
    status: str,
) -> None:
    ensure_schema_and_migrate()
    with _connect() as conn:
        with conn.cursor() as cursor:
            _upsert_watch_symbol_row(
                cursor,
                state_key=_state_key(),
                guild_id=guild_id,
                symbol=symbol,
                status="inactive" if status == "inactive" else "active",
                thread_id=thread_id,
                starter_message_id=starter_message_id,
            )


def set_watch_symbol_thread_status(guild_id: int, symbol: str, status: str) -> None:
    _execute(
        """
        INSERT INTO bot_watch_symbols (state_key, guild_id, symbol, status)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (state_key, guild_id, symbol) DO UPDATE SET status = EXCLUDED.status, updated_at = now()
        """,
        (_state_key(), guild_id, _normalize_symbol(symbol), "inactive" if status == "inactive" else "active"),
    )


def get_watch_reference_snapshot(guild_id: int, symbol: str) -> WatchReferenceSnapshotEntry | None:
    row = _fetchone(
        """
        SELECT basis, reference_price, session_date, checked_at
        FROM bot_watch_reference_snapshots
        WHERE state_key = %s AND guild_id = %s AND symbol = %s
        """,
        (_state_key(), guild_id, _normalize_symbol(symbol)),
    )
    if row is None:
        return None
    return {"basis": row[0], "reference_price": float(row[1]), "session_date": row[2], "checked_at": row[3]}


def set_watch_reference_snapshot(
    guild_id: int,
    symbol: str,
    *,
    basis: str,
    reference_price: float,
    session_date: str,
    checked_at: str,
    cursor: Any | None = None,
    state_key: str | None = None,
) -> None:
    query = """
        INSERT INTO bot_watch_reference_snapshots (
            state_key, guild_id, symbol, basis, reference_price, session_date, checked_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (state_key, guild_id, symbol) DO UPDATE SET
            basis = EXCLUDED.basis,
            reference_price = EXCLUDED.reference_price,
            session_date = EXCLUDED.session_date,
            checked_at = EXCLUDED.checked_at,
            updated_at = now()
        """
    params = (state_key or _state_key(), guild_id, _normalize_symbol(symbol), basis, reference_price, session_date, checked_at)
    if cursor is not None:
        cursor.execute(query, params)
        return
    _execute(query, params)


def get_watch_session_alert(guild_id: int, symbol: str) -> WatchSessionAlertEntry:
    row = _fetchone(
        """
        SELECT active_session_date, highest_up_band, highest_down_band, current_comment_id,
               intraday_comment_ids, close_comment_ids_by_session, pending_close_sessions,
               last_finalized_session_date, updated_at
        FROM bot_watch_session_alerts
        WHERE state_key = %s AND guild_id = %s AND symbol = %s
        """,
        (_state_key(), guild_id, _normalize_symbol(symbol)),
    )
    if row is None:
        return {"highest_up_band": 0, "highest_down_band": 0, "intraday_comment_ids": [], "close_comment_ids_by_session": {}}
    return _watch_alert_entry_from_row(row)


def update_watch_session_alert(
    guild_id: int,
    symbol: str,
    *,
    active_session_date: str | None = None,
    highest_up_band: int | None = None,
    highest_down_band: int | None = None,
    current_comment_id: int | None | object = _UNSET,
    intraday_comment_ids: list[int] | None = None,
    close_comment_ids_by_session: dict[str, int] | None = None,
    last_finalized_session_date: str | None = None,
    updated_at: str | None = None,
) -> WatchSessionAlertEntry:
    def mutate(entry: WatchSessionAlertEntry) -> None:
        if active_session_date is not None:
            entry["active_session_date"] = active_session_date
        if highest_up_band is not None:
            entry["highest_up_band"] = int(highest_up_band)
        if highest_down_band is not None:
            entry["highest_down_band"] = int(highest_down_band)
        if current_comment_id is not _UNSET:
            if current_comment_id is None:
                entry.pop("current_comment_id", None)
            else:
                entry["current_comment_id"] = int(current_comment_id)
        if intraday_comment_ids is not None:
            entry["intraday_comment_ids"] = [int(item) for item in intraday_comment_ids]
        if close_comment_ids_by_session is not None:
            entry["close_comment_ids_by_session"] = {str(key): int(value) for key, value in close_comment_ids_by_session.items()}
        if last_finalized_session_date is not None:
            entry["last_finalized_session_date"] = last_finalized_session_date
        if updated_at is not None:
            entry["updated_at"] = updated_at

    return mutate_watch_session_alert(guild_id, symbol, mutate)


def mutate_watch_session_alert(
    guild_id: int,
    symbol: str,
    mutator: Callable[[WatchSessionAlertEntry], None],
) -> WatchSessionAlertEntry:
    ensure_schema_and_migrate()
    normalized = _normalize_symbol(symbol)
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT active_session_date, highest_up_band, highest_down_band, current_comment_id,
                       intraday_comment_ids, close_comment_ids_by_session, pending_close_sessions,
                       last_finalized_session_date, updated_at
                FROM bot_watch_session_alerts
                WHERE state_key = %s AND guild_id = %s AND symbol = %s
                FOR UPDATE
                """,
                (_state_key(), guild_id, normalized),
            )
            row = cursor.fetchone()
            entry = (
                _watch_alert_entry_from_row(row)
                if row is not None
                else {"highest_up_band": 0, "highest_down_band": 0, "intraday_comment_ids": [], "close_comment_ids_by_session": {}}
            )
            mutator(entry)
            _upsert_watch_session_alert_row(cursor, _state_key(), _watch_alert_row_from_entry(guild_id, normalized, entry))
            return cast(WatchSessionAlertEntry, entry)


def _upsert_watch_session_alert_row(cursor: Any, state_key: str, row: dict[str, Any]) -> None:
    cursor.execute(
        """
        INSERT INTO bot_watch_session_alerts (
            state_key, guild_id, symbol, active_session_date, highest_up_band, highest_down_band,
            current_comment_id, intraday_comment_ids, close_comment_ids_by_session,
            pending_close_sessions, last_finalized_session_date, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        ON CONFLICT (state_key, guild_id, symbol) DO UPDATE SET
            active_session_date = EXCLUDED.active_session_date,
            highest_up_band = EXCLUDED.highest_up_band,
            highest_down_band = EXCLUDED.highest_down_band,
            current_comment_id = EXCLUDED.current_comment_id,
            intraday_comment_ids = EXCLUDED.intraday_comment_ids,
            close_comment_ids_by_session = EXCLUDED.close_comment_ids_by_session,
            pending_close_sessions = EXCLUDED.pending_close_sessions,
            last_finalized_session_date = EXCLUDED.last_finalized_session_date,
            updated_at = EXCLUDED.updated_at,
            row_updated_at = now()
        """,
        (
            state_key,
            row["guild_id"],
            row["symbol"],
            row["active_session_date"],
            row["highest_up_band"],
            row["highest_down_band"],
            row["current_comment_id"],
            row["intraday_comment_ids"],
            _json_dumps(row["close_comment_ids_by_session"]),
            _json_dumps(row["pending_close_sessions"]),
            row["last_finalized_session_date"],
            row["updated_at"],
        ),
    )


def set_watch_current_comment_id(guild_id: int, symbol: str, message_id: int) -> WatchSessionAlertEntry:
    return update_watch_session_alert(guild_id, symbol, current_comment_id=int(message_id))


def clear_watch_current_comment_id(guild_id: int, symbol: str) -> WatchSessionAlertEntry:
    return update_watch_session_alert(guild_id, symbol, current_comment_id=None)


def replace_watch_session_alert(guild_id: int, symbol: str, entry: dict[str, Any]) -> WatchSessionAlertEntry:
    replacement = dict(entry)

    def mutate(current: WatchSessionAlertEntry) -> None:
        current.clear()
        current.update(replacement)

    return mutate_watch_session_alert(guild_id, symbol, mutate)


def get_watch_cooldown_hit(guild_id: int, key: str) -> str | None:
    row = _fetchone(
        "SELECT hit_at FROM bot_watch_alert_cooldowns WHERE state_key = %s AND guild_id = %s AND alert_key = %s",
        (_state_key(), guild_id, key),
    )
    return row[0] if row else None


def set_watch_cooldown_hit(guild_id: int, key: str, hit_at: str, *, cursor: Any | None = None, state_key: str | None = None) -> None:
    query = """
        INSERT INTO bot_watch_alert_cooldowns (state_key, guild_id, alert_key, hit_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (state_key, guild_id, alert_key) DO UPDATE SET hit_at = EXCLUDED.hit_at, updated_at = now()
        """
    params = (state_key or _state_key(), guild_id, key, hit_at)
    if cursor is not None:
        cursor.execute(query, params)
        return
    _execute(query, params)


def get_watch_alert_latch(guild_id: int, symbol: str) -> str | None:
    row = _fetchone(
        "SELECT direction FROM bot_watch_alert_latches WHERE state_key = %s AND guild_id = %s AND symbol = %s",
        (_state_key(), guild_id, _normalize_symbol(symbol)),
    )
    return row[0] if row else None


def set_watch_alert_latch(guild_id: int, symbol: str, direction: str, *, cursor: Any | None = None, state_key: str | None = None) -> None:
    query = """
        INSERT INTO bot_watch_alert_latches (state_key, guild_id, symbol, direction)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (state_key, guild_id, symbol) DO UPDATE SET direction = EXCLUDED.direction, updated_at = now()
        """
    params = (state_key or _state_key(), guild_id, _normalize_symbol(symbol), direction)
    if cursor is not None:
        cursor.execute(query, params)
        return
    _execute(query, params)


def clear_watch_alert_latch(guild_id: int, symbol: str) -> None:
    _execute(
        "DELETE FROM bot_watch_alert_latches WHERE state_key = %s AND guild_id = %s AND symbol = %s",
        (_state_key(), guild_id, _normalize_symbol(symbol)),
    )


def get_watch_baseline(guild_id: int, symbol: str) -> float | None:
    row = _fetchone(
        "SELECT price FROM bot_watch_baselines WHERE state_key = %s AND guild_id = %s AND symbol = %s",
        (_state_key(), guild_id, _normalize_symbol(symbol)),
    )
    return float(row[0]) if row else None


def set_watch_baseline(
    guild_id: int,
    symbol: str,
    price: float,
    checked_at: str,
    *,
    cursor: Any | None = None,
    state_key: str | None = None,
) -> None:
    query = """
        INSERT INTO bot_watch_baselines (state_key, guild_id, symbol, price, checked_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (state_key, guild_id, symbol) DO UPDATE SET
            price = EXCLUDED.price,
            checked_at = EXCLUDED.checked_at,
            updated_at = now()
        """
    params = (state_key or _state_key(), guild_id, _normalize_symbol(symbol), float(price), checked_at)
    if cursor is not None:
        cursor.execute(query, params)
        return
    _execute(query, params)


def is_news_dedup_seen(dedup_key: str, date_text: str) -> bool:
    row = _fetchone(
        "SELECT 1 FROM bot_news_dedup WHERE state_key = %s AND date_text = %s AND dedup_key = %s",
        (_state_key(), date_text, dedup_key),
    )
    return row is not None


def mark_news_dedup_seen(dedup_key: str, date_text: str) -> None:
    _execute(
        """
        INSERT INTO bot_news_dedup (state_key, date_text, dedup_key)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (_state_key(), date_text, dedup_key),
    )


def cleanup_news_dedup(keep_recent_days: int = 7) -> None:
    ensure_schema_and_migrate()
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT date_text FROM bot_news_dedup WHERE state_key = %s ORDER BY date_text",
                (_state_key(),),
            )
            dates = [row[0] for row in cursor.fetchall()]
            if len(dates) <= keep_recent_days:
                return
            for old_date in dates[:-keep_recent_days]:
                cursor.execute(
                    "DELETE FROM bot_news_dedup WHERE state_key = %s AND date_text = %s",
                    (_state_key(), old_date),
                )
