import asyncio
import logging

import discord
from discord import app_commands

from bot.common.logging import setup_logging
from bot.features.auto_scheduler import auto_screenshot_scheduler
from bot.features.admin.command import register as register_admin
from bot.features.kheatmap.command import register as register_kheatmap
from bot.features.usheatmap.command import register as register_usheatmap

logger = logging.getLogger(__name__)


class BotApp:
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = False

        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)
        self._synced = False
        self._scheduler_task: asyncio.Task | None = None

        register_admin(self.tree, self.client)
        register_kheatmap(self.tree, self.client)
        register_usheatmap(self.tree, self.client)

        @self.client.event
        async def on_ready() -> None:
            if not self._synced:
                synced_commands = await self.tree.sync()
                logger.info(
                    "Synced %s global commands: %s",
                    len(synced_commands),
                    [c.name for c in synced_commands],
                )
                self._synced = True
            if self._scheduler_task is None or self._scheduler_task.done():
                self._scheduler_task = asyncio.create_task(auto_screenshot_scheduler(self.client))
                logger.info("Auto screenshot scheduler started.")
            logger.info("Logged in as %s (ID: %s)", self.client.user, self.client.user.id)

        @self.client.event
        async def on_message(message: discord.Message) -> None:
            if message.author == self.client.user:
                return
            if message.content == "!ping":
                await message.channel.send("pong")


def create_bot_app() -> BotApp:
    setup_logging()
    return BotApp()
