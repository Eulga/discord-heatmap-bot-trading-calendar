from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html import unescape
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

_TAG_RE = re.compile(r"<[^>]+>")
_PHOTO_PATH_MARKERS = ("/photo/", "/photos/", "/picture/", "/gallery/")
_HARD_BLOCKLIST_KEYWORDS = (
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
    "무료 제공",
    "무료화",
    "전 회원",
    "실시간 시세",
    "계좌 인증",
    "평생 공짜",
    "혜택 제공",
    "이벤트 참여",
    "종목 추천",
)
_PHOTO_TITLE_PREFIXES = ("[포토]", "포토뉴스", "사진:")


@dataclass(frozen=True)
class CollectedNewsArticle:
    provider: str
    region: str
    title: str
    description: str
    url: str
    canonical_url: str
    source: str
    published_at: datetime
    query: str
    raw_payload: dict[str, Any]

    def article_key(self) -> str:
        base = f"{self.provider}|{self.region}|{self.canonical_url}"
        return sha256(base.encode("utf-8")).hexdigest()


NewsItem = CollectedNewsArticle


@dataclass(frozen=True)
class NewsQueryUniverse:
    domestic_stock_queries: tuple[str, ...] = ()
    global_stock_queries: tuple[str, ...] = ()


class NewsProvider(Protocol):
    async def fetch(
        self,
        now: datetime,
        *,
        query_universe: NewsQueryUniverse | None = None,
    ) -> list[CollectedNewsArticle]: ...


class ErrorNewsProvider:
    def __init__(self, message: str) -> None:
        self._message = message
        self.last_fetch_stats = {"fetched": 0, "accepted": 0, "skipped": 0}

    async def fetch(
        self,
        now: datetime,
        *,
        query_universe: NewsQueryUniverse | None = None,
    ) -> list[CollectedNewsArticle]:
        raise RuntimeError(self._message)


class MockNewsProvider:
    provider_key = "mock"

    def __init__(self) -> None:
        self.last_fetch_stats = {"fetched": 0, "accepted": 0, "skipped": 0}

    async def fetch(
        self,
        now: datetime,
        *,
        query_universe: NewsQueryUniverse | None = None,
    ) -> list[CollectedNewsArticle]:
        raw_items = [
            {
                "title": "한국 수출지표 개선 기대",
                "description": "수출 지표 개선 기대가 국내 증시 심리에 영향을 주고 있다.",
                "url": "https://example.com/kr-export",
                "source": "MockNewsKR",
                "published_at": (now - timedelta(minutes=32)).isoformat(),
                "region": "domestic",
                "query": "mock-domestic",
            },
            {
                "title": "Fed 위원 발언에 채권금리 혼조",
                "description": "연준 위원 발언 이후 미국 국채 금리가 혼조세를 보였다.",
                "url": "https://example.com/global-fed",
                "source": "MockNewsGlobal",
                "published_at": (now - timedelta(minutes=41)).isoformat(),
                "region": "global",
                "query": "mock-global",
            },
        ]
        articles: list[CollectedNewsArticle] = []
        for raw in raw_items:
            article = _normalize_common_article(
                raw_item=raw,
                provider=self.provider_key,
                region=str(raw["region"]),
                title=str(raw["title"]),
                description=str(raw["description"]),
                url=str(raw["url"]),
                source=str(raw["source"]),
                published_at=now - timedelta(minutes=32 if raw["region"] == "domestic" else 41),
                query=str(raw["query"]),
                now=now,
                max_age_hours=24,
            )
            if article is not None:
                articles.append(article)
        self.last_fetch_stats = {"fetched": len(raw_items), "accepted": len(articles), "skipped": len(raw_items) - len(articles)}
        return articles


class HybridNewsProvider:
    provider_key = "hybrid"

    def __init__(self, domestic_provider: NewsProvider, global_provider: NewsProvider) -> None:
        self.domestic_provider = domestic_provider
        self.global_provider = global_provider
        self.last_fetch_stats = {"fetched": 0, "accepted": 0, "skipped": 0}

    async def fetch(
        self,
        now: datetime,
        *,
        query_universe: NewsQueryUniverse | None = None,
    ) -> list[CollectedNewsArticle]:
        domestic_items, global_items = await asyncio.gather(
            _fetch_with_query_universe(self.domestic_provider, now, query_universe=query_universe),
            _fetch_with_query_universe(self.global_provider, now, query_universe=query_universe),
        )
        self.last_fetch_stats = _combine_fetch_stats(self.domestic_provider, self.global_provider)
        return [*domestic_items, *global_items]


