from bot.common.clock import date_key


def build_post_title() -> str:
    return f"[{date_key()} 한국장 히트맵]"


def build_body(timestamp_text: str, source_lines: list[str], failed: list[str]) -> str:
    lines = [f"{timestamp_text} KST 업데이트"]
    lines.extend(source_lines)
    if failed:
        lines.append("Failed:")
        lines.extend(f"- {line}" for line in failed)
    return "\n".join(lines)
