from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

from bot.app.settings import WATCH_ALERT_THRESHOLD_PCT
from bot.common.clock import timestamp_text
from bot.intel.instrument_registry import format_watch_symbol, normalize_canonical_symbol


@dataclass(frozen=True)
class WatchBandEvent:
    direction: str
    band: int
    change_pct: float


BLANK_WATCH_STARTER = "\u200b"


def calculate_change_pct(reference_price: float, current_price: float) -> float:
    if reference_price <= 0:
        return 0.0
    return ((current_price - reference_price) / reference_price) * 100


def direction_band_for_change(change_pct: float) -> tuple[str | None, int]:
    threshold = max(0.1, float(WATCH_ALERT_THRESHOLD_PCT))
    if change_pct >= threshold:
        return "up", int(change_pct // threshold)
    if change_pct <= -threshold:
        return "down", int(abs(change_pct) // threshold)
    return None, 0


def evaluate_band_event(
    *,
    highest_up_band: int,
    highest_down_band: int,
    change_pct: float,
) -> WatchBandEvent | None:
    direction, band = direction_band_for_change(change_pct)
    if direction == "up" and band > highest_up_band:
        return WatchBandEvent(direction="up", band=band, change_pct=change_pct)
    if direction == "down" and band > highest_down_band:
        return WatchBandEvent(direction="down", band=band, change_pct=change_pct)
    return None


def starter_status(*, highest_up_band: int, highest_down_band: int, active: bool) -> str:
    if not active:
        return "inactive"
    if highest_up_band > 0 and highest_down_band > 0:
        return "both-active"
    if highest_up_band > 0:
        return "up-active"
    if highest_down_band > 0:
        return "down-active"
    return "idle"


def render_blank_watch_starter() -> str:
    return BLANK_WATCH_STARTER


def render_watch_placeholder(symbol: str, *, active: bool) -> str:
    lines = [format_watch_symbol(symbol), f"상태: {'실시간 감시중' if active else '감시 중단됨'}"]
    if active:
        lines.append("현재가 조회 전")
    else:
        lines.append("실시간 감시가 중단되었습니다")
    return "\n".join(lines)


def watch_currency_symbol(symbol: str) -> str:
    canonical = normalize_canonical_symbol(symbol) or symbol.strip().upper()
    market = canonical.split(":", 1)[0] if ":" in canonical else ""
    if market == "KRX":
        return "₩"
    if market in {"NAS", "NYS", "AMS"}:
        return "$"
    return ""


def format_watch_price(symbol: str, price: float) -> str:
    currency = watch_currency_symbol(symbol)
    return f"{currency}{price:,.2f}" if currency else f"{price:,.2f}"


def _format_band_threshold_pct(band: int) -> str:
    threshold = max(Decimal("0.1"), Decimal(str(WATCH_ALERT_THRESHOLD_PCT)))
    threshold_pct = threshold * band
    text = format(threshold_pct.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def render_watch_current_comment(
    symbol: str,
    *,
    reference_price: float,
    current_price: float,
    change_pct: float,
    updated_at: datetime,
) -> str:
    return "\n".join(
        [
            format_watch_symbol(symbol),
            "상태: 실시간 감시중",
            f"전일 종가: {format_watch_price(symbol, reference_price)}",
            f"현재가: {format_watch_price(symbol, current_price)}",
            f"변동률: {change_pct:+.2f}%",
            f"마지막 갱신: {timestamp_text(updated_at)}",
        ]
    )


def render_watch_starter(
    symbol: str,
    *,
    reference_price: float,
    current_price: float,
    change_pct: float,
    updated_at: datetime,
) -> str:
    return render_watch_current_comment(
        symbol,
        reference_price=reference_price,
        current_price=current_price,
        change_pct=change_pct,
        updated_at=updated_at,
    )


def render_band_comment(symbol: str, *, direction: str, band: int, change_pct: float, updated_at: datetime) -> str:
    threshold_pct = _format_band_threshold_pct(band)
    band_label = f"+{threshold_pct}%" if direction == "up" else f"-{threshold_pct}%"
    direction_label = "상승" if direction == "up" else "하락"
    return f"{format_watch_symbol(symbol)} {band_label} 이상 {direction_label} : {change_pct:+.2f}% · {timestamp_text(updated_at)}"


def render_close_comment(
    symbol: str,
    *,
    session_date: str,
    reference_price: float,
    close_price: float,
) -> str:
    change_pct = calculate_change_pct(reference_price, close_price)
    return "\n".join(
        [
            f"[watch-close:{symbol}:{session_date}]",
            f"{format_watch_symbol(symbol)} 마감가 알림",
            f"날짜: {session_date}",
            f"전일 종가: {reference_price:,.2f}",
            f"마감가: {close_price:,.2f}",
            f"최종 변동률: {change_pct:+.2f}%",
        ]
    )
