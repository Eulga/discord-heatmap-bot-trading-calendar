from datetime import datetime
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

import pytest

from bot.intel.providers import news as news_module
from bot.intel.providers.news import NaverNewsProvider

KST = ZoneInfo("Asia/Seoul")


class StubNaverNewsProvider(NaverNewsProvider):
    def __init__(
        self,
        payloads: dict[str, dict],
        *,
        domestic_query: str | list[str] = "국내 증시",
        global_query: str | list[str] = "미국 증시",
        domestic_stock_query: str | list[str] = (),
        global_stock_query: str | list[str] = (),
        limit_per_region: int = 1,
    ) -> None:
        super().__init__(
            client_id="client-id",
            client_secret="client-secret",
            domestic_query=domestic_query,
            global_query=global_query,
            domestic_stock_query=domestic_stock_query,
            global_stock_query=global_stock_query,
            limit_per_region=limit_per_region,
            max_age_hours=24,
            timeout_seconds=5,
            retry_count=0,
        )
        self.payloads = payloads

    def _request_json(self, query: str) -> dict:
        return self.payloads.get(query, {"items": []})


@pytest.mark.asyncio
async def test_naver_news_provider_normalizes_html_and_filters_old_items():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {
                "items": [
                    {
                        "title": "<b>코스피</b> 반등 기대",
                        "originallink": "https://news.example.com/article-1",
                        "link": "https://openapi.naver.com/l?article-1",
                        "pubDate": "Wed, 18 Mar 2026 07:10:00 +0900",
                    },
                    {
                        "title": "오래된 기사",
                        "originallink": "https://news.example.com/old",
                        "link": "https://openapi.naver.com/l?old",
                        "pubDate": "Mon, 16 Mar 2026 07:10:00 +0900",
                    },
                ]
            },
            "미국 증시": {
                "items": [
                    {
                        "title": "미 <b>증시</b> 혼조",
                        "originallink": "https://global.example.com/article-2",
                        "link": "https://openapi.naver.com/l?article-2",
                        "pubDate": "Wed, 18 Mar 2026 06:55:00 +0900",
                    }
                ]
            },
        }
    )

    now = datetime(2026, 3, 18, 7, 30, tzinfo=KST)
    items = await provider.fetch(now)

    assert len(items) == 2
    assert items[0].region == "domestic"
    assert items[0].title == "코스피 반등 기대"
    assert items[0].source == "news.example.com"
    assert items[0].link == "https://news.example.com/article-1"
    assert items[1].region == "global"
    assert items[1].title == "미 증시 혼조"
    assert items[1].source == "global.example.com"


@pytest.mark.asyncio
async def test_naver_news_provider_filters_low_signal_items_and_keeps_major_global_news():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {"items": []},
            "미국 증시": {
                "items": [
                    {
                        "title": "[AI의 종목 이야기] 지금 사야 할 반도체주는?",
                        "originallink": "https://noise.example.com/article-1",
                        "link": "https://openapi.naver.com/l?noise-1",
                        "description": "종목 이야기",
                        "pubDate": "Thu, 19 Mar 2026 13:30:00 +0900",
                    },
                    {
                        "title": "[속보] FOMC 동결...연준 연내 인하 전망 유지",
                        "originallink": "https://major.example.com/article-2",
                        "link": "https://openapi.naver.com/l?major-2",
                        "description": "미국 증시와 국채 금리가 즉각 반응했다.",
                        "pubDate": "Thu, 19 Mar 2026 13:28:00 +0900",
                    },
                    {
                        "title": "[시장 따라잡기] 반도체 외 지수 반등 이끌 유망 종목은?",
                        "originallink": "https://mixed.example.com/article-3",
                        "link": "https://openapi.naver.com/l?mixed-3",
                        "description": "국내 증시에서 주목할 만한 종목을 정리했다.",
                        "pubDate": "Thu, 19 Mar 2026 13:31:00 +0900",
                    },
                ]
            },
        }
    )

    now = datetime(2026, 3, 19, 13, 39, tzinfo=KST)
    items = await provider.fetch(now)

    assert [item.title for item in items] == ["[속보] FOMC 동결...연준 연내 인하 전망 유지"]
    assert items[0].region == "global"
    assert items[0].source == "major.example.com"


