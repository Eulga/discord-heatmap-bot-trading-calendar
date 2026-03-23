from io import BytesIO
import zipfile

from bot.intel.instrument_registry import (
    build_krx_etf_records,
    build_krx_etn_records,
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
