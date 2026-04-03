from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha1
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from bot.features.watch.session import get_watch_market_session
from bot.intel.instrument_registry import InstrumentRecord, load_registry, normalize_stored_watch_symbol

_DEFAULT_KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
_DEFAULT_HEADERS = {
    "content-type": "application/json; charset=utf-8",
    "custtype": "P",
    "User-Agent": "discord-heatmap-bot/1.0",
}
_TOKEN_REFRESH_MARGIN = timedelta(minutes=5)
_QUOTE_STALE_AFTER = timedelta(minutes=2)
_KOREA_TZ = ZoneInfo("Asia/Seoul")
_DOMESTIC_MARKET_DIV_CODES = {
    "KRX": "J",
    "NX": "NX",
    "UN": "UN",
}
_OVERSEAS_EXCHANGE_CODES = {
    "NAS": "NAS",
    "NYS": "NYS",
    "AMS": "AMS",
    "BAQ": "BAQ",
    "BAY": "BAY",
    "BAA": "BAA",
}
_OVERSEAS_EXCHANGE_ALIASES = {
    "NYS": ("AMS",),
    "AMS": ("NYS",),
}


@dataclass
class Quote:
    symbol: str
    price: float
    asof: datetime
    provider: str = ""


@dataclass
class WatchSnapshot:
    symbol: str
    current_price: float
    previous_close: float
    session_close_price: float | None
    asof: datetime
    session_date: str
    provider: str = ""


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


@dataclass(frozen=True)
class _ResolvedSymbol:
    canonical_symbol: str
    market_code: str
    ticker_or_code: str
    kis_exchange_code: str


class MarketDataProvider(Protocol):
    async def get_watch_snapshot(self, symbol: str, now: datetime) -> WatchSnapshot: ...

    async def warm_watch_snapshots(self, symbols: list[str], now: datetime) -> None: ...


class EodSummaryProvider(Protocol):
    async def get_summary(self, now: datetime) -> EodSummary: ...


class MarketDataProviderError(RuntimeError):
    def __init__(self, message: str, *, provider_key: str = "market_data_provider") -> None:
        super().__init__(message)
        self.provider_key = provider_key


class MockMarketDataProvider:
    async def get_watch_snapshot(self, symbol: str, now: datetime) -> WatchSnapshot:
        token = sha1(f"{symbol}|{now.strftime('%Y%m%d%H%M')}".encode("utf-8")).hexdigest()
        seed = int(token[:8], 16)
        base = 10000 + (seed % 90000)
        noise = ((seed >> 8) % 500) / 100
        current_price = base + noise
        previous_close = max(1.0, current_price * 0.97)
        session = get_watch_market_session(symbol.upper(), now)
        session_close_price = None if session.is_regular_session_open else current_price
        return WatchSnapshot(
            symbol=symbol.upper(),
            current_price=current_price,
            previous_close=previous_close,
            session_close_price=session_close_price,
            asof=now,
            session_date=session.session_date,
            provider="mock",
        )

    async def warm_watch_snapshots(self, symbols: list[str], now: datetime) -> None:
        return None

    async def warm_quotes(self, symbols: list[str], now: datetime) -> None:
        await self.warm_watch_snapshots(symbols, now)

    async def get_quote(self, symbol: str, now: datetime) -> Quote:
        snapshot = await self.get_watch_snapshot(symbol, now)
        return Quote(symbol=snapshot.symbol, price=snapshot.current_price, asof=snapshot.asof, provider=snapshot.provider)


class ErrorMarketDataProvider:
    def __init__(self, message: str, *, provider_key: str = "market_data_provider") -> None:
        self._message = message
        self.provider_key = provider_key

    async def get_watch_snapshot(self, symbol: str, now: datetime) -> WatchSnapshot:
        raise MarketDataProviderError(self._message, provider_key=self.provider_key)

    async def warm_watch_snapshots(self, symbols: list[str], now: datetime) -> None:
        return None

    async def warm_quotes(self, symbols: list[str], now: datetime) -> None:
        await self.warm_watch_snapshots(symbols, now)

    async def get_quote(self, symbol: str, now: datetime) -> Quote:
        raise MarketDataProviderError(self._message, provider_key=self.provider_key)


