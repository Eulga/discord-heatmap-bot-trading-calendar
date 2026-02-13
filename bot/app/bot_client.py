import discord
from discord import app_commands

from bot.features.admin.command import register as register_admin
from bot.features.kheatmap.command import register as register_kheatmap
from bot.features.usheatmap.command import register as register_usheatmap


class BotApp:
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = False

        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)
        self._synced = False

        register_admin(self.tree, self.client)
        register_kheatmap(self.tree, self.client)
        register_usheatmap(self.tree, self.client)

        @self.client.event
        async def on_ready() -> None:
            if not self._synced:
                synced_commands = await self.tree.sync()
                print(f"Synced {len(synced_commands)} global commands: {[c.name for c in synced_commands]}")
                self._synced = True
            print(f"Logged in as {self.client.user} (ID: {self.client.user.id})")

        @self.client.event
        async def on_message(message: discord.Message) -> None:
            if message.author == self.client.user:
                return
            if message.content == "!ping":
                await message.channel.send("pong")



def create_bot_app() -> BotApp:
    return BotApp()
