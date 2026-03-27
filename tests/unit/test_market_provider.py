from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

import pytest
import json

from bot.intel.instrument_registry import InstrumentRecord, InstrumentRegistry, ProviderIds
from bot.intel.providers import market as market_provider

KST = ZoneInfo("Asia/Seoul")


def _registry(*records: InstrumentRecord) -> InstrumentRegistry:
    return InstrumentRegistry(generated_at="2026-03-23T00:00:00+00:00", records=records)


def _record(
    canonical_symbol: str,
    *,
    market_code: str,
    ticker_or_code: str,
    kis_exchange_code: str,
) -> InstrumentRecord:
    return InstrumentRecord(
        canonical_symbol=canonical_symbol,
        market_code=market_code,
        ticker_or_code=ticker_or_code,
        display_name_ko="",
        display_name_en=ticker_or_code,
        aliases=(canonical_symbol, ticker_or_code),
        provider_ids=ProviderIds(kis_exchange_code=kis_exchange_code),
        source="test",
    )


@pytest.mark.asyncio
async def test_error_market_data_provider_raises_message():
    provider = market_provider.ErrorMarketDataProvider("kis-credentials-missing")

    with pytest.raises(RuntimeError, match="kis-credentials-missing"):
        await provider.get_quote("KRX:005930", datetime(2026, 3, 23, 10, 0, tzinfo=KST))


@pytest.mark.asyncio
async def test_kis_provider_requests_domestic_quote_for_krx_symbol(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    calls: list[dict] = []

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("KRX:005930", market_code="KRX", ticker_or_code="005930", kis_exchange_code="KRX")),
    )

    async def fake_request_kis_json(**kwargs):
        calls.append(kwargs)
        return {"rt_cd": "0", "output": {"stck_prpr": "73100", "stck_sdpr": "70900"}}

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    quote = await provider.get_quote("KRX:005930", now)

    assert quote.symbol == "KRX:005930"
    assert quote.price == 73100.0
    assert quote.asof == now
    assert calls == [
        {
            "path": "/uapi/domestic-stock/v1/quotations/inquire-price",
            "tr_id": "FHKST01010100",
            "params": {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": "005930",
            },
            "fallback_symbol": "KRX:005930",
        }
    ]


@pytest.mark.asyncio
async def test_kis_provider_marks_domestic_snapshot_stale_when_provider_time_is_old(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("KRX:005930", market_code="KRX", ticker_or_code="005930", kis_exchange_code="KRX")),
    )

    async def fake_request_kis_json(**kwargs):
        return {
            "rt_cd": "0",
            "output": {
                "stck_prpr": "73100",
                "stck_sdpr": "70900",
                "stck_bsop_date": "20260323",
                "stck_cntg_hour": "095500",
            },
        }

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    with pytest.raises(market_provider.MarketDataProviderError, match="stale-quote:KRX:005930"):
        await provider.get_watch_snapshot("KRX:005930", now)


@pytest.mark.asyncio
async def test_kis_provider_allows_post_close_domestic_snapshot_with_last_trade_time(monkeypatch):
    now = datetime(2026, 3, 24, 8, 55, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("KRX:005930", market_code="KRX", ticker_or_code="005930", kis_exchange_code="KRX")),
    )

    async def fake_request_kis_json(**kwargs):
        return {
            "rt_cd": "0",
            "output": {
                "stck_prpr": "73100",
                "stck_sdpr": "70900",
                "stck_clpr": "73100",
                "stck_bsop_date": "20260323",
                "stck_cntg_hour": "153000",
            },
        }

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    snapshot = await provider.get_watch_snapshot("KRX:005930", now)

    assert snapshot.symbol == "KRX:005930"
    assert snapshot.session_date == "2026-03-23"
    assert snapshot.session_close_price == 73100.0


@pytest.mark.asyncio
async def test_watch_snapshot_fresh_allows_post_close_us_snapshot(monkeypatch):
    now = datetime(2026, 3, 24, 9, 10, tzinfo=KST)
    snapshot = market_provider.WatchSnapshot(
        symbol="NAS:AAPL",
        current_price=214.37,
        previous_close=208.52,
        session_close_price=214.37,
        asof=datetime(2026, 3, 24, 9, 0, tzinfo=KST),
        session_date="2026-03-23",
        provider="massive_reference",
    )

    market_provider._ensure_watch_snapshot_fresh(snapshot, now)


