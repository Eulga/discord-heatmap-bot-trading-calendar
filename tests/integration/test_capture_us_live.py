import pytest

from bot.app.settings import US_MARKET_URLS
from bot.markets.providers.us import capture


@pytest.mark.live
@pytest.mark.asyncio
async def test_capture_us_live():
    path = await capture(US_MARKET_URLS["sp500"], "sp500_live_test")
    assert path.exists()
    assert path.stat().st_size > 70000
