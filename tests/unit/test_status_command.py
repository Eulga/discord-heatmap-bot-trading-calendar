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
    assert "polygon_reference" in rows
