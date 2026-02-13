import pytest

from bot.app.settings import KOREA_MARKET_URLS
from bot.markets.providers.korea import capture


@pytest.mark.live
@pytest.mark.asyncio
async def test_capture_korea_live():
    path = await capture(KOREA_MARKET_URLS["kospi"], "kospi_live_test")
    assert path.exists()
    assert path.stat().st_size > 120000