@pytest.mark.asyncio
async def test_kis_provider_requests_overseas_quote_for_us_symbol(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    calls: list[dict] = []

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", kis_exchange_code="NAS")),
    )

    async def fake_request_kis_json(**kwargs):
        calls.append(kwargs)
        return {"rt_cd": "0", "output": {"last": "214.37", "base": "208.52"}}

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    quote = await provider.get_quote("NAS:AAPL", now)

    assert quote.symbol == "NAS:AAPL"
    assert quote.price == 214.37
    assert calls == [
        {
            "path": "/uapi/overseas-price/v1/quotations/price",
            "tr_id": "HHDFS00000300",
            "params": {
                "AUTH": "",
                "EXCD": "NAS",
                "SYMB": "AAPL",
            },
            "fallback_symbol": "NAS:AAPL",
        }
    ]


@pytest.mark.asyncio
async def test_kis_provider_retries_nys_symbol_on_ams_when_primary_exchange_returns_empty_quote(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    calls: list[dict] = []

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NYS:UCO", market_code="NYS", ticker_or_code="UCO", kis_exchange_code="NYS")),
    )

    async def fake_request_kis_json(**kwargs):
        calls.append(kwargs)
        if kwargs["params"]["EXCD"] == "NYS":
            return {"rt_cd": "0", "output": {"last": ""}}
        return {"rt_cd": "0", "output": {"last": "40.10", "base": "41.00"}}

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    quote = await provider.get_quote("NYS:UCO", now)

    assert quote.symbol == "NYS:UCO"
    assert quote.price == 40.10
    assert calls == [
        {
            "path": "/uapi/overseas-price/v1/quotations/price",
            "tr_id": "HHDFS00000300",
            "params": {
                "AUTH": "",
                "EXCD": "NYS",
                "SYMB": "UCO",
            },
            "fallback_symbol": "NYS:UCO",
        },
        {
            "path": "/uapi/overseas-price/v1/quotations/price",
            "tr_id": "HHDFS00000300",
            "params": {
                "AUTH": "",
                "EXCD": "AMS",
                "SYMB": "UCO",
            },
            "fallback_symbol": "NYS:UCO",
        },
    ]


@pytest.mark.asyncio
async def test_kis_provider_retries_nys_symbol_on_ams_when_primary_exchange_returns_not_found(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    calls: list[dict] = []

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NYS:UCO", market_code="NYS", ticker_or_code="UCO", kis_exchange_code="NYS")),
    )

    async def fake_request_kis_json(**kwargs):
        calls.append(kwargs)
        if kwargs["params"]["EXCD"] == "NYS":
            raise RuntimeError("not-found:NYS:UCO")
        return {"rt_cd": "0", "output": {"last": "40.10", "base": "41.00"}}

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    quote = await provider.get_quote("NYS:UCO", now)

    assert quote.symbol == "NYS:UCO"
    assert quote.price == 40.10
    assert [call["params"]["EXCD"] for call in calls] == ["NYS", "AMS"]


@pytest.mark.asyncio
async def test_kis_provider_reuses_token_until_refresh_window(monkeypatch):
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    issued: list[str] = []

    def fake_issue_access_token_sync():
        token = f"token-{len(issued) + 1}"
        issued.append(token)
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
        }

    monkeypatch.setattr(provider, "_issue_access_token_sync", fake_issue_access_token_sync)

    first = await provider._get_access_token()
    second = await provider._get_access_token()
    provider._token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    third = await provider._get_access_token()

    assert first == "Bearer token-1"
    assert second == "Bearer token-1"
    assert third == "Bearer token-2"
    assert issued == ["token-1", "token-2"]