class MarketauxNewsProvider:
    provider_key = "marketaux"

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
        self.limit_per_region = max(1, min(limit_per_region, 100))
        self.max_age_hours = max(1, max_age_hours)
        self.timeout_seconds = max(1, min(timeout_seconds, 10))
        self.retry_count = max(0, min(retry_count, 1))
        self.last_fetch_stats = {"fetched": 0, "accepted": 0, "skipped": 0}

    async def fetch(
        self,
        now: datetime,
        *,
        query_universe: NewsQueryUniverse | None = None,
    ) -> list[CollectedNewsArticle]:
        latest_allowed = now + timedelta(minutes=5)
        articles: list[CollectedNewsArticle] = []
        fetched = 0
        skipped = 0
        global_queries = _merge_queries(
            self.global_queries,
            query_universe.global_stock_queries if query_universe else (),
        )
        for query in global_queries or [""]:
            payload = await asyncio.to_thread(self._request_json, query)
            raw_items = payload.get("data")
            if not isinstance(raw_items, list):
                raise RuntimeError("marketaux-invalid-response")
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    skipped += 1
                    continue
                fetched += 1
                article = self._normalize_item(raw_item, query, now, latest_allowed)
                if article is None:
                    skipped += 1
                    continue
                articles.append(article)
        self.last_fetch_stats = {"fetched": fetched, "accepted": len(articles), "skipped": skipped}
        return articles

    def _request_json(self, query: str) -> dict[str, Any]:
        params = {
            "api_token": self.api_token,
            "countries": ",".join(self.countries) if self.countries else "",
            "language": ",".join(self.language) if self.language else "",
            "filter_entities": "false",
            "group_similar": "false",
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
        query: str,
        now: datetime,
        latest_allowed: datetime,
    ) -> CollectedNewsArticle | None:
        title = str(raw_item.get("title") or "").strip()
        description = str(raw_item.get("description") or raw_item.get("snippet") or "").strip()
        url = str(raw_item.get("url") or "").strip()
        source = _marketaux_source(raw_item.get("source"), url)
        published_at_text = str(raw_item.get("published_at") or "").strip()
        if not title or not url or not published_at_text:
            return None
        try:
            published_at = datetime.fromisoformat(published_at_text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if published_at.tzinfo is None or published_at > latest_allowed:
            return None
        return _normalize_common_article(
            raw_item=raw_item,
            provider=self.provider_key,
            region="global",
            title=title,
            description=description,
            url=url,
            source=source,
            published_at=published_at,
            query=query,
            now=now,
            max_age_hours=self.max_age_hours,
        )


class NaverNewsProvider:
    provider_key = "naver"

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
        self.display = min(max(limit_per_region, 1), 100)
        self.max_age_hours = max(1, max_age_hours)
        self.timeout_seconds = max(1, min(timeout_seconds, 10))
        self.retry_count = max(0, min(retry_count, 1))
        self.last_fetch_stats = {"fetched": 0, "accepted": 0, "skipped": 0}

    async def fetch(
        self,
        now: datetime,
        *,
        query_universe: NewsQueryUniverse | None = None,
    ) -> list[CollectedNewsArticle]:
        domestic_dynamic_queries = (
            query_universe.domestic_stock_queries
            if query_universe and (self.domestic_queries or self.domestic_stock_queries)
            else ()
        )
        global_dynamic_queries = (
            query_universe.global_stock_queries
            if query_universe and (self.global_queries or self.global_stock_queries)
            else ()
        )
        domestic_queries = _merge_queries(
            self.domestic_queries,
            domestic_dynamic_queries,
            self.domestic_stock_queries,
        )
        global_queries = _merge_queries(
            self.global_queries,
            global_dynamic_queries,
            self.global_stock_queries,
        )
        domestic_task = asyncio.to_thread(
            self._fetch_region,
            domestic_queries,
            "domestic",
            now,
        )
        global_task = asyncio.to_thread(
            self._fetch_region,
            global_queries,
            "global",
            now,
        )
        domestic_result, global_result = await asyncio.gather(domestic_task, global_task)
        articles = [*domestic_result[0], *global_result[0]]
        fetched = domestic_result[1] + global_result[1]
        skipped = domestic_result[2] + global_result[2]
        self.last_fetch_stats = {"fetched": fetched, "accepted": len(articles), "skipped": skipped}
        return articles

    def _fetch_region(self, queries: Sequence[str], region: str, now: datetime) -> tuple[list[CollectedNewsArticle], int, int]:
        articles: list[CollectedNewsArticle] = []
        fetched = 0
        skipped = 0
        for query in queries:
            payload = self._request_json(query)
            raw_items = payload.get("items")
            if not isinstance(raw_items, list):
                raise RuntimeError("naver-news-invalid-response")
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    skipped += 1
                    continue
                fetched += 1
                article = self._normalize_item(raw_item, region, query, now)
                if article is None:
                    skipped += 1
                    continue
                articles.append(article)
        return articles, fetched, skipped

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
        query: str,
        now: datetime,
    ) -> CollectedNewsArticle | None:
        title = _clean_html_text(str(raw_item.get("title") or ""))
        description = _clean_html_text(str(raw_item.get("description") or ""))
        url = str(raw_item.get("originallink") or raw_item.get("link") or "").strip()
        published_at_text = str(raw_item.get("pubDate") or "").strip()
        if not title or not url or not published_at_text:
            return None
        try:
            published_at = parsedate_to_datetime(published_at_text)
        except (TypeError, ValueError, IndexError):
            return None
        if published_at.tzinfo is None:
            return None
        return _normalize_common_article(
            raw_item=raw_item,
            provider=self.provider_key,
            region=region,
            title=title,
            description=description,
            url=url,
            source=_source_from_url(url),
            published_at=published_at,
            query=query,
            now=now,
            max_age_hours=self.max_age_hours,
        )


