import logging

import discord
from discord import app_commands

from bot.app.settings import DISCORD_GLOBAL_ADMIN_USER_IDS
from bot.common.clock import now_kst
from bot.features.watch.service import render_watch_placeholder
from bot.features.watch.session import get_watch_market_session
from bot.features.watch.thread_service import delete_watch_thread, upsert_watch_thread
from bot.forum.repository import (
    add_watch_symbol,
    clear_watch_symbol_runtime_state,
    delete_watch_symbol,
    get_guild_watch_forum_channel_id,
    get_watch_session_alert,
    get_watch_symbol_thread,
    get_watch_symbol_status,
    list_watch_symbols,
    load_state,
    save_state,
    set_watch_symbol_thread_status,
    update_watch_session_alert,
)
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

logger = logging.getLogger(__name__)


def _reset_reactivated_same_session_band_state(state, guild_id: int, symbol: str, existing_thread) -> None:
    if not isinstance(existing_thread, dict):
        return
    if str(existing_thread.get("status") or "") != "inactive":
        return

    now = now_kst()
    market_session = get_watch_market_session(symbol, now)
    if not market_session.is_regular_session_open:
        return

    alert_entry = get_watch_session_alert(state, guild_id, symbol)
    active_session_date = str(alert_entry.get("active_session_date") or "")
    last_finalized_session_date = str(alert_entry.get("last_finalized_session_date") or "")
    if active_session_date != market_session.session_date or active_session_date == last_finalized_session_date:
        return

    update_watch_session_alert(
        state,
        guild_id,
        symbol,
        highest_up_band=0,
        highest_down_band=0,
        updated_at=now.isoformat(),
    )


def _interaction_user_id(interaction: discord.Interaction) -> int | None:
    return getattr(getattr(interaction, "user", None), "id", None)


def _is_authorized_admin(interaction: discord.Interaction) -> bool:
    guild = interaction.guild
    if guild is None:
        return False
    user = getattr(interaction, "user", None)
    user_id = getattr(user, "id", None)
    member = user if isinstance(user, discord.Member) else None
    is_global_admin = isinstance(user_id, int) and user_id in DISCORD_GLOBAL_ADMIN_USER_IDS
    is_owner = isinstance(user_id, int) and guild.owner_id == user_id
    is_admin = bool(member and member.guild_permissions.administrator)
    return is_global_admin or is_owner or is_admin


def _watch_status_label(status: str) -> str:
    return "실시간 감시중" if status == "active" else "감시 중단됨"


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

    registry = load_registry()

    canonical = normalize_canonical_symbol(raw)
    if canonical is not None:
        if registry.get(canonical) is not None:
            return canonical, None
        return None, "일치하는 종목을 찾지 못했습니다."

    normalized, warning = normalize_stored_watch_symbol(raw)
    if (
        is_canonical_symbol(normalized)
        and warning in {"legacy-krx-code", "legacy-us-ticker"}
    ):
        if registry.get(normalized) is not None:
            return normalized, None
        return None, "일치하는 종목을 찾지 못했습니다."

    results = _dedupe_results(registry.search(raw, limit=10))
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


def resolve_tracked_watch_symbol(symbol: str, *, guild_symbols: list[str]) -> tuple[str | None, str | None]:
    raw = symbol.strip().upper()
    if not raw:
        return None, "종목을 입력해주세요."
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


async def autocomplete_tracked_watch_symbol(
    interaction: discord.Interaction,
    current: str,
    *,
    active_only: bool | None = None,
) -> list[app_commands.Choice[str]]:
    if interaction.guild_id is None:
        return []
    state = load_state()
    guild_symbols = list_watch_symbols(state, interaction.guild_id)
    if active_only is not None:
        guild_symbols = [
            symbol
            for symbol in guild_symbols
            if (get_watch_symbol_status(state, interaction.guild_id, symbol) == "active") is active_only
        ]
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


