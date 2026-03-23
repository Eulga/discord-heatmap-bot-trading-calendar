from bot.features.status import command as status_command


def test_fmt_dict_rows_formats_bool_provider_status():
    text = status_command._fmt_dict_rows({"kis_quote": {"ok": True, "message": "configured", "updated_at": ""}})

    assert "kis_quote: ok" in text


def test_default_job_rows_marks_eod_paused_by_default(monkeypatch):
    monkeypatch.setattr(status_command, "EOD_SUMMARY_ENABLED", False)
    rows = status_command._default_job_rows()

    assert rows["eod_summary"]["status"] == "paused"


def test_default_provider_rows_include_registry_and_optional_sources():
    rows = status_command._default_provider_rows()

    assert "instrument_registry" in rows
    assert "kis_quote" in rows
    assert "massive_reference" in rows


def test_merge_defaults_normalizes_legacy_polygon_reference_key():
    merged = status_command._merge_defaults({"polygon_reference": {"ok": True, "message": "legacy", "updated_at": ""}}, {})

    assert "massive_reference" in merged
    assert "polygon_reference" not in merged


def test_merge_defaults_normalizes_legacy_market_data_provider_key():
    merged = status_command._merge_defaults({"market_data_provider": {"ok": True, "message": "legacy", "updated_at": ""}}, {})

    assert "kis_quote" in merged
    assert "market_data_provider" not in merged


def test_merge_defaults_prefers_canonical_provider_key_over_legacy_alias():
    merged = status_command._merge_defaults(
        {
            "market_data_provider": {"ok": False, "message": "legacy", "updated_at": ""},
            "kis_quote": {"ok": True, "message": "quote:KRX:005930", "updated_at": ""},
        },
        {},
    )

    assert merged["kis_quote"]["message"] == "quote:KRX:005930"
