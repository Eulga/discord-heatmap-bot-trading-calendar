import asyncio

import discord
from discord import app_commands

from bot.features.auto_scheduler import auto_screenshot_scheduler
from bot.features.admin.command import register as register_admin
from bot.features.kheatmap.command import register as register_kheatmap
from bot.features.status.command import register as register_status
from bot.features.usheatmap.command import register as register_usheatmap
from bot.features.watch.command import register as register_watch
from bot.features.intel_scheduler import intel_scheduler


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

        @self.client.event
        async def on_ready() -> None:
            if not self._synced:
                synced_commands = await self.tree.sync()
                print(f"Synced {len(synced_commands)} global commands: {[c.name for c in synced_commands]}")
                self._synced = True
            if self._scheduler_task is None or self._scheduler_task.done():
                self._scheduler_task = asyncio.create_task(auto_screenshot_scheduler(self.client))
                print("Auto screenshot scheduler started.")
            if self._intel_task is None or self._intel_task.done():
                self._intel_task = asyncio.create_task(intel_scheduler(self.client))
                print("Intel scheduler started.")
            print(f"Logged in as {self.client.user} (ID: {self.client.user.id})")

        @self.client.event
        async def on_message(message: discord.Message) -> None:
            if message.author == self.client.user:
                return
            if message.content == "!ping":
                await message.channel.send("pong")


def create_bot_app() -> BotApp:
    return BotApp()
