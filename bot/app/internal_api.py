from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from pathlib import Path
from typing import Any

from aiohttp import web

from bot.app.settings import (
    INTERNAL_API_ENABLED,
    INTERNAL_API_HOST,
    INTERNAL_API_PORT,
    INTERNAL_API_TOKEN,
    KOREA_MARKET_URLS,
    US_MARKET_URLS,
)
from bot.common.clock import now_kst
from bot.forum.repository import get_command_state, load_state, save_state
from bot.markets.providers.korea import capture as capture_korea
from bot.markets.providers.us import capture as capture_us

logger = logging.getLogger(__name__)

CaptureFunc = Callable[[str, str], Awaitable[Path]]
HeatmapMarket = str

_CAPTURE_SPECS: dict[HeatmapMarket, tuple[str, dict[str, str], CaptureFunc]] = {
    "kr": ("kheatmap", KOREA_MARKET_URLS, capture_korea),
    "us": ("usheatmap", US_MARKET_URLS, capture_us),
}


def _request_token(request: web.Request) -> str:
    header_token = request.headers.get("x-internal-token", "").strip()
    if header_token:
        return header_token

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token.strip()

    return ""


def _authorized(request: web.Request) -> bool:
    return bool(INTERNAL_API_TOKEN) and _request_token(request) == INTERNAL_API_TOKEN


def _markets_from_value(value: Any) -> list[HeatmapMarket]:
    market = str(value or "all").strip().lower()
    if market == "all":
        return ["kr", "us"]
    if market in _CAPTURE_SPECS:
        return [market]
    raise ValueError("market은 all, kr, us 중 하나여야 합니다.")


async def capture_heatmap_artifacts(markets: Iterable[HeatmapMarket]) -> dict[str, Any]:
    state = load_state()
    captured: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []

    for market in markets:
        command_key, targets, capture_func = _CAPTURE_SPECS[market]
        command_state = get_command_state(state, command_key)
        last_images = command_state["last_images"]

        for market_label, url in targets.items():
            try:
                captured_path = await capture_func(url=url, market_label=market_label)
            except Exception as exc:
                failed.append({"label": market_label, "message": str(exc).strip() or "unknown error"})
                continue

            captured_at = now_kst().isoformat()
            last_images[market_label] = {
                "path": str(captured_path),
                "captured_at": captured_at,
            }
            captured.append(
                {
                    "capturedAt": captured_at,
                    "file": str(captured_path),
                    "label": market_label,
                    "market": market,
                }
            )

        command_state["last_run_at"] = now_kst().isoformat()

    save_state(state)
    return {
        "captured": captured,
        "failed": failed,
        "ok": bool(captured) and not failed,
    }


async def _handle_health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def _handle_generate(request: web.Request) -> web.Response:
    if not _authorized(request):
        return web.json_response({"error": "internal token이 올바르지 않습니다."}, status=403)

    lock: asyncio.Lock = request.app["heatmap_lock"]
    if lock.locked():
        return web.json_response({"error": "히트맵 생성이 이미 진행 중입니다."}, status=409)

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    try:
        markets = _markets_from_value(payload.get("market") if isinstance(payload, dict) else "all")
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=400)

    async with lock:
        result = await capture_heatmap_artifacts(markets)

    status = 200 if result["captured"] else 502
    return web.json_response(result, status=status)


async def start_internal_api_server() -> web.AppRunner | None:
    if not INTERNAL_API_ENABLED:
        return None

    if not INTERNAL_API_TOKEN:
        logger.error("[internal-api] INTERNAL_API_TOKEN이 없어 내부 API를 시작하지 않습니다.")
        return None

    app = web.Application()
    app["heatmap_lock"] = asyncio.Lock()
    app.router.add_get("/health", _handle_health)
    app.router.add_post("/internal/heatmaps/generate", _handle_generate)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, INTERNAL_API_HOST, INTERNAL_API_PORT)
    await site.start()
    logger.info("[internal-api] 내부 API 시작 host=%s port=%s", INTERNAL_API_HOST, INTERNAL_API_PORT)
    return runner