def _normalize_common_article(
    *,
    raw_item: dict[str, Any],
    provider: str,
    region: str,
    title: str,
    description: str,
    url: str,
    source: str,
    published_at: datetime,
    query: str,
    now: datetime,
    max_age_hours: int,
) -> CollectedNewsArticle | None:
    canonical_url = _canonicalize_url(url)
    if canonical_url is None:
        return None
    if region not in {"domestic", "global"}:
        return None
    if published_at.tzinfo is None:
        return None
    if published_at < now - timedelta(hours=max_age_hours) or published_at > now + timedelta(minutes=5):
        return None
    cleaned_title = _clean_html_text(title)
    cleaned_description = _clean_html_text(description)
    if not cleaned_title or _is_hard_blocked(cleaned_title, cleaned_description, canonical_url):
        return None
    return CollectedNewsArticle(
        provider=provider,
        region=region,
        title=cleaned_title,
        description=cleaned_description,
        url=url.strip(),
        canonical_url=canonical_url,
        source=(source or _source_from_url(canonical_url)).strip() or _source_from_url(canonical_url),
        published_at=published_at,
        query=query,
        raw_payload=dict(raw_item),
    )


def _clean_html_text(text: str) -> str:
    return " ".join(unescape(_TAG_RE.sub("", text)).split())


def _canonicalize_url(url: str) -> str | None:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), netloc, path, "", parsed.query, ""))


def _source_from_url(url: str) -> str:
    parsed = urlparse(url)
    hostname = parsed.netloc.strip().lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname or "unknown"


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


def _merge_queries(*groups: Sequence[str]) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for raw in group:
            query = str(raw).strip()
            if not query or query in seen:
                continue
            seen.add(query)
            queries.append(query)
    return queries


def _marketaux_source(value: Any, url: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("domain", "name", "source"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return _source_from_url(url)


def _is_hard_blocked(title: str, description: str, canonical_url: str) -> bool:
    title_lower = title.lower()
    text = f"{title_lower} {description.lower()}".strip()
    if any(title_lower.startswith(prefix.lower()) for prefix in _PHOTO_TITLE_PREFIXES):
        return True
    if any(marker in canonical_url.lower() for marker in _PHOTO_PATH_MARKERS):
        return True
    return any(keyword in text for keyword in _HARD_BLOCKLIST_KEYWORDS)


def _combine_fetch_stats(*providers: NewsProvider) -> dict[str, int]:
    combined = {"fetched": 0, "accepted": 0, "skipped": 0}
    for provider in providers:
        stats = getattr(provider, "last_fetch_stats", {})
        if not isinstance(stats, dict):
            continue
        for key in combined:
            value = stats.get(key, 0)
            if isinstance(value, int):
                combined[key] += value
    return combined


async def _fetch_with_query_universe(
    provider: NewsProvider,
    now: datetime,
    *,
    query_universe: NewsQueryUniverse | None = None,
) -> list[CollectedNewsArticle]:
    try:
        return await provider.fetch(now, query_universe=query_universe)
    except TypeError as exc:
        if "query_universe" not in str(exc):
            raise
        return await provider.fetch(now)  # type: ignore[call-arg]
