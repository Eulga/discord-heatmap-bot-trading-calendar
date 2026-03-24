from typing import Any, TypedDict

try:
    from typing import NotRequired
except ImportError:  # Python < 3.11
    from typing_extensions import NotRequired


class ImageCacheEntry(TypedDict):
    path: str
    captured_at: str


class DailyPostEntry(TypedDict):
    thread_id: int
    starter_message_id: int
    content_message_ids: NotRequired[list[int]]


class CommandState(TypedDict):
    daily_posts_by_guild: dict[str, dict[str, DailyPostEntry]]
    last_images: dict[str, ImageCacheEntry]
    last_run_at: NotRequired[str]


class GuildConfig(TypedDict):
    forum_channel_id: NotRequired[int]
    news_forum_channel_id: NotRequired[int]
    eod_forum_channel_id: NotRequired[int]
    watch_alert_channel_id: NotRequired[int]
    auto_screenshot_enabled: NotRequired[bool]
    last_auto_attempts: NotRequired[dict[str, str]]
    last_auto_runs: NotRequired[dict[str, str]]
    last_auto_skips: NotRequired[dict[str, dict[str, str]]]
    watchlist: NotRequired[list[str]]
    watch_alert_cooldowns: NotRequired[dict[str, str]]
    watch_alert_latches: NotRequired[dict[str, str]]


class AppState(TypedDict):
    commands: dict[str, CommandState]
    guilds: dict[str, GuildConfig]
    system: NotRequired[dict[str, Any]]
