from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from bot.common.fs import atomic_write_json


MODULE_ROOT = Path(__file__).resolve().parent
DATA_DIR = MODULE_ROOT / "data"
REGISTRY_FILE = DATA_DIR / "instrument_registry.json"
RUNTIME_REGISTRY_FILE = Path("data/state/instrument_registry.json")
SEED_FILE = DATA_DIR / "instrument_registry_seed.json"
SUPPORTED_MARKETS = ("KRX", "NAS", "NYS", "AMS")
_CANONICAL_RE = re.compile(r"^(?P<market>[A-Z]{3}):(?P<symbol>[A-Z0-9.\-]{1,32})$")
_SEARCH_TEXT_RE = re.compile(r"[^0-9A-Z가-힣]+")
_RAW_US_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_RAW_KR_RE = re.compile(r"^\d{6}$")
_MARKET_PRIORITY = {"KRX": 0, "NAS": 1, "NYS": 2, "AMS": 3}
_DEFAULT_HEADERS = {"User-Agent": "discord-heatmap-bot/1.0"}


@dataclass(frozen=True)
class ProviderIds:
    kis_exchange_code: str = ""
    sec_exchange: str = ""
    polygon_primary_exchange: str = ""
    twelve_mic_code: str = ""
    figi: str = ""


@dataclass(frozen=True)
class InstrumentRecord:
    canonical_symbol: str
    market_code: str
    ticker_or_code: str
    display_name_ko: str
    display_name_en: str
    aliases: tuple[str, ...]
    provider_ids: ProviderIds
    source: str = ""

    @property
    def display_name(self) -> str:
        return self.display_name_ko or self.display_name_en or self.ticker_or_code

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["aliases"] = list(self.aliases)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> InstrumentRecord:
        provider_ids = payload.get("provider_ids", {})
        return cls(
            canonical_symbol=str(payload.get("canonical_symbol") or "").upper(),
            market_code=str(payload.get("market_code") or "").upper(),
            ticker_or_code=str(payload.get("ticker_or_code") or "").upper(),
            display_name_ko=str(payload.get("display_name_ko") or "").strip(),
            display_name_en=str(payload.get("display_name_en") or "").strip(),
            aliases=tuple(str(x).strip() for x in payload.get("aliases", ()) if str(x).strip()),
            provider_ids=ProviderIds(
                kis_exchange_code=str(provider_ids.get("kis_exchange_code") or "").upper(),
                sec_exchange=str(provider_ids.get("sec_exchange") or "").strip(),
                polygon_primary_exchange=str(provider_ids.get("polygon_primary_exchange") or "").strip(),
                twelve_mic_code=str(provider_ids.get("twelve_mic_code") or "").strip(),
                figi=str(provider_ids.get("figi") or "").strip(),
            ),
            source=str(payload.get("source") or "").strip(),
        )


@dataclass(frozen=True)
class RegistrySearchResult:
    record: InstrumentRecord
    score: int