@pytest.mark.asyncio
async def test_kis_provider_refreshes_and_retries_after_auth_failure(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    token_issues = {"count": 0}
    request_tokens: list[str] = []

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", kis_exchange_code="NAS")),
    )

    def fake_issue_access_token_sync():
        token_issues["count"] += 1
        return {
            "access_token": f"token-{token_issues['count']}",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

    def fake_request_json_sync(*, token_header: str, **kwargs):
        request_tokens.append(token_header)
        if len(request_tokens) == 1:
            raise RuntimeError("kis-auth-failed")
        return {"rt_cd": "0", "output": {"last": "214.37", "base": "208.52"}}

    monkeypatch.setattr(provider, "_issue_access_token_sync", fake_issue_access_token_sync)
    monkeypatch.setattr(provider, "_request_json_sync", fake_request_json_sync)

    quote = await provider.get_quote("NAS:AAPL", now)

    assert quote.price == 214.37
    assert token_issues["count"] == 2
    assert request_tokens == ["Bearer token-1", "Bearer token-2"]


@pytest.mark.asyncio
async def test_kis_provider_falls_back_to_single_quote_after_stale_batch_quote(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    calls: list[str] = []

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", kis_exchange_code="NAS")),
    )

    async def fake_request_kis_json(**kwargs):
        calls.append(kwargs["path"])
        if kwargs["path"].endswith("/multprice"):
            return {
                "rt_cd": "0",
                "output2": [
                    {
                        "excd": "NAS",
                        "symb": "AAPL",
                        "last": "214.37",
                        "base": "208.52",
                        "khms": "095500",
                    }
                ],
            }
        return {"rt_cd": "0", "output": {"last": "214.37", "base": "208.52", "khms": "100000"}}

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    await provider.warm_quotes(["NAS:AAPL"], now)
    quote = await provider.get_quote("NAS:AAPL", now)

    assert quote.price == 214.37
    assert calls == [
        "/uapi/overseas-price/v1/quotations/multprice",
        "/uapi/overseas-price/v1/quotations/price",
    ]


@pytest.mark.asyncio
async def test_kis_provider_warm_quotes_dedupes_duplicate_symbols(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    calls: list[dict] = []

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", kis_exchange_code="NAS")),
    )

    async def fake_request_kis_json(**kwargs):
        calls.append(kwargs)
        return {
            "rt_cd": "0",
            "output2": [
                {
                    "excd": "NAS",
                    "symb": "AAPL",
                    "last": "214.37",
                    "base": "208.52",
                    "khms": "100000",
                }
            ],
        }

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    await provider.warm_quotes(["NAS:AAPL", "NAS:AAPL"], now)
    first = await provider.get_quote("NAS:AAPL", now)
    second = await provider.get_quote("NAS:AAPL", now)

    assert first.price == 214.37
    assert second.price == 214.37
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_kis_provider_falls_back_to_single_quote_after_batch_warm_failure(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", kis_exchange_code="NAS")),
    )

    async def fake_request_kis_json(**kwargs):
        path = kwargs["path"]
        calls.append((path, kwargs["tr_id"]))
        if path.endswith("/multprice"):
            raise RuntimeError("kis-unreachable")
        return {"rt_cd": "0", "output": {"last": "214.37", "base": "208.52", "khms": "100000"}}

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    await provider.warm_quotes(["NAS:AAPL"], now)
    quote = await provider.get_quote("NAS:AAPL", now)

    assert quote.price == 214.37
    assert calls == [
        ("/uapi/overseas-price/v1/quotations/multprice", "HHDFS76220000"),
        ("/uapi/overseas-price/v1/quotations/price", "HHDFS00000300"),
    ]


@pytest.mark.asyncio
async def test_kis_provider_falls_back_to_single_quote_after_batch_row_omission(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", kis_exchange_code="NAS")),
    )

    async def fake_request_kis_json(**kwargs):
        path = kwargs["path"]
        calls.append((path, kwargs["tr_id"]))
        if path.endswith("/multprice"):
            return {"rt_cd": "0", "output2": []}
        return {"rt_cd": "0", "output": {"last": "214.37", "base": "208.52", "khms": "100000"}}

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    await provider.warm_quotes(["NAS:AAPL"], now)
    quote = await provider.get_quote("NAS:AAPL", now)

    assert quote.price == 214.37
    assert calls == [
        ("/uapi/overseas-price/v1/quotations/multprice", "HHDFS76220000"),
        ("/uapi/overseas-price/v1/quotations/price", "HHDFS00000300"),
    ]


@pytest.mark.asyncio
async def test_kis_provider_falls_back_to_single_quote_after_domestic_warm_failure(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    calls: list[str] = []

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("KRX:005930", market_code="KRX", ticker_or_code="005930", kis_exchange_code="KRX")),
    )

    async def fake_request_kis_json(**kwargs):
        calls.append(kwargs["path"])
        if len(calls) == 1:
            raise RuntimeError("kis-unreachable")
        return {"rt_cd": "0", "output": {"stck_prpr": "73100", "stck_sdpr": "70900"}}

    monkeypatch.setattr(provider, "_request_kis_json", fake_request_kis_json)

    await provider.warm_quotes(["KRX:005930"], now)
    quote = await provider.get_quote("KRX:005930", now)

    assert quote.price == 73100.0
    assert calls == [
        "/uapi/domestic-stock/v1/quotations/inquire-price",
        "/uapi/domestic-stock/v1/quotations/inquire-price",
    ]


