from pathlib import Path
from uuid import uuid4

from playwright.async_api import async_playwright

from bot.app.settings import DATA_ROOT, US_CAPTURE_SELECTOR, US_USER_AGENT
from bot.common.clock import capture_stamp
from bot.markets.providers._common import ensure_capture_file


async def wait_for_us_render_ready(page) -> None:
    await page.wait_for_function(
        """
        () => {
          const map = document.querySelector('#map');
          if (!map) return false;
          const rect = map.getBoundingClientRect();
          if (rect.width < 900 || rect.height < 500) return false;
          const canvas = map.querySelector('canvas');
          if (!canvas || canvas.width < 600 || canvas.height < 300) return false;

          try {
            const ctx = canvas.getContext('2d');
            if (!ctx) return false;
            const sx = Math.floor(canvas.width * 0.1);
            const sy = Math.floor(canvas.height * 0.1);
            const sw = Math.max(20, Math.floor(canvas.width * 0.8));
            const sh = Math.max(20, Math.floor(canvas.height * 0.8));
            const data = ctx.getImageData(sx, sy, sw, sh).data;
            let first = -1;
            let varied = false;
            for (let i = 0; i < data.length; i += 16) {
              const v = (data[i] << 16) | (data[i + 1] << 8) | data[i + 2];
              if (first === -1) first = v;
              else if (v !== first) {
                varied = true;
                break;
              }
            }
            return varied;
          } catch {
            return map.querySelectorAll('canvas').length >= 2;
          }
        }
        """,
        timeout=25000,
    )
    await page.wait_for_timeout(800)


async def capture(url: str, market_label: str) -> Path:
    output_dir = DATA_ROOT / "usheatmap"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{market_label}_{capture_stamp()}_{uuid4().hex[:8]}.png"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1700, "height": 1300},
            user_agent=US_USER_AGENT,
            locale="en-US",
        )
        page = await context.new_page()
        try:
            last_error: Exception | None = None
            for attempt in range(2):
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    await page.wait_for_timeout(2500)
                    await page.wait_for_selector(US_CAPTURE_SELECTOR, timeout=20000)
                    await wait_for_us_render_ready(page)
                    await page.locator(US_CAPTURE_SELECTOR).first.screenshot(path=str(output_path), type="png")
                    ensure_capture_file(output_path, min_size_bytes=70000)
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt == 0:
                        await page.wait_for_timeout(2500)
                        continue
                    raise
            if last_error is not None:
                raise last_error
        finally:
            await context.close()
            await browser.close()

    return output_path
