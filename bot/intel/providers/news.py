from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha1
from html import unescape
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

_TAG_RE = re.compile(r"<[^>]+>")
_BREAKING_KEYWORDS = (
    "속보",
    "긴급",
    "급락",
    "급등",
    "쇼크",
    "충격",
    "서프라이즈",
    "깜짝",
    "불확실성",
)
_BLOCKLIST_KEYWORDS = (
    "ai의 종목 이야기",
    "종목 이야기",
    "종목 pick",
    "종목pick",
    "마켓pro",
    "market pro",
    "기자수첩",
    "사설",
    "칼럼",
    "오피니언",
    "특징주",
    "티타임",
    "이시각헤드라인",
    "시장 따라잡기",
)
_LOW_SIGNAL_KEYWORDS = (
    "표창",
    "공로",
    "수상",
    "협약",
    "행사",
    "개최",
    "캠페인",
    "기부",
    "봉사",
    "준공",
    "개관",
    "게임주",
    "제약",
    "바이오",
    "섹터",
    "테마",
    "액티브 etf",
    "etf 경쟁",
    "무료 제공",
    "무료화",
    "전 회원",
    "실시간 시세",
    "계좌 인증",
    "평생 공짜",
    "혜택",
    "정조준",
    "개장시황",
    "사도 되나",
    "왜?",
    "헤지펀드",
    "인사이드 헤지펀드",
)
_QUERY_STOPWORDS = {"증시", "시장", "국내", "해외", "매매"}
_TITLE_SIMILARITY_STOPWORDS = {
    "미국",
    "국내",
    "증시",
    "시장",
    "주식",
    "지수",
    "뉴스",
    "경제",
    "브리핑",
    "속보",
    "개장",
    "마감",
}
_REGION_GATE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "domestic": (
        "코스피",
        "코스닥",
        "krx",
        "환율",
        "원/달러",
        "외국인",
        "기관",
        "수출",
        "한국은행",
    ),
    "global": (
        "미국",
        "미 증시",
        "뉴욕",
        "나스닥",
        "s&p",
        "s&p 500",
        "다우",
        "연준",
        "파월",
        "fed",
        "fomc",
        "cpi",
        "pce",
        "월가",
    ),
}
_PRIORITY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "domestic": (
        "코스피",
        "코스닥",
        "krx",
        "원/달러",
        "환율",
        "한국은행",
        "금리",
        "수출",
        "외국인",
        "기관",
        "공매도",
        "실적",
        "가이던스",
    ),
    "global": (
        "미국",
        "미 증시",
        "뉴욕",
        "나스닥",
        "s&p",
        "s&p 500",
        "다우",
        "연준",
        "파월",
        "fed",
        "fomc",
        "cpi",
        "pce",
        "고용",
        "국채",
        "월가",
        "엔비디아",
        "테슬라",
        "애플",
        "관세",
        "중동",
        "원유",
    ),
}
_CROSS_REGION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "domestic": (
        "나스닥",
        "s&p",
        "다우",
        "연준",
        "fed",
        "fomc",
        "뉴욕",
        "월가",
        "미국",
        "파월",
    ),
    "global": (
        "코스피",
        "코스닥",
        "국내",
        "krx",
        "원/달러",
        "환율",
        "한국은행",
        "한은",
        "외국인",
        "기관",
        "삼성전자",
        "sk하이닉스",
    ),
}
_STOCK_EVENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "domestic": (
        "실적",
        "영업익",
        "가이던스",
        "수주",
        "계약",
        "인수",
        "합병",
        "규제",
        "소송",
        "승인",
        "투자",
        "증설",
        "감산",
        "증산",
        "수출",
        "관세",
        "리콜",
        "배당",
        "자사주",
        "유상증자",
        "무상증자",
        "상장폐지",
        "매출",
        "시총",
    ),
    "global": (
        "earnings",
        "guidance",
        "실적",
        "매출",
        "영업익",
        "가이던스",
        "수주",
        "계약",
        "인수",
        "합병",
        "규제",
        "소송",
        "승인",
        "투자",
        "증설",
        "감산",
        "증산",
        "관세",
        "리콜",
        "시총",
        "supply",
        "demand",
    ),
}
_STOCK_LOW_SIGNAL_KEYWORDS = (
    "목표가",
    "리포트",
    "추천",
    "종목",
    "무료 제공",
    "무료화",
    "전 회원",
    "실시간 시세",
    "계좌 인증",
    "혜택",
    "서비스",
    "앱",
    "플랫폼",
    "출시",
    "론칭",
    "오픈",
)
_STOCK_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    "삼성전자": ("삼성전자", "삼전"),
    "sk하이닉스": ("sk하이닉스", "하이닉스", "sk하닉"),
    "현대차": ("현대차", "정의선"),
    "한화에어로스페이스": ("한화에어로스페이스", "한화에어로"),
    "셀트리온": ("셀트리온",),
    "엔비디아": ("엔비디아", "nvidia"),
    "애플": ("애플", "apple"),
    "마이크로소프트": ("마이크로소프트", "ms"),
    "테슬라": ("테슬라", "tesla"),
    "마이크론": ("마이크론", "micron"),
}
_SOURCE_WEIGHTS = {
    "reuters.com": 6,
    "bloomberg.com": 6,
    "wsj.com": 5,
    "cnbc.com": 4,
    "biz.chosun.com": 4,
    "yna.co.kr": 4,
    "yonhapnewstv.co.kr": 4,
    "news1.kr": 4,
    "newsis.com": 3,
    "hankyung.com": 3,
    "mk.co.kr": 3,
    "edaily.co.kr": 3,
    "sedaily.com": 3,
    "fnnews.com": 3,
    "economist.co.kr": 2,
    "econovill.com": 2,
    "etoday.co.kr": 2,
    "biz.sbs.co.kr": 2,
    "news.einfomax.co.kr": 4,
    "daily.hankooki.com": -2,
    "naeil.com": -1,
    "mstoday.co.kr": -1,
    "newsroad.co.kr": -1,
    "tokenpost.kr": -4,
    "press9.kr": -4,
    "science.ytn.co.kr": -2,
    "polinews.co.kr": -2,
    "glocale.co.kr": -2,
    "startuptoday.co.kr": -2,
    "sidae.com": -2,
    "choicenews.co.kr": -3,
}
_MAX_ITEMS_PER_SOURCE = 2
_TREND_TARGET_THEMES = 3
_TREND_MAX_THEMES = 5
_TREND_EXPANSION_RATIO = 0.72
_TREND_SCORE_FLOOR = 24
_TREND_HARD_BLOCKLIST_KEYWORDS = _BLOCKLIST_KEYWORDS + (
    "특징주",
    "테마주",
    "관련주",
    "수혜주",
    "목표가",
    "리포트",
    "추천",
    "무료",
    "혜택",
)


