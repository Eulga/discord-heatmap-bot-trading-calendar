import os

import discord
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set. Copy .env.example to .env and set the token.")


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready() -> None:
    print(f"Logged in as {client.user} (ID: {client.user.id})")


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author == client.user:
        return

    if message.content == "!ping":
        await message.channel.send("pong")


if __name__ == "__main__":
    client.run(TOKEN)