@pytest.mark.asyncio
async def test_naver_news_provider_merges_multi_query_candidates_by_score():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {
                "items": [
                    {
                        "title": "코스피 장중 약세",
                        "originallink": "https://dup.example.com/article-1",
                        "link": "https://openapi.naver.com/l?dup-1",
                        "description": "국내 증시 약세",
                        "pubDate": "Thu, 19 Mar 2026 13:00:00 +0900",
                    }
                ]
            },
            "코스피": {
                "items": [
                    {
                        "title": "[속보] 코스피 급락, 외국인 매도 확대",
                        "originallink": "https://dup.example.com/article-1",
                        "link": "https://openapi.naver.com/l?dup-1",
                        "description": "코스피와 환율이 흔들린다.",
                        "pubDate": "Thu, 19 Mar 2026 13:00:00 +0900",
                    }
                ]
            },
            "미국 증시": {"items": []},
        },
        domestic_query=["국내 증시", "코스피"],
        limit_per_region=1,
    )

    now = datetime(2026, 3, 19, 13, 39, tzinfo=KST)
    items = await provider.fetch(now)

    assert len(items) == 1
    assert items[0].title == "[속보] 코스피 급락, 외국인 매도 확대"


@pytest.mark.asyncio
async def test_naver_news_provider_penalizes_low_signal_corporate_pr():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {
                "items": [
                    {
                        "title": "한미반도체, 지역경제 활성화 공로로 표창",
                        "originallink": "https://pr.example.com/article-1",
                        "link": "https://openapi.naver.com/l?pr-1",
                        "description": "반도체 기업 행사 소식",
                        "pubDate": "Thu, 19 Mar 2026 13:50:00 +0900",
                    },
                    {
                        "title": "[속보] 코스피 급락…외국인 1조 순매도",
                        "originallink": "https://market.example.com/article-2",
                        "link": "https://openapi.naver.com/l?market-2",
                        "description": "국내 증시와 환율이 흔들린다.",
                        "pubDate": "Thu, 19 Mar 2026 13:40:00 +0900",
                    },
                ]
            },
            "미국 증시": {"items": []},
        },
        limit_per_region=1,
    )

    now = datetime(2026, 3, 19, 13, 55, tzinfo=KST)
    items = await provider.fetch(now)

    assert len(items) == 1
    assert items[0].title == "[속보] 코스피 급락…외국인 1조 순매도"


@pytest.mark.asyncio
async def test_naver_news_provider_filters_single_stock_and_etf_headlines_without_macro_signal():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {
                "items": [
                    {
                        "title": "SK이터닉스 주가 25% 도약…5만원선 돌파",
                        "originallink": "https://stock.example.com/article-1",
                        "link": "https://openapi.naver.com/l?stock-1",
                        "description": "개별 종목 기사",
                        "pubDate": "Thu, 19 Mar 2026 13:34:00 +0900",
                    },
                    {
                        "title": "삼성 코스닥 액티브 ETF 선행매매 논란",
                        "originallink": "https://etf.example.com/article-2",
                        "link": "https://openapi.naver.com/l?etf-2",
                        "description": "ETF 기사",
                        "pubDate": "Thu, 19 Mar 2026 13:33:00 +0900",
                    },
                    {
                        "title": "환율 1500원 돌파에 긴장 고조…정부 즉각 대응",
                        "originallink": "https://macro.example.com/article-3",
                        "link": "https://openapi.naver.com/l?macro-3",
                        "description": "원달러 환율 급등",
                        "pubDate": "Thu, 19 Mar 2026 13:32:00 +0900",
                    },
                ]
            },
            "미국 증시": {"items": []},
        },
        limit_per_region=3,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    items = await provider.fetch(now)

    assert len(items) == 1
    assert items[0].title == "환율 1500원 돌파에 긴장 고조…정부 즉각 대응"


@pytest.mark.asyncio
async def test_naver_news_provider_keeps_only_one_domestic_market_drop_topic():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {
                "items": [
                    {
                        "title": "코스피 2%대 급락 출발…중동 긴장·금리 동결에 투심 흔들",
                        "originallink": "https://major.example.com/article-1",
                        "link": "https://openapi.naver.com/l?major-1",
                        "description": "코스피가 급락 출발했다.",
                        "pubDate": "Thu, 19 Mar 2026 13:36:00 +0900",
                    },
                    {
                        "title": "코스피, 외국인 매도에 2%대 하락",
                        "originallink": "https://other.example.com/article-2",
                        "link": "https://openapi.naver.com/l?other-2",
                        "description": "코스피 하락세",
                        "pubDate": "Thu, 19 Mar 2026 13:35:00 +0900",
                    },
                ]
            },
            "미국 증시": {"items": []},
        },
        limit_per_region=5,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    items = await provider.fetch(now)

    assert len(items) == 1
    assert "코스피" in items[0].title