@pytest.mark.asyncio
async def test_kis_provider_raises_not_found_when_registry_record_missing(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")

    monkeypatch.setattr(market_provider, "load_registry", lambda: _registry())

    with pytest.raises(RuntimeError, match="not-found:KRX:005930"):
        await provider.get_quote("KRX:005930", now)


@pytest.mark.asyncio
async def test_kis_provider_raises_unsupported_market_when_kis_exchange_is_invalid(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", kis_exchange_code="LON")),
    )

    with pytest.raises(RuntimeError, match="unsupported-market:NAS:AAPL"):
        await provider.get_quote("NAS:AAPL", now)


def test_kis_request_json_maps_rate_limit(monkeypatch):
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")

    def fake_urlopen(request, timeout):
        raise HTTPError(url=request.full_url, code=429, msg="Too Many Requests", hdrs=None, fp=None)

    monkeypatch.setattr(market_provider, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="kis-rate-limited"):
        provider._request_json_sync(
            path="/uapi/overseas-price/v1/quotations/price",
            tr_id="HHDFS00000300",
            token_header="Bearer token",
            params={"AUTH": "", "EXCD": "NAS", "SYMB": "AAPL"},
        )


def test_kis_request_json_maps_token_issue_limit_403_to_rate_limit(monkeypatch):
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")

    class _ErrorBody:
        def read(self):
            return json.dumps(
                {
                    "error_code": "EGW00133",
                    "error_description": "접근토큰 발급 잠시 후 다시 시도하세요(1분당 1회)",
                },
                ensure_ascii=False,
            ).encode("utf-8")

        def close(self):
            return None

    def fake_urlopen(request, timeout):
        raise HTTPError(
            url=request.full_url,
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=_ErrorBody(),
        )

    monkeypatch.setattr(market_provider, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="kis-rate-limited"):
        provider._request_json_sync(
            path="/oauth2/tokenP",
            tr_id="",
            token_header="",
            body={"grant_type": "client_credentials"},
            method="POST",
        )


def test_kis_request_json_maps_network_failure(monkeypatch):
    provider = market_provider.KisMarketDataProvider(app_key="key", app_secret="secret")
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        raise URLError("network down")

    monkeypatch.setattr(market_provider, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="kis-unreachable"):
        provider._request_json_sync(
            path="/uapi/overseas-price/v1/quotations/price",
            tr_id="HHDFS00000300",
            token_header="Bearer token",
            params={"AUTH": "", "EXCD": "NAS", "SYMB": "AAPL"},
        )

    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_massive_provider_uses_live_trade_price_for_us_symbol(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc)
    provider = market_provider.MassiveSnapshotMarketDataProvider(api_key="key")

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", kis_exchange_code="NAS")),
    )

    def fake_request_json(ticker: str, *, fallback_symbol: str):
        return {
            "status": "OK",
            "ticker": {
                "lastTrade": {
                    "p": "214.37",
                    "t": str(int(now.timestamp() * 1_000_000_000)),
                },
                "prevDay": {"c": "208.52"},
            },
        }

    monkeypatch.setattr(provider, "_request_json", fake_request_json)

    quote = await provider.get_quote("NAS:AAPL", now)

    assert quote.symbol == "NAS:AAPL"
    assert quote.price == 214.37
    assert quote.provider == "massive_reference"


@pytest.mark.asyncio
async def test_routed_provider_falls_back_to_massive_for_us_symbols(monkeypatch):
    now = datetime(2026, 3, 23, 10, 0, tzinfo=KST)

    class FailingPrimary:
        async def get_quote(self, symbol: str, now: datetime):
            raise market_provider.MarketDataProviderError("kis-unreachable", provider_key="kis_quote")

    class MassiveFallback:
        async def get_quote(self, symbol: str, now: datetime):
            return market_provider.Quote(
                symbol=symbol,
                price=215.0,
                asof=now,
                provider="massive_reference",
            )

    monkeypatch.setattr(
        market_provider,
        "load_registry",
        lambda: _registry(_record("NAS:AAPL", market_code="NAS", ticker_or_code="AAPL", kis_exchange_code="NAS")),
    )

    provider = market_provider.RoutedMarketDataProvider(
        primary_provider=FailingPrimary(),
        us_fallback_provider=MassiveFallback(),
    )

    quote = await provider.get_quote("NAS:AAPL", now)

    assert quote.provider == "massive_reference"
    assert quote.price == 215.0
