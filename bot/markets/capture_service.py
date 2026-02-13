from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from bot.app.types import AppState
from bot.common.clock import now_kst
from bot.forum.repository import get_command_state
from bot.markets.cache import is_cache_valid

CaptureFunc = Callable[[str, str], Awaitable[Path]]


async def get_or_capture_images(
    state: AppState,
    command_key: str,
    targets: dict[str, str],
    capture_func: CaptureFunc,
) -> tuple[list[Path], list[str], dict[str, str]]:
    command_state = get_command_state(state, command_key)
    last_images = command_state["last_images"]

    successful_paths: list[Path] = []
    failed: list[str] = []
    source_map: dict[str, str] = {}
    now = now_kst()

    for market_label, url in targets.items():
        cache = last_images.get(market_label, {})
        cached_path_value = cache.get("path")
        cached_at = cache.get("captured_at")

        if isinstance(cached_path_value, str) and isinstance(cached_at, str):
            cached_path = Path(cached_path_value)
            if is_cache_valid(cached_path, cached_at, now):
                successful_paths.append(cached_path)
                source_map[market_label] = "cached"
                continue

        try:
            captured_path = await capture_func(url=url, market_label=market_label)
            successful_paths.append(captured_path)
            source_map[market_label] = "captured"
            last_images[market_label] = {
                "path": str(captured_path),
                "captured_at": now_kst().isoformat(),
            }
        except PlaywrightTimeoutError:
            failed.append(f"{market_label}: timed out while rendering")
        except Exception as exc:
            message = str(exc).strip()
            if "Executable doesn't exist" in message:
                message = "Chromium is not installed. Run: python -m playwright install chromium"
            failed.append(f"{market_label}: {message or 'unknown error'}")

    command_state["last_run_at"] = now_kst().isoformat()
    return successful_paths, failed, source_map
