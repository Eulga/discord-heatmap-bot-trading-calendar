from bot.common.clock import date_key
from bot.intel.providers.news import NewsItem


def build_post_title() -> str:
    return f"[{date_key()} 아침 경제 뉴스 브리핑]"


def _fmt(items: list[NewsItem]) -> list[str]:
    lines: list[str] = []
    for item in items:
        lines.append(
            f"- {item.title} | {item.source} | {item.published_at.strftime('%H:%M')} | {item.link}"
        )
    return lines


def build_body(timestamp_text: str, domestic: list[NewsItem], global_items: list[NewsItem]) -> str:
    lines = [f"{timestamp_text} KST 브리핑", "", "[국내]"]
    lines.extend(_fmt(domestic) or ["- (데이터 없음)"])
    lines.extend(["", "[해외]"])
    lines.extend(_fmt(global_items) or ["- (데이터 없음)"])
    return "\n".join(lines)
