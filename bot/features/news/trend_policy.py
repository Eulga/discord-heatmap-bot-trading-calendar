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

    blocks = [_theme_block(index, theme) for index, theme in enumerate(themes, start=1)]
    messages: list[str] = []
    current = [f"[{label} 트렌드 테마]"]

    for block in blocks:
        candidate = current + [""] + block if len(current) > 1 else current + block
        if len("\n".join(candidate)) > max_chars and len(current) > 1:
            messages.append("\n".join(current))
            current = [f"[{label} 트렌드 테마]"] + block
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
        f"{index}. {theme.theme_name}",
        f"- 근거: {' | '.join(theme.reason_tags)}",
    ]
    for item in theme.representative_items:
        lines.append(_fmt_item(item))
    return lines


def _fmt_item(item: NewsItem) -> str:
    return f"- {item.title} | {item.source} | {item.published_at.strftime('%H:%M')} | {item.link}"
