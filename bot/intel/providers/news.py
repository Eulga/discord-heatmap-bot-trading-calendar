from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha1
from typing import Protocol


@dataclass
class NewsItem:
    title: str
    link: str
    source: str
    published_at: datetime
    region: str  # domestic | global

    def dedup_key(self) -> str:
        base = f"{self.region}|{self.source}|{self.title.strip().lower()}|{self.link.strip()}"
        return sha1(base.encode("utf-8")).hexdigest()


class NewsProvider(Protocol):
    async def fetch(self, now: datetime) -> list[NewsItem]: ...


class MockNewsProvider:
    async def fetch(self, now: datetime) -> list[NewsItem]:
        return [
            NewsItem("한국 수출지표 개선 기대", "https://example.com/kr-export", "MockNewsKR", now - timedelta(minutes=32), "domestic"),
            NewsItem("원/달러 환율 장초반 하락", "https://example.com/kr-fx", "MockNewsKR", now - timedelta(minutes=25), "domestic"),
            NewsItem("KOSPI 대형주 중심 반등", "https://example.com/kr-kospi", "MockNewsKR", now - timedelta(minutes=18), "domestic"),
            NewsItem("Fed 위원 발언에 채권금리 혼조", "https://example.com/global-fed", "MockNewsGlobal", now - timedelta(minutes=41), "global"),
            NewsItem("미 기술주 선물 상승", "https://example.com/global-tech", "MockNewsGlobal", now - timedelta(minutes=29), "global"),
            NewsItem("유럽 PMI 발표 앞두고 관망", "https://example.com/global-pmi", "MockNewsGlobal", now - timedelta(minutes=21), "global"),
            # duplicate candidate
            NewsItem("한국 수출지표 개선 기대", "https://example.com/kr-export", "MockNewsKR", now - timedelta(minutes=30), "domestic"),
        ]
