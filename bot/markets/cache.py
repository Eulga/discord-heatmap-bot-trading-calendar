from datetime import datetime, timedelta
from pathlib import Path

from bot.app.settings import CACHE_TTL_SECONDS, TIMEZONE


def parse_iso_datetime(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TIMEZONE)
    return dt.astimezone(TIMEZONE)


def is_cache_valid(image_path: Path, captured_at: str, now: datetime) -> bool:
    if not image_path.exists():
        return False
    parsed = parse_iso_datetime(captured_at)
    if parsed is None:
        return False
    return now - parsed <= timedelta(seconds=CACHE_TTL_SECONDS)