@pytest.mark.asyncio
async def test_naver_news_provider_prefers_weighted_domestic_source_for_same_theme():
    provider = StubNaverNewsProvider(
        {
            "코스피": {
                "items": [
                    {
                        "title": "코스피 2%대 급락 출발…중동 긴장에 투심 흔들",
                        "originallink": "https://polinews.co.kr/article-1",
                        "link": "https://openapi.naver.com/l?polinews-1",
                        "description": "코스피 급락",
                        "pubDate": "Thu, 19 Mar 2026 13:39:00 +0900",
                    },
                    {
                        "title": "코스피 2%대 급락 출발…중동 긴장에 투심 흔들",
                        "originallink": "https://fnnews.com/article-2",
                        "link": "https://openapi.naver.com/l?fnnews-2",
                        "description": "코스피 급락",
                        "pubDate": "Thu, 19 Mar 2026 13:38:00 +0900",
                    },
                ]
            },
            "미국 증시": {"items": []},
        },
        domestic_query=["코스피"],
        limit_per_region=1,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    items = await provider.fetch(now)

    assert len(items) == 1
    assert items[0].source == "fnnews.com"


@pytest.mark.asyncio
async def test_naver_news_provider_keeps_partial_results_on_rate_limit_after_success():
    class RateLimitedProvider(StubNaverNewsProvider):
        def _request_json(self, query: str) -> dict:
            if query == "코스피":
                return {
                    "items": [
                        {
                            "title": "코스피 2%대 급락 출발",
                            "originallink": "https://fnnews.com/article-1",
                            "link": "https://openapi.naver.com/l?fnnews-1",
                            "description": "코스피 약세",
                            "pubDate": "Thu, 19 Mar 2026 13:36:00 +0900",
                        }
                    ]
                }
            raise RuntimeError("naver-news-rate-limited")

    provider = RateLimitedProvider(
        {},
        domestic_query=["코스피", "코스닥"],
        global_query=[],
        limit_per_region=3,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    items = await provider.fetch(now)

    assert len(items) == 1
    assert items[0].source == "fnnews.com"


@pytest.mark.asyncio
async def test_naver_news_provider_can_return_up_to_twenty_items_per_region():
    queries = [f"KRX지표{index}" for index in range(25)]
    provider = StubNaverNewsProvider(
        (
            {
                query: {
                    "items": [
                        {
                            "title": f"{query} 흐름 점검",
                            "originallink": f"https://source{index}.example.com/article-{index}",
                            "link": f"https://openapi.naver.com/l?source-{index}",
                            "description": f"{query} 뉴스 {index}",
                            "pubDate": "Thu, 19 Mar 2026 13:40:00 +0900",
                        }
                    ]
                }
                for index, query in enumerate(queries)
            }
            | {"미국 증시": {"items": []}}
        ),
        domestic_query=queries,
        limit_per_region=20,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    items = await provider.fetch(now)

    assert len(items) == 20
    assert all(item.region == "domestic" for item in items)


@pytest.mark.asyncio
async def test_naver_news_provider_preserves_score_order_over_recency():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {
                "items": [
                    {
                        "title": "환율 보합 출발",
                        "originallink": "https://example.com/article-1",
                        "link": "https://openapi.naver.com/l?article-1",
                        "description": "환율 보합",
                        "pubDate": "Thu, 19 Mar 2026 13:49:00 +0900",
                    },
                    {
                        "title": "[속보] 코스피 급락…환율 1500원 돌파",
                        "originallink": "https://example.com/article-2",
                        "link": "https://openapi.naver.com/l?article-2",
                        "description": "코스피와 환율 급등",
                        "pubDate": "Thu, 19 Mar 2026 13:42:00 +0900",
                    },
                ]
            },
            "미국 증시": {"items": []},
        },
        domestic_query=["국내 증시"],
        limit_per_region=2,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    items = await provider.fetch(now)

    assert [item.title for item in items] == ["[속보] 코스피 급락…환율 1500원 돌파", "환율 보합 출발"]


@pytest.mark.asyncio
async def test_naver_news_provider_keeps_high_impact_stock_headline_from_stock_query():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {"items": []},
            "미국 증시": {"items": []},
            "삼성전자": {
                "items": [
                    {
                        "title": "삼성전자, HBM 수주 확대에 매출 가이던스 상향",
                        "originallink": "https://newsis.com/article-1",
                        "link": "https://openapi.naver.com/l?newsis-1",
                        "description": "삼성전자가 HBM 계약 확대와 실적 가이던스 상향을 공개했다.",
                        "pubDate": "Thu, 19 Mar 2026 13:44:00 +0900",
                    }
                ]
            },
        },
        domestic_stock_query=["삼성전자"],
        limit_per_region=5,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    items = await provider.fetch(now)

    assert len(items) == 1
    assert items[0].title == "삼성전자, HBM 수주 확대에 매출 가이던스 상향"
    assert items[0].region == "domestic"


@pytest.mark.asyncio
async def test_naver_news_provider_reserves_one_slot_for_strong_stock_headline():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {
                "items": [
                    {
                        "title": "[속보] 코스피 급락…환율 1500원 돌파",
                        "originallink": "https://example.com/macro-1",
                        "link": "https://openapi.naver.com/l?macro-1",
                        "description": "코스피와 환율 급등",
                        "pubDate": "Thu, 19 Mar 2026 13:40:00 +0900",
                    },
                    {
                        "title": "유가 급등에 국고채 금리 상승",
                        "originallink": "https://example.com/macro-2",
                        "link": "https://openapi.naver.com/l?macro-2",
                        "description": "금리 상승",
                        "pubDate": "Thu, 19 Mar 2026 13:39:00 +0900",
                    },
                    {
                        "title": "코스닥 약세…외국인 매도 확대",
                        "originallink": "https://example.com/macro-3",
                        "link": "https://openapi.naver.com/l?macro-3",
                        "description": "코스닥 약세",
                        "pubDate": "Thu, 19 Mar 2026 13:38:00 +0900",
                    },
                    {
                        "title": "원/달러 환율 급등에 수입물가 부담",
                        "originallink": "https://example.com/macro-4",
                        "link": "https://openapi.naver.com/l?macro-4",
                        "description": "환율 부담",
                        "pubDate": "Thu, 19 Mar 2026 13:37:00 +0900",
                    },
                    {
                        "title": "공매도 재개 앞두고 증시 경계감",
                        "originallink": "https://example.com/macro-5",
                        "link": "https://openapi.naver.com/l?macro-5",
                        "description": "공매도 이슈",
                        "pubDate": "Thu, 19 Mar 2026 13:36:00 +0900",
                    },
                ]
            },
            "삼성전자": {
                "items": [
                    {
                        "title": "삼성전자, HBM 대형 수주 확보…매출 가이던스 상향",
                        "originallink": "https://example.com/stock-1",
                        "link": "https://openapi.naver.com/l?stock-1",
                        "description": "삼성전자 실적 개선",
                        "pubDate": "Thu, 19 Mar 2026 13:35:00 +0900",
                    }
                ]
            },
            "미국 증시": {"items": []},
        },
        domestic_query=["국내 증시"],
        domestic_stock_query=["삼성전자"],
        limit_per_region=5,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    items = await provider.fetch(now)

    assert len(items) >= 2
    assert any(item.title == "삼성전자, HBM 대형 수주 확보…매출 가이던스 상향" for item in items)


