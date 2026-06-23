import asyncio
import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bot.app.settings import INTEL_API_TIMEOUT_SECONDS, STOCK_DASHBOARD_API_BASE_URL, STOCK_DASHBOARD_INTERNAL_TOKEN

logger = logging.getLogger(__name__)


def _post_dashboard_delivery_results_sync(kind: str, results: list[dict[str, Any]]) -> None:
    if not results:
        return

    if not STOCK_DASHBOARD_API_BASE_URL or not STOCK_DASHBOARD_INTERNAL_TOKEN:
        logger.warning("[dashboard-delivery] %s result save skipped: dashboard config missing", kind)
        return

    request = Request(
        f"{STOCK_DASHBOARD_API_BASE_URL.rstrip('/')}/api/discord/deliveries/{kind}",
        data=json.dumps({"results": results}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "discord-heatmap-bot/1.0",
            "x-internal-token": STOCK_DASHBOARD_INTERNAL_TOKEN,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=INTEL_API_TIMEOUT_SECONDS) as response:
            if response.status >= 400:
                raise RuntimeError(f"dashboard-{kind}-result-save-failed:{response.status}")
    except HTTPError as exc:
        raise RuntimeError(f"dashboard-{kind}-result-save-failed:{exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"dashboard-{kind}-result-save-unreachable") from exc


async def record_dashboard_delivery_results(kind: str, results: list[dict[str, Any]]) -> None:
    if not results:
        return

    try:
        await asyncio.to_thread(_post_dashboard_delivery_results_sync, kind, results)
        logger.info("[dashboard-delivery] %s result saved results=%s", kind, len(results))
    except Exception as exc:
        logger.warning("[dashboard-delivery] %s result save failed: %s", kind, exc)
