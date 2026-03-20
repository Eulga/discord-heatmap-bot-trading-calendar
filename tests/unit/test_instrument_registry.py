from io import BytesIO
import zipfile

from bot.intel.instrument_registry import (
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


def test_build_sec_records_maps_supported_exchanges():
    records = build_sec_records(
        [
            {"ticker": "NVDA", "name": "NVIDIA CORP", "exchange": "Nasdaq"},
            {"ticker": "KO", "name": "COCA-COLA CO", "exchange": "NYSE"},
            {"ticker": "SPY", "name": "SPDR S&P 500 ETF TRUST", "exchange": "NYSE Arca"},
        ]
    )

    assert {record["canonical_symbol"] for record in records} == {"NAS:NVDA", "NYS:KO", "AMS:SPY"}


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