async def autocomplete_active_watch_symbol(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    return await autocomplete_tracked_watch_symbol(interaction, current, active_only=True)


async def autocomplete_inactive_watch_symbol(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    return await autocomplete_tracked_watch_symbol(interaction, current, active_only=False)


async def autocomplete_any_watch_symbol(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    return await autocomplete_tracked_watch_symbol(interaction, current, active_only=None)


def register(tree: app_commands.CommandTree, client) -> None:
    watch = app_commands.Group(name="watch", description="관심종목 watchlist 관리")

    @watch.command(name="add", description="관심 종목 추가")
    @app_commands.describe(symbol="종목명, 종목 코드, 또는 티커")
    async def watch_add(interaction: discord.Interaction, symbol: str) -> None:
        if interaction.guild_id is None:
            logger.warning("[command] watch.add rejected reason=no-guild user=%s", _interaction_user_id(interaction))
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return
        resolved_symbol, error = resolve_watch_add_symbol(symbol)
        if resolved_symbol is None:
            logger.warning(
                "[command] watch.add result=failed guild=%s user=%s symbol=%s detail=%s",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                error,
            )
            await interaction.response.send_message(error or "관심종목을 해석하지 못했습니다.", ephemeral=True)
            return

        state = load_state()
        watch_forum_channel_id = get_guild_watch_forum_channel_id(state, interaction.guild_id)
        if watch_forum_channel_id is None:
            logger.warning(
                "[command] watch.add result=failed guild=%s user=%s symbol=%s resolved=%s detail=watch-forum-missing",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                resolved_symbol,
            )
            await interaction.response.send_message(
                "watch 포럼이 설정되지 않았습니다. 운영자에게 `/setwatchforum` 설정을 요청해주세요.",
                ephemeral=True,
            )
            return

        existing_thread = get_watch_symbol_thread(state, interaction.guild_id, resolved_symbol)
        added = add_watch_symbol(state, interaction.guild_id, resolved_symbol)
        if not added:
            status = get_watch_symbol_status(state, interaction.guild_id, resolved_symbol)
            logger.warning(
                "[command] watch.add result=ignored guild=%s user=%s symbol=%s resolved=%s detail=already-tracked",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                resolved_symbol,
            )
            message = (
                "이미 감시 중단된 관심종목입니다. `/watch start`를 사용해주세요."
                if status == "inactive"
                else "이미 등록되었거나 잘못된 종목 코드입니다."
            )
            await interaction.response.send_message(message, ephemeral=True)
            return

        _reset_reactivated_same_session_band_state(state, interaction.guild_id, resolved_symbol, existing_thread)

        try:
            await upsert_watch_thread(
                client=client,
                state=state,
                guild_id=interaction.guild_id,
                forum_channel_id=watch_forum_channel_id,
                symbol=resolved_symbol,
                active=True,
                starter_text=render_watch_placeholder(resolved_symbol, active=True),
            )
        except Exception as exc:
            logger.exception(
                "[command] watch.add result=failed guild=%s user=%s symbol=%s resolved=%s detail=%s",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                resolved_symbol,
                exc,
            )
            await interaction.response.send_message("thread 생성 또는 starter 복구에 실패했습니다.", ephemeral=True)
            return

        save_state(state)
        logger.info(
            "[command] watch.add result=ok guild=%s user=%s symbol=%s resolved=%s",
            interaction.guild_id,
            _interaction_user_id(interaction),
            symbol,
            resolved_symbol,
        )
        await interaction.response.send_message(
            f"관심종목 `{format_watch_symbol(resolved_symbol)}` 를 추가했습니다.",
            ephemeral=True,
        )

    watch_add.autocomplete("symbol")(autocomplete_watch_add_symbol)

    @watch.command(name="start", description="실시간 감시 시작")
    @app_commands.describe(symbol="종목명, 종목 코드, 또는 티커")
    async def watch_start(interaction: discord.Interaction, symbol: str) -> None:
        if interaction.guild_id is None:
            logger.warning("[command] watch.start rejected reason=no-guild user=%s", _interaction_user_id(interaction))
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        state = load_state()
        guild_symbols = list_watch_symbols(state, interaction.guild_id)
        resolved_symbol, error = resolve_tracked_watch_symbol(symbol, guild_symbols=guild_symbols)
        if resolved_symbol is None:
            logger.warning(
                "[command] watch.start result=failed guild=%s user=%s symbol=%s detail=%s",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                error,
            )
            await interaction.response.send_message(error or "등록된 관심종목을 찾지 못했습니다.", ephemeral=True)
            return

        if get_watch_symbol_status(state, interaction.guild_id, resolved_symbol) == "active":
            logger.warning(
                "[command] watch.start result=ignored guild=%s user=%s symbol=%s resolved=%s detail=already-active",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                resolved_symbol,
            )
            await interaction.response.send_message("이미 실시간 감시중인 종목입니다.", ephemeral=True)
            return

        watch_forum_channel_id = get_guild_watch_forum_channel_id(state, interaction.guild_id)
        if watch_forum_channel_id is None:
            logger.warning(
                "[command] watch.start result=failed guild=%s user=%s symbol=%s resolved=%s detail=watch-forum-missing",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                resolved_symbol,
            )
            await interaction.response.send_message(
                "watch 포럼이 설정되지 않았습니다. 운영자에게 `/setwatchforum` 설정을 요청해주세요.",
                ephemeral=True,
            )
            return

        existing_thread = get_watch_symbol_thread(state, interaction.guild_id, resolved_symbol)
        _reset_reactivated_same_session_band_state(state, interaction.guild_id, resolved_symbol, existing_thread)

        try:
            await upsert_watch_thread(
                client=client,
                state=state,
                guild_id=interaction.guild_id,
                forum_channel_id=watch_forum_channel_id,
                symbol=resolved_symbol,
                active=True,
                starter_text=render_watch_placeholder(resolved_symbol, active=True),
            )
        except Exception as exc:
            logger.exception(
                "[command] watch.start result=failed guild=%s user=%s symbol=%s resolved=%s detail=%s",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                resolved_symbol,
                exc,
            )
            await interaction.response.send_message("thread 생성 또는 starter 복구에 실패했습니다.", ephemeral=True)
            return

        save_state(state)
        logger.info(
            "[command] watch.start result=ok guild=%s user=%s symbol=%s resolved=%s",
            interaction.guild_id,
            _interaction_user_id(interaction),
            symbol,
            resolved_symbol,
        )
        await interaction.response.send_message(
            f"관심종목 `{format_watch_symbol(resolved_symbol)}` 의 실시간 감시를 시작했습니다.",
            ephemeral=True,
        )

    watch_start.autocomplete("symbol")(autocomplete_inactive_watch_symbol)

    @watch.command(name="stop", description="실시간 감시 중단")
    @app_commands.describe(symbol="종목명, 종목 코드, 또는 티커")
    async def watch_stop(interaction: discord.Interaction, symbol: str) -> None:
        if interaction.guild_id is None:
            logger.warning("[command] watch.stop rejected reason=no-guild user=%s", _interaction_user_id(interaction))
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        state = load_state()
        guild_symbols = list_watch_symbols(state, interaction.guild_id)
        resolved_symbol, error = resolve_tracked_watch_symbol(symbol, guild_symbols=guild_symbols)
        if resolved_symbol is None:
            logger.warning(
                "[command] watch.stop result=failed guild=%s user=%s symbol=%s detail=%s",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                error,
            )
            await interaction.response.send_message(error or "등록된 관심종목을 찾지 못했습니다.", ephemeral=True)
            return

        if get_watch_symbol_status(state, interaction.guild_id, resolved_symbol) == "inactive":
            logger.warning(
                "[command] watch.stop result=ignored guild=%s user=%s symbol=%s resolved=%s detail=already-inactive",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                resolved_symbol,
            )
            await interaction.response.send_message("이미 감시가 중단된 종목입니다.", ephemeral=True)
            return

        existing_thread = get_watch_symbol_thread(state, interaction.guild_id, resolved_symbol)
        has_tracked_thread_handle = isinstance(existing_thread, dict) and isinstance(existing_thread.get("thread_id"), int)
        has_tracked_thread_handle = has_tracked_thread_handle and isinstance(existing_thread.get("starter_message_id"), int)
        watch_forum_channel_id = get_guild_watch_forum_channel_id(state, interaction.guild_id)
        stale_thread_handle = False
        if has_tracked_thread_handle:
            if watch_forum_channel_id is None:
                logger.warning(
                    "[command] watch.stop result=failed guild=%s user=%s symbol=%s resolved=%s detail=watch-forum-missing",
                    interaction.guild_id,
                    _interaction_user_id(interaction),
                    symbol,
                    resolved_symbol,
                )
                await interaction.response.send_message(
                    f"관심종목 `{format_watch_symbol(resolved_symbol)}` 의 실시간 감시 중단에 실패했습니다. "
                    "기존 스레드 상태를 갱신할 수 없습니다. `/setwatchforum` 설정을 확인한 뒤 다시 시도해주세요.",
                    ephemeral=True,
                )
                return
            try:
                handle = await upsert_watch_thread(
                    client=client,
                    state=state,
                    guild_id=interaction.guild_id,
                    forum_channel_id=watch_forum_channel_id,
                    symbol=resolved_symbol,
                    active=False,
                    starter_text=render_watch_placeholder(resolved_symbol, active=False),
                    allow_create=False,
                )
                if handle is None:
                    stale_thread_handle = True
                    logger.warning(
                        "[command] watch.stop result=degraded guild=%s user=%s symbol=%s resolved=%s detail=stale-thread",
                        interaction.guild_id,
                        _interaction_user_id(interaction),
                        symbol,
                        resolved_symbol,
                    )
            except Exception as exc:
                logger.exception(
                    "[command] watch.stop result=failed guild=%s user=%s symbol=%s resolved=%s detail=%s",
                    interaction.guild_id,
                    _interaction_user_id(interaction),
                    symbol,
                    resolved_symbol,
                    exc,
                )
                await interaction.response.send_message(
                    f"관심종목 `{format_watch_symbol(resolved_symbol)}` 의 실시간 감시 중단에 실패했습니다. "
                    "기존 스레드 상태를 갱신하지 못했습니다. 다시 시도해주세요.",
                    ephemeral=True,
                )
                return

        set_watch_symbol_thread_status(state, interaction.guild_id, resolved_symbol, "inactive")
        clear_watch_symbol_runtime_state(state, interaction.guild_id, resolved_symbol)
        save_state(state)
        logger.info(
            "[command] watch.stop result=ok guild=%s user=%s symbol=%s resolved=%s",
            interaction.guild_id,
            _interaction_user_id(interaction),
            symbol,
            resolved_symbol,
        )
        if stale_thread_handle:
            await interaction.response.send_message(
                f"관심종목 `{format_watch_symbol(resolved_symbol)}` 의 실시간 감시를 중단했습니다. "
                "저장된 스레드를 찾지 못해 기존 스레드 안내 문구는 갱신하지 못했습니다.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"관심종목 `{format_watch_symbol(resolved_symbol)}` 의 실시간 감시를 중단했습니다.",
                ephemeral=True,
            )

    watch_stop.autocomplete("symbol")(autocomplete_active_watch_symbol)

    @watch.command(name="delete", description="관심 종목 완전 삭제")
    @app_commands.describe(symbol="종목명, 종목 코드, 또는 티커")
    async def watch_delete(interaction: discord.Interaction, symbol: str) -> None:
        if interaction.guild_id is None:
            logger.warning("[command] watch.delete rejected reason=no-guild user=%s", _interaction_user_id(interaction))
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return
        if not _is_authorized_admin(interaction):
            logger.warning(
                "[command] watch.delete rejected reason=unauthorized guild=%s user=%s",
                interaction.guild_id,
                _interaction_user_id(interaction),
            )
            await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
            return

        state = load_state()
        guild_symbols = sorted(set(list_watch_symbols(state, interaction.guild_id)))
        resolved_symbol, error = resolve_tracked_watch_symbol(symbol, guild_symbols=guild_symbols)
        if resolved_symbol is None:
            logger.warning(
                "[command] watch.delete result=failed guild=%s user=%s symbol=%s detail=%s",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                error,
            )
            await interaction.response.send_message(error or "등록된 관심종목을 찾지 못했습니다.", ephemeral=True)
            return

        try:
            thread_delete_result = await delete_watch_thread(
                client=client,
                state=state,
                guild_id=interaction.guild_id,
                symbol=resolved_symbol,
            )
        except Exception as exc:
            logger.exception(
                "[command] watch.delete result=failed guild=%s user=%s symbol=%s resolved=%s detail=%s",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                resolved_symbol,
                exc,
            )
            await interaction.response.send_message("thread 삭제에 실패했습니다.", ephemeral=True)
            return

        deleted = delete_watch_symbol(state, interaction.guild_id, resolved_symbol)
        if not deleted:
            logger.warning(
                "[command] watch.delete result=ignored guild=%s user=%s symbol=%s resolved=%s",
                interaction.guild_id,
                _interaction_user_id(interaction),
                symbol,
                resolved_symbol,
            )
            await interaction.response.send_message("등록되지 않은 종목입니다.", ephemeral=True)
            return

        save_state(state)
        logger.info(
            "[command] watch.delete result=ok guild=%s user=%s symbol=%s resolved=%s thread=%s",
            interaction.guild_id,
            _interaction_user_id(interaction),
            symbol,
            resolved_symbol,
            thread_delete_result,
        )
        await interaction.response.send_message(
            f"관심종목 `{format_watch_symbol(resolved_symbol)}` 를 완전히 삭제했습니다.",
            ephemeral=True,
        )

    watch_delete.autocomplete("symbol")(autocomplete_any_watch_symbol)

    @watch.command(name="list", description="관심 종목 목록 조회")
    async def watch_list(interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            logger.warning("[command] watch.list rejected reason=no-guild user=%s", _interaction_user_id(interaction))
            await interaction.response.send_message("이 명령어는 서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return
        state = load_state()
        symbols = list_watch_symbols(state, interaction.guild_id)
        if not symbols:
            logger.info(
                "[command] watch.list result=empty guild=%s user=%s",
                interaction.guild_id,
                _interaction_user_id(interaction),
            )
            await interaction.response.send_message("등록된 관심종목이 없습니다.", ephemeral=True)
            return
        lines = [
            f"- {format_watch_symbol(symbol)} | {_watch_status_label(get_watch_symbol_status(state, interaction.guild_id, symbol))}"
            for symbol in symbols
        ]
        logger.info(
            "[command] watch.list result=ok guild=%s user=%s count=%s",
            interaction.guild_id,
            _interaction_user_id(interaction),
            len(symbols),
        )
        await interaction.response.send_message("등록 목록:\n" + "\n".join(lines), ephemeral=True)

    tree.add_command(watch)