@dataclass(frozen=True)
class _ScoredNewsItem:
    item: NewsItem
    score: int
    bucket: str
    description: str


@dataclass(frozen=True)
class _QuerySpec:
    text: str
    kind: str


@dataclass(frozen=True)
class ThemeDefinition:
    name: str
    region: str
    probe_query: str
    keywords: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    representative_symbols: tuple[str, ...] = ()
    exclude_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class ThemeHit:
    definition: ThemeDefinition
    item: NewsItem
    score: int
    bucket: str
    reason_tags: tuple[str, ...]
    matched_symbols: tuple[str, ...]


@dataclass(frozen=True)
class ThemeBrief:
    theme_name: str
    region: str
    score: int
    reason_tags: tuple[str, ...]
    representative_items: tuple[NewsItem, ...]
    article_count: int
    source_count: int


@dataclass(frozen=True)
class TrendThemeReport:
    generated_at: datetime
    themes_by_region: dict[str, tuple[ThemeBrief, ...]]

    def for_region(self, region: str) -> tuple[ThemeBrief, ...]:
        return self.themes_by_region.get(region, ())


@dataclass(frozen=True)
class NewsAnalysis:
    briefing_items: tuple[NewsItem, ...]
    trend_report: TrendThemeReport


@dataclass(frozen=True)
class _RegionNewsAnalysis:
    selected_items: tuple[NewsItem, ...]
    trend_candidates: tuple[_ScoredNewsItem, ...]


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

    def story_key(self) -> str:
        base = f"{self.source}|{self.title.strip().lower()}|{self.link.strip()}"
        return sha1(base.encode("utf-8")).hexdigest()


class NewsProvider(Protocol):
    async def fetch(self, now: datetime) -> list[NewsItem]: ...

    async def analyze(self, now: datetime) -> NewsAnalysis: ...


class ErrorNewsProvider:
    def __init__(self, message: str) -> None:
        self._message = message

    async def fetch(self, now: datetime) -> list[NewsItem]:
        raise RuntimeError(self._message)

    async def analyze(self, now: datetime) -> NewsAnalysis:
        raise RuntimeError(self._message)


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

    async def analyze(self, now: datetime) -> NewsAnalysis:
        items = await self.fetch(now)
        return _build_news_analysis(
            items=items,
            candidates_by_region=_fallback_candidates_by_region(items, now),
            generated_at=now,
        )


async def _coerce_news_analysis(provider: NewsProvider, now: datetime) -> NewsAnalysis:
    analyze = getattr(provider, "analyze", None)
    if callable(analyze):
        return await analyze(now)
    items = await provider.fetch(now)
    return _build_news_analysis(
        items=items,
        candidates_by_region=_fallback_candidates_by_region(items, now),
        generated_at=now,
    )


class HybridNewsProvider:
    def __init__(self, domestic_provider: NewsProvider, global_provider: NewsProvider) -> None:
        self.domestic_provider = domestic_provider
        self.global_provider = global_provider

    async def fetch(self, now: datetime) -> list[NewsItem]:
        analysis = await self.analyze(now)
        return list(analysis.briefing_items)

    async def analyze(self, now: datetime) -> NewsAnalysis:
        domestic_analysis, global_analysis = await asyncio.gather(
            _coerce_news_analysis(self.domestic_provider, now),
            _coerce_news_analysis(self.global_provider, now),
        )
        best_by_key: dict[str, NewsItem] = {}
        for item in (*domestic_analysis.briefing_items, *global_analysis.briefing_items):
            current = best_by_key.get(item.dedup_key())
            if current is None or current.published_at < item.published_at:
                best_by_key[item.dedup_key()] = item
        merged_items = tuple(
            sorted(best_by_key.values(), key=lambda item: (item.region, item.published_at), reverse=True)
        )
        return NewsAnalysis(
            briefing_items=merged_items,
            trend_report=TrendThemeReport(
                generated_at=now,
                themes_by_region={
                    "domestic": domestic_analysis.trend_report.for_region("domestic"),
                    "global": global_analysis.trend_report.for_region("global"),
                },
            ),
        )


