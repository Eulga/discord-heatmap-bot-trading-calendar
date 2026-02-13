from discord import app_commands

from bot.app.settings import KOREA_MARKET_URLS
from bot.features.kheatmap.policy import build_body, build_post_title
from bot.features.runner import run_heatmap_command
from bot.markets.providers.korea import capture


def register(tree: app_commands.CommandTree, client) -> None:
    @tree.command(name="kheatmap", description="Create or update daily Korea heatmap post in forum.")
    async def kheatmap_command(interaction):
        await run_heatmap_command(
            interaction=interaction,
            client=client,
            command_key="kheatmap",
            targets=KOREA_MARKET_URLS,
            capture_func=capture,
            title_builder=build_post_title,
            body_builder=build_body,
        )