class KisMarketDataProvider:
    def __init__(
        self,
        *,
        app_key: str,
        app_secret: str,
        timeout_seconds: int = 5,
        retry_count: int = 1,
        base_url: str = _DEFAULT_KIS_BASE_URL,
    ) -> None:
        self.app_key = app_key.strip()
        self.app_secret = app_secret.strip()
        self.timeout_seconds = max(1, min(timeout_seconds, 10))
        self.retry_count = max(0, min(retry_count, 1))
        self.base_url = base_url.rstrip("/")
        self.provider_key = "kis_quote"
        self._token_header = ""
        self._token_expires_at: datetime | None = None
        self._token_lock = asyncio.Lock()
        self._poll_cache_key = ""
        self._snapshot_cache: dict[str, WatchSnapshot] = {}
        self._snapshot_errors: dict[str, str] = {}

    async def warm_watch_snapshots(self, symbols: list[str], now: datetime) -> None:
        self._reset_poll_cache(now)
        pending: dict[str, _ResolvedSymbol] = {}

        for symbol in symbols:
            normalized, _warning = normalize_stored_watch_symbol(symbol, registry=load_registry())
            cache_key = normalized or symbol.strip().upper()
            if (
                not cache_key
                or cache_key in self._snapshot_cache
                or cache_key in self._snapshot_errors
                or cache_key in pending
            ):
                continue
            try:
                resolved = self._resolve_symbol(symbol)
            except RuntimeError as exc:
                self._snapshot_errors[cache_key] = str(exc)
                continue
            pending[resolved.canonical_symbol] = resolved

        domestic = [item for item in pending.values() if item.market_code == "KRX"]
        overseas: dict[str, list[_ResolvedSymbol]] = {}
        for item in pending.values():
            if item.market_code == "KRX":
                continue
            overseas.setdefault(item.kis_exchange_code, []).append(item)

        if domestic:
            await asyncio.gather(*(self._warm_fetch_and_store(item, now) for item in domestic))

        for items in overseas.values():
            for chunk in _chunk(items, 10):
                await self._warm_overseas_chunk(chunk, now)

    async def get_watch_snapshot(self, symbol: str, now: datetime) -> WatchSnapshot:
        self._reset_poll_cache(now)
        resolved = self._resolve_symbol(symbol)
        cached = self._snapshot_cache.get(resolved.canonical_symbol)
        if cached is not None:
            return cached
        cached_error = self._snapshot_errors.get(resolved.canonical_symbol)
        if cached_error:
            raise MarketDataProviderError(cached_error, provider_key=self.provider_key)
        return await self._fetch_and_store(resolved, now)

    async def get_quote(self, symbol: str, now: datetime) -> Quote:
        snapshot = await self.get_watch_snapshot(symbol, now)
        return Quote(symbol=snapshot.symbol, price=snapshot.current_price, asof=snapshot.asof, provider=snapshot.provider)

    async def warm_quotes(self, symbols: list[str], now: datetime) -> None:
        await self.warm_watch_snapshots(symbols, now)

    async def _fetch_and_store(self, resolved: _ResolvedSymbol, now: datetime) -> WatchSnapshot:
        try:
            snapshot = await self._fetch_snapshot(resolved, now)
        except RuntimeError as exc:
            self._snapshot_errors[resolved.canonical_symbol] = str(exc)
            raise MarketDataProviderError(str(exc), provider_key=self.provider_key) from exc
        self._snapshot_cache[resolved.canonical_symbol] = snapshot
        self._snapshot_errors.pop(resolved.canonical_symbol, None)
        return snapshot

    async def _warm_fetch_and_store(self, resolved: _ResolvedSymbol, now: datetime) -> None:
        try:
            snapshot = await self._fetch_snapshot(resolved, now)
        except RuntimeError:
            # Warm-up is best-effort. Leave the symbol uncached so get_watch_snapshot()
            # can still retry the single-symbol path in the same poll cycle.
            return
        self._snapshot_cache[resolved.canonical_symbol] = snapshot
        self._snapshot_errors.pop(resolved.canonical_symbol, None)

    async def _fetch_snapshot(self, resolved: _ResolvedSymbol, now: datetime) -> WatchSnapshot:
        if resolved.market_code == "KRX":
            return await self._fetch_domestic_snapshot(resolved, now)
        if resolved.market_code in {"NAS", "NYS", "AMS"}:
            return await self._fetch_overseas_snapshot(resolved, now)
        raise RuntimeError(f"unsupported-market:{resolved.canonical_symbol}")

    async def _fetch_domestic_snapshot(self, resolved: _ResolvedSymbol, now: datetime) -> WatchSnapshot:
        market_div = _DOMESTIC_MARKET_DIV_CODES.get(resolved.kis_exchange_code)
        if market_div is None:
            raise RuntimeError(f"unsupported-market:{resolved.canonical_symbol}")

        payload = await self._request_kis_json(
            path="/uapi/domestic-stock/v1/quotations/inquire-price",
            tr_id="FHKST01010100",
            params={
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_ISCD": resolved.ticker_or_code,
            },
            fallback_symbol=resolved.canonical_symbol,
        )
        output = payload.get("output")
        if not isinstance(output, dict):
            raise RuntimeError(f"not-found:{resolved.canonical_symbol}")
        price = _parse_positive_float(output.get("stck_prpr"))
        if price is None:
            raise RuntimeError(f"not-found:{resolved.canonical_symbol}")
        previous_close = _parse_domestic_previous_close(output, current_price=price)
        if previous_close is None:
            raise RuntimeError(f"missing-previous-close:{resolved.canonical_symbol}")
        session = get_watch_market_session(resolved.canonical_symbol, now)
        session_close_price = _parse_domestic_session_close(output)
        if session.is_regular_session_open:
            session_close_price = None
        asof = _parse_domestic_asof(now, output)
        snapshot = WatchSnapshot(
            symbol=resolved.canonical_symbol,
            current_price=price,
            previous_close=previous_close,
            session_close_price=session_close_price,
            asof=asof,
            session_date=session.session_date,
            provider=self.provider_key,
        )
        self._ensure_fresh_snapshot(snapshot, now)
        return snapshot

    async def _fetch_overseas_snapshot(self, resolved: _ResolvedSymbol, now: datetime) -> WatchSnapshot:
        exchange_codes = (resolved.kis_exchange_code, *_OVERSEAS_EXCHANGE_ALIASES.get(resolved.kis_exchange_code, ()))
        last_error: RuntimeError | None = None

        for exchange_code in exchange_codes:
            try:
                payload = await self._request_kis_json(
                    path="/uapi/overseas-price/v1/quotations/price",
                    tr_id="HHDFS00000300",
                    params={
                        "AUTH": "",
                        "EXCD": exchange_code,
                        "SYMB": resolved.ticker_or_code,
                    },
                    fallback_symbol=resolved.canonical_symbol,
                )
            except RuntimeError as exc:
                last_error = exc
                if str(exc).startswith(f"not-found:{resolved.canonical_symbol}"):
                    continue
                raise
            output = payload.get("output")
            if not isinstance(output, dict):
                last_error = RuntimeError(f"not-found:{resolved.canonical_symbol}")
                continue
            try:
                snapshot = self._normalize_overseas_snapshot(output, resolved, now)
                self._ensure_fresh_snapshot(snapshot, now)
                return snapshot
            except RuntimeError as exc:
                last_error = exc
                if not str(exc).startswith(f"not-found:{resolved.canonical_symbol}"):
                    raise

        raise last_error or RuntimeError(f"not-found:{resolved.canonical_symbol}")

    async def _warm_overseas_chunk(self, chunk: list[_ResolvedSymbol], now: datetime) -> None:
        params: dict[str, str] = {
            "AUTH": "",
            "NREC": str(len(chunk)),
        }
        for index, item in enumerate(chunk, start=1):
            params[f"EXCD_{index:02d}"] = item.kis_exchange_code
            params[f"SYMB_{index:02d}"] = item.ticker_or_code

        try:
            payload = await self._request_kis_json(
                path="/uapi/overseas-price/v1/quotations/multprice",
                tr_id="HHDFS76220000",
                params=params,
            )
        except RuntimeError as exc:
            # Batch warm-up is best-effort. Leave symbols uncached so get_watch_snapshot()
            # can still fall back to the single-symbol endpoint in the same poll.
            return

        rows = payload.get("output2")
        if not isinstance(rows, list):
            rows = payload.get("output1")
        if not isinstance(rows, list):
            return

        rows_by_symbol: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            exchange = str(row.get("excd") or "").strip().upper()
            ticker = str(row.get("symb") or "").strip().upper()
            if exchange and ticker:
                rows_by_symbol[(exchange, ticker)] = row

        for item in chunk:
            row = rows_by_symbol.get((item.kis_exchange_code, item.ticker_or_code))
            if row is None:
                continue
            try:
                snapshot = self._normalize_overseas_snapshot(row, item, now)
                self._ensure_fresh_snapshot(snapshot, now)
            except RuntimeError:
                continue
            self._snapshot_cache[item.canonical_symbol] = snapshot
            self._snapshot_errors.pop(item.canonical_symbol, None)

    async def _request_kis_json(
        self,
        *,
        path: str,
        tr_id: str,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        method: str = "GET",
        fallback_symbol: str | None = None,
        allow_auth_retry: bool = True,
    ) -> dict[str, Any]:
        token_header = await self._get_access_token()
        try:
            payload = await asyncio.to_thread(
                self._request_json_sync,
                path=path,
                tr_id=tr_id,
                token_header=token_header,
                params=params,
                body=body,
                method=method,
            )
        except RuntimeError as exc:
            if allow_auth_retry and str(exc) == "kis-auth-failed":
                token_header = await self._get_access_token(force_refresh=True)
                payload = await asyncio.to_thread(
                    self._request_json_sync,
                    path=path,
                    tr_id=tr_id,
                    token_header=token_header,
                    params=params,
                    body=body,
                    method=method,
                )
            else:
                raise
        self._raise_for_payload_error(payload, fallback_symbol=fallback_symbol)
        return payload

    async def _get_access_token(self, *, force_refresh: bool = False) -> str:
        async with self._token_lock:
            now = datetime.now(timezone.utc)
            if (
                not force_refresh
                and self._token_header
                and self._token_expires_at is not None
                and now + _TOKEN_REFRESH_MARGIN < self._token_expires_at
            ):
                return self._token_header

            payload = await asyncio.to_thread(self._issue_access_token_sync)
            access_token = str(payload.get("access_token") or "").strip()
            token_type = str(payload.get("token_type") or "Bearer").strip() or "Bearer"
            if not access_token:
                raise RuntimeError("kis-auth-failed")
            expires_in = payload.get("expires_in")
            if isinstance(expires_in, (int, float)):
                expires_at = now + timedelta(seconds=max(60, int(expires_in)))
            else:
                expires_at = now + timedelta(hours=24)
            self._token_header = f"{token_type} {access_token}"
            self._token_expires_at = expires_at
            return self._token_header

    def _issue_access_token_sync(self) -> dict[str, Any]:
        payload = self._request_json_sync(
            path="/oauth2/tokenP",
            tr_id="",
            token_header="",
            body={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
            },
            method="POST",
        )
        self._raise_for_payload_error(payload)
        return payload

    def _request_json_sync(
        self,
        *,
        path: str,
        tr_id: str,
        token_header: str,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        method: str = "GET",
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        headers = dict(_DEFAULT_HEADERS)
        headers["appkey"] = self.app_key
        headers["appsecret"] = self.app_secret
        if tr_id:
            headers["tr_id"] = tr_id
        if token_header:
            headers["authorization"] = token_header
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(url, headers=headers, data=data, method=method.upper())

        for attempt in range(self.retry_count + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise RuntimeError("kis-unreachable")
                return payload
            except HTTPError as exc:
                error_payload = _read_http_error_payload(exc)
                error_message = _error_payload_message(error_payload)
                if exc.code == 429 or _looks_like_rate_limit_error(error_message):
                    raise RuntimeError("kis-rate-limited") from exc
                if exc.code in {401, 403}:
                    raise RuntimeError("kis-auth-failed") from exc
                if attempt >= self.retry_count:
                    raise RuntimeError("kis-unreachable") from exc
            except json.JSONDecodeError as exc:
                raise RuntimeError("kis-unreachable") from exc
            except URLError as exc:
                if attempt >= self.retry_count:
                    raise RuntimeError("kis-unreachable") from exc
        raise RuntimeError("kis-unreachable")

    def _resolve_symbol(self, symbol: str) -> _ResolvedSymbol:
        registry = load_registry()
        normalized, _warning = normalize_stored_watch_symbol(symbol, registry=registry)
        canonical_symbol = normalized or symbol.strip().upper()
        record = registry.get(canonical_symbol)
        if record is None:
            raise RuntimeError(f"not-found:{canonical_symbol}")
        return _resolve_registry_record(record)

    def _normalize_overseas_snapshot(
        self,
        output: dict[str, Any],
        resolved: _ResolvedSymbol,
        now: datetime,
    ) -> WatchSnapshot:
        price = _parse_positive_float(output.get("last"))
        if price is None:
            raise RuntimeError(f"not-found:{resolved.canonical_symbol}")
        asof = _parse_intraday_time(now, output.get("khms"))
        previous_close = _parse_overseas_previous_close(output)
        if previous_close is None:
            raise RuntimeError(f"missing-previous-close:{resolved.canonical_symbol}")
        session = get_watch_market_session(resolved.canonical_symbol, asof)
        session_close_price = _parse_overseas_session_close(output)
        if session.is_regular_session_open:
            session_close_price = None
        return WatchSnapshot(
            symbol=resolved.canonical_symbol,
            current_price=price,
            previous_close=previous_close,
            session_close_price=session_close_price,
            asof=asof,
            session_date=session.session_date,
            provider=self.provider_key,
        )

    def _raise_for_payload_error(self, payload: dict[str, Any], *, fallback_symbol: str | None = None) -> None:
        rt_cd = str(payload.get("rt_cd") or "").strip()
        if not rt_cd or rt_cd == "0":
            return
        message = " ".join(str(payload.get(key) or "").strip() for key in ("msg_cd", "msg1")).strip().lower()
        if any(keyword in message for keyword in ("auth", "token", "인증", "접근토큰")):
            raise RuntimeError("kis-auth-failed")
        if any(keyword in message for keyword in ("rate", "limit", "유량", "too many")):
            raise RuntimeError("kis-rate-limited")
        if fallback_symbol and any(keyword in message for keyword in ("not found", "no data", "종목", "없", "조회되지")):
            raise RuntimeError(f"not-found:{fallback_symbol}")
        if fallback_symbol:
            raise RuntimeError(f"not-found:{fallback_symbol}")
        raise RuntimeError("kis-unreachable")

    def _ensure_fresh_snapshot(self, snapshot: WatchSnapshot, now: datetime) -> None:
        asof = snapshot.asof
        if asof.tzinfo is None:
            asof = asof.replace(tzinfo=now.tzinfo)
        if now - asof > _QUOTE_STALE_AFTER and not _allows_post_close_stale_snapshot(snapshot, now):
            raise RuntimeError(f"stale-quote:{snapshot.symbol}")
        if snapshot.previous_close <= 0:
            raise RuntimeError(f"missing-previous-close:{snapshot.symbol}")
        if not snapshot.session_date:
            raise RuntimeError(f"missing-session-date:{snapshot.symbol}")

    def _reset_poll_cache(self, now: datetime) -> None:
        poll_key = now.isoformat()
        if poll_key == self._poll_cache_key:
            return
        self._poll_cache_key = poll_key
        self._snapshot_cache = {}
        self._snapshot_errors = {}


class MassiveSnapshotMarketDataProvider:
    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: int = 5,
        retry_count: int = 1,
        base_url: str = "https://api.massive.com",
    ) -> None:
        self.api_key = api_key.strip()
        self.timeout_seconds = max(1, min(timeout_seconds, 10))
        self.retry_count = max(0, min(retry_count, 1))
        self.base_url = base_url.rstrip("/")
        self.provider_key = "massive_reference"

    async def warm_watch_snapshots(self, symbols: list[str], now: datetime) -> None:
        return None

    async def warm_quotes(self, symbols: list[str], now: datetime) -> None:
        await self.warm_watch_snapshots(symbols, now)

    async def get_watch_snapshot(self, symbol: str, now: datetime) -> WatchSnapshot:
        return await asyncio.to_thread(self._get_watch_snapshot_sync, symbol, now)

    async def get_quote(self, symbol: str, now: datetime) -> Quote:
        snapshot = await self.get_watch_snapshot(symbol, now)
        return Quote(symbol=snapshot.symbol, price=snapshot.current_price, asof=snapshot.asof, provider=snapshot.provider)

    def _get_watch_snapshot_sync(self, symbol: str, now: datetime) -> WatchSnapshot:
        registry = load_registry()
        normalized, _warning = normalize_stored_watch_symbol(symbol, registry=registry)
        canonical_symbol = normalized or symbol.strip().upper()
        record = registry.get(canonical_symbol)
        if record is None:
            raise MarketDataProviderError(f"not-found:{canonical_symbol}", provider_key=self.provider_key)
        if record.market_code not in {"NAS", "NYS", "AMS"}:
            raise MarketDataProviderError(f"unsupported-market:{canonical_symbol}", provider_key=self.provider_key)

        payload = self._request_json(record.ticker_or_code, fallback_symbol=canonical_symbol)
        snapshot = payload.get("ticker")
        if not isinstance(snapshot, dict):
            raise MarketDataProviderError(f"not-found:{canonical_symbol}", provider_key=self.provider_key)

        price = _parse_positive_float(_nested_get(snapshot, "lastTrade", "p"))
        if price is None:
            raise MarketDataProviderError(f"not-found:{canonical_symbol}", provider_key=self.provider_key)
        previous_close = _parse_positive_float(_nested_get(snapshot, "prevDay", "c"))
        if previous_close is None:
            raise MarketDataProviderError(f"missing-previous-close:{canonical_symbol}", provider_key=self.provider_key)

        asof = _parse_epoch_datetime(_nested_get(snapshot, "lastTrade", "t")) or now
        session = get_watch_market_session(canonical_symbol, asof)
        session_close_price = _parse_positive_float(_nested_get(snapshot, "day", "c"))
        if session.is_regular_session_open:
            session_close_price = None
        watch_snapshot = WatchSnapshot(
            symbol=canonical_symbol,
            current_price=price,
            previous_close=previous_close,
            session_close_price=session_close_price,
            asof=asof,
            session_date=session.session_date,
            provider=self.provider_key,
        )
        _ensure_watch_snapshot_fresh(watch_snapshot, now)
        return watch_snapshot

    def _request_json(self, ticker: str, *, fallback_symbol: str) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}?{urlencode({'apiKey': self.api_key})}",
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
                    raise MarketDataProviderError("massive-invalid-response", provider_key=self.provider_key)
                status = str(payload.get("status") or "").strip().upper()
                if status and status not in {"OK", "SUCCESS"}:
                    message = _error_payload_message(payload)
                    if _looks_like_entitlement_error(message):
                        raise MarketDataProviderError("massive-entitlement-required", provider_key=self.provider_key)
                    raise MarketDataProviderError(
                        f"not-found:{fallback_symbol}" if "not found" in message else "massive-invalid-response",
                        provider_key=self.provider_key,
                    )
                return payload
            except HTTPError as exc:
                error_payload = _read_http_error_payload(exc)
                error_message = _error_payload_message(error_payload)
                if exc.code == 429 or _looks_like_rate_limit_error(error_message):
                    raise MarketDataProviderError("massive-rate-limited", provider_key=self.provider_key) from exc
                if exc.code in {401, 403}:
                    if _looks_like_entitlement_error(error_message):
                        raise MarketDataProviderError("massive-entitlement-required", provider_key=self.provider_key) from exc
                    raise MarketDataProviderError("massive-auth-failed", provider_key=self.provider_key) from exc
                if exc.code == 404:
                    raise MarketDataProviderError(f"not-found:{fallback_symbol}", provider_key=self.provider_key) from exc
                if attempt >= self.retry_count:
                    raise MarketDataProviderError("massive-unreachable", provider_key=self.provider_key) from exc
            except json.JSONDecodeError as exc:
                raise MarketDataProviderError("massive-invalid-response", provider_key=self.provider_key) from exc
            except URLError as exc:
                if attempt >= self.retry_count:
                    raise MarketDataProviderError("massive-unreachable", provider_key=self.provider_key) from exc
        raise MarketDataProviderError("massive-unreachable", provider_key=self.provider_key)


