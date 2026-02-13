import asyncio
from pathlib import Path
from uuid import uuid4

from playwright.async_api import async_playwright

from bot.app.settings import DATA_ROOT, KOREA_CAPTURE_SELECTOR
from bot.common.clock import capture_stamp
from bot.markets.providers._common import ensure_capture_file


async def wait_for_korea_render_ready(page) -> None:
    await page.wait_for_function(
        """
        () => {
          const root = document.querySelector('.marketmap-wrap');
          const map = document.querySelector('.fiq-marketmap');
          if (!root || !map) return false;
          const rootRect = root.getBoundingClientRect();
          const mapRect = map.getBoundingClientRect();
          const textCount = map.querySelectorAll('text').length;
          return (
            rootRect.width > 1200 &&
            rootRect.height > 700 &&
            mapRect.width > 1000 &&
            mapRect.height > 500 &&
            textCount > 120
          );
        }
        """,
        timeout=25000,
    )
    await asyncio.sleep(1.0)


async def capture(url: str, market_label: str) -> Path:
    output_dir = DATA_ROOT / "kheatmap"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{market_label}_{capture_stamp()}_{uuid4().hex[:8]}.png"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 1400})
        page = await context.new_page()
        try:
            last_error: Exception | None = None
            for attempt in range(2):
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_selector(KOREA_CAPTURE_SELECTOR, timeout=15000)
                    await page.wait_for_selector(".fiq-marketmap", timeout=15000)
                    await page.wait_for_load_state("networkidle", timeout=12000)
                    await wait_for_korea_render_ready(page)
                    await page.locator(KOREA_CAPTURE_SELECTOR).screenshot(path=str(output_path), type="png")
                    ensure_capture_file(output_path, min_size_bytes=120000)
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt == 0:
                        await page.wait_for_timeout(2000)
                        continue
                    raise
            if last_error is not None:
                raise last_error
        finally:
            await context.close()
            await browser.close()

    return output_path