@pytest.mark.asyncio
async def test_naver_news_provider_filters_promotional_market_service_headlines():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {"items": []},
            "미국 증시": {
                "items": [
                    {
                        "title": "두나무 증권플러스, 미국 주식 실시간 시세 전 회원 무료 제공",
                        "originallink": "https://hankyung.com/article-1",
                        "link": "https://openapi.naver.com/l?hankyung-1",
                        "description": "미국 주식 실시간 시세를 무료 제공한다.",
                        "pubDate": "Thu, 19 Mar 2026 13:44:00 +0900",
                    },
                    {
                        "title": "연준 \"인플레 진전 없인 인하 없다\"…고유가 충격 확산",
                        "originallink": "https://biz.sbs.co.kr/article-2",
                        "link": "https://openapi.naver.com/l?sbs-2",
                        "description": "미국 증시와 국채 금리가 반응했다.",
                        "pubDate": "Thu, 19 Mar 2026 13:43:00 +0900",
                    },
                ]
            },
        },
        limit_per_region=5,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    items = await provider.fetch(now)

    assert [item.title for item in items] == ["연준 \"인플레 진전 없인 인하 없다\"…고유가 충격 확산"]
    assert items[0].region == "global"


@pytest.mark.asyncio
async def test_naver_news_provider_maps_auth_failures(monkeypatch):
    provider = NaverNewsProvider(
        client_id="client-id",
        client_secret="client-secret",
        domestic_query="국내 증시",
        global_query="미국 증시",
        retry_count=0,
    )

    def fail_urlopen(request, timeout):
        raise HTTPError(request.full_url, 403, "Forbidden", hdrs=None, fp=None)

    monkeypatch.setattr(news_module, "urlopen", fail_urlopen)

    with pytest.raises(RuntimeError, match="naver-news-auth-failed:403"):
        await provider.fetch(datetime(2026, 3, 18, 7, 30, tzinfo=KST))