class RoutedMarketDataProvider:
    def __init__(
        self,
        *,
        primary_provider: MarketDataProvider,
        us_fallback_provider: MarketDataProvider | None = None,
    ) -> None:
        self.primary_provider = primary_provider
        self.us_fallback_provider = us_fallback_provider

    async def warm_watch_snapshots(self, symbols: list[str], now: datetime) -> None:
        warm_watch_snapshots = getattr(self.primary_provider, "warm_watch_snapshots", None)
        if callable(warm_watch_snapshots):
            await warm_watch_snapshots(symbols, now)
            return
        warm_quotes = getattr(self.primary_provider, "warm_quotes", None)
        if callable(warm_quotes):
            await warm_quotes(symbols, now)

    async def get_watch_snapshot(self, symbol: str, now: datetime) -> WatchSnapshot:
        registry = load_registry()
        normalized, _warning = normalize_stored_watch_symbol(symbol, registry=registry)
        canonical_symbol = normalized or symbol.strip().upper()
        record = registry.get(canonical_symbol)
        if record is None:
            raise MarketDataProviderError(f"not-found:{canonical_symbol}")

        if record.market_code not in {"NAS", "NYS", "AMS"} or self.us_fallback_provider is None:
            return await _provider_get_watch_snapshot(self.primary_provider, canonical_symbol, now)

        try:
            return await _provider_get_watch_snapshot(self.primary_provider, canonical_symbol, now)
        except MarketDataProviderError as primary_exc:
            try:
                return await _provider_get_watch_snapshot(self.us_fallback_provider, canonical_symbol, now)
            except MarketDataProviderError as fallback_exc:
                raise MarketDataProviderError(
                    f"{primary_exc.provider_key}:{primary_exc} | {fallback_exc.provider_key}:{fallback_exc}",
                    provider_key=fallback_exc.provider_key,
                ) from fallback_exc
        except RuntimeError as primary_exc:
            try:
                return await _provider_get_watch_snapshot(self.us_fallback_provider, canonical_symbol, now)
            except MarketDataProviderError as fallback_exc:
                raise MarketDataProviderError(
                    f"kis_quote:{primary_exc} | {fallback_exc.provider_key}:{fallback_exc}",
                    provider_key=fallback_exc.provider_key,
                ) from fallback_exc

    async def get_quote(self, symbol: str, now: datetime) -> Quote:
        get_quote = getattr(self.primary_provider, "get_quote", None)
        registry = load_registry()
        normalized, _warning = normalize_stored_watch_symbol(symbol, registry=registry)
        canonical_symbol = normalized or symbol.strip().upper()
        record = registry.get(canonical_symbol)
        if callable(get_quote) and (record is None or record.market_code not in {"NAS", "NYS", "AMS"} or self.us_fallback_provider is None):
            return await get_quote(canonical_symbol, now)

        if record is not None and record.market_code in {"NAS", "NYS", "AMS"} and self.us_fallback_provider is not None:
            try:
                if callable(get_quote):
                    return await get_quote(canonical_symbol, now)
                snapshot = await _provider_get_watch_snapshot(self.primary_provider, canonical_symbol, now)
                return Quote(symbol=snapshot.symbol, price=snapshot.current_price, asof=snapshot.asof, provider=snapshot.provider)
            except Exception:
                fallback_get_quote = getattr(self.us_fallback_provider, "get_quote", None)
                if callable(fallback_get_quote):
                    return await fallback_get_quote(canonical_symbol, now)

        snapshot = await self.get_watch_snapshot(symbol, now)
        return Quote(symbol=snapshot.symbol, price=snapshot.current_price, asof=snapshot.asof, provider=snapshot.provider)

    async def warm_quotes(self, symbols: list[str], now: datetime) -> None:
        await self.warm_watch_snapshots(symbols, now)


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


