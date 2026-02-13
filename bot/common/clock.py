from datetime import datetime

from bot.app.settings import TIMEZONE


def now_kst() -> datetime:
    return datetime.now(TIMEZONE)


def date_key(dt: datetime | None = None) -> str:
    value = dt or now_kst()
    return value.strftime("%Y-%m-%d")


def timestamp_text(dt: datetime | None = None) -> str:
    value = dt or now_kst()
    return value.strftime("%Y-%m-%d %H:%M:%S")


def capture_stamp(dt: datetime | None = None) -> str:
    value = dt or now_kst()
    return value.strftime("%Y%m%d_%H%M%S")
