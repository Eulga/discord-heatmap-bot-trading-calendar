from copy import deepcopy
import os
from pathlib import Path

import pytest

os.environ.setdefault("DISCORD_BOT_TOKEN", "test-token")

from bot.app import internal_api


@pytest.mark.asyncio
async def test_capture_heatmap_artifacts_updates_last_images(monkeypatch, tmp_path):
    state = {"commands": {}, "guilds": {}}
    saved = {"state": None}

    async def fake_capture(url: str, market_label: str) -> Path:
        path = tmp_path / f"{market_label}.png"
        path.write_bytes(b"image")
        return path

    monkeypatch.setattr(
        internal_api,
        "_CAPTURE_SPECS",
        {"kr": ("kheatmap", {"kospi": "https://example.com"}, fake_capture)},
    )
    monkeypatch.setattr(internal_api, "load_state", lambda: state)
    monkeypatch.setattr(internal_api, "save_state", lambda value: saved.__setitem__("state", deepcopy(value)))

    result = await internal_api.capture_heatmap_artifacts(["kr"])

    assert result["ok"] is True
    assert result["captured"][0]["label"] == "kospi"
    assert result["failed"] == []
    assert saved["state"]["commands"]["kheatmap"]["last_images"]["kospi"]["path"].endswith("kospi.png")
    assert saved["state"]["commands"]["kheatmap"]["last_run_at"]


@pytest.mark.asyncio
async def test_capture_heatmap_artifacts_returns_partial_failures(monkeypatch):
    state = {"commands": {}, "guilds": {}}

    async def fake_capture(url: str, market_label: str) -> Path:
        raise RuntimeError(f"{market_label} failed")

    monkeypatch.setattr(
        internal_api,
        "_CAPTURE_SPECS",
        {"us": ("usheatmap", {"sp500": "https://example.com"}, fake_capture)},
    )
    monkeypatch.setattr(internal_api, "load_state", lambda: state)
    monkeypatch.setattr(internal_api, "save_state", lambda _value: None)

    result = await internal_api.capture_heatmap_artifacts(["us"])

    assert result["ok"] is False
    assert result["captured"] == []
    assert result["failed"] == [{"label": "sp500", "message": "sp500 failed"}]


def test_markets_from_value_accepts_all_and_single_markets():
    assert internal_api._markets_from_value("all") == ["kr", "us"]
    assert internal_api._markets_from_value("kr") == ["kr"]
    assert internal_api._markets_from_value("us") == ["us"]


def test_markets_from_value_rejects_unknown_market():
    with pytest.raises(ValueError, match="market"):
        internal_api._markets_from_value("jp")
