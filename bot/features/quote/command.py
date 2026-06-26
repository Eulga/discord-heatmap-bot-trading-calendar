import asyncio
from difflib import SequenceMatcher
import json
import logging
import unicodedata
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import discord
from discord import app_commands

from bot.app.settings import INTEL_API_TIMEOUT_SECONDS, STOCK_DASHBOARD_API_BASE_URL, STOCK_DASHBOARD_INTERNAL_TOKEN
from bot.features.dashboard_session import dashboard_market_session, schedule_icon

logger = logging.getLogger(__name__)
QUOTE_EMBED_COLOR = 0x22D3EE
QUOTE_EMBED_DESCRIPTION_LIMIT = 4000
NEWS_EMBED_COLOR = 0x38BDF8
SCHEDULE_EMBED_COLOR = 0xF59E0B
STOCK_EMBED_COLOR = 0x14B8A6
THEME_CHOICE_LIMIT = 25
THEME_MATCH_THRESHOLD = 0.62

RANGE_LABELS = {
    "today": "오늘",
    "tomorrow": "내일",
    "week": "이번주",
}


def _signed_change_text(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith(("+", "-")):
        return f"{text}%"
    try:
        parsed = float(text)
    except ValueError:
        return text
    return f"{parsed:+.2f}%"


def _change_value(value: str) -> float | None:
    try:
        return float(str(value or "").replace("%", "").replace("+", "").strip())
    except ValueError:
        return None


def _market_marker(market: str, change: float | None) -> str:
    if change is None or change == 0:
        return "⚪"

    is_kr_market = market in {"국장", "KR", "KRX"}
    if change > 0:
        return "🔴" if is_kr_market else "🟢"
    return "🔵" if is_kr_market else "🔴"


def _format_quote_item(item: dict[str, Any]) -> str:
    symbol = str(item.get("symbol") or "").strip()
    name = str(item.get("name") or symbol or "관심종목").strip()
    market = str(item.get("market") or "").strip()
    change = _change_value(str(item.get("change") or ""))
    session = dashboard_market_session(market)
    title = f"({symbol}) {name}".strip() if symbol else name

    if item.get("quoteAvailable") is False:
        return f"{title}\n⚪ 시세 없음"

    change_text = _signed_change_text(str(item.get("change") or ""))
    if not change_text:
        return f"{title}\n⚪ {session.basis_label} 확인 안됨"

    return f"{title}\n{_market_marker(market, change)} {session.basis_label} {change_text}"


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rstrip() + "\n…"


def _schedule_memo_signal(text: str) -> str:
    if any(keyword in text for keyword in ("우호", "완화", "개선", "강함")):
        return "🟢"
    if any(keyword in text for keyword in ("부담", "악화", "둔화", "약화")):
        return "🔴"
    if text.strip():
        return "⚪"
    return ""


def _format_schedule_memo(memo: str) -> str:
    parts = [part.strip() for part in memo.split("·") if part.strip()]
    if not parts:
        return ""

    visible_parts: list[str] = []
    judgment_parts: list[str] = []

    for part in parts:
        if part.startswith("판정 "):
            judgment_parts.extend(item.strip() for item in part.replace("판정 ", "", 1).split("/") if item.strip())
            continue
        visible_parts.append(part)

    marker = _schedule_memo_signal(" / ".join(judgment_parts))
    return " ".join(part for part in [marker, " · ".join(visible_parts)] if part)


def _normalize_theme_key(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    return "".join(character for character in text if character.isalnum())


def _is_all_theme(value: str) -> bool:
    normalized = _normalize_theme_key(value)
    return normalized in {"", "전체", "all"}


def _theme_match_score(query: str, theme: str) -> float:
    normalized_query = _normalize_theme_key(query)
    normalized_theme = _normalize_theme_key(theme)

    if not normalized_query:
        return 1.0

    if normalized_query == normalized_theme:
        return 1.0

    if normalized_query in normalized_theme:
        return 0.92

    if normalized_theme in normalized_query:
        return 0.86

    return SequenceMatcher(None, normalized_query, normalized_theme).ratio()


def _theme_choices(payload: dict[str, Any], query: str, *, include_all: bool = True) -> list[tuple[str, str, int]]:
    raw_themes = payload.get("themes")
    themes: list[tuple[str, str, int]] = []

    if include_all:
        themes.append(("전체", "전체", 0))

    if isinstance(raw_themes, list):
        for item in raw_themes:
            if not isinstance(item, dict):
                continue

            name = str(item.get("name") or "").strip()
            if not name:
                continue

            try:
                count = int(item.get("count") or 0)
            except (TypeError, ValueError):
                count = 0

            themes.append((name, name, count))

    normalized_query = _normalize_theme_key(query)
    scored = [
        (score, index, name, value, count)
        for index, (name, value, count) in enumerate(themes)
        if (score := _theme_match_score(query, name)) >= (0.0 if not normalized_query else 0.42)
    ]
    scored.sort(key=lambda item: (-item[0], 0 if item[3] == "전체" else 1, item[2]))
    return [(name, value, count) for _score, _index, name, value, count in scored[:THEME_CHOICE_LIMIT]]


def _resolve_theme_input(theme: str, payload: dict[str, Any]) -> tuple[str | None, list[str]]:
    normalized = theme.strip()

    if _is_all_theme(normalized):
        return "", []

    choices = _theme_choices(payload, normalized, include_all=False)

    if not choices:
        return normalized, []

    best_name, best_value, _count = choices[0]
    if _theme_match_score(normalized, best_name) >= THEME_MATCH_THRESHOLD:
        return best_value, []

    return None, [name for name, _value, _count in choices[:5]]


def _build_quote_embed(payload: dict[str, Any]) -> discord.Embed:
    theme = str(payload.get("theme") or "전체").strip()
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return discord.Embed(
            title=f"{theme} 시세",
            description="해당 테마에 등록된 관심종목이 없습니다.",
            color=QUOTE_EMBED_COLOR,
        )

    blocks = [_format_quote_item(item) for item in items if isinstance(item, dict)]
    if not blocks:
        return discord.Embed(
            title=f"{theme} 시세",
            description="표시할 수 있는 관심종목이 없습니다.",
            color=QUOTE_EMBED_COLOR,
        )

    description = "\n\n".join(blocks)
    description = _truncate(description, QUOTE_EMBED_DESCRIPTION_LIMIT)

    embed = discord.Embed(title=f"{theme} 시세", description=description, color=QUOTE_EMBED_COLOR)
    embed.set_footer(text="시장별 현재 세션 기준")
    return embed


def _build_stock_embed(payload: dict[str, Any]) -> discord.Embed:
    item = payload.get("item")
    query = str(payload.get("query") or "종목").strip()
    if not isinstance(item, dict):
        return discord.Embed(
            title=f"{query} 조회 결과",
            description="웹 관심종목에서 해당 종목을 찾지 못했습니다.",
            color=STOCK_EMBED_COLOR,
        )

    symbol = str(item.get("symbol") or "").strip()
    name = str(item.get("name") or symbol or "관심종목").strip()
    category = str(item.get("category") or "").strip()
    market = str(item.get("market") or "").strip()
    price = str(item.get("price") or "시세 없음").strip()
    change_text = _signed_change_text(str(item.get("change") or ""))
    change = _change_value(str(item.get("change") or ""))
    news = str(item.get("news") or "").strip()
    session = dashboard_market_session(market)

    lines = [
        " · ".join(part for part in [category if category != "직접 추가" else "", market] if part),
        f"현재가 {price}",
    ]
    if change_text:
        lines.append(f"{_market_marker(market, change)} {session.basis_label} {change_text}")
    if news:
        lines.append(f"뉴스: {news}")

    embed = discord.Embed(
        title=f"({symbol}) {name}" if symbol else name,
        description="\n".join(line for line in lines if line),
        color=STOCK_EMBED_COLOR,
    )
    embed.set_footer(text=session.footer_text)
    return embed


def _build_news_embed(payload: dict[str, Any]) -> discord.Embed:
    theme = str(payload.get("theme") or "전체").strip()
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return discord.Embed(
            title=f"{theme} 뉴스",
            description="표시할 뉴스가 없습니다.",
            color=NEWS_EMBED_COLOR,
        )

    blocks = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        source = str(item.get("source") or "").strip()
        time = str(item.get("time") or "").strip()
        symbol = str(item.get("symbol") or "").strip()
        meta = " · ".join(part for part in [symbol, source, time] if part)
        blocks.append(f"• {title}\n  {meta}" if meta else f"• {title}")

    description = _truncate("\n\n".join(blocks), QUOTE_EMBED_DESCRIPTION_LIMIT)
    return discord.Embed(title=f"{theme} 뉴스", description=description or "표시할 뉴스가 없습니다.", color=NEWS_EMBED_COLOR)


def _build_schedule_embed(payload: dict[str, Any]) -> discord.Embed:
    range_key = str(payload.get("range") or "today").strip()
    title = f"{RANGE_LABELS.get(range_key, '오늘')} 일정"
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return discord.Embed(title=title, description="표시할 일정이 없습니다.", color=SCHEDULE_EMBED_COLOR)

    sections: dict[str, list[str]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        date = str(item.get("date") or "").strip()
        time = str(item.get("time") or "").strip()
        event_title = str(item.get("title") or "").strip()
        raw_event_type = str(item.get("eventType") or "earnings").strip()
        event_type = "경제" if raw_event_type == "economic" else "공시" if raw_event_type == "disclosure" else "실적"
        market = str(item.get("market") or "").strip()
        memo = str(item.get("memo") or "").strip()
        url = str(item.get("url") or "").strip()
        icon = schedule_icon(market, raw_event_type, event_title)
        market_label = "매크로" if raw_event_type == "economic" else market or "일정"
        section = f"{icon} {market_label} {event_type}".strip()
        schedule_time = " ".join(part for part in [date, time] if part)
        line = f"• {schedule_time} · {event_title}".strip()
        if memo:
            line = f"{line}\n  {_format_schedule_memo(memo)}"
        if url:
            line = f"{line}\n  [원문 보기]({url})"
        sections.setdefault(section, []).append(line)

    blocks = [f"**{section}**\n" + "\n".join(lines) for section, lines in sections.items()]
    description = _truncate("\n\n".join(blocks), QUOTE_EMBED_DESCRIPTION_LIMIT)
    embed = discord.Embed(title=title, description=description, color=SCHEDULE_EMBED_COLOR)
    embed.set_footer(text="KST 기준")
    return embed


def _build_help_embed() -> discord.Embed:
    description = "\n".join(
        [
            "`/시세 테마:반도체` - 같은 테마 관심종목 시세 조회",
            "`/종목 종목:삼성전자` - 단일 관심종목 시세와 최신 뉴스 조회",
            "`/뉴스 테마:반도체` - 테마 관련 최신 뉴스 조회",
            "`/일정 기간:오늘` - 어닝/경제 일정 조회",
            "`/도움말` - 사용 가능한 명령 확인",
            "",
            "테마는 일부만 입력해도 비슷한 항목을 찾습니다. 예: `ai반도체`, `빅테크`",
            "입력창 자동완성에 현재 등록된 테마와 종목 수가 표시됩니다.",
        ]
    )
    return discord.Embed(title="Drumstick 명령어", description=description, color=QUOTE_EMBED_COLOR)


def _fetch_dashboard_api(path: str, params: dict[str, str]) -> dict[str, Any]:
    if not STOCK_DASHBOARD_API_BASE_URL or not STOCK_DASHBOARD_INTERNAL_TOKEN:
        raise RuntimeError("stock-dashboard-api-not-configured")

    query = urlencode(params)
    request = Request(
        f"{STOCK_DASHBOARD_API_BASE_URL.rstrip('/')}{path}?{query}",
        headers={
            "Accept": "application/json",
            "x-internal-token": STOCK_DASHBOARD_INTERNAL_TOKEN,
        },
    )
    with urlopen(request, timeout=INTEL_API_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise RuntimeError("stock-dashboard-invalid-response")
    return data


def _fetch_dashboard_quotes(theme: str, *, limit: str | None = None) -> dict[str, Any]:
    params = {"theme": theme}
    if limit:
        params["limit"] = limit
    return _fetch_dashboard_api("/api/discord/quotes", params)


def _fetch_dashboard_stock(query: str) -> dict[str, Any]:
    return _fetch_dashboard_api("/api/discord/stocks", {"query": query})


def _fetch_dashboard_news(theme: str) -> dict[str, Any]:
    return _fetch_dashboard_api("/api/discord/news", {"theme": theme})


def _fetch_dashboard_schedule(range_value: str) -> dict[str, Any]:
    return _fetch_dashboard_api("/api/discord/schedule", {"range": range_value})


def _fetch_dashboard_themes() -> dict[str, Any]:
    return _fetch_dashboard_api("/api/discord/themes", {})


async def autocomplete_theme(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    try:
        payload = await asyncio.to_thread(_fetch_dashboard_themes)
    except Exception:
        logger.exception("[command] 테마 자동완성 실패 guild=%s current=%s", interaction.guild_id, current)
        return []

    return [
        app_commands.Choice(name=(f"{name} · {count}종목" if count else name)[:100], value=value)
        for name, value, count in _theme_choices(payload, current)
    ]


def register(tree: app_commands.CommandTree, client) -> None:
    @tree.command(name="시세", description="웹 관심종목 테마별 시세 조회")
    @app_commands.describe(theme="웹 관심종목 카테고리 이름. 예: 반도체, AI·반도체, 빅테크")
    @app_commands.rename(theme="테마")
    async def quote_command(interaction: discord.Interaction, theme: str) -> None:
        normalized_theme = theme.strip()
        if not normalized_theme:
            await interaction.response.send_message("테마명을 입력해 주세요.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        try:
            theme_payload = await asyncio.to_thread(_fetch_dashboard_themes)
            resolved_theme, suggestions = _resolve_theme_input(normalized_theme, theme_payload)
            if resolved_theme is None:
                await interaction.followup.send(
                    f"`{normalized_theme}` 테마를 찾지 못했습니다. 비슷한 테마: {', '.join(suggestions)}",
                    ephemeral=True,
                )
                return

            payload = await asyncio.to_thread(_fetch_dashboard_quotes, resolved_theme)
        except Exception as exc:
            logger.exception("[command] 시세 조회 실패 guild=%s user=%s theme=%s", interaction.guild_id, getattr(getattr(interaction, "user", None), "id", None), normalized_theme)
            await interaction.followup.send(f"`{normalized_theme}` 시세를 불러오지 못했습니다.", ephemeral=True)
            return

        await interaction.followup.send(embed=_build_quote_embed(payload))

    quote_command.autocomplete("theme")(autocomplete_theme)

    @tree.command(name="종목", description="웹 관심종목 단일 종목 조회")
    @app_commands.describe(query="종목명, 종목 코드, 또는 티커")
    @app_commands.rename(query="종목")
    async def stock_command(interaction: discord.Interaction, query: str) -> None:
        normalized_query = query.strip()
        if not normalized_query:
            await interaction.response.send_message("종목명을 입력해 주세요.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        try:
            payload = await asyncio.to_thread(_fetch_dashboard_stock, normalized_query)
        except Exception:
            logger.exception("[command] 종목 조회 실패 guild=%s query=%s", interaction.guild_id, normalized_query)
            await interaction.followup.send(f"`{normalized_query}` 종목 정보를 불러오지 못했습니다.", ephemeral=True)
            return

        await interaction.followup.send(embed=_build_stock_embed(payload))

    @tree.command(name="뉴스", description="웹 관심종목 테마별 뉴스 조회")
    @app_commands.describe(theme="웹 관심종목 카테고리 이름. 비우면 전체 뉴스")
    @app_commands.rename(theme="테마")
    async def news_command(interaction: discord.Interaction, theme: str = "") -> None:
        normalized_theme = theme.strip()

        await interaction.response.defer(thinking=True)
        try:
            if normalized_theme:
                theme_payload = await asyncio.to_thread(_fetch_dashboard_themes)
                resolved_theme, suggestions = _resolve_theme_input(normalized_theme, theme_payload)
                if resolved_theme is None:
                    await interaction.followup.send(
                        f"`{normalized_theme}` 테마를 찾지 못했습니다. 비슷한 테마: {', '.join(suggestions)}",
                        ephemeral=True,
                    )
                    return
            else:
                resolved_theme = ""

            payload = await asyncio.to_thread(_fetch_dashboard_news, resolved_theme)
        except Exception:
            logger.exception("[command] 뉴스 조회 실패 guild=%s theme=%s", interaction.guild_id, normalized_theme)
            await interaction.followup.send("뉴스를 불러오지 못했습니다.", ephemeral=True)
            return

        await interaction.followup.send(embed=_build_news_embed(payload))

    news_command.autocomplete("theme")(autocomplete_theme)

    @tree.command(name="일정", description="어닝/경제 일정 조회")
    @app_commands.describe(range_value="조회 기간")
    @app_commands.rename(range_value="기간")
    @app_commands.choices(
        range_value=[
            app_commands.Choice(name="오늘", value="today"),
            app_commands.Choice(name="내일", value="tomorrow"),
            app_commands.Choice(name="이번주", value="week"),
        ]
    )
    async def schedule_command(interaction: discord.Interaction, range_value: app_commands.Choice[str]) -> None:
        await interaction.response.defer(thinking=True)
        try:
            payload = await asyncio.to_thread(_fetch_dashboard_schedule, range_value.value)
        except Exception:
            logger.exception("[command] 일정 조회 실패 guild=%s range=%s", interaction.guild_id, range_value.value)
            await interaction.followup.send("일정을 불러오지 못했습니다.", ephemeral=True)
            return

        await interaction.followup.send(embed=_build_schedule_embed(payload))

    @tree.command(name="도움말", description="Drumstick 명령어 안내")
    async def help_command(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=_build_help_embed(), ephemeral=True)
