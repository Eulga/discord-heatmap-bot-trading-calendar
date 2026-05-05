import asyncio
import logging

import discord
from discord import app_commands

from bot.app.command_sync import format_command_sync_error, record_command_sync
from bot.app.settings import (
    DEFAULT_FORUM_CHANNEL_ID,
    EOD_TARGET_FORUM_ID,
    NEWS_TARGET_FORUM_ID,
)
from bot.common.logging import setup_logging
from bot.forum.state_store import (
    ensure_schema_and_migrate,
    get_guild_eod_forum_channel_id,
    get_guild_forum_channel_id,
    get_guild_news_forum_channel_id,
    list_legacy_watch_route_migrations_needed,
    set_guild_eod_forum_channel_id,
    set_guild_forum_channel_id,
    set_guild_news_forum_channel_id,
)
from bot.features.auto_scheduler import auto_screenshot_scheduler
from bot.features.admin.command import register as register_admin
from bot.features.kheatmap.command import register as register_kheatmap
from bot.features.local_model.command import register as register_local_model
from bot.features.status.command import register as register_status
from bot.features.usheatmap.command import register as register_usheatmap
from bot.features.watch.command import register as register_watch
from bot.features.intel_scheduler import intel_scheduler

logger = logging.getLogger(__name__)


async def _fetch_channel(client: discord.Client, channel_id: int) -> discord.abc.GuildChannel | discord.Thread | None:
    channel = client.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await client.fetch_channel(channel_id)
    except Exception:
        return None


async def _bootstrap_guild_channel_routes_from_env(client: discord.Client) -> None:
    specs = [
        (
            DEFAULT_FORUM_CHANNEL_ID,
            "DEFAULT_FORUM_CHANNEL_ID",
            discord.ForumChannel,
            get_guild_forum_channel_id,
            set_guild_forum_channel_id,
        ),
        (
            NEWS_TARGET_FORUM_ID,
            "NEWS_TARGET_FORUM_ID",
            discord.ForumChannel,
            get_guild_news_forum_channel_id,
            set_guild_news_forum_channel_id,
        ),
        (
            EOD_TARGET_FORUM_ID,
            "EOD_TARGET_FORUM_ID",
            discord.ForumChannel,
            get_guild_eod_forum_channel_id,
            set_guild_eod_forum_channel_id,
        ),
    ]

    for channel_id, env_name, expected_type, getter, setter in specs:
        if channel_id is None:
            continue
        channel = await _fetch_channel(client, channel_id)
        if channel is None:
            logger.warning("[startup] ignored %s because channel %s is not accessible", env_name, channel_id)
            continue
        if not isinstance(channel, expected_type):
            logger.warning(
                "[startup] ignored %s because channel %s is not a %s",
                env_name,
                channel_id,
                expected_type.__name__,
            )
            continue
        guild = getattr(channel, "guild", None)
        guild_id = getattr(guild, "id", None)
        if not isinstance(guild_id, int):
            logger.warning("[startup] ignored %s because channel %s has no guild context", env_name, channel_id)
            continue
        if getter(guild_id) is not None:
            continue
        setter(guild_id, channel_id)
        logger.info("[startup] bootstrapped %s into state for guild=%s channel=%s", env_name, guild_id, channel_id)


def _warn_legacy_watch_route_migration_needed() -> None:
    for guild_id, legacy_watch_channel_id in list_legacy_watch_route_migrations_needed():
        logger.warning(
            "[startup] watch route migration required guild=%s legacy_watch_alert_channel_id=%s detail=/setwatchforum-required",
            guild_id,
            legacy_watch_channel_id,
        )


class BotApp:
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = False

        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)
        self._synced = False
        self._scheduler_task: asyncio.Task | None = None
        self._intel_task: asyncio.Task | None = None

        register_admin(self.tree, self.client)
        register_status(self.tree, self.client)
        register_watch(self.tree, self.client)
        register_kheatmap(self.tree, self.client)
        register_usheatmap(self.tree, self.client)
        register_local_model(self.tree, self.client)

        @self.client.event
        async def on_ready() -> None:
            if not self._synced:
                try:
                    synced_commands = await self.tree.sync()
                except Exception as exc:
                    detail = format_command_sync_error(exc)
                    record_command_sync("failed", detail)
                    logger.error("%s", detail)
                else:
                    logger.info(
                        "Synced %s global commands: %s",
                        len(synced_commands),
                        [c.name for c in synced_commands],
                    )
                    record_command_sync("ok", f"{len(synced_commands)} commands synced")
                    self._synced = True
            await _bootstrap_guild_channel_routes_from_env(self.client)
            _warn_legacy_watch_route_migration_needed()
            if self._scheduler_task is None or self._scheduler_task.done():
                self._scheduler_task = asyncio.create_task(auto_screenshot_scheduler(self.client))
                logger.info("Auto screenshot scheduler started.")
            if self._intel_task is None or self._intel_task.done():
                self._intel_task = asyncio.create_task(intel_scheduler(self.client))
                logger.info("Intel scheduler started.")
            logger.info("Logged in as %s (ID: %s)", self.client.user, self.client.user.id)

        @self.client.event
        async def on_message(message: discord.Message) -> None:
            if message.author == self.client.user:
                return
            if message.content == "!ping":
                await message.channel.send("pong")


def create_bot_app() -> BotApp:
    setup_logging()
    ensure_schema_and_migrate()
    return BotApp()