class MarketauxNewsProvider:
    def __init__(
        self,
        api_token: str,
        global_query: str | Sequence[str],
        *,
        countries: str | Sequence[str] = ("us",),
        language: str | Sequence[str] = ("en",),
        limit_per_region: int = 20,
        max_age_hours: int = 24,
        timeout_seconds: int = 5,
        retry_count: int = 1,
    ) -> None:
        self.api_token = api_token.strip()
        self.global_queries = _normalize_queries(global_query)
        self.countries = _normalize_queries(countries)
        self.language = _normalize_queries(language)
        self.limit_per_region = max(1, min(limit_per_region, 20))
        self.max_age_hours = max(1, max_age_hours)
        self.timeout_seconds = max(1, min(timeout_seconds, 10))
        self.retry_count = max(0, min(retry_count, 1))

    async def fetch(self, now: datetime) -> list[NewsItem]:
        analysis = await self.analyze(now)
        return list(analysis.briefing_items)

    async def analyze(self, now: datetime) -> NewsAnalysis:
        cutoff = now - timedelta(hours=self.max_age_hours)
        latest_allowed = now + timedelta(minutes=5)
        queries = self.global_queries or [""]
        best_by_key: dict[str, NewsItem] = {}

        for query in queries:
            payload = await asyncio.to_thread(self._request_json, query)
            raw_items = payload.get("data")
            if not isinstance(raw_items, list):
                raise RuntimeError("marketaux-invalid-response")
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    continue
                item = self._normalize_item(raw_item, cutoff, latest_allowed)
                if item is None:
                    continue
                current = best_by_key.get(item.dedup_key())
                if current is None or current.published_at < item.published_at:
                    best_by_key[item.dedup_key()] = item

        items = sorted(best_by_key.values(), key=lambda item: item.published_at, reverse=True)[: self.limit_per_region]
        return _build_news_analysis(
            items=items,
            candidates_by_region=_fallback_candidates_by_region(items, now),
            generated_at=now,
        )

    def _request_json(self, query: str) -> dict[str, Any]:
        params = {
            "api_token": self.api_token,
            "countries": ",".join(self.countries) if self.countries else "",
            "language": ",".join(self.language) if self.language else "",
            "filter_entities": "true",
            "must_have_entities": "true",
            "group_similar": "true",
            "sort": "published_at",
            "sort_order": "desc",
            "limit": str(self.limit_per_region),
        }
        if query:
            params["search"] = query
        request = Request(
            f"https://api.marketaux.com/v1/news/all?{urlencode(params)}",
            headers={
                "Accept": "application/json",
                "User-Agent": "discord-heatmap-bot/1.0",
            },
        )
        for attempt in range(self.retry_count + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise RuntimeError("marketaux-invalid-response")
                return payload
            except HTTPError as exc:
                if exc.code in {401, 403}:
                    raise RuntimeError(f"marketaux-auth-failed:{exc.code}") from exc
                if exc.code == 429:
                    raise RuntimeError("marketaux-rate-limited") from exc
                if exc.code in {400, 404}:
                    raise RuntimeError(f"marketaux-request-invalid:{exc.code}") from exc
                if attempt >= self.retry_count:
                    raise RuntimeError(f"marketaux-upstream-error:{exc.code}") from exc
            except json.JSONDecodeError as exc:
                raise RuntimeError("marketaux-invalid-response") from exc
            except URLError as exc:
                if attempt >= self.retry_count:
                    raise RuntimeError("marketaux-unreachable") from exc
        raise RuntimeError("marketaux-unreachable")

    def _normalize_item(
        self,
        raw_item: dict[str, Any],
        cutoff: datetime,
        latest_allowed: datetime,
    ) -> NewsItem | None:
        title = str(raw_item.get("title") or "").strip()
        link = str(raw_item.get("url") or "").strip()
        source = str(raw_item.get("source") or "").strip()
        published_at_text = str(raw_item.get("published_at") or "").strip()
        if not title or not link or not published_at_text:
            return None
        parsed_link = urlparse(link)
        if parsed_link.scheme not in {"http", "https"} or not parsed_link.netloc:
            return None
        try:
            published_at = datetime.fromisoformat(published_at_text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if published_at.tzinfo is None or published_at < cutoff or published_at > latest_allowed:
            return None
        return NewsItem(
            title=title,
            link=link,
            source=source or _source_from_link(link),
            published_at=published_at,
            region="global",
        )


class NaverNewsProvider:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        domestic_query: str | Sequence[str],
        global_query: str | Sequence[str],
        *,
        domestic_stock_query: str | Sequence[str] = (),
        global_stock_query: str | Sequence[str] = (),
        limit_per_region: int = 20,
        max_age_hours: int = 24,
        timeout_seconds: int = 5,
        retry_count: int = 1,
    ) -> None:
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.domestic_queries = _normalize_queries(domestic_query)
        self.global_queries = _normalize_queries(global_query)
        self.domestic_stock_queries = _normalize_queries(domestic_stock_query)
        self.global_stock_queries = _normalize_queries(global_stock_query)
        self.limit_per_region = max(1, min(limit_per_region, 20))
        self.display = min(max(self.limit_per_region * 4, 15), 100)
        self.max_age_hours = max(1, max_age_hours)
        self.timeout_seconds = max(1, min(timeout_seconds, 10))
        self.retry_count = max(0, min(retry_count, 1))

    async def fetch(self, now: datetime) -> list[NewsItem]:
        analysis = await self.analyze(now)
        return list(analysis.briefing_items)

    async def analyze(self, now: datetime) -> NewsAnalysis:
        tasks = [
            asyncio.to_thread(
                self._fetch_region_analysis,
                _build_query_specs(self.domestic_queries, self.domestic_stock_queries),
                _build_theme_probe_query_specs("domestic"),
                "domestic",
                now,
            ),
            asyncio.to_thread(
                self._fetch_region_analysis,
                _build_query_specs(self.global_queries, self.global_stock_queries),
                _build_theme_probe_query_specs("global"),
                "global",
                now,
            ),
        ]
        results = await asyncio.gather(*tasks)
        items = [item for result in results for item in result.selected_items]
        candidates_by_region = {
            region: result.trend_candidates for region, result in zip(("domestic", "global"), results, strict=False)
        }
        return _build_news_analysis(items=items, candidates_by_region=candidates_by_region, generated_at=now)

    def _fetch_region_analysis(
        self,
        query_specs: Sequence[_QuerySpec],
        trend_query_specs: Sequence[_QuerySpec],
        region: str,
        now: datetime,
    ) -> _RegionNewsAnalysis:
        if not query_specs:
            return _RegionNewsAnalysis(selected_items=(), trend_candidates=())

        cutoff = now - timedelta(hours=self.max_age_hours)
        latest_allowed = now + timedelta(minutes=5)
        best_by_key: dict[str, _ScoredNewsItem] = {}
        trend_best_by_key: dict[str, _ScoredNewsItem] = {}

        all_query_specs = [*query_specs, *trend_query_specs]
        for query_spec in all_query_specs:
            try:
                payload = self._request_json(query_spec.text)
            except RuntimeError as exc:
                if str(exc) == "naver-news-rate-limited" and (best_by_key or trend_best_by_key):
                    break
                raise
            raw_items = payload.get("items")
            if not isinstance(raw_items, list):
                raise RuntimeError("naver-news-invalid-response")

            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    continue
                candidate = self._normalize_item(raw_item, region, query_spec, now, cutoff, latest_allowed)
                if candidate is None:
                    continue
                _merge_scored_candidate(trend_best_by_key, candidate)
                if query_spec.kind != "theme":
                    _merge_scored_candidate(best_by_key, candidate)

        ranked = sorted(
            best_by_key.values(),
            key=lambda candidate: (candidate.score, candidate.item.published_at),
            reverse=True,
        )

        selected: list[NewsItem] = []
        per_source: dict[str, int] = {}
        seen_topics: set[str] = set()
        seen_title_tokens: list[set[str]] = []
        stock_soft_cap = max(2, self.limit_per_region // 4)
        selected_stock = 0
        deferred_stock: list[_ScoredNewsItem] = []
        has_ranked_stock = any(candidate.bucket == "stock" for candidate in ranked)
        for index, candidate in enumerate(ranked):
            remaining_slots = self.limit_per_region - len(selected)
            stock_available_later = has_ranked_stock and any(
                future.bucket == "stock" for future in ranked[index + 1 :]
            )
            if (
                remaining_slots == 1
                and selected_stock == 0
                and candidate.bucket != "stock"
                and stock_available_later
            ):
                continue

            if candidate.bucket == "stock" and selected_stock >= stock_soft_cap:
                deferred_stock.append(candidate)
                continue

            if _should_skip_candidate(
                candidate,
                per_source=per_source,
                seen_topics=seen_topics,
                seen_title_tokens=seen_title_tokens,
            ):
                continue

            selected.append(candidate.item)
            per_source[candidate.item.source] = per_source.get(candidate.item.source, 0) + 1
            topic = _topic_key(candidate.item.title, candidate.item.region)
            if topic:
                seen_topics.add(topic)
            seen_title_tokens.append(_headline_similarity_tokens(candidate.item.title))
            if candidate.bucket == "stock":
                selected_stock += 1
            if len(selected) >= self.limit_per_region:
                break

        if len(selected) < self.limit_per_region:
            for candidate in deferred_stock:
                if _should_skip_candidate(
                    candidate,
                    per_source=per_source,
                    seen_topics=seen_topics,
                    seen_title_tokens=seen_title_tokens,
                ):
                    continue

                selected.append(candidate.item)
                per_source[candidate.item.source] = per_source.get(candidate.item.source, 0) + 1
                topic = _topic_key(candidate.item.title, candidate.item.region)
                if topic:
                    seen_topics.add(topic)
                seen_title_tokens.append(_headline_similarity_tokens(candidate.item.title))
                if len(selected) >= self.limit_per_region:
                    break

        trend_ranked = tuple(
            sorted(
                trend_best_by_key.values(),
                key=lambda candidate: (candidate.score, candidate.item.published_at),
                reverse=True,
            )
        )
        return _RegionNewsAnalysis(selected_items=tuple(selected), trend_candidates=trend_ranked)

    def _request_json(self, query: str) -> dict[str, Any]:
        params = urlencode(
            {
                "query": query,
                "display": self.display,
                "start": 1,
                "sort": "date",
            }
        )
        request = Request(
            f"https://openapi.naver.com/v1/search/news.json?{params}",
            headers={
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
                "Accept": "application/json",
                "User-Agent": "discord-heatmap-bot/1.0",
            },
        )

        for attempt in range(self.retry_count + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise RuntimeError("naver-news-invalid-response")
                return payload
            except HTTPError as exc:
                if exc.code in {401, 403}:
                    raise RuntimeError(f"naver-news-auth-failed:{exc.code}") from exc
                if exc.code == 429:
                    raise RuntimeError("naver-news-rate-limited") from exc
                if exc.code in {400, 404}:
                    raise RuntimeError(f"naver-news-request-invalid:{exc.code}") from exc
                if attempt >= self.retry_count:
                    raise RuntimeError(f"naver-news-upstream-error:{exc.code}") from exc
            except json.JSONDecodeError as exc:
                raise RuntimeError("naver-news-invalid-response") from exc
            except URLError as exc:
                if attempt >= self.retry_count:
                    raise RuntimeError("naver-news-unreachable") from exc

        raise RuntimeError("naver-news-unreachable")

    def _normalize_item(
        self,
        raw_item: dict[str, Any],
        region: str,
        query_spec: _QuerySpec,
        now: datetime,
        cutoff: datetime,
        latest_allowed: datetime,
    ) -> _ScoredNewsItem | None:
        title = _clean_html_text(str(raw_item.get("title") or ""))
        description = _clean_html_text(str(raw_item.get("description") or ""))
        link = str(raw_item.get("originallink") or raw_item.get("link") or "").strip()
        published_at_text = str(raw_item.get("pubDate") or "").strip()
        if not title or not link or not published_at_text:
            return None

        parsed_link = urlparse(link)
        if parsed_link.scheme not in {"http", "https"} or not parsed_link.netloc:
            return None

        try:
            published_at = parsedate_to_datetime(published_at_text)
        except (TypeError, ValueError, IndexError):
            return None
        if published_at.tzinfo is None:
            return None
        if published_at < cutoff or published_at > latest_allowed:
            return None

        scored = _score_news_item(
            title=title,
            description=description,
            link=link,
            region=region,
            query=query_spec.text,
            query_kind=query_spec.kind,
            now=now,
            published_at=published_at,
        )
        if scored is None:
            return None

        score, bucket = scored

        return _ScoredNewsItem(
            item=NewsItem(
                title=title,
                link=link,
                source=_source_from_link(link),
                published_at=published_at,
                region=region,
            ),
            score=score,
            bucket=bucket,
            description=description,
        )


def _clean_html_text(text: str) -> str:
    return " ".join(unescape(_TAG_RE.sub("", text)).split())


def _source_from_link(link: str) -> str:
    hostname = urlparse(link).netloc.strip().lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname or "naver-news"


def _normalize_queries(value: str | Sequence[str]) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    queries: list[str] = []
    seen: set[str] = set()
    for raw in value:
        query = str(raw).strip()
        if not query or query in seen:
            continue
        seen.add(query)
        queries.append(query)
    return queries


def _build_query_specs(macro_queries: Sequence[str], stock_queries: Sequence[str]) -> list[_QuerySpec]:
    specs: list[_QuerySpec] = []
    seen: set[str] = set()
    for query in macro_queries:
        if query in seen:
            continue
        seen.add(query)
        specs.append(_QuerySpec(text=query, kind="macro"))
    for query in stock_queries:
        if query in seen:
            continue
        seen.add(query)
        specs.append(_QuerySpec(text=query, kind="stock"))
    return specs


_THEME_DEFINITIONS: tuple[ThemeDefinition, ...] = (
    ThemeDefinition(
        name="반도체",
        region="domestic",
        probe_query="반도체 수주",
        keywords=("반도체", "hbm", "메모리", "파운드리", "ai 칩", "chip"),
        aliases=("반도체주", "hbm", "메모리"),
        representative_symbols=("삼성전자", "sk하이닉스", "한미반도체", "리노공업"),
    ),
    ThemeDefinition(
        name="건설/원전",
        region="domestic",
        probe_query="원전 건설 수주",
        keywords=("원전", "smr", "원자로", "플랜트", "건설", "해외 수주"),
        aliases=("원자력", "건설주"),
        representative_symbols=("두산에너빌리티", "현대건설", "한전기술", "대우건설"),
    ),
    ThemeDefinition(
        name="전력설비",
        region="domestic",
        probe_query="전력설비 전력망",
        keywords=("전력설비", "전력망", "송전", "변압기", "배전", "전선", "데이터센터 전력"),
        aliases=("전력기기",),
        representative_symbols=("효성중공업", "ls electric", "hd현대일렉트릭", "일진전기"),
    ),
    ThemeDefinition(
        name="방산",
        region="domestic",
        probe_query="방산 수주",
        keywords=("방산", "국방", "무기", "미사일", "전투기", "장갑차"),
        aliases=("방산주",),
        representative_symbols=("한화에어로스페이스", "lig넥스원", "현대로템", "한국항공우주"),
    ),
    ThemeDefinition(
        name="조선",
        region="domestic",
        probe_query="조선 수주",
        keywords=("조선", "선박", "lng선", "조선업", "선가"),
        aliases=("조선주",),
        representative_symbols=("hd한국조선해양", "삼성중공업", "한화오션", "hd현대미포"),
    ),
    ThemeDefinition(
        name="2차전지",
        region="domestic",
        probe_query="2차전지 배터리",
        keywords=("2차전지", "배터리", "양극재", "음극재", "전해질"),
        aliases=("이차전지",),
        representative_symbols=("lg에너지솔루션", "에코프로", "포스코퓨처엠", "삼성sdi"),
    ),
    ThemeDefinition(
        name="바이오",
        region="domestic",
        probe_query="바이오 임상",
        keywords=("바이오", "신약", "임상", "의약품", "제약"),
        aliases=("바이오주",),
        representative_symbols=("셀트리온", "삼성바이오로직스", "유한양행", "sk바이오팜"),
        exclude_keywords=("화장품",),
    ),
    ThemeDefinition(
        name="자동차",
        region="domestic",
        probe_query="자동차 전기차",
        keywords=("자동차", "전기차", "완성차", "자율주행", "ev"),
        aliases=("자동차주",),
        representative_symbols=("현대차", "기아", "현대모비스"),
    ),
    ThemeDefinition(
        name="AI/반도체",
        region="global",
        probe_query="AI semiconductor",
        keywords=("ai", "반도체", "gpu", "chip", "semiconductor", "hbm"),
        aliases=("ai 반도체",),
        representative_symbols=("엔비디아", "amd", "tsmc", "브로드컴", "마이크론"),
    ),
    ThemeDefinition(
        name="메가캡 기술주",
        region="global",
        probe_query="미국 빅테크",
        keywords=("빅테크", "메가캡", "기술주", "tech", "mag7"),
        aliases=("미국 기술주",),
        representative_symbols=("애플", "마이크로소프트", "알파벳", "아마존", "메타"),
    ),
    ThemeDefinition(
        name="에너지/원유",
        region="global",
        probe_query="원유 에너지",
        keywords=("원유", "oil", "에너지", "유가", "천연가스", "opec"),
        aliases=("에너지주",),
        representative_symbols=("엑슨모빌", "셰브론", "exxon", "chevron"),
    ),
    ThemeDefinition(
        name="금리/Fed",
        region="global",
        probe_query="연준 금리",
        keywords=("연준", "fed", "fomc", "금리", "국채", "파월"),
        aliases=("연준", "미국 금리"),
        representative_symbols=("파월",),
    ),
    ThemeDefinition(
        name="EV",
        region="global",
        probe_query="미국 전기차",
        keywords=("전기차", "ev", "자율주행", "배터리"),
        aliases=("ev",),
        representative_symbols=("테슬라", "rivian", "lucid", "byd"),
    ),
    ThemeDefinition(
        name="방산",
        region="global",
        probe_query="미국 방산",
        keywords=("방산", "국방", "defense", "missile", "군사"),
        aliases=("defense",),
        representative_symbols=("록히드마틴", "rtx", "northrop", "lockheed"),
    ),
    ThemeDefinition(
        name="중국/관세",
        region="global",
        probe_query="중국 관세",
        keywords=("중국", "관세", "tariff", "무역전쟁", "수출 규제"),
        aliases=("대중국",),
        representative_symbols=("알리바바", "byd", "텐센트"),
    ),
    ThemeDefinition(
        name="클라우드/데이터센터",
        region="global",
        probe_query="데이터센터 클라우드",
        keywords=("클라우드", "데이터센터", "서버", "server", "hyperscale"),
        aliases=("데이터센터",),
        representative_symbols=("아마존", "마이크로소프트", "오라클", "알파벳"),
    ),
)


def _build_theme_probe_query_specs(region: str) -> list[_QuerySpec]:
    return [
        _QuerySpec(text=definition.probe_query, kind="theme")
        for definition in _THEME_DEFINITIONS
        if definition.region == region
    ]


def _theme_definitions_for_region(region: str) -> tuple[ThemeDefinition, ...]:
    return tuple(definition for definition in _THEME_DEFINITIONS if definition.region == region)


def _merge_scored_candidate(target: dict[str, _ScoredNewsItem], candidate: _ScoredNewsItem) -> None:
    key = candidate.item.dedup_key()
    previous = target.get(key)
    if previous is None or candidate.score > previous.score:
        target[key] = candidate


def _build_news_analysis(
    *,
    items: Sequence[NewsItem],
    candidates_by_region: dict[str, Sequence[_ScoredNewsItem]],
    generated_at: datetime,
) -> NewsAnalysis:
    report = _build_trend_theme_report(candidates_by_region, generated_at)
    return NewsAnalysis(briefing_items=tuple(items), trend_report=report)


def _fallback_candidates_by_region(items: Sequence[NewsItem], now: datetime) -> dict[str, tuple[_ScoredNewsItem, ...]]:
    candidates: dict[str, list[_ScoredNewsItem]] = {"domestic": [], "global": []}
    for item in items:
        title_lower = item.title.lower()
        event_hits = _count_keyword_hits(title_lower, _STOCK_EVENT_KEYWORDS.get(item.region, ()))
        has_stock_symbol = any(
            alias in title_lower
            for aliases in _STOCK_QUERY_ALIASES.values()
            for alias in aliases
        )
        bucket = "stock" if event_hits > 0 and has_stock_symbol else "macro"
        score = max(1, _recency_score(max(0.0, (now - item.published_at).total_seconds() / 60)))
        score += 4 * _count_keyword_hits(title_lower, _BREAKING_KEYWORDS)
        score += max(_SOURCE_WEIGHTS.get(item.source, 0), 0)
        candidates.setdefault(item.region, []).append(
            _ScoredNewsItem(
                item=item,
                score=score,
                bucket=bucket,
                description="",
            )
        )
    return {region: tuple(values) for region, values in candidates.items()}


def _should_skip_candidate(
    candidate: _ScoredNewsItem,
    *,
    per_source: dict[str, int],
    seen_topics: set[str],
    seen_title_tokens: list[set[str]],
) -> bool:
    source_count = per_source.get(candidate.item.source, 0)
    if source_count >= _MAX_ITEMS_PER_SOURCE:
        return True

    topic = _topic_key(candidate.item.title, candidate.item.region)
    if topic and topic in seen_topics:
        return True

    title_tokens = _headline_similarity_tokens(candidate.item.title)
    return _is_near_duplicate(title_tokens, seen_title_tokens)


def _score_news_item(
    *,
    title: str,
    description: str,
    link: str,
    region: str,
    query: str,
    query_kind: str,
    now: datetime,
    published_at: datetime,
) -> tuple[int, str] | None:
    title_lower = title.lower()
    description_lower = description.lower()
    link_lower = link.lower()
    text = f"{title_lower} {description_lower}".strip()
    query_tokens = _stock_query_tokens(query) if query_kind == "stock" else _query_tokens(query)
    breaking_hits = _count_keyword_hits(title_lower, _BREAKING_KEYWORDS)
    source_weight = _SOURCE_WEIGHTS.get(_source_from_link(link), 0)

    if any(keyword in text for keyword in _BLOCKLIST_KEYWORDS):
        return None
    if "/photos/" in link_lower or "/photo/" in link_lower or title_lower.startswith("[포토]"):
        return None
    if query_kind == "stock":
        if not _is_high_impact_stock_story(title_lower, description_lower, region, query_tokens):
            return None
        age_minutes = max(0.0, (now - published_at).total_seconds() / 60)
        title_query_hits = _count_keyword_hits(title_lower, query_tokens)
        title_event_hits = _count_keyword_hits(title_lower, _STOCK_EVENT_KEYWORDS.get(region, ()))
        desc_event_hits = _count_keyword_hits(description_lower, _STOCK_EVENT_KEYWORDS.get(region, ()))
        score = _recency_score(age_minutes)
        score += 4 * breaking_hits
        score += 4 * title_event_hits
        score += 1 * desc_event_hits
        score += 3 * title_query_hits
        score += min(_count_keyword_hits(text, query_tokens), 2)
        score += source_weight
        score -= 3 * _count_keyword_hits(text, _STOCK_LOW_SIGNAL_KEYWORDS)
        if score <= 0:
            return None
        return score + 2, "stock"
    if query_kind == "theme":
        theme_query_hits = _count_keyword_hits(text, query_tokens)
        title_query_hits = _count_keyword_hits(title_lower, query_tokens)
        theme_event_hits = _count_keyword_hits(text, _STOCK_EVENT_KEYWORDS.get(region, ()))
        title_low_signal_hits = _count_keyword_hits(title_lower, _LOW_SIGNAL_KEYWORDS)
        has_symbol_signal = any(
            alias in text
            for aliases in _STOCK_QUERY_ALIASES.values()
            for alias in aliases
        )
        if theme_query_hits == 0 and theme_event_hits == 0:
            return None
        if title_low_signal_hits > 0 and theme_event_hits == 0:
            return None
        age_minutes = max(0.0, (now - published_at).total_seconds() / 60)
        score = _recency_score(age_minutes)
        score += 2 * theme_query_hits
        score += 2 * title_query_hits
        score += 2 * theme_event_hits
        score += 4 * breaking_hits
        score += source_weight
        score -= 4 * title_low_signal_hits
        score -= 2 * _count_keyword_hits(description_lower, _LOW_SIGNAL_KEYWORDS)
        if _looks_like_promotional_story(text):
            score -= 8
        if score <= 0:
            return None
        bucket = "stock" if theme_event_hits > 0 and has_symbol_signal else "macro"
        return score + 1, bucket

    if region == "domestic" and any(keyword in title_lower for keyword in ("주가", "etf", "액티브 etf")):
        return None

    title_gate_hits = _count_keyword_hits(title_lower, _REGION_GATE_KEYWORDS.get(region, ()))
    title_query_hits = _count_keyword_hits(title_lower, query_tokens)
    title_priority_hits = _count_keyword_hits(title_lower, _PRIORITY_KEYWORDS.get(region, ()))
    title_low_signal_hits = _count_keyword_hits(title_lower, _LOW_SIGNAL_KEYWORDS)
    region_hits = _count_keyword_hits(text, _PRIORITY_KEYWORDS.get(region, ()))
    query_hits = _count_keyword_hits(text, query_tokens)
    cross_hits = _count_keyword_hits(title_lower, _CROSS_REGION_KEYWORDS.get(region, ()))
    if title_gate_hits == 0 and title_query_hits == 0:
        return None
    if cross_hits > 0 and title_gate_hits <= cross_hits:
        return None
    if region_hits == 0 and query_hits == 0:
        return None
    if _looks_like_promotional_story(text) and breaking_hits == 0 and title_priority_hits < 2:
        return None
    if title_low_signal_hits > 0 and breaking_hits == 0 and title_priority_hits < 2:
        return None

    age_minutes = max(0.0, (now - published_at).total_seconds() / 60)
    score = _recency_score(age_minutes)
    score += 4 * breaking_hits
    score += 2 * _count_keyword_hits(description_lower, _BREAKING_KEYWORDS)
    score += 3 * title_priority_hits
    score += 1 * _count_keyword_hits(description_lower, _PRIORITY_KEYWORDS.get(region, ()))
    score += min(query_hits, 3)
    score += source_weight
    score -= 5 * title_low_signal_hits
    score -= 2 * _count_keyword_hits(description_lower, _LOW_SIGNAL_KEYWORDS)
    if _looks_like_promotional_story(text):
        score -= 8
    if score <= 0:
        return None
    return score, "macro"


def _topic_key(title: str, region: str) -> str | None:
    title_lower = title.lower()
    base = ""
    if region == "domestic":
        if "코스피" in title_lower:
            base = "domestic:코스피"
        elif "코스닥" in title_lower:
            base = "domestic:코스닥"
        elif "환율" in title_lower or "원/달러" in title_lower:
            base = "domestic:환율"
        elif "한국은행" in title_lower or "한은" in title_lower or "금리" in title_lower:
            base = "domestic:금리"
        elif "외국인" in title_lower or "기관" in title_lower:
            base = "domestic:수급"
        elif "공매도" in title_lower:
            base = "domestic:공매도"
    else:
        if any(keyword in title_lower for keyword in ("연준", "fomc", "fed", "파월")):
            base = "global:연준"
        elif any(keyword in title_lower for keyword in ("나스닥", "s&p", "s&p 500", "다우", "미국 증시", "미 증시", "뉴욕", "월가")):
            base = "global:미국증시"
        elif any(keyword in title_lower for keyword in ("cpi", "pce", "고용", "국채")):
            base = "global:지표"
        elif "sec" in title_lower:
            base = "global:sec"
    if not base:
        return None
    return base


def _query_tokens(query: str) -> tuple[str, ...]:
    tokens = [
        token.strip().lower()
        for token in re.split(r"[|,/ ]+", query)
        if len(token.strip()) >= 2 and token.strip().lower() not in _QUERY_STOPWORDS
    ]
    return tuple(dict.fromkeys(tokens))


def _stock_query_tokens(query: str) -> tuple[str, ...]:
    normalized = query.strip().lower()
    aliases = _STOCK_QUERY_ALIASES.get(normalized)
    if aliases:
        return aliases
    return _query_tokens(query)


def _count_keyword_hits(text: str, keywords: Sequence[str]) -> int:
    return sum(1 for keyword in dict.fromkeys(keywords) if keyword and keyword in text)


def _looks_like_promotional_story(text: str) -> bool:
    promo_patterns = (
        ("무료", "제공"),
        ("무료", "시세"),
        ("무료화",),
        ("공짜",),
        ("전 회원",),
        ("실시간 시세",),
        ("계좌 인증",),
        ("혜택",),
        ("이벤트",),
        ("헤지펀드",),
    )
    return any(all(part in text for part in pattern) for pattern in promo_patterns)


def _is_high_impact_stock_story(
    title_lower: str,
    description_lower: str,
    region: str,
    query_tokens: Sequence[str],
) -> bool:
    if not query_tokens:
        return False
    text = f"{title_lower} {description_lower}".strip()
    title_query_hits = _count_keyword_hits(title_lower, query_tokens)
    if title_query_hits == 0:
        return False
    if _looks_like_promotional_story(text):
        return False
    title_event_hits = _count_keyword_hits(title_lower, _STOCK_EVENT_KEYWORDS.get(region, ()))
    if _count_keyword_hits(title_lower, _STOCK_LOW_SIGNAL_KEYWORDS) > 0 and title_event_hits == 0:
        return False
    if "주가" in title_lower and title_event_hits == 0:
        return False
    breaking_hits = _count_keyword_hits(title_lower, _BREAKING_KEYWORDS)
    return title_event_hits > 0 or breaking_hits > 0


def _headline_similarity_tokens(title: str) -> set[str]:
    normalized = re.sub(r"[^0-9a-zA-Z가-힣]+", " ", title.lower())
    return {
        token
        for token in normalized.split()
        if len(token) >= 2 and token not in _TITLE_SIMILARITY_STOPWORDS
    }


def _is_near_duplicate(title_tokens: set[str], existing_token_sets: Sequence[set[str]]) -> bool:
    if len(title_tokens) < 3:
        return False
    for existing in existing_token_sets:
        intersection = len(title_tokens & existing)
        union = len(title_tokens | existing)
        if intersection >= 3 and union > 0 and (intersection / union) >= 0.45:
            return True
    return False


def _recency_score(age_minutes: float) -> int:
    if age_minutes <= 30:
        return 8
    if age_minutes <= 60:
        return 6
    if age_minutes <= 180:
        return 4
    if age_minutes <= 720:
        return 2
    return 0


def _build_trend_theme_report(
    candidates_by_region: dict[str, Sequence[_ScoredNewsItem]],
    generated_at: datetime,
) -> TrendThemeReport:
    themes_by_region: dict[str, tuple[ThemeBrief, ...]] = {}
    for region in ("domestic", "global"):
        themes_by_region[region] = _select_theme_briefs(
            _rank_theme_briefs(candidates_by_region.get(region, ()), region)
        )
    return TrendThemeReport(generated_at=generated_at, themes_by_region=themes_by_region)


def _rank_theme_briefs(candidates: Sequence[_ScoredNewsItem], region: str) -> list[ThemeBrief]:
    briefs: list[ThemeBrief] = []
    for definition in _theme_definitions_for_region(region):
        hits = [
            hit
            for candidate in candidates
            if (hit := _match_theme_candidate(definition, candidate)) is not None
        ]
        unique_hits = _unique_theme_hits_by_story(hits)
        if len(unique_hits) < 2:
            continue
        representative_hits = _pick_representative_theme_hits(unique_hits)
        if len(representative_hits) < 2:
            continue
        article_count = len(unique_hits)
        source_count = len({hit.item.source for hit in unique_hits})
        aggregate_score = sum(hit.score for hit in unique_hits[:3])
        aggregate_score += article_count * 4
        aggregate_score += source_count * 3
        if any(hit.bucket == "macro" for hit in unique_hits) and any(hit.bucket == "stock" for hit in unique_hits):
            aggregate_score += 4
        if aggregate_score < _TREND_SCORE_FLOOR:
            continue
        briefs.append(
            ThemeBrief(
                theme_name=definition.name,
                region=region,
                score=aggregate_score,
                reason_tags=_build_theme_reason_tags(unique_hits, representative_hits),
                representative_items=tuple(hit.item for hit in representative_hits),
                article_count=article_count,
                source_count=source_count,
            )
        )
    return sorted(
        briefs,
        key=lambda brief: (brief.score, brief.article_count, brief.source_count),
        reverse=True,
    )


def _select_theme_briefs(briefs: Sequence[ThemeBrief]) -> tuple[ThemeBrief, ...]:
    qualified = [brief for brief in briefs if brief.score >= _TREND_SCORE_FLOOR]
    if len(qualified) <= _TREND_TARGET_THEMES:
        return tuple(qualified)

    selected = qualified[:_TREND_TARGET_THEMES]
    threshold = max(_TREND_SCORE_FLOOR, int(selected[-1].score * _TREND_EXPANSION_RATIO))
    for brief in qualified[_TREND_TARGET_THEMES : _TREND_MAX_THEMES]:
        if brief.score < threshold:
            break
        selected.append(brief)
    return tuple(selected)


def _match_theme_candidate(definition: ThemeDefinition, candidate: _ScoredNewsItem) -> ThemeHit | None:
    if candidate.item.region != definition.region:
        return None

    title_lower = candidate.item.title.lower()
    description_lower = candidate.description.lower()
    text = f"{title_lower} {description_lower}".strip()
    if any(keyword in text for keyword in _TREND_HARD_BLOCKLIST_KEYWORDS):
        return None
    if any(keyword in text for keyword in definition.exclude_keywords):
        return None
    if _looks_like_promotional_story(text):
        return None
    if "주가" in title_lower and candidate.bucket != "stock":
        return None

    keyword_hits = [keyword for keyword in definition.keywords if keyword in text]
    alias_hits = [alias for alias in definition.aliases if alias in text]
    symbol_hits = [
        symbol
        for symbol in definition.representative_symbols
        if symbol.lower() in text
    ]
    if not keyword_hits and not alias_hits and not symbol_hits:
        return None

    title_theme_hits = [keyword for keyword in (*definition.keywords, *definition.aliases) if keyword in title_lower]
    if not title_theme_hits and not symbol_hits and len(keyword_hits) + len(alias_hits) < 2:
        return None

    event_hits = _count_keyword_hits(text, _STOCK_EVENT_KEYWORDS.get(definition.region, ()))
    signal_score = candidate.score
    signal_score += 3 * len(dict.fromkeys(keyword_hits))
    signal_score += 2 * len(dict.fromkeys(alias_hits))
    signal_score += 4 * len(dict.fromkeys(symbol_hits))
    signal_score += min(event_hits, 3) * 2
    if candidate.bucket == "stock":
        signal_score += 3
    if signal_score < _TREND_SCORE_FLOOR - 6:
        return None

    reason_tags: list[str] = []
    if keyword_hits or alias_hits:
        reason_tags.append("테마 반복")
    if symbol_hits:
        reason_tags.append("대표 종목 동반")
    if event_hits > 0:
        reason_tags.append("이벤트 headline")
    if _count_keyword_hits(title_lower, _BREAKING_KEYWORDS) > 0:
        reason_tags.append("속보 신호")

    return ThemeHit(
        definition=definition,
        item=candidate.item,
        score=signal_score,
        bucket=candidate.bucket,
        reason_tags=tuple(reason_tags),
        matched_symbols=tuple(dict.fromkeys(symbol_hits)),
    )


def _unique_theme_hits_by_story(hits: Sequence[ThemeHit]) -> list[ThemeHit]:
    best_by_story: dict[str, ThemeHit] = {}
    for hit in hits:
        key = hit.item.story_key()
        previous = best_by_story.get(key)
        if previous is None or hit.score > previous.score:
            best_by_story[key] = hit
    return sorted(
        best_by_story.values(),
        key=lambda hit: (hit.score, hit.item.published_at),
        reverse=True,
    )


def _pick_representative_theme_hits(hits: Sequence[ThemeHit]) -> list[ThemeHit]:
    selected: list[ThemeHit] = []
    used_keys: set[str] = set()
    used_sources: set[str] = set()

    macro_hit = _pick_preferred_theme_hit(
        [hit for hit in hits if hit.bucket == "macro"],
        used_keys=used_keys,
        used_sources=used_sources,
    )
    if macro_hit is not None:
        selected.append(macro_hit)
        used_keys.add(macro_hit.item.story_key())
        used_sources.add(macro_hit.item.source)

    stock_hit = _pick_preferred_theme_hit(
        [hit for hit in hits if hit.bucket == "stock"],
        used_keys=used_keys,
        used_sources=used_sources,
    )
    if stock_hit is not None:
        selected.append(stock_hit)
        used_keys.add(stock_hit.item.story_key())
        used_sources.add(stock_hit.item.source)

    for hit in hits:
        if len(selected) >= 2:
            break
        story_key = hit.item.story_key()
        if story_key in used_keys:
            continue
        if hit.item.source in used_sources:
            alternate = _pick_preferred_theme_hit(
                hits,
                used_keys=used_keys,
                used_sources=used_sources,
            )
            if alternate is not None and alternate.item.story_key() != story_key:
                hit = alternate
                story_key = hit.item.story_key()
        if story_key in used_keys:
            continue
        selected.append(hit)
        used_keys.add(story_key)
        used_sources.add(hit.item.source)

    return selected[:2]


def _pick_preferred_theme_hit(
    hits: Sequence[ThemeHit],
    *,
    used_keys: set[str],
    used_sources: set[str],
) -> ThemeHit | None:
    for hit in hits:
        if hit.item.story_key() in used_keys:
            continue
        if hit.item.source not in used_sources:
            return hit
    for hit in hits:
        if hit.item.story_key() not in used_keys:
            return hit
    return None


def _build_theme_reason_tags(
    hits: Sequence[ThemeHit],
    representative_hits: Sequence[ThemeHit],
) -> tuple[str, ...]:
    reason_tags = [f"기사 {len(hits)}건", f"{len({hit.item.source for hit in hits})}개 소스"]
    matched_symbols: list[str] = []
    for hit in representative_hits:
        for symbol in hit.matched_symbols:
            if symbol not in matched_symbols:
                matched_symbols.append(symbol)
    if matched_symbols:
        symbol_text = "·".join(matched_symbols[:2])
        reason_tags.append(f"대표 종목 {symbol_text}")
    if any(hit.bucket == "stock" for hit in hits):
        reason_tags.append("종목 이벤트 포함")
    return tuple(reason_tags)
