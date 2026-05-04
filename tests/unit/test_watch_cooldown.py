from datetime import datetime
from zoneinfo import ZoneInfo

from bot.features import intel_scheduler
from bot.features.watch import service
from bot.features.watch.session import get_watch_market_session, is_adjacent_watch_session_date


KST = ZoneInfo("Asia/Seoul")


def test_watch_band_ladder_only_advances_to_new_highest_band():
    first = service.evaluate_band_event(highest_up_band=0, highest_down_band=0, change_pct=-4.1)
    repeat = service.evaluate_band_event(highest_up_band=0, highest_down_band=1, change_pct=-4.8)
    expanded = service.evaluate_band_event(highest_up_band=0, highest_down_band=1, change_pct=-7.4)

    assert first == service.WatchBandEvent(direction="down", band=1, change_pct=-4.1)
    assert repeat is None
    assert expanded == service.WatchBandEvent(direction="down", band=2, change_pct=-7.4)


def test_watch_starter_status_supports_both_active_and_inactive():
    assert service.starter_status(highest_up_band=0, highest_down_band=0, active=True) == "idle"
    assert service.starter_status(highest_up_band=2, highest_down_band=0, active=True) == "up-active"
    assert service.starter_status(highest_up_band=0, highest_down_band=1, active=True) == "down-active"
    assert service.starter_status(highest_up_band=2, highest_down_band=1, active=True) == "both-active"
    assert service.starter_status(highest_up_band=2, highest_down_band=1, active=False) == "inactive"


def test_watch_rendering_uses_user_facing_copy():
    updated_at = datetime(2026, 3, 26, 10, 0, tzinfo=KST)

    current_comment = service.render_watch_current_comment(
        "KRX:005930",
        reference_price=100.0,
        current_price=107.1,
        change_pct=7.1,
        updated_at=updated_at,
    )
    comment = service.render_band_comment(
        "KRX:005930",
        direction="up",
        band=2,
        change_pct=7.1,
        updated_at=updated_at,
    )
    inactive_placeholder = service.render_watch_placeholder("KRX:005930", active=False)

    assert "상태: 실시간 감시중" in current_comment
    assert "전일 종가: ₩100.00" in current_comment
    assert "현재가: ₩107.10" in current_comment
    assert "기준 세션" not in current_comment
    assert "당일 alert status" not in current_comment
    assert "당일 최고 상승 band" not in current_comment
    assert comment == "삼성전자 (KRX:005930) +6% 이상 상승 : +7.10% · 2026-03-26 10:00:00"
    assert "상태: 감시 중단됨" in inactive_placeholder
    assert inactive_placeholder.endswith("실시간 감시가 중단되었습니다")


def test_watch_blank_starter_has_no_visible_text():
    assert service.render_blank_watch_starter() == service.BLANK_WATCH_STARTER


def test_watch_rendering_preserves_fractional_band_threshold_text(monkeypatch):
    updated_at = datetime(2026, 3, 26, 10, 0, tzinfo=KST)

    monkeypatch.setattr(service, "WATCH_ALERT_THRESHOLD_PCT", 2.5)
    up_comment = service.render_band_comment(
        "KRX:005930",
        direction="up",
        band=2,
        change_pct=5.1,
        updated_at=updated_at,
    )
    assert up_comment == "삼성전자 (KRX:005930) +5% 이상 상승 : +5.10% · 2026-03-26 10:00:00"

    monkeypatch.setattr(service, "WATCH_ALERT_THRESHOLD_PCT", 0.5)
    down_comment = service.render_band_comment(
        "KRX:005930",
        direction="down",
        band=1,
        change_pct=-0.7,
        updated_at=updated_at,
    )
    assert down_comment == "삼성전자 (KRX:005930) -0.5% 이상 하락 : -0.70% · 2026-03-26 10:00:00"


def test_watch_rendering_uses_dollar_symbol_for_us_products():
    current_comment = service.render_watch_current_comment(
        "NAS:AAPL",
        reference_price=100.0,
        current_price=107.1,
        change_pct=7.1,
        updated_at=datetime(2026, 3, 27, 0, 0, tzinfo=KST),
    )

    assert "전일 종가: $100.00" in current_comment
    assert "현재가: $107.10" in current_comment


def test_watch_market_session_identifies_krx_open_and_preopen_session_dates():
    open_now = datetime(2026, 3, 26, 10, 0, tzinfo=KST)
    preopen_now = datetime(2026, 3, 26, 8, 30, tzinfo=KST)

    open_session = get_watch_market_session("KRX:005930", open_now)
    preopen_session = get_watch_market_session("KRX:005930", preopen_now)

    assert open_session.market_mic == "XKRX"
    assert open_session.is_regular_session_open is True
    assert open_session.session_date == "2026-03-26"
    assert preopen_session.is_regular_session_open is False
    assert preopen_session.session_date == "2026-03-25"


def test_watch_market_session_identifies_us_regular_session_and_after_close():
    open_now = datetime(2026, 3, 27, 0, 0, tzinfo=KST)
    closed_now = datetime(2026, 3, 27, 6, 30, tzinfo=KST)

    open_session = get_watch_market_session("NAS:AAPL", open_now)
    closed_session = get_watch_market_session("NAS:AAPL", closed_now)

    assert open_session.market_mic == "XNYS"
    assert open_session.is_regular_session_open is True
    assert open_session.session_date == "2026-03-26"
    assert closed_session.is_regular_session_open is False
    assert closed_session.is_after_regular_close is True
    assert closed_session.session_date == "2026-03-26"


def test_watch_session_adjacency_uses_trading_calendar():
    assert is_adjacent_watch_session_date(
        "KRX:005930",
        previous_session_date="2026-03-26",
        next_session_date="2026-03-27",
    ) is True
    assert is_adjacent_watch_session_date(
        "KRX:005930",
        previous_session_date="2026-03-24",
        next_session_date="2026-03-27",
    ) is False


def test_watch_close_finalization_due_time_is_exact_kst_minute_for_krx():
    assert intel_scheduler._is_watch_close_finalization_due(
        "KRX:005930",
        datetime(2026, 3, 26, 15, 59, tzinfo=KST),
    ) is False
    assert intel_scheduler._is_watch_close_finalization_due(
        "KRX:005930",
        datetime(2026, 3, 26, 16, 0, tzinfo=KST),
    ) is True
    assert intel_scheduler._is_watch_close_finalization_due(
        "KRX:005930",
        datetime(2026, 3, 26, 16, 1, tzinfo=KST),
    ) is False


def test_watch_close_finalization_due_time_is_exact_kst_minute_for_us_markets():
    for symbol in ("NAS:AAPL", "NYS:IBM", "AMS:SPY"):
        assert intel_scheduler._is_watch_close_finalization_due(
            symbol,
            datetime(2026, 3, 27, 6, 59, tzinfo=KST),
        ) is False
        assert intel_scheduler._is_watch_close_finalization_due(
            symbol,
            datetime(2026, 3, 27, 7, 0, tzinfo=KST),
        ) is True
        assert intel_scheduler._is_watch_close_finalization_due(
            symbol,
            datetime(2026, 3, 27, 7, 1, tzinfo=KST),
        ) is False
