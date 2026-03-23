import discord
from discord import app_commands

from bot.forum.repository import add_watch_symbol, list_watch_symbols, load_state, remove_watch_symbol, save_state
from bot.intel.instrument_registry import (
    RegistrySearchResult,
    format_instrument_label,
    format_watch_symbol,
    is_canonical_symbol,
    load_registry,
    normalize_canonical_symbol,
    normalize_search_text,
    normalize_stored_watch_symbol,
)


def _dedupe_results(results: list[RegistrySearchResult]) -> list[RegistrySearchResult]:
    deduped: list[RegistrySearchResult] = []
    seen: set[str] = set()
    for result in results:
        if result.record.canonical_symbol in seen:
            continue
        seen.add(result.record.canonical_symbol)
        deduped.append(result)
    return deduped


def _candidate_lines(results: list[RegistrySearchResult], *, limit: int = 5) -> str:
    rows = [f"- {format_instrument_label(result.record)}" for result in _dedupe_results(results)[:limit]]
    return "\n".join(rows)


def resolve_watch_add_symbol(symbol: str) -> tuple[str | None, str | None]:
    raw = symbol.strip()
    if not raw:
        return None, "종목명, 종목 코드, 또는 티커를 입력해주세요."

    canonical = normalize_canonical_symbol(raw)
    if canonical is not None:
        return canonical, None

    normalized, warning = normalize_stored_watch_symbol(raw)
    if normalized.startswith("KRX:") and warning == "legacy-krx-code":
        return normalized, None
    if is_canonical_symbol(normalized) and warning == "legacy-us-ticker":
        return normalized, None

    results = _dedupe_results(load_registry().search(raw, limit=10))
    if len(results) == 1:
        return results[0].record.canonical_symbol, None
    exact_results = [result for result in results if result.score >= 900]
    if len(exact_results) == 1:
        return exact_results[0].record.canonical_symbol, None
    if len(results) > 1:
        return None, (
            "여러 후보가 있어 자동 선택하지 않았습니다.\n"
            f"{_candidate_lines(results)}\n"
            "autocomplete에서 다시 선택해주세요."
        )
    return None, "일치하는 종목을 찾지 못했습니다."


def resolve_watch_remove_symbol(symbol: str, *, guild_symbols: list[str]) -> tuple[str | None, str | None]:
    raw = symbol.strip().upper()
    if not raw:
        return None, "제거할 종목을 입력해주세요."
    if raw in guild_symbols:
        return raw, None

    canonical = normalize_canonical_symbol(raw)
    if canonical and canonical in guild_symbols:
        return canonical, None

    normalized, _warning = normalize_stored_watch_symbol(raw)
    if normalized in guild_symbols:
        return normalized, None

    allowed = {item for item in guild_symbols if is_canonical_symbol(item)}
    results = _dedupe_results(load_registry().search(raw, allowed_symbols=allowed, limit=10))
    if len(results) == 1:
        return results[0].record.canonical_symbol, None
    if len(results) > 1:
        return None, (
            "여러 후보가 있어 자동 선택하지 않았습니다.\n"
            f"{_candidate_lines(results)}\n"
            "autocomplete에서 다시 선택해주세요."
        )
    return None, "등록된 관심종목에서 일치하는 항목을 찾지 못했습니다."


async def autocomplete_watch_add_symbol(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    current = current.strip()
    if not current:
        return []
    choices: list[app_commands.Choice[str]] = []
    canonical = normalize_canonical_symbol(current)
    if canonical is not None:
        choices.append(app_commands.Choice(name=canonical, value=canonical))
    elif current.isdigit() and len(current) == 6:
        choices.append(app_commands.Choice(name=f"국내코드 | KRX:{current}", value=f"KRX:{current}"))

    for result in _dedupe_results(load_registry().search(current, limit=25)):
        label = format_instrument_label(result.record)
        if any(choice.value == result.record.canonical_symbol for choice in choices):
            continue
        choices.append(app_commands.Choice(name=label[:100], value=result.record.canonical_symbol))
        if len(choices) >= 25:
            break
    return choices[:25]


async def autocomplete_watch_remove_symbol(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    if interaction.guild_id is None:
        return []
    state = load_state()
    guild_symbols = list_watch_symbols(state, interaction.guild_id)
    current = current.strip()
    choices: list[app_commands.Choice[str]] = []

    allowed = {item for item in guild_symbols if is_canonical_symbol(item)}
    if current:
        for result in _dedupe_results(load_registry().search(current, allowed_symbols=allowed, limit=25)):
            choices.append(
                app_commands.Choice(
                    name=format_instrument_label(result.record)[:100],
                    value=result.record.canonical_symbol,
                )
            )
            if len(choices) >= 25:
                return choices[:25]

    legacy_symbols = [item for item in guild_symbols if not is_canonical_symbol(item)]
    query = normalize_search_text(current)
    for symbol in legacy_symbols:
        display = f"{symbol} | legacy"
        if query and query not in normalize_search_text(display):
            continue
        choices.append(app_commands.Choice(name=display[:100], value=symbol))
        if len(choices) >= 25:
            break
    return choices[:25]


def register(tree: app_commands.CommandTree, client) -> None:
    watch = app_commands.Group(name="watch", description="관심종목 watchlist 관리")

    @watch.command(name="add", description="관심 종목 추가")
    @app_commands.describe(symbol="종목명, 종목 코드, 또는 티커")
    async def watch_add(interaction: discord.Interaction, symbol: str) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return
        resolved_symbol, error = resolve_watch_add_symbol(symbol)
        if resolved_symbol is None:
            await interaction.response.send_message(error or "관심종목을 해석하지 못했습니다.", ephemeral=True)
            return

        state = load_state()
        added = add_watch_symbol(state, interaction.guild_id, resolved_symbol)
        save_state(state)
        if added:
            await interaction.response.send_message(
                f"관심종목 `{format_watch_symbol(resolved_symbol)}` 를 추가했습니다.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message("이미 등록되었거나 잘못된 종목 코드입니다.", ephemeral=True)

    watch_add.autocomplete("symbol")(autocomplete_watch_add_symbol)

    @watch.command(name="remove", description="관심 종목 제거")
    @app_commands.describe(symbol="종목명, 종목 코드, 또는 티커")
    async def watch_remove(interaction: discord.Interaction, symbol: str) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return
        state = load_state()
        guild_symbols = list_watch_symbols(state, interaction.guild_id)
        resolved_symbol, error = resolve_watch_remove_symbol(symbol, guild_symbols=guild_symbols)
        if resolved_symbol is None:
            await interaction.response.send_message(error or "등록된 관심종목을 찾지 못했습니다.", ephemeral=True)
            return

        removed = remove_watch_symbol(state, interaction.guild_id, resolved_symbol)
        save_state(state)
        if removed:
            await interaction.response.send_message(
                f"관심종목 `{format_watch_symbol(resolved_symbol)}` 를 제거했습니다.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message("등록되지 않은 종목입니다.", ephemeral=True)

    watch_remove.autocomplete("symbol")(autocomplete_watch_remove_symbol)

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
        lines = [f"- {format_watch_symbol(symbol)}" for symbol in symbols]
        await interaction.response.send_message("등록 목록:\n" + "\n".join(lines), ephemeral=True)

    tree.add_command(watch)
