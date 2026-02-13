from discord import app_commands

from bot.app.settings import US_MARKET_URLS
from bot.features.runner import run_heatmap_command
from bot.features.usheatmap.policy import build_body, build_post_title
from bot.markets.providers.us import capture


def register(tree: app_commands.CommandTree, client) -> None:
    @tree.command(name="usheatmap", description="Create or update daily US heatmap post in forum.")
    async def usheatmap_command(interaction):
        await run_heatmap_command(
            interaction=interaction,
            client=client,
            command_key="usheatmap",
            targets=US_MARKET_URLS,
            capture_func=capture,
            title_builder=build_post_title,
            body_builder=build_body,
        )
