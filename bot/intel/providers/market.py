from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1
from typing import Protocol


@dataclass
class Quote:
    symbol: str
    price: float
    asof: datetime


@dataclass
class EodRow:
    symbol: str
    name: str
    change_pct: float
    turnover_billion_krw: float


@dataclass
class EodSummary:
    date_text: str
    kospi_change_pct: float
    kosdaq_change_pct: float
    top_gainers: list[EodRow]
    top_losers: list[EodRow]
    top_turnover: list[EodRow]


class MarketDataProvider(Protocol):
    async def get_quote(self, symbol: str, now: datetime) -> Quote: ...


class EodSummaryProvider(Protocol):
    async def get_summary(self, now: datetime) -> EodSummary: ...


class MockMarketDataProvider:
    async def get_quote(self, symbol: str, now: datetime) -> Quote:
        token = sha1(f"{symbol}|{now.strftime('%Y%m%d%H%M')}".encode("utf-8")).hexdigest()
        seed = int(token[:8], 16)
        base = 10000 + (seed % 90000)
        noise = ((seed >> 8) % 500) / 100
        return Quote(symbol=symbol.upper(), price=base + noise, asof=now)


class MockEodSummaryProvider:
    async def get_summary(self, now: datetime) -> EodSummary:
        gainers = [
            EodRow("005930", "삼성전자", 4.2, 1300.5),
            EodRow("000660", "SK하이닉스", 3.9, 980.4),
            EodRow("035420", "NAVER", 3.1, 410.2),
            EodRow("051910", "LG화학", 2.8, 350.1),
            EodRow("005380", "현대차", 2.4, 290.7),
        ]
        losers = [
            EodRow("068270", "셀트리온", -2.9, 250.1),
            EodRow("207940", "삼성바이오로직스", -2.4, 210.2),
            EodRow("017670", "SK텔레콤", -2.1, 130.7),
            EodRow("105560", "KB금융", -1.9, 180.6),
            EodRow("055550", "신한지주", -1.6, 170.2),
        ]
        turnover = [
            EodRow("005930", "삼성전자", 4.2, 1300.5),
            EodRow("000660", "SK하이닉스", 3.9, 980.4),
            EodRow("035720", "카카오", 1.1, 620.0),
            EodRow("373220", "LG에너지솔루션", 0.4, 580.2),
            EodRow("035420", "NAVER", 3.1, 410.2),
        ]
        return EodSummary(
            date_text=now.strftime("%Y-%m-%d"),
            kospi_change_pct=0.82,
            kosdaq_change_pct=-0.27,
            top_gainers=gainers,
            top_losers=losers,
            top_turnover=turnover,
        )
