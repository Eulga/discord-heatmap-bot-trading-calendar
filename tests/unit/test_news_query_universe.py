from bot.features import intel_scheduler
from bot.intel.instrument_registry import InstrumentRecord, ProviderIds
from bot.intel.providers.market import NewsRankingInstrument


def _record(
    canonical_symbol: str,
    *,
    market_code: str,
    ticker_or_code: str,
    display_name_ko: str = "",
    display_name_en: str = "",
) -> InstrumentRecord:
    return InstrumentRecord(
        canonical_symbol=canonical_symbol,
        market_code=market_code,
        ticker_or_code=ticker_or_code,
        display_name_ko=display_name_ko,
        display_name_en=display_name_en,
        aliases=(canonical_symbol, ticker_or_code),
        provider_ids=ProviderIds(kis_exchange_code=market_code),
        source="test",
    )


def _ranked(
    canonical_symbol: str,
    *,
    market_code: str,
    ticker_or_code: str,
    display_name_ko: str = "",
    display_name_en: str = "",
    source: str = "rank",
) -> NewsRankingInstrument:
    return NewsRankingInstrument(
        canonical_symbol=canonical_symbol,
        market_code=market_code,
        ticker_or_code=ticker_or_code,
        display_name_ko=display_name_ko,
        display_name_en=display_name_en,
        source=source,
        raw_payload={"symbol": canonical_symbol},
    )


def test_news_query_universe_builder_merges_rankings_and_watchlist_by_symbol():
    universe = intel_scheduler._build_news_query_universe_from_sources(
        domestic_ranked=[
            _ranked("KRX:005930", market_code="KRX", ticker_or_code="005930", display_name_ko="삼성전자"),
            _ranked("KRX:000660", market_code="KRX", ticker_or_code="000660", display_name_ko="SK하이닉스"),
        ],
        global_ranked=[
            _ranked("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", display_name_en="Apple"),
            _ranked("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", display_name_en="Apple duplicate"),
        ],
        watch_records=[
            _record("KRX:005930", market_code="KRX", ticker_or_code="005930", display_name_ko="삼성전자"),
            _record("NYS:IBM", market_code="NYS", ticker_or_code="IBM", display_name_en="IBM"),
        ],
        include_overseas=True,
    )

    assert universe.domestic_stock_queries == ("삼성전자", "SK하이닉스")
    assert universe.global_stock_queries == ("Apple OR AAPL", "IBM")
