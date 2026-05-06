from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from bot.intel.providers.news import (
    CollectedNewsArticle,
    HybridNewsProvider,
    MarketauxNewsProvider,
    NaverNewsProvider,
    NewsQueryUniverse,
)


KST = ZoneInfo("Asia/Seoul")


def _naver_item(
    *,
    title: str = "한국 증시 상승",
    description: str = "기관 매수세가 유입됐다.",
    url: str = "https://news.example.com/articles/1",
    pub_date: str = "Fri, 13 Feb 2026 07:10:00 +0900",
) -> dict[str, str]:
    return {
        "title": title,
        "description": description,
        "originallink": url,
        "link": url,
        "pubDate": pub_date,
    }


def _article(now: datetime, *, provider: str = "naver", url: str = "https://news.example.com/a") -> CollectedNewsArticle:
    return CollectedNewsArticle(
        provider=provider,
        region="domestic",
        title="테스트 기사",
        description="설명",
        url=url,
        canonical_url=url,
        source="news.example.com",
        published_at=now,
        query="경제",
        raw_payload={"url": url},
    )


@pytest.mark.asyncio
async def test_naver_news_provider_preserves_raw_payload_and_normalized_fields():
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    raw = _naver_item(
        title="<b>코스피</b> 반등",
        description="환율 안정으로 <b>투심</b>이 개선됐다.",
        url="HTTPS://WWW.News.Example.com/Market/1/",
    )
    provider = NaverNewsProvider(
        client_id="id",
        client_secret="secret",
        domestic_query=["국내 증시"],
        global_query=[],
        max_age_hours=24,
    )
    provider._request_json = lambda query: {"items": [raw]}  # type: ignore[method-assign]

    articles = await provider.fetch(now)

    assert len(articles) == 1
    article = articles[0]
    assert article.provider == "naver"
    assert article.region == "domestic"
    assert article.title == "코스피 반등"
    assert article.description == "환율 안정으로 투심이 개선됐다."
    assert article.canonical_url == "https://news.example.com/Market/1"
    assert article.query == "국내 증시"
    assert article.raw_payload == raw
    assert provider.last_fetch_stats == {"fetched": 1, "accepted": 1, "skipped": 0}


@pytest.mark.asyncio
async def test_naver_news_provider_keeps_basic_quality_filter_only():
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    recent = "Fri, 13 Feb 2026 07:10:00 +0900"
    old = "Thu, 12 Feb 2026 06:00:00 +0900"
    raw_items = [
        _naver_item(title="삼성전자 목표가 상향", url="https://same-source.example.com/a", pub_date=recent),
        _naver_item(title="SK하이닉스 수급 개선", url="https://same-source.example.com/b", pub_date=recent),
        _naver_item(title="현대차 실적 전망", url="https://same-source.example.com/c", pub_date=recent),
        _naver_item(title="", url="https://news.example.com/missing-title", pub_date=recent),
        _naver_item(title="잘못된 URL", url="ftp://news.example.com/bad", pub_date=recent),
        _naver_item(title="naive date", url="https://news.example.com/naive", pub_date="Fri, 13 Feb 2026 07:10:00"),
        _naver_item(title="너무 오래된 기사", url="https://news.example.com/old", pub_date=old),
        _naver_item(title="[포토] 장 시작 전 모습", url="https://news.example.com/photo/1", pub_date=recent),
        _naver_item(title="전 회원 무료 제공 이벤트", url="https://news.example.com/promo", pub_date=recent),
    ]
    provider = NaverNewsProvider(
        client_id="id",
        client_secret="secret",
        domestic_query=["경제"],
        global_query=[],
        max_age_hours=12,
    )
    provider._request_json = lambda query: {"items": raw_items}  # type: ignore[method-assign]

    articles = await provider.fetch(now)

    assert [article.title for article in articles] == ["삼성전자 목표가 상향", "SK하이닉스 수급 개선", "현대차 실적 전망"]
    assert len({article.source for article in articles}) == 1
    assert provider.last_fetch_stats == {"fetched": 9, "accepted": 3, "skipped": 6}


@pytest.mark.asyncio
async def test_naver_news_provider_does_not_dedupe_query_duplicates():
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    raw = _naver_item(title="같은 기사", url="https://news.example.com/duplicate")
    provider = NaverNewsProvider(
        client_id="id",
        client_secret="secret",
        domestic_query=["경제"],
        global_query=[],
        domestic_stock_query=["삼성전자"],
    )
    provider._request_json = lambda query: {"items": [raw]}  # type: ignore[method-assign]

    articles = await provider.fetch(now)

    assert len(articles) == 2
    assert articles[0].article_key() == articles[1].article_key()
    assert [article.query for article in articles] == ["경제", "삼성전자"]


