from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from bot.intel.instrument_registry import (
    MODULE_ROOT,
    REGISTRY_FILE,
    SEED_FILE,
    build_registry,
    fetch_dart_corpcode_bytes,
    fetch_krx_elw_rows,
    fetch_krx_etf_rows,
    fetch_krx_etn_rows,
    fetch_krx_pf_rows,
    fetch_sec_company_tickers,
    read_dart_corpcode_bytes,
    save_registry,
)


REPO_ROOT = MODULE_ROOT.parent.parent
RAW_DART_FILE = REPO_ROOT / "docs" / "references" / "external" / "opendart-corpcode.xml"
RAW_SEC_FILE = REPO_ROOT / "docs" / "references" / "external" / "sec-company-tickers-exchange.json"

load_dotenv(REPO_ROOT / ".env")


def _load_seed_records() -> list[dict]:
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))


def _load_sec_rows() -> list[dict]:
    if RAW_SEC_FILE.exists():
        payload = json.loads(RAW_SEC_FILE.read_text(encoding="utf-8"))
        rows = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return fetch_sec_company_tickers()


def _load_dart_bytes(dart_api_key: str | None) -> bytes | None:
    if RAW_DART_FILE.exists():
        return read_dart_corpcode_bytes(RAW_DART_FILE)
    if dart_api_key:
        return fetch_dart_corpcode_bytes(dart_api_key)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the generated instrument registry artifact.")
    parser.add_argument("--output", type=Path, default=REGISTRY_FILE)
    parser.add_argument("--dart-api-key", default=os.getenv("DART_API_KEY", "").strip())
    args = parser.parse_args()

    registry = build_registry(
        seed_records=_load_seed_records(),
        dart_xml_bytes=_load_dart_bytes(args.dart_api_key or None),
        sec_payload=_load_sec_rows(),
        krx_etf_rows=fetch_krx_etf_rows(),
        krx_etn_rows=fetch_krx_etn_rows(),
        krx_elw_rows=fetch_krx_elw_rows(),
        krx_pf_rows=fetch_krx_pf_rows(),
    )
    save_registry(registry, path=args.output)
    print(
        "instrument registry built",
        f"output={args.output}",
        f"records={len(registry.records)}",
        f"generated_at={registry.generated_at}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
