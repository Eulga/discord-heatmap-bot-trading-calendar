from datetime import datetime
from zoneinfo import ZoneInfo

from bot.markets.trading_calendar import is_krx_trading_day, is_nyse_trading_day

KST = ZoneInfo("Asia/Seoul")


def test_krx_holiday_false():
    dt = datetime(2025, 1, 1, 16, 0, tzinfo=KST)
    assert is_krx_trading_day(dt) is False


def test_krx_weekday_true():
    dt = datetime(2025, 1, 2, 16, 0, tzinfo=KST)
    assert is_krx_trading_day(dt) is True


def test_nyse_holiday_false():
    dt = datetime(2025, 1, 2, 7, 0, tzinfo=KST)
    assert is_nyse_trading_day(dt) is False


def test_nyse_weekday_true():
    dt = datetime(2025, 1, 3, 7, 0, tzinfo=KST)
    assert is_nyse_trading_day(dt) is True


def test_nyse_date_uses_new_york_day():
    dt = datetime(2025, 1, 2, 7, 0, tzinfo=KST)
    # 2025-01-02 07:00 KST == 2025-01-01 in New York (NYSE holiday)
    assert is_nyse_trading_day(dt) is False
