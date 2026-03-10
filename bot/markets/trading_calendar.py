from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import exchange_calendars as xcals

NY_TZ = ZoneInfo("America/New_York")


@lru_cache(maxsize=1)
def _krx_calendar():
    return xcals.get_calendar("XKRX")


@lru_cache(maxsize=1)
def _nyse_calendar():
    return xcals.get_calendar("XNYS")


def is_krx_trading_day(now_kst: datetime) -> bool:
    session = now_kst.date().isoformat()
    return bool(_krx_calendar().is_session(session))


def is_nyse_trading_day(now_kst: datetime) -> bool:
    ny_date = now_kst.astimezone(NY_TZ).date().isoformat()
    return bool(_nyse_calendar().is_session(ny_date))


def safe_check_krx_trading_day(now_kst: datetime) -> tuple[bool | None, str | None]:
    try:
        return is_krx_trading_day(now_kst), None
    except Exception as exc:
        return None, str(exc)


def safe_check_nyse_trading_day(now_kst: datetime) -> tuple[bool | None, str | None]:
    try:
        return is_nyse_trading_day(now_kst), None
    except Exception as exc:
        return None, str(exc)
