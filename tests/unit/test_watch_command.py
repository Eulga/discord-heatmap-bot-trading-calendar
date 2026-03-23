from bot.features.watch.command import resolve_watch_add_symbol, resolve_watch_remove_symbol


def test_resolve_watch_add_symbol_supports_korean_name():
    resolved, error = resolve_watch_add_symbol("삼성전자")

    assert error is None
    assert resolved == "KRX:005930"


def test_resolve_watch_add_symbol_supports_us_ticker():
    resolved, error = resolve_watch_add_symbol("AAPL")

    assert error is None
    assert resolved == "NAS:AAPL"


def test_resolve_watch_add_symbol_supports_krx_etf_name():
    resolved, error = resolve_watch_add_symbol("KODEX 200")

    assert error is None
    assert resolved == "KRX:069500"


def test_resolve_watch_add_symbol_supports_krx_etn_name():
    resolved, error = resolve_watch_add_symbol("KB 천연가스 선물 ETN(H)")

    assert error is None
    assert resolved == "KRX:580020"


def test_resolve_watch_add_symbol_rejects_ambiguous_query():
    resolved, error = resolve_watch_add_symbol("현대")

    assert resolved is None
    assert error is not None
    assert "여러 후보" in error


def test_resolve_watch_remove_symbol_supports_name_match():
    resolved, error = resolve_watch_remove_symbol("삼성전자", guild_symbols=["KRX:005930"])

    assert error is None
    assert resolved == "KRX:005930"
