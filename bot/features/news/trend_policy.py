from __future__ import annotations

from datetime import datetime
from typing import Sequence

from bot.common.clock import date_key
from bot.intel.providers.news import NewsItem, ThemeBrief, TrendThemeReport

DISCORD_MESSAGE_LIMIT = 2000
_REGION_LABELS = {
    "domestic": "국내",
    "global": "해외",
}


def build_trend_post_title(dt: datetime | None = None) -> str:
    return f"[{date_key(dt)} 트렌드 테마 뉴스]"


def build_trend_starter_body(timestamp: str, report: TrendThemeReport) -> str:
    domestic = report.for_region("domestic")
    global_items = report.for_region("global")
    lines = [
        f"{timestamp} KST 트렌드 테마 브리핑",
        "",
        f"국내 테마 {len(domestic)}개 | 해외 테마 {len(global_items)}개",
        _summary_line("domestic", domestic),
        _summary_line("global", global_items),
    ]
    return "\n".join(lines)


def build_trend_region_messages(
    region: str,
    themes: Sequence[ThemeBrief],
    *,
    max_chars: int = DISCORD_MESSAGE_LIMIT,
) -> list[str]:
    label = _REGION_LABELS.get(region, region)
    if not themes:
        return [f"[{label} 트렌드 테마]\n- (유의미한 테마 부족)"]

    header = f"[{label} 트렌드 테마]"
    blocks = []
    for index, theme in enumerate(themes, start=1):
        blocks.extend(_fit_theme_block(header, _theme_block(index, theme), max_chars))
    messages: list[str] = []
    current = [header]

    for block in blocks:
        candidate = current + [""] + block if len(current) > 1 else current + block
        if len("\n".join(candidate)) > max_chars and len(current) > 1:
            messages.append("\n".join(current))
            current = [header] + block
            continue
        current = candidate

    if current:
        messages.append("\n".join(current))
    return messages


def _summary_line(region: str, themes: Sequence[ThemeBrief]) -> str:
    label = _REGION_LABELS.get(region, region)
    if not themes:
        return f"- {label}: (유의미한 테마 부족)"
    return f"- {label}: {', '.join(theme.theme_name for theme in themes)}"


def _theme_block(index: int, theme: ThemeBrief) -> list[str]:
    lines = [
        _truncate_text(f"{index}. {theme.theme_name}", 120),
        _truncate_text(f"- 근거: {' | '.join(theme.reason_tags)}", 240),
    ]
    for item in theme.representative_items:
        lines.append(_fmt_item(item))
    return lines


def _fmt_item(item: NewsItem) -> str:
    return _truncate_text(
        f"- {item.title} | {item.source} | {item.published_at.strftime('%H:%M')} | {item.link}",
        480,
    )


def _fit_theme_block(header: str, block: list[str], max_chars: int) -> list[list[str]]:
    if len("\n".join([header] + block)) <= max_chars:
        return [block]

    body_budget = max(24, max_chars - len(header) - 1)
    title_budget = max(16, body_budget // 3)
    title = _truncate_text(block[0], title_budget)
    continuation_title = _truncate_text(f"{title} (계속)", title_budget)
    chunks: list[list[str]] = []
    current = [title]

    for raw_line in block[1:]:
        active_title = title if not chunks else continuation_title
        if current[0] != active_title:
            current = [active_title]
        available = max_chars - len("\n".join([header] + current)) - 1
        if available <= 0:
            chunks.append(current)
            current = [continuation_title]
            available = max_chars - len("\n".join([header] + current)) - 1
        safe_line = _truncate_text(raw_line, max(1, available))
        candidate = current + [safe_line]
        if len("\n".join([header] + candidate)) > max_chars and len(current) > 1:
            chunks.append(current)
            current = [continuation_title]
            available = max_chars - len("\n".join([header] + current)) - 1
            safe_line = _truncate_text(raw_line, max(1, available))
            current.append(safe_line)
            continue
        current = candidate

    if current:
        chunks.append(current)
    return chunks


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 1:
        return text[:max_chars]
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1]}…"
