from datetime import timedelta

from bot.markets.cache import is_cache_valid


def test_cache_valid_exact_one_hour(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"x")

    from bot.common.clock import now_kst

    now = now_kst()
    captured_at = (now - timedelta(hours=1)).isoformat()
    assert is_cache_valid(p, captured_at, now) is True


def test_cache_invalid_over_one_hour(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"x")

    from bot.common.clock import now_kst

    now = now_kst()
    captured_at = (now - timedelta(hours=1, seconds=1)).isoformat()
    assert is_cache_valid(p, captured_at, now) is False