class InstrumentRegistry:
    def __init__(self, *, generated_at: str, records: Iterable[InstrumentRecord], metadata: dict[str, Any] | None = None) -> None:
        self.generated_at = generated_at
        self.records = tuple(records)
        self.metadata = metadata or {}
        self._by_symbol = {record.canonical_symbol: record for record in self.records}

    def get(self, canonical_symbol: str) -> InstrumentRecord | None:
        return self._by_symbol.get(canonical_symbol.strip().upper())

    def counts_by_market(self) -> dict[str, int]:
        counts: dict[str, int] = {market: 0 for market in SUPPORTED_MARKETS}
        for record in self.records:
            counts[record.market_code] = counts.get(record.market_code, 0) + 1
        return counts

    def search(self, query: str, *, allowed_symbols: set[str] | None = None, limit: int = 25) -> list[RegistrySearchResult]:
        query = query.strip()
        if not query:
            return []
        canonical = normalize_canonical_symbol(query)
        if canonical:
            record = self.get(canonical)
            return [RegistrySearchResult(record, 1000)] if record else []

        normalized_query = normalize_search_text(query)
        if not normalized_query:
            return []

        results: list[RegistrySearchResult] = []
        for record in self.records:
            if allowed_symbols is not None and record.canonical_symbol not in allowed_symbols:
                continue
            score = _score_record(record, normalized_query)
            if score <= 0:
                continue
            results.append(RegistrySearchResult(record, score))

        results.sort(
            key=lambda result: (
                -result.score,
                _MARKET_PRIORITY.get(result.record.market_code, 99),
                result.record.display_name,
                result.record.canonical_symbol,
            )
        )
        return results[:limit]

    def to_payload(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "metadata": self.metadata,
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> InstrumentRegistry:
        records = [InstrumentRecord.from_dict(item) for item in payload.get("records", []) if isinstance(item, dict)]
        return cls(
            generated_at=str(payload.get("generated_at") or ""),
            records=records,
            metadata=dict(payload.get("metadata") or {}),
        )


def normalize_search_text(value: str) -> str:
    return _SEARCH_TEXT_RE.sub("", value.strip().upper())


def normalize_canonical_symbol(value: str) -> str | None:
    match = _CANONICAL_RE.match(value.strip().upper())
    if not match:
        return None
    market = match.group("market")
    if market not in SUPPORTED_MARKETS:
        return None
    return f"{market}:{match.group('symbol')}"


def is_canonical_symbol(value: str) -> bool:
    return normalize_canonical_symbol(value) is not None


def format_instrument_label(record: InstrumentRecord) -> str:
    return f"{record.display_name} | {record.canonical_symbol}"


def format_watch_symbol(symbol: str) -> str:
    registry = load_registry()
    normalized, warning = normalize_stored_watch_symbol(symbol, registry=registry)
    record = registry.get(normalized)
    if record is not None:
        return f"{record.display_name} ({record.canonical_symbol})"
    if warning:
        return f"{normalized} ({warning})"
    return normalized


def normalize_stored_watch_symbol(value: str, *, registry: InstrumentRegistry | None = None) -> tuple[str, str | None]:
    registry = registry or load_registry()
    raw = value.strip().upper()
    if not raw:
        return "", "empty"

    canonical = normalize_canonical_symbol(raw)
    if canonical:
        return canonical, None
    if _RAW_KR_RE.fullmatch(raw):
        return f"KRX:{raw}", "legacy-krx-code"
    if _RAW_US_RE.fullmatch(raw):
        results = registry.search(raw, limit=10)
        exact = [item.record for item in results if item.record.ticker_or_code == raw and item.record.market_code in {"NAS", "NYS", "AMS"}]
        unique = {record.canonical_symbol: record for record in exact}
        if len(unique) == 1:
            record = next(iter(unique.values()))
            return record.canonical_symbol, "legacy-us-ticker"
        if len(unique) > 1:
            return raw, "legacy-ambiguous"
        return raw, "legacy-unresolved"
    return raw, "legacy-unresolved"


def load_registry_payload(path: Path = REGISTRY_FILE) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise RuntimeError("instrument-registry-invalid-payload")
    return payload


def _registry_from_payload(payload: dict[str, Any], *, source: str, path: Path) -> InstrumentRegistry:
    metadata = dict(payload.get("metadata") or {})
    metadata.setdefault("active_source", source)
    metadata.setdefault("active_path", str(path))
    normalized_payload = dict(payload)
    normalized_payload["metadata"] = metadata
    return InstrumentRegistry.from_payload(normalized_payload)


@lru_cache(maxsize=1)
def load_registry() -> InstrumentRegistry:
    if RUNTIME_REGISTRY_FILE.exists():
        return _registry_from_payload(load_registry_payload(RUNTIME_REGISTRY_FILE), source="runtime", path=RUNTIME_REGISTRY_FILE)
    if REGISTRY_FILE.exists():
        return _registry_from_payload(load_registry_payload(REGISTRY_FILE), source="bundled", path=REGISTRY_FILE)
    if SEED_FILE.exists():
        generated_at = datetime.now(timezone.utc).isoformat()
        return _registry_from_payload(
            {"generated_at": generated_at, "records": _load_seed_payload()},
            source="seed",
            path=SEED_FILE,
        )
    return InstrumentRegistry(generated_at="", records=(), metadata={"status": "missing"})


def clear_registry_cache() -> None:
    load_registry.cache_clear()


def _load_seed_payload() -> list[dict[str, Any]]:
    with SEED_FILE.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, list):
        raise RuntimeError("instrument-registry-seed-invalid")
    return [item for item in payload if isinstance(item, dict)]


