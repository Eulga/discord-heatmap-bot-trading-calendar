import json
from io import BytesIO
import zipfile

import bot.intel.instrument_registry as registry_module
from bot.intel.instrument_registry import (
    InstrumentRecord,
    InstrumentRegistry,
    ProviderIds,
    build_krx_elw_records,
    build_krx_etf_records,
    build_krx_etn_records,
    build_krx_pf_records,
    clear_registry_cache,
    build_sec_records,
    load_registry,
    normalize_stored_watch_symbol,
    parse_dart_corpcode,
    registry_status,
)


def test_normalize_stored_watch_symbol_promotes_domestic_code_and_us_ticker():
    assert normalize_stored_watch_symbol("005930")[0] == "KRX:005930"
    assert normalize_stored_watch_symbol("AAPL")[0] == "NAS:AAPL"


def test_registry_search_matches_korean_name():
    results = load_registry().search("삼성전자", limit=5)

    assert results
    assert results[0].record.canonical_symbol == "KRX:005930"


def test_registry_search_matches_kosdaq_name():
    results = load_registry().search("제주반도체", limit=5)

    assert results
    assert results[0].record.display_name_ko == "제주반도체"


def test_registry_search_matches_krx_etf_name():
    results = load_registry().search("KODEX 200", limit=5)

    assert results
    assert results[0].record.canonical_symbol == "KRX:069500"


def test_registry_search_matches_krx_etn_name():
    results = load_registry().search("KB 천연가스 선물 ETN(H)", limit=5)

    assert results
    assert results[0].record.canonical_symbol == "KRX:580020"


def test_registry_search_matches_krx_elw_name():
    results = load_registry().search("KBL002삼성전자콜", limit=5)

    assert results
    assert results[0].record.canonical_symbol == "KRX:58L002"


def test_registry_search_matches_krx_pf_name():
    results = load_registry().search("대신 KOSPI200인덱스 X클래스", limit=5)

    assert results
    assert results[0].record.canonical_symbol == "KRX:0106J0"


def test_build_sec_records_maps_supported_exchanges():
    records = build_sec_records(
        [
            {"ticker": "NVDA", "name": "NVIDIA CORP", "exchange": "Nasdaq"},
            {"ticker": "KO", "name": "COCA-COLA CO", "exchange": "NYSE"},
            {"ticker": "SPY", "name": "SPDR S&P 500 ETF TRUST", "exchange": "NYSE Arca"},
        ]
    )

    assert {record["canonical_symbol"] for record in records} == {"NAS:NVDA", "NYS:KO", "AMS:SPY"}


def test_build_krx_etf_records_maps_finder_rows():
    records = build_krx_etf_records(
        [
            {"full_code": "KR7069500007", "short_code": "069500", "codeName": "KODEX 200"},
            {"full_code": "KR7102110004", "short_code": "102110", "codeName": "TIGER 200"},
        ]
    )

    assert {record["canonical_symbol"] for record in records} == {"KRX:069500", "KRX:102110"}


def test_build_krx_etn_records_maps_finder_rows():
    records = build_krx_etn_records(
        [
            {"full_code": "KRG580000203", "short_code": "580020", "codeName": "KB 천연가스 선물 ETN(H)"},
            {"full_code": "KRG580000211", "short_code": "580021", "codeName": "KB 인버스 천연가스 선물 ETN"},
        ]
    )

    assert {record["canonical_symbol"] for record in records} == {"KRX:580020", "KRX:580021"}


def test_build_krx_elw_records_maps_finder_rows():
    records = build_krx_elw_records(
        [
            {"full_code": "KR658L002009", "short_code": "58L002", "codeName": "KBL002삼성전자콜"},
            {"full_code": "KR658L003007", "short_code": "58L003", "codeName": "KBL003삼성전자콜"},
        ]
    )

    assert {record["canonical_symbol"] for record in records} == {"KRX:58L002", "KRX:58L003"}


