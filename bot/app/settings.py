import os
from datetime import timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw) if raw.isdigit() else default


def _env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name, "").strip()
    return Path(raw) if raw else default


TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set. Copy .env.example to .env and set the token.")

# Optional fallback forum channel if a guild-specific mapping is not configured.
_default_forum_channel_id = os.getenv("DEFAULT_FORUM_CHANNEL_ID", "").strip()
DEFAULT_FORUM_CHANNEL_ID = int(_default_forum_channel_id) if _default_forum_channel_id.isdigit() else None
CACHE_TTL_SECONDS = 3600
_global_admin_ids = os.getenv("DISCORD_GLOBAL_ADMIN_USER_IDS", "").strip()
DISCORD_GLOBAL_ADMIN_USER_IDS: set[int] = {
    int(x.strip()) for x in _global_admin_ids.split(",") if x.strip().isdigit()
}

try:
    TIMEZONE = ZoneInfo("Asia/Seoul")
except Exception:
    TIMEZONE = timezone(timedelta(hours=9))

DATA_ROOT = Path("data/heatmaps")
STATE_FILE = DATA_ROOT / "state.json"
LOG_FILE_PATH = _env_path("LOG_FILE_PATH", Path("data/logs/bot.log"))
LOG_RETENTION_DAYS = _env_int("LOG_RETENTION_DAYS", 7)
LOG_CONSOLE_ENABLED = _env_bool("LOG_CONSOLE_ENABLED", True)

KOREA_MARKET_URLS: dict[str, str] = {
    "kospi": "https://markets.hankyung.com/marketmap/kospi",
    "kosdaq": "https://markets.hankyung.com/marketmap/kosdaq",
}
KOREA_CAPTURE_SELECTOR = ".marketmap-wrap"

US_MARKET_URLS: dict[str, str] = {
    "sp500": "https://finviz.com/map.ashx?t=sec",
    "russell2000": "https://finviz.com/map.ashx?t=sec_rut",
}
US_CAPTURE_SELECTOR = "#map"
US_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)