@pytest.mark.asyncio
async def test_naver_news_provider_analyze_builds_trend_report_from_probe_queries_only():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {"items": []},
            "미국 증시": {"items": []},
            "반도체 수주": {
                "items": [
                    {
                        "title": "반도체 업황 회복에 코스피 강세…삼성전자·SK하이닉스 동반 상승",
                        "originallink": "https://fnnews.com/article-semi-1",
                        "link": "https://openapi.naver.com/l?semi-1",
                        "description": "반도체 업황 개선과 수급 회복",
                        "pubDate": "Thu, 19 Mar 2026 13:40:00 +0900",
                    },
                    {
                        "title": "삼성전자, HBM 대형 수주 확보…매출 가이던스 상향",
                        "originallink": "https://newsis.com/article-semi-2",
                        "link": "https://openapi.naver.com/l?semi-2",
                        "description": "HBM 수주와 가이던스 상향",
                        "pubDate": "Thu, 19 Mar 2026 13:35:00 +0900",
                    },
                ]
            },
            "원전 건설 수주": {
                "items": [
                    {
                        "title": "원전 수주 기대에 건설·플랜트주 강세",
                        "originallink": "https://yna.co.kr/article-nuke-1",
                        "link": "https://openapi.naver.com/l?nuke-1",
                        "description": "원전과 건설 수주 기대",
                        "pubDate": "Thu, 19 Mar 2026 13:39:00 +0900",
                    },
                    {
                        "title": "두산에너빌리티, SMR 핵심 기자재 공급 계약",
                        "originallink": "https://mk.co.kr/article-nuke-2",
                        "link": "https://openapi.naver.com/l?nuke-2",
                        "description": "SMR 공급 계약 체결",
                        "pubDate": "Thu, 19 Mar 2026 13:34:00 +0900",
                    },
                ]
            },
            "전력설비 전력망": {
                "items": [
                    {
                        "title": "전력망 투자 확대에 전력설비주 강세",
                        "originallink": "https://hankyung.com/article-power-1",
                        "link": "https://openapi.naver.com/l?power-1",
                        "description": "전력망과 변압기 투자 확대",
                        "pubDate": "Thu, 19 Mar 2026 13:38:00 +0900",
                    },
                    {
                        "title": "LS ELECTRIC, 북미 데이터센터 전력설비 수주",
                        "originallink": "https://sedaily.com/article-power-2",
                        "link": "https://openapi.naver.com/l?power-2",
                        "description": "전력설비 계약",
                        "pubDate": "Thu, 19 Mar 2026 13:33:00 +0900",
                    },
                ]
            },
        },
        limit_per_region=5,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    analysis = await provider.analyze(now)

    assert list(analysis.briefing_items) == []
    domestic_names = [theme.theme_name for theme in analysis.trend_report.for_region("domestic")]
    assert domestic_names[0] == "반도체"
    assert {"반도체", "건설/원전", "전력설비"}.issubset(domestic_names)
    assert all(len(theme.representative_items) == 2 for theme in analysis.trend_report.for_region("domestic"))


