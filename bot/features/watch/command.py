import discord
from discord import app_commands

from bot.forum.repository import add_watch_symbol, list_watch_symbols, load_state, remove_watch_symbol, save_state


def register(tree: app_commands.CommandTree, client) -> None:
    watch = app_commands.Group(name="watch", description="관심종목 watchlist 관리")

    @watch.command(name="add", description="관심 종목 추가")
    @app_commands.describe(symbol="종목 코드 또는 티커")
    async def watch_add(interaction: discord.Interaction, symbol: str) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return
        state = load_state()
        added = add_watch_symbol(state, interaction.guild_id, symbol)
        save_state(state)
        if added:
            await interaction.response.send_message(f"관심종목 `{symbol.upper()}` 를 추가했습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("이미 등록되었거나 잘못된 종목 코드입니다.", ephemeral=True)

    @watch.command(name="remove", description="관심 종목 제거")
    @app_commands.describe(symbol="종목 코드 또는 티커")
    async def watch_remove(interaction: discord.Interaction, symbol: str) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return
        state = load_state()
        removed = remove_watch_symbol(state, interaction.guild_id, symbol)
        save_state(state)
        if removed:
            await interaction.response.send_message(f"관심종목 `{symbol.upper()}` 를 제거했습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("등록되지 않은 종목입니다.", ephemeral=True)

    @watch.command(name="list", description="관심 종목 목록 조회")
    async def watch_list(interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return
        state = load_state()
        symbols = list_watch_symbols(state, interaction.guild_id)
        if not symbols:
            await interaction.response.send_message("등록된 관심종목이 없습니다.", ephemeral=True)
            return
        await interaction.response.send_message("등록 목록:\n- " + "\n- ".join(symbols), ephemeral=True)

    tree.add_command(watch)