@pytest.mark.asyncio
async def test_naver_news_provider_adds_dynamic_stock_queries_after_macro():
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    raw = _naver_item(title="동적 기사", url="https://news.example.com/dynamic")
    provider = NaverNewsProvider(
        client_id="id",
        client_secret="secret",
        domestic_query=["국내 증시"],
        global_query=["미국 증시"],
        domestic_stock_query=["반도체"],
        global_stock_query=["빅테크"],
    )
    provider._request_json = lambda query: {"items": [dict(raw, originallink=f"https://news.example.com/{query}")]}  # type: ignore[method-assign]

    articles = await provider.fetch(
        now,
        query_universe=NewsQueryUniverse(
            domestic_stock_queries=("삼성전자",),
            global_stock_queries=("Apple OR AAPL",),
        ),
    )

    assert [article.query for article in articles] == [
        "국내 증시",
        "삼성전자",
        "반도체",
        "미국 증시",
        "Apple OR AAPL",
        "빅테크",
    ]


@pytest.mark.asyncio
async def test_naver_news_provider_does_not_enable_empty_region_with_dynamic_queries():
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    raw = _naver_item(title="국내 동적 기사", url="https://news.example.com/domestic-dynamic")
    provider = NaverNewsProvider(
        client_id="id",
        client_secret="secret",
        domestic_query=["국내 증시"],
        global_query=[],
    )
    provider._request_json = lambda query: {"items": [raw]}  # type: ignore[method-assign]

    articles = await provider.fetch(
        now,
        query_universe=NewsQueryUniverse(
            domestic_stock_queries=("삼성전자",),
            global_stock_queries=("Apple OR AAPL",),
        ),
    )

    assert [article.query for article in articles] == ["국내 증시", "삼성전자"]
    assert {article.region for article in articles} == {"domestic"}


@pytest.mark.asyncio
async def test_marketaux_news_provider_preserves_raw_payload_and_description():
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    raw = {
        "title": "Fed officials discuss rate path",
        "description": "Treasury yields were mixed after the remarks.",
        "url": "https://global.example.com/fed",
        "published_at": "2026-02-12T22:10:00Z",
        "source": {"name": "Global Wire", "domain": "global.example.com"},
        "entities": [{"symbol": "SPY"}],
    }
    provider = MarketauxNewsProvider(
        api_token="token",
        global_query=["fed"],
        countries=["us"],
        language=["en"],
        max_age_hours=24,
    )
    provider._request_json = lambda query: {"data": [raw]}  # type: ignore[method-assign]

    articles = await provider.fetch(now)

    assert len(articles) == 1
    article = articles[0]
    assert article.provider == "marketaux"
    assert article.region == "global"
    assert article.description == "Treasury yields were mixed after the remarks."
    assert article.source == "global.example.com"
    assert article.query == "fed"
    assert article.raw_payload == raw


@pytest.mark.asyncio
async def test_marketaux_news_provider_adds_dynamic_global_queries():
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    raw = {
        "title": "Apple shares move",
        "description": "The stock moved after volume increased.",
        "url": "https://global.example.com/apple",
        "published_at": "2026-02-12T22:10:00Z",
        "source": "Global Wire",
    }
    provider = MarketauxNewsProvider(
        api_token="token",
        global_query=["US stocks"],
        countries=["us"],
        language=["en"],
        max_age_hours=24,
    )
    provider._request_json = lambda query: {"data": [dict(raw, url=f"https://global.example.com/{query}")]}  # type: ignore[method-assign]

    articles = await provider.fetch(
        now,
        query_universe=NewsQueryUniverse(global_stock_queries=("Apple OR AAPL",)),
    )

    assert [article.query for article in articles] == ["US stocks", "Apple OR AAPL"]


@pytest.mark.asyncio
async def test_hybrid_news_provider_combines_results_without_deduping():
    now = datetime(2026, 2, 13, 7, 30, tzinfo=KST)
    first = _article(now, provider="naver", url="https://news.example.com/a")
    second = _article(now, provider="naver", url="https://news.example.com/a")

    class Provider:
        def __init__(self, articles):
            self.articles = articles
            self.last_fetch_stats = {"fetched": len(articles), "accepted": len(articles), "skipped": 0}

        async def fetch(self, now):
            return self.articles

    provider = HybridNewsProvider(Provider([first]), Provider([second]))

    articles = await provider.fetch(now)

    assert articles == [first, second]
    assert provider.last_fetch_stats == {"fetched": 2, "accepted": 2, "skipped": 0}