def _resolve_registry_record(record: InstrumentRecord) -> _ResolvedSymbol:
    canonical_symbol = record.canonical_symbol.strip().upper()
    market_code = record.market_code.strip().upper()
    ticker_or_code = record.ticker_or_code.strip().upper()
    exchange_code = (record.provider_ids.kis_exchange_code or market_code).strip().upper()

    if market_code == "KRX":
        if exchange_code not in _DOMESTIC_MARKET_DIV_CODES:
            raise RuntimeError(f"unsupported-market:{canonical_symbol}")
        return _ResolvedSymbol(canonical_symbol, market_code, ticker_or_code, exchange_code)

    if market_code in {"NAS", "NYS", "AMS"}:
        if exchange_code not in _OVERSEAS_EXCHANGE_CODES:
            raise RuntimeError(f"unsupported-market:{canonical_symbol}")
        return _ResolvedSymbol(canonical_symbol, market_code, ticker_or_code, exchange_code)

    raise RuntimeError(f"unsupported-market:{canonical_symbol}")


def _parse_positive_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value) if float(value) > 0 else None
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _parse_first_positive_float(payload: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = _parse_positive_float(payload.get(key))
        if value is not None:
            return value
    return None


def _parse_signed_difference(output: dict[str, Any]) -> float | None:
    difference = _parse_positive_float(output.get("prdy_vrss"))
    if difference is None:
        return None
    sign = str(output.get("prdy_vrss_sign") or "").strip()
    if sign in {"4", "5"}:
        return -difference
    return difference


def _parse_domestic_previous_close(output: dict[str, Any], *, current_price: float) -> float | None:
    previous_close = _parse_first_positive_float(output, ("stck_sdpr", "stck_prdy_clpr", "bfdy_clpr"))
    if previous_close is not None:
        return previous_close
    signed_difference = _parse_signed_difference(output)
    if signed_difference is None:
        return None
    candidate = current_price - signed_difference
    return candidate if candidate > 0 else None


def _parse_domestic_session_close(output: dict[str, Any]) -> float | None:
    return _parse_first_positive_float(output, ("stck_clpr", "clpr"))


def _parse_domestic_asof(now: datetime, output: dict[str, Any]) -> datetime:
    date_text = str(output.get("stck_bsop_date") or output.get("bsop_date") or "").strip()
    time_text = str(output.get("stck_cntg_hour") or output.get("cntg_hour") or "").strip()
    if len(date_text) == 8 and date_text.isdigit() and len(time_text) == 6 and time_text.isdigit():
        return datetime(
            year=int(date_text[0:4]),
            month=int(date_text[4:6]),
            day=int(date_text[6:8]),
            hour=int(time_text[0:2]),
            minute=int(time_text[2:4]),
            second=int(time_text[4:6]),
            tzinfo=_KOREA_TZ,
        )
    if len(time_text) == 6 and time_text.isdigit():
        base = now.astimezone(_KOREA_TZ)
        return _parse_intraday_time(base, time_text)
    return now


def _parse_overseas_previous_close(output: dict[str, Any]) -> float | None:
    return _parse_first_positive_float(output, ("base", "pbas", "prev", "pcls"))


def _parse_overseas_session_close(output: dict[str, Any]) -> float | None:
    return _parse_first_positive_float(output, ("clos", "clos1", "curr_day_clpr", "day_clpr"))


def _nested_get(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _read_http_error_payload(exc: HTTPError) -> dict[str, Any] | None:
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception:
        return None
    if not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return payload if isinstance(payload, dict) else {"raw": raw}


def _error_payload_message(payload: dict[str, Any] | None) -> str:
    if not payload:
        return ""
    return " ".join(
        str(payload.get(key) or "").strip().lower()
        for key in ("status", "message", "error", "error_code", "error_description", "msg_cd", "msg1", "raw")
    ).strip()


def _looks_like_rate_limit_error(message: str) -> bool:
    return any(keyword in message for keyword in ("rate", "limit", "유량", "too many", "1분당 1회"))


def _looks_like_entitlement_error(message: str) -> bool:
    return any(keyword in message for keyword in ("not entitled", "not_authorized", "not authorized", "upgrade your plan"))


async def _provider_get_watch_snapshot(provider: Any, symbol: str, now: datetime) -> WatchSnapshot:
    get_watch_snapshot = getattr(provider, "get_watch_snapshot", None)
    if callable(get_watch_snapshot):
        return await get_watch_snapshot(symbol, now)
    get_quote = getattr(provider, "get_quote", None)
    if not callable(get_quote):
        raise MarketDataProviderError("watch-snapshot-unsupported")
    quote = await get_quote(symbol, now)
    session = get_watch_market_session(symbol, quote.asof)
    return WatchSnapshot(
        symbol=quote.symbol,
        current_price=quote.price,
        previous_close=quote.price,
        session_close_price=None if session.is_regular_session_open else quote.price,
        asof=quote.asof,
        session_date=session.session_date,
        provider=getattr(quote, "provider", "") or getattr(provider, "provider_key", ""),
    )


def _ensure_watch_snapshot_fresh(snapshot: WatchSnapshot, now: datetime) -> None:
    asof = snapshot.asof
    if asof.tzinfo is None:
        asof = asof.replace(tzinfo=now.tzinfo)
    if now - asof > _QUOTE_STALE_AFTER and not _allows_post_close_stale_snapshot(snapshot, now):
        raise MarketDataProviderError(
            f"stale-quote:{snapshot.symbol}",
            provider_key=snapshot.provider or "market_data_provider",
        )
    if snapshot.previous_close <= 0:
        raise MarketDataProviderError(
            f"missing-previous-close:{snapshot.symbol}",
            provider_key=snapshot.provider or "market_data_provider",
        )
    if not snapshot.session_date:
        raise MarketDataProviderError(
            f"missing-session-date:{snapshot.symbol}",
            provider_key=snapshot.provider or "market_data_provider",
        )


def _allows_post_close_stale_snapshot(snapshot: WatchSnapshot, now: datetime) -> bool:
    if snapshot.session_close_price is None:
        return False
    try:
        session = get_watch_market_session(snapshot.symbol, now)
    except Exception:
        return False
    return not session.is_regular_session_open and snapshot.session_date == session.session_date


def _ensure_quote_fresh(quote: Quote, now: datetime) -> None:
    asof = quote.asof
    if asof.tzinfo is None:
        asof = asof.replace(tzinfo=now.tzinfo)
    if now - asof > _QUOTE_STALE_AFTER:
        raise MarketDataProviderError(f"stale-quote:{quote.symbol}", provider_key=quote.provider or "market_data_provider")


def _parse_intraday_time(now: datetime, value: Any) -> datetime:
    text = str(value or "").strip()
    if len(text) != 6 or not text.isdigit():
        return now
    candidate = now.replace(
        hour=int(text[0:2]),
        minute=int(text[2:4]),
        second=int(text[4:6]),
        microsecond=0,
    )
    if candidate - now > timedelta(hours=12):
        candidate -= timedelta(days=1)
    if now - candidate > timedelta(hours=12):
        candidate += timedelta(days=1)
    return candidate


def _parse_epoch_datetime(value: Any) -> datetime | None:
    try:
        raw = int(str(value or "").strip())
    except (TypeError, ValueError):
        return None
    if raw <= 0:
        return None
    if raw >= 10**18:
        timestamp = raw / 1_000_000_000
    elif raw >= 10**15:
        timestamp = raw / 1_000_000
    elif raw >= 10**12:
        timestamp = raw / 1_000
    else:
        timestamp = raw
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _chunk(items: list[_ResolvedSymbol], size: int) -> list[list[_ResolvedSymbol]]:
    return [items[index : index + size] for index in range(0, len(items), size)]
