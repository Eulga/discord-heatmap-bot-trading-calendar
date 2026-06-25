from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
NY = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class DashboardMarketSession:
    basis_label: str
    footer_text: str
    icon: str
    market_date: str
    market_label: str
    session_label: str


def _minutes(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _is_kr_market(market: str) -> bool:
    return market.strip().upper() in {"국장", "KR", "KRX", "XKRX"}


def _is_us_market(market: str) -> bool:
    return market.strip().upper() in {"미장", "US", "NAS", "NYS", "AMS", "XNYS"}


def _kr_session(now: datetime) -> tuple[str, str]:
    local_now = now.astimezone(KST)
    minutes = _minutes(local_now)
    is_weekday = local_now.weekday() < 5

    if not is_weekday:
        return "휴장", "최근 종가 기준"
    if 8 * 60 <= minutes < 9 * 60:
        return "장전", "전일종가 대비"
    if 9 * 60 <= minutes < 15 * 60 + 30:
        return "정규장", "전일종가 대비"
    if 15 * 60 + 30 <= minutes < 18 * 60:
        return "시간외", "정규장 종가 대비"
    return "장마감", "최근 종가 기준"


def _us_session(now: datetime) -> tuple[str, str]:
    local_now = now.astimezone(NY)
    minutes = _minutes(local_now)
    is_weekday = local_now.weekday() < 5

    if not is_weekday:
        return "휴장", "최근 종가 기준"
    if 4 * 60 <= minutes < 9 * 60 + 30:
        return "프리마켓", "전일 정규장 종가 대비"
    if 9 * 60 + 30 <= minutes < 16 * 60:
        return "정규장", "전일종가 대비"
    if 16 * 60 <= minutes < 20 * 60:
        return "애프터마켓", "정규장 종가 대비"
    return "장마감", "최근 종가 기준"


def dashboard_market_session(market: str, now: datetime | None = None) -> DashboardMarketSession:
    base_now = now or datetime.now(tz=KST)

    if _is_kr_market(market):
        local_now = base_now.astimezone(KST)
        market_label = "국장"
        session_label, basis_label = _kr_session(base_now)
        icon = "🇰🇷"
    elif _is_us_market(market):
        local_now = base_now.astimezone(NY)
        market_label = "미장"
        session_label, basis_label = _us_session(base_now)
        icon = "🇺🇸"
    else:
        local_now = base_now.astimezone(KST)
        market_label = market.strip() or "시장"
        session_label = "기준 확인"
        basis_label = "최근 데이터 기준"
        icon = "🌐"

    market_date = local_now.date().isoformat()
    return DashboardMarketSession(
        basis_label=basis_label,
        footer_text=f"{icon} {market_label} {session_label} · {market_date} · {basis_label}",
        icon=icon,
        market_date=market_date,
        market_label=market_label,
        session_label=session_label,
    )


def schedule_icon(market: str, event_type: str, title: str = "") -> str:
    normalized_type = event_type.strip().lower()
    text = f"{normalized_type} {title}".lower()

    if normalized_type == "economic" or any(keyword in text for keyword in ("fomc", "cpi", "ppi", "pce", "gdp", "ism", "금리", "물가", "고용")):
        return "🌐"
    if normalized_type == "disclosure":
        return "📄"
    if _is_kr_market(market):
        return "🇰🇷"
    if _is_us_market(market):
        return "🇺🇸"
    return "📅"