def test_build_krx_pf_records_maps_finder_rows():
    records = build_krx_pf_records(
        [
            {"full_code": "KR60106J0003", "short_code": "0106J0", "codeName": "대신 KOSPI200인덱스 X클래스"},
            {"full_code": "KR60107M0001", "short_code": "0107M0", "codeName": "유진 챔피언중단기크레딧 X클래스"},
        ]
    )

    assert {record["canonical_symbol"] for record in records} == {"KRX:0106J0", "KRX:0107M0"}


def test_parse_dart_corpcode_reads_stock_code_from_zip_bytes():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <result>
      <list>
        <corp_code>001</corp_code>
        <corp_name>삼성전자</corp_name>
        <corp_eng_name>Samsung Electronics</corp_eng_name>
        <stock_code>005930</stock_code>
      </list>
    </result>
    """
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CORPCODE.xml", xml)

    records = parse_dart_corpcode(buffer.getvalue())

    assert len(records) == 1
    assert records[0]["canonical_symbol"] == "KRX:005930"
    assert records[0]["display_name_ko"] == "삼성전자"


def test_registry_status_reports_loaded_counts():
    status = registry_status()

    assert status["status"] == "ok"
    assert "loaded=" in status["message"]
    assert "source=" in status["message"]


def test_load_registry_prefers_runtime_artifact(monkeypatch, tmp_path):
    runtime_file = tmp_path / "runtime-instrument-registry.json"
    bundled_file = tmp_path / "bundled-instrument-registry.json"
    seed_file = tmp_path / "instrument-registry-seed.json"
    bundled_file.write_text(
        json.dumps(
            {
                "generated_at": "2026-03-23T00:00:00+00:00",
                "records": [
                    {
                        "canonical_symbol": "KRX:005930",
                        "market_code": "KRX",
                        "ticker_or_code": "005930",
                        "display_name_ko": "삼성전자",
                        "display_name_en": "",
                        "aliases": ["삼성전자", "005930", "KRX:005930"],
                        "provider_ids": {"kis_exchange_code": "KRX"},
                        "source": "dart",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    runtime_file.write_text(
        json.dumps(
            {
                "generated_at": "2026-03-24T00:00:00+00:00",
                "records": [
                    {
                        "canonical_symbol": "KRX:58L002",
                        "market_code": "KRX",
                        "ticker_or_code": "58L002",
                        "display_name_ko": "KBL002삼성전자콜",
                        "display_name_en": "",
                        "aliases": ["KBL002삼성전자콜", "58L002", "KRX:58L002"],
                        "provider_ids": {"kis_exchange_code": "KRX"},
                        "source": "krx-elw",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seed_file.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(registry_module, "RUNTIME_REGISTRY_FILE", runtime_file)
    monkeypatch.setattr(registry_module, "REGISTRY_FILE", bundled_file)
    monkeypatch.setattr(registry_module, "SEED_FILE", seed_file)
    clear_registry_cache()

    loaded = registry_module.load_registry()

    assert loaded.generated_at == "2026-03-24T00:00:00+00:00"
    assert loaded.metadata["active_source"] == "runtime"
    assert loaded.get("KRX:58L002") is not None
    clear_registry_cache()


def test_save_registry_uses_atomic_write_json(monkeypatch, tmp_path):
    target = tmp_path / "instrument-registry.json"
    calls: dict[str, object] = {}

    def fake_atomic_write_json(path, payload):
        calls["path"] = path
        calls["payload"] = payload

    monkeypatch.setattr(registry_module, "atomic_write_json", fake_atomic_write_json)

    registry = InstrumentRegistry(
        generated_at="2026-03-23T00:00:00+00:00",
        records=(
            InstrumentRecord(
                canonical_symbol="KRX:005930",
                market_code="KRX",
                ticker_or_code="005930",
                display_name_ko="삼성전자",
                display_name_en="Samsung Electronics",
                aliases=("삼성전자", "Samsung Electronics", "005930", "KRX:005930"),
                provider_ids=ProviderIds(kis_exchange_code="KRX"),
                source="dart",
            ),
        ),
    )

    registry_module.save_registry(registry, path=target)

    assert calls["path"] == target
    payload = calls["payload"]
    assert isinstance(payload, dict)
    assert payload["records"][0]["canonical_symbol"] == "KRX:005930"