def registry_status() -> dict[str, str]:
    try:
        registry = load_registry()
    except Exception as exc:
        return {"status": "failed", "message": str(exc), "updated_at": ""}
    counts = registry.counts_by_market()
    total = len(registry.records)
    status = "ok" if total > 0 else "disabled"
    active_source = str(registry.metadata.get("active_source") or "unknown")
    message = (
        f"source={active_source} loaded={total} "
        f"krx={counts.get('KRX', 0)} nas={counts.get('NAS', 0)} "
        f"nys={counts.get('NYS', 0)} ams={counts.get('AMS', 0)}"
    )
    return {"status": status, "message": message, "updated_at": registry.generated_at}


def build_registry(
    *,
    seed_records: Iterable[dict[str, Any]],
    dart_xml_bytes: bytes | None = None,
    sec_payload: Iterable[dict[str, Any]] | None = None,
    krx_etf_rows: Iterable[dict[str, Any]] | None = None,
    krx_etn_rows: Iterable[dict[str, Any]] | None = None,
    krx_elw_rows: Iterable[dict[str, Any]] | None = None,
    krx_pf_rows: Iterable[dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> InstrumentRegistry:
    merged: dict[str, dict[str, Any]] = {}
    for payload in seed_records:
        record = _normalized_payload(payload)
        if record is not None:
            merged[record["canonical_symbol"]] = record

    for payload in parse_dart_corpcode(dart_xml_bytes) if dart_xml_bytes else ():
        _merge_payload(merged, payload, preferred_source="dart")

    for payload in build_sec_records(sec_payload or ()):
        _merge_payload(merged, payload, preferred_source="sec")

    for payload in build_krx_etf_records(krx_etf_rows or ()):
        _merge_payload(merged, payload, preferred_source="krx-etf")

    for payload in build_krx_etn_records(krx_etn_rows or ()):
        _merge_payload(merged, payload, preferred_source="krx-etn")

    for payload in build_krx_elw_records(krx_elw_rows or ()):
        _merge_payload(merged, payload, preferred_source="krx-elw")

    for payload in build_krx_pf_records(krx_pf_rows or ()):
        _merge_payload(merged, payload, preferred_source="krx-pf")

    records = [
        InstrumentRecord.from_dict(payload)
        for payload in sorted(
            merged.values(),
            key=lambda item: (
                _MARKET_PRIORITY.get(str(item.get("market_code") or ""), 99),
                str(item.get("display_name_ko") or item.get("display_name_en") or item.get("ticker_or_code") or ""),
                str(item.get("canonical_symbol") or ""),
            ),
        )
    ]
    metadata = {
        "counts_by_market": {
            market: sum(1 for record in records if record.market_code == market) for market in SUPPORTED_MARKETS
        }
    }
    return InstrumentRegistry(
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
        records=records,
        metadata=metadata,
    )


def save_registry(registry: InstrumentRegistry, path: Path = REGISTRY_FILE) -> None:
    atomic_write_json(path, registry.to_payload())
    clear_registry_cache()


def build_live_registry(
    *,
    dart_api_key: str,
    seed_records: Iterable[dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> InstrumentRegistry:
    api_key = dart_api_key.strip()
    if not api_key:
        raise RuntimeError("dart-api-key-missing")
    return build_registry(
        seed_records=seed_records or _load_seed_payload(),
        dart_xml_bytes=fetch_dart_corpcode_bytes(api_key),
        sec_payload=fetch_sec_company_tickers(),
        krx_etf_rows=fetch_krx_etf_rows(),
        krx_etn_rows=fetch_krx_etn_rows(),
        krx_elw_rows=fetch_krx_elw_rows(),
        krx_pf_rows=fetch_krx_pf_rows(),
        generated_at=generated_at,
    )


def read_dart_corpcode_bytes(path: Path) -> bytes:
    return path.read_bytes()


def fetch_dart_corpcode_bytes(api_key: str) -> bytes:
    request = urllib.request.Request(
        f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key.strip()}",
        headers=_DEFAULT_HEADERS,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def fetch_sec_company_tickers() -> list[dict[str, Any]]:
    request = urllib.request.Request("https://www.sec.gov/files/company_tickers_exchange.json", headers=_DEFAULT_HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    fields = payload.get("fields") if isinstance(payload, dict) else None
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(fields, list) or not isinstance(rows, list):
        raise RuntimeError("sec-company-tickers-invalid-response")
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized_rows.append(row)
            continue
        if not isinstance(row, list) or len(row) != len(fields):
            continue
        normalized_rows.append({str(key): value for key, value in zip(fields, row, strict=False)})
    return normalized_rows


def fetch_krx_etf_rows() -> list[dict[str, Any]]:
    return fetch_krx_structured_rows("ETF")


def fetch_krx_etn_rows() -> list[dict[str, Any]]:
    return fetch_krx_structured_rows("ETN")


def fetch_krx_elw_rows() -> list[dict[str, Any]]:
    return fetch_krx_structured_rows("ELW")


def fetch_krx_pf_rows() -> list[dict[str, Any]]:
    return fetch_krx_structured_rows("PF")


def fetch_krx_structured_rows(kind: str) -> list[dict[str, Any]]:
    kind = kind.strip().upper()
    if kind not in {"ETF", "ETN", "ELW", "PF"}:
        raise RuntimeError(f"unsupported-krx-structured-kind:{kind}")
    referer = f"https://data.krx.co.kr/comm/finder/finder_secuprodisu.jsp?mktsel={kind}"
    request = urllib.request.Request(
        "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
        data=urllib.parse.urlencode(
            {
                "mktsel": kind,
                "searchText": "",
                "locale": "ko_KR",
                "bld": "dbms/comm/finder/finder_secuprodisu",
            }
        ).encode("utf-8"),
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": referer,
            "Origin": "https://data.krx.co.kr",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    rows = payload.get("block1") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError(f"krx-structured-invalid-response:{kind.lower()}")
    return [row for row in rows if isinstance(row, dict)]


def parse_dart_corpcode(raw_bytes: bytes) -> list[dict[str, Any]]:
    try:
        with zipfile.ZipFile(BytesIO(raw_bytes)) as archive:
            file_names = archive.namelist()
            xml_name = next((name for name in file_names if name.lower().endswith(".xml")), None)
            if xml_name is None:
                return []
            xml_bytes = archive.read(xml_name)
    except zipfile.BadZipFile:
        xml_bytes = raw_bytes

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    records: list[dict[str, Any]] = []
    for item in root.findall(".//list"):
        stock_code = (item.findtext("stock_code") or "").strip()
        corp_name = (item.findtext("corp_name") or "").strip()
        corp_eng_name = (item.findtext("corp_eng_name") or "").strip()
        if not _RAW_KR_RE.fullmatch(stock_code) or not corp_name:
            continue
        records.append(
            _normalized_payload(
                {
                    "canonical_symbol": f"KRX:{stock_code}",
                    "market_code": "KRX",
                    "ticker_or_code": stock_code,
                    "display_name_ko": corp_name,
                    "display_name_en": corp_eng_name,
                    "aliases": [corp_name, corp_eng_name, stock_code, f"KRX:{stock_code}"],
                    "provider_ids": {
                        "kis_exchange_code": "KRX",
                        "twelve_mic_code": "XKRX",
                    },
                    "source": "dart",
                }
            )
        )
    return [record for record in records if record is not None]


def build_sec_records(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        name = str(row.get("name") or "").strip()
        exchange = str(row.get("exchange") or "").strip()
        market_code = infer_market_code_from_sec_exchange(exchange)
        if market_code is None or not ticker or not name:
            continue
        results.append(
            _normalized_payload(
                {
                    "canonical_symbol": f"{market_code}:{ticker}",
                    "market_code": market_code,
                    "ticker_or_code": ticker,
                    "display_name_ko": "",
                    "display_name_en": name,
                    "aliases": [ticker, name, f"{market_code}:{ticker}"],
                    "provider_ids": {
                        "kis_exchange_code": market_code,
                        "sec_exchange": exchange,
                    },
                    "source": "sec",
                }
            )
        )
    return [record for record in results if record is not None]


def build_krx_etf_records(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_krx_structured_records(rows, source="krx-etf")


def build_krx_etn_records(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_krx_structured_records(rows, source="krx-etn")


def build_krx_elw_records(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_krx_structured_records(rows, source="krx-elw")


def build_krx_pf_records(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_krx_structured_records(rows, source="krx-pf")


def build_krx_structured_records(rows: Iterable[dict[str, Any]], *, source: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in rows:
        short_code = str(row.get("short_code") or "").strip().upper()
        name = str(row.get("codeName") or "").strip()
        full_code = str(row.get("full_code") or "").strip().upper()
        if not short_code or not name:
            continue
        results.append(
            _normalized_payload(
                {
                    "canonical_symbol": f"KRX:{short_code}",
                    "market_code": "KRX",
                    "ticker_or_code": short_code,
                    "display_name_ko": name,
                    "display_name_en": "",
                    "aliases": [short_code, full_code, name, f"KRX:{short_code}"],
                    "provider_ids": {
                        "kis_exchange_code": "KRX",
                        "twelve_mic_code": "XKRX",
                    },
                    "source": source,
                }
            )
        )
    return [record for record in results if record is not None]


def infer_market_code_from_sec_exchange(exchange: str) -> str | None:
    normalized = exchange.strip().upper()
    if not normalized:
        return None
    if "NASDAQ" in normalized:
        return "NAS"
    if "ARCA" in normalized or "AMERICAN" in normalized or "AMEX" in normalized or "NYSE MKT" in normalized:
        return "AMS"
    if "NYSE" in normalized:
        return "NYS"
    return None


def _merge_payload(store: dict[str, dict[str, Any]], payload: dict[str, Any], *, preferred_source: str) -> None:
    canonical_symbol = str(payload.get("canonical_symbol") or "").upper()
    if not canonical_symbol:
        return
    current = store.get(canonical_symbol)
    if current is None:
        store[canonical_symbol] = payload
        return

    aliases = {
        *current.get("aliases", ()),
        *payload.get("aliases", ()),
    }
    provider_ids = dict(current.get("provider_ids", {}))
    provider_ids.update({key: value for key, value in payload.get("provider_ids", {}).items() if value})
    current.update(
        {
            "display_name_ko": payload.get("display_name_ko") or current.get("display_name_ko", ""),
            "display_name_en": payload.get("display_name_en") or current.get("display_name_en", ""),
            "aliases": sorted(str(alias).strip() for alias in aliases if str(alias).strip()),
            "provider_ids": provider_ids,
        }
    )
    if current.get("source") != preferred_source:
        current["source"] = preferred_source


def _normalized_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    canonical_symbol = normalize_canonical_symbol(str(payload.get("canonical_symbol") or ""))
    if canonical_symbol is None:
        return None
    market_code, ticker_or_code = canonical_symbol.split(":", maxsplit=1)
    aliases = {ticker_or_code, canonical_symbol}
    for candidate in payload.get("aliases", ()):
        text = str(candidate).strip()
        if text:
            aliases.add(text)
    display_name_ko = str(payload.get("display_name_ko") or "").strip()
    display_name_en = str(payload.get("display_name_en") or "").strip()
    if display_name_ko:
        aliases.add(display_name_ko)
    if display_name_en:
        aliases.add(display_name_en)
    provider_ids = dict(payload.get("provider_ids") or {})
    return {
        "canonical_symbol": canonical_symbol,
        "market_code": market_code,
        "ticker_or_code": ticker_or_code,
        "display_name_ko": display_name_ko,
        "display_name_en": display_name_en,
        "aliases": sorted(aliases),
        "provider_ids": {
            "kis_exchange_code": str(provider_ids.get("kis_exchange_code") or market_code).upper(),
            "sec_exchange": str(provider_ids.get("sec_exchange") or "").strip(),
            "polygon_primary_exchange": str(provider_ids.get("polygon_primary_exchange") or "").strip(),
            "twelve_mic_code": str(provider_ids.get("twelve_mic_code") or "").strip(),
            "figi": str(provider_ids.get("figi") or "").strip(),
        },
        "source": str(payload.get("source") or "").strip(),
    }


def _score_record(record: InstrumentRecord, query: str) -> int:
    direct_code = normalize_search_text(record.ticker_or_code)
    direct_names = [
        normalize_search_text(record.display_name_ko),
        normalize_search_text(record.display_name_en),
    ]
    aliases = [normalize_search_text(alias) for alias in record.aliases]
    if query == normalize_search_text(record.canonical_symbol):
        return 1000
    if query == direct_code:
        return 940
    if query in direct_names:
        return 900
    if query in aliases:
        return 860
    if direct_code.startswith(query):
        return 820
    if any(name.startswith(query) for name in direct_names if name):
        return 780
    if any(alias.startswith(query) for alias in aliases if alias):
        return 740
    if query in direct_code:
        return 720
    if any(query in name for name in direct_names if name):
        return 690
    if any(query in alias for alias in aliases if alias):
        return 660
    return 0
