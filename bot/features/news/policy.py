from datetime import datetime

from bot.common.clock import date_key
from bot.intel.providers.news import NewsItem

DISCORD_MESSAGE_LIMIT = 2000
_REGION_LABELS = {
    "domestic": "국내",
    "global": "해외",
}


def build_post_title(region: str | None = None, dt: datetime | None = None) -> str:
    if region is None:
        return f"[{date_key(dt)} 아침 경제 뉴스 브리핑]"
    label = _REGION_LABELS.get(region, region)
    return f"[{date_key(dt)} {label} 경제 뉴스 브리핑]"


def _fmt(items: list[NewsItem]) -> list[str]:
    lines: list[str] = []
    for item in items:
        source_time = " · ".join(part for part in [item.source, item.published_at.strftime("%H:%M")] if part)
        block = [f"**{item.title}**"]
        if source_time:
            block.append(source_time)
        if item.summary:
            block.append(f"> {_truncate_line(item.summary, 180)}")
        block.append(item.link)
        lines.append("\n".join(block))
    return lines


def _fits(lines: list[str], future_lines: list[str], max_chars: int) -> bool:
    return len("\n".join(lines + future_lines)) <= max_chars


def _truncate_line(text: str, max_chars: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max(0, max_chars - 1)].rstrip()}…"


def _append_section_items(lines: list[str], item_lines: list[str], future_lines: list[str], max_chars: int) -> None:
    if not item_lines:
        lines.append("- (데이터 없음)")
        return

    added = 0
    for item_line in item_lines:
        if not _fits(lines + [item_line], future_lines, max_chars):
            break
        lines.append(item_line)
        added += 1

    if added == 0:
        lines.append("- (본문 길이 제한으로 생략)")
        return

    omitted = len(item_lines) - added
    if omitted <= 0:
        return

    summary_line = f"- (추가 기사 {omitted}건 생략)"
    if _fits(lines + [summary_line], future_lines, max_chars):
        lines.append(summary_line)


def build_body(
    timestamp_text: str,
    domestic: list[NewsItem],
    global_items: list[NewsItem],
    *,
    max_chars: int = DISCORD_MESSAGE_LIMIT,
) -> str:
    domestic_lines = _fmt(domestic)
    global_lines = _fmt(global_items)

    lines = [f"{timestamp_text} KST 브리핑", "", "[국내]"]
    global_min_lines = ["", "[해외]"]
    global_min_lines.append(global_lines[0] if global_lines else "- (데이터 없음)")
    _append_section_items(lines, domestic_lines, global_min_lines, max_chars)

    lines.extend(["", "[해외]"])
    _append_section_items(lines, global_lines, [], max_chars)
    return "\n".join(lines)


def build_region_body(
    timestamp_text: str,
    region: str,
    items: list[NewsItem],
    *,
    max_chars: int = DISCORD_MESSAGE_LIMIT,
) -> str:
    label = _REGION_LABELS.get(region, region)
    lines = [f"{timestamp_text} KST 브리핑", "", f"[{label}]"]
    _append_section_items(lines, _fmt(items), [], max_chars)
    return "\n".join(lines)
