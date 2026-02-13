from bot.features.kheatmap import policy as k_policy
from bot.features.usheatmap import policy as u_policy


def test_kheatmap_title(monkeypatch):
    monkeypatch.setattr(k_policy, "date_key", lambda: "2026-02-13")
    assert k_policy.build_post_title() == "[2026-02-13 한국장 히트맵]"


def test_usheatmap_title(monkeypatch):
    monkeypatch.setattr(u_policy, "date_key", lambda: "2026-02-13")
    assert u_policy.build_post_title() == "[2026-02-13 미국장 히트맵]"
