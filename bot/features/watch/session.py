from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import exchange_calendars as xcals


KRX_TZ = ZoneInfo("Asia/Seoul")
NY_TZ = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class WatchMarketSession:
    market_code: str
    market_mic: str
    timezone: ZoneInfo
    local_now: datetime
    session_date: str
    is_trading_day: bool
    is_regular_session_open: bool
    regular_open_at: datetime
    regular_close_at: datetime

    @property
    def is_after_regular_close(self) -> bool:
        return self.is_trading_day and not self.is_regular_session_open and self.local_now >= self.regular_close_at


@lru_cache(maxsize=1)
def _krx_calendar():
    return xcals.get_calendar("XKRX")


@lru_cache(maxsize=1)
def _nyse_calendar():
    return xcals.get_calendar("XNYS")


def _market_config(symbol: str) -> tuple[str, ZoneInfo, int, int, int, int]:
    market_code = symbol.strip().upper().split(":", maxsplit=1)[0]
    if market_code == "KRX":
        return "XKRX", KRX_TZ, 9, 0, 15, 30
    if market_code in {"NAS", "NYS", "AMS"}:
        return "XNYS", NY_TZ, 9, 30, 16, 0
    raise RuntimeError(f"unsupported-market:{symbol}")


def _calendar_for_mic(market_mic: str):
    if market_mic == "XKRX":
        return _krx_calendar()
    if market_mic == "XNYS":
        return _nyse_calendar()
    raise RuntimeError(f"unsupported-market-mic:{market_mic}")


def _session_date(calendar, date_text: str, *, direction: str = "none") -> str:
    session = calendar.date_to_session(date_text, direction=direction)
    return session.date().isoformat()


def _previous_session_date(calendar, date_text: str) -> str:
    session = calendar.date_to_session(date_text, direction="next" if not calendar.is_session(date_text) else "none")
    previous = calendar.previous_session(session)
    return previous.date().isoformat()


def get_watch_market_session(symbol: str, now: datetime) -> WatchMarketSession:
    market_mic, timezone, open_hour, open_minute, close_hour, close_minute = _market_config(symbol)
    calendar = _calendar_for_mic(market_mic)
    local_now = now.astimezone(timezone)
    local_date = local_now.date().isoformat()
    is_trading_day = bool(calendar.is_session(local_date))
    regular_open_at = local_now.replace(hour=open_hour, minute=open_minute, second=0, microsecond=0)
    regular_close_at = local_now.replace(hour=close_hour, minute=close_minute, second=0, microsecond=0)
    is_regular_session_open = is_trading_day and regular_open_at <= local_now < regular_close_at

    if is_trading_day and local_now >= regular_open_at:
        session_date = local_date
    elif is_trading_day:
        session_date = _previous_session_date(calendar, local_date)
    else:
        session_date = _previous_session_date(calendar, local_date)

    return WatchMarketSession(
        market_code=symbol.strip().upper().split(":", maxsplit=1)[0],
        market_mic=market_mic,
        timezone=timezone,
        local_now=local_now,
        session_date=session_date,
        is_trading_day=is_trading_day,
        is_regular_session_open=is_regular_session_open,
        regular_open_at=regular_open_at,
        regular_close_at=regular_close_at,
    )


def session_date_for_snapshot(symbol: str, asof: datetime) -> str:
    return get_watch_market_session(symbol, asof).session_date
