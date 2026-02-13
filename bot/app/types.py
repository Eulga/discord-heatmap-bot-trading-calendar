from typing import NotRequired, TypedDict


class ImageCacheEntry(TypedDict):
    path: str
    captured_at: str


class DailyPostEntry(TypedDict):
    thread_id: int
    starter_message_id: int


class CommandState(TypedDict):
    daily_posts_by_guild: dict[str, dict[str, DailyPostEntry]]
    last_images: dict[str, ImageCacheEntry]
    last_run_at: NotRequired[str]


class GuildConfig(TypedDict):
    forum_channel_id: int


class AppState(TypedDict):
    commands: dict[str, CommandState]
    guilds: dict[str, GuildConfig]