@pytest.mark.asyncio
async def test_naver_news_provider_analyze_filters_noisy_theme_and_limits_extra_theme_slots():
    provider = StubNaverNewsProvider(
        {
            "국내 증시": {"items": []},
            "미국 증시": {"items": []},
            "반도체 수주": {
                "items": [
                    {
                        "title": "반도체 업황 회복에 코스피 강세",
                        "originallink": "https://fnnews.com/article-1",
                        "link": "https://openapi.naver.com/l?semi-a",
                        "description": "반도체 업황 개선",
                        "pubDate": "Thu, 19 Mar 2026 13:40:00 +0900",
                    },
                    {
                        "title": "SK하이닉스, HBM 공급 계약 확대",
                        "originallink": "https://newsis.com/article-2",
                        "link": "https://openapi.naver.com/l?semi-b",
                        "description": "HBM 공급 확대",
                        "pubDate": "Thu, 19 Mar 2026 13:35:00 +0900",
                    },
                ]
            },
            "원전 건설 수주": {
                "items": [
                    {
                        "title": "원전 수주 기대에 건설주 강세",
                        "originallink": "https://yna.co.kr/article-3",
                        "link": "https://openapi.naver.com/l?nuke-a",
                        "description": "원전과 건설 수주",
                        "pubDate": "Thu, 19 Mar 2026 13:39:00 +0900",
                    },
                    {
                        "title": "현대건설, 원전 플랜트 수주전 본격화",
                        "originallink": "https://mk.co.kr/article-4",
                        "link": "https://openapi.naver.com/l?nuke-b",
                        "description": "원전 플랜트 수주전",
                        "pubDate": "Thu, 19 Mar 2026 13:34:00 +0900",
                    },
                ]
            },
            "전력설비 전력망": {
                "items": [
                    {
                        "title": "전력설비 투자 확대 기대에 전력기기 강세",
                        "originallink": "https://hankyung.com/article-5",
                        "link": "https://openapi.naver.com/l?power-a",
                        "description": "전력망 투자 확대",
                        "pubDate": "Thu, 19 Mar 2026 13:38:00 +0900",
                    },
                    {
                        "title": "효성중공업, 초고압 변압기 공급 계약",
                        "originallink": "https://sedaily.com/article-6",
                        "link": "https://openapi.naver.com/l?power-b",
                        "description": "전력설비 공급 계약",
                        "pubDate": "Thu, 19 Mar 2026 13:33:00 +0900",
                    },
                ]
            },
            "방산 수주": {
                "items": [
                    {
                        "title": "방산 수출 기대에 국방주 강세",
                        "originallink": "https://biz.chosun.com/article-7",
                        "link": "https://openapi.naver.com/l?defense-a",
                        "description": "방산 수주 기대",
                        "pubDate": "Thu, 19 Mar 2026 13:32:00 +0900",
                    },
                    {
                        "title": "한화에어로스페이스, 미사일 엔진 공급 계약",
                        "originallink": "https://edaily.co.kr/article-8",
                        "link": "https://openapi.naver.com/l?defense-b",
                        "description": "방산 계약",
                        "pubDate": "Thu, 19 Mar 2026 13:31:00 +0900",
                    },
                ]
            },
            "바이오 임상": {
                "items": [
                    {
                        "title": "[특징주] 바이오 관련주 급등, 지금 사야 할 종목은",
                        "originallink": "https://noise.example.com/article-9",
                        "link": "https://openapi.naver.com/l?bio-a",
                        "description": "특징주 기사",
                        "pubDate": "Thu, 19 Mar 2026 13:37:00 +0900",
                    },
                    {
                        "title": "[칼럼] 바이오 투자, 지금이 기회인가",
                        "originallink": "https://noise.example.com/article-10",
                        "link": "https://openapi.naver.com/l?bio-b",
                        "description": "칼럼 기사",
                        "pubDate": "Thu, 19 Mar 2026 13:36:00 +0900",
                    },
                ]
            },
        },
        limit_per_region=5,
    )

    now = datetime(2026, 3, 19, 13, 50, tzinfo=KST)
    analysis = await provider.analyze(now)

    domestic_names = [theme.theme_name for theme in analysis.trend_report.for_region("domestic")]
    assert "바이오" not in domestic_names
    assert {"반도체", "건설/원전", "전력설비", "방산"}.issubset(domestic_names)
