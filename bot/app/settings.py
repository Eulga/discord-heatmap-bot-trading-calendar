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


def _env_channel_id(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw.isdigit() else None


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name, "").strip()
    return Path(raw) if raw else default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    normalized = raw.replace("|", ",").replace(";", ",").replace("\n", ",")
    values = [part.strip() for part in normalized.split(",") if part.strip()]
    return values or default

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set. Copy .env.example to .env and set the token.")

# Optional bootstrap forum channel copied into matching guild state at startup.
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
STATE_FILE = Path("data/state/state.json")
LEGACY_STATE_FILE = DATA_ROOT / "state.json"
STATE_BACKEND = os.getenv("STATE_BACKEND", "file").strip().lower() or "file"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
POSTGRES_STATE_KEY = os.getenv("POSTGRES_STATE_KEY", "default").strip() or "default"
LOG_FILE_PATH = _env_path("LOG_FILE_PATH", Path("data/logs/bot.log"))
LOG_RETENTION_DAYS = _env_int("LOG_RETENTION_DAYS", 7)
LOG_CONSOLE_ENABLED = _env_bool("LOG_CONSOLE_ENABLED", True)
INTERNAL_API_ENABLED = _env_bool("INTERNAL_API_ENABLED", False)
INTERNAL_API_HOST = os.getenv("INTERNAL_API_HOST", "0.0.0.0").strip() or "0.0.0.0"
INTERNAL_API_PORT = _env_int("INTERNAL_API_PORT", 8090)
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "").strip()

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

NEWS_BRIEFING_ENABLED = _env_bool("NEWS_BRIEFING_ENABLED", True)
NEWS_BRIEFING_TIME = os.getenv("NEWS_BRIEFING_TIME", "07:30").strip() or "07:30"
NEWS_BRIEFING_TRADING_DAYS_ONLY = _env_bool("NEWS_BRIEFING_TRADING_DAYS_ONLY", False)
STOCK_DASHBOARD_ALERT_DELIVERY_ENABLED = _env_bool("STOCK_DASHBOARD_ALERT_DELIVERY_ENABLED", True)
STOCK_DASHBOARD_ALERT_POLL_INTERVAL_SECONDS = max(
    30,
    min(_env_int("STOCK_DASHBOARD_ALERT_POLL_INTERVAL_SECONDS", 60), 600),
)
STOCK_DASHBOARD_NEWS_DELIVERY_ENABLED = _env_bool("STOCK_DASHBOARD_NEWS_DELIVERY_ENABLED", True)
STOCK_DASHBOARD_NEWS_MAX_PER_BATCH = max(1, min(_env_int("STOCK_DASHBOARD_NEWS_MAX_PER_BATCH", 6), 10))
STOCK_DASHBOARD_NEWS_POLL_INTERVAL_SECONDS = max(
    60,
    min(_env_int("STOCK_DASHBOARD_NEWS_POLL_INTERVAL_SECONDS", 300), 1800),
)
STOCK_DASHBOARD_REPORT_DELIVERY_ENABLED = _env_bool("STOCK_DASHBOARD_REPORT_DELIVERY_ENABLED", True)
STOCK_DASHBOARD_REPORT_POLL_INTERVAL_SECONDS = max(
    60,
    min(_env_int("STOCK_DASHBOARD_REPORT_POLL_INTERVAL_SECONDS", 300), 1800),
)
STOCK_DASHBOARD_MARKET_REPORT_FORUM_ID = _env_channel_id("STOCK_DASHBOARD_MARKET_REPORT_FORUM_ID")
STOCK_DASHBOARD_WATCHLIST_REPORT_FORUM_ID = _env_channel_id("STOCK_DASHBOARD_WATCHLIST_REPORT_FORUM_ID")
STOCK_DASHBOARD_WEB_BASE_URL = os.getenv("STOCK_DASHBOARD_WEB_BASE_URL", "").strip().rstrip("/")
NEWS_PROVIDER_KIND = os.getenv("NEWS_PROVIDER_KIND", "mock").strip().lower() or "mock"
MARKET_DATA_PROVIDER_KIND = os.getenv("MARKET_DATA_PROVIDER_KIND", "mock").strip().lower() or "mock"
STOCK_DASHBOARD_API_BASE_URL = os.getenv("STOCK_DASHBOARD_API_BASE_URL", "").strip().rstrip("/")
STOCK_DASHBOARD_INTERNAL_TOKEN = os.getenv("STOCK_DASHBOARD_INTERNAL_TOKEN", "").strip()
DART_API_KEY = os.getenv("DART_API_KEY", "").strip()
KIS_APP_KEY = os.getenv("KIS_APP_KEY", "").strip()
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET", "").strip()
MARKETAUX_API_TOKEN = os.getenv("MARKETAUX_API_TOKEN", "").strip()
MASSIVE_API_KEY = os.getenv("MASSIVE_API_KEY", "").strip() or os.getenv("POLYGON_API_KEY", "").strip()
POLYGON_API_KEY = MASSIVE_API_KEY
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "").strip()
OPENFIGI_API_KEY = os.getenv("OPENFIGI_API_KEY", "").strip()
NAVER_NEWS_CLIENT_ID = os.getenv("NAVER_NEWS_CLIENT_ID", "").strip()
NAVER_NEWS_CLIENT_SECRET = os.getenv("NAVER_NEWS_CLIENT_SECRET", "").strip()
NAVER_NEWS_DOMESTIC_QUERY = os.getenv("NAVER_NEWS_DOMESTIC_QUERY", "국내 증시").strip() or "국내 증시"
NAVER_NEWS_GLOBAL_QUERY = os.getenv("NAVER_NEWS_GLOBAL_QUERY", "미국 증시").strip() or "미국 증시"
NAVER_NEWS_DOMESTIC_QUERIES = _env_list(
    "NAVER_NEWS_DOMESTIC_QUERIES",
    [NAVER_NEWS_DOMESTIC_QUERY, "코스피 지수", "코스닥 지수", "원달러 환율", "한국은행 금리"],
)
NAVER_NEWS_GLOBAL_QUERIES = _env_list(
    "NAVER_NEWS_GLOBAL_QUERIES",
    [NAVER_NEWS_GLOBAL_QUERY, "나스닥", "S&P 500", "연준", "FOMC"],
)
NAVER_NEWS_DOMESTIC_STOCK_QUERIES = _env_list(
    "NAVER_NEWS_DOMESTIC_STOCK_QUERIES",
    ["삼성전자", "SK하이닉스", "현대차", "한화에어로스페이스", "셀트리온"],
)
NAVER_NEWS_GLOBAL_STOCK_QUERIES = _env_list(
    "NAVER_NEWS_GLOBAL_STOCK_QUERIES",
    ["엔비디아", "애플", "마이크로소프트", "테슬라", "마이크론"],
)
MARKETAUX_NEWS_GLOBAL_QUERY = (
    os.getenv("MARKETAUX_NEWS_GLOBAL_QUERY", "Nasdaq OR S&P 500 OR Federal Reserve OR FOMC OR Treasury yields").strip()
    or "Nasdaq OR S&P 500 OR Federal Reserve OR FOMC OR Treasury yields"
)
MARKETAUX_NEWS_GLOBAL_QUERIES = _env_list(
    "MARKETAUX_NEWS_GLOBAL_QUERIES",
    [
        MARKETAUX_NEWS_GLOBAL_QUERY,
        "US stocks OR Nasdaq",
        "Federal Reserve OR FOMC",
        "Treasury yields OR CPI OR PCE",
    ],
)
MARKETAUX_NEWS_COUNTRIES = _env_list("MARKETAUX_NEWS_COUNTRIES", ["us"])
MARKETAUX_NEWS_LANGUAGE = _env_list("MARKETAUX_NEWS_LANGUAGE", ["en"])
NAVER_NEWS_LIMIT_PER_REGION = max(1, min(_env_int("NAVER_NEWS_LIMIT_PER_REGION", 20), 20))
NAVER_NEWS_MAX_AGE_HOURS = max(1, min(_env_int("NAVER_NEWS_MAX_AGE_HOURS", 24), 72))
INTEL_API_TIMEOUT_SECONDS = max(1, min(_env_int("INTEL_API_TIMEOUT_SECONDS", 5), 10))
INTEL_API_RETRY_COUNT = max(0, min(_env_int("INTEL_API_RETRY_COUNT", 1), 1))

EOD_SUMMARY_ENABLED = _env_bool("EOD_SUMMARY_ENABLED", False)
EOD_SUMMARY_TIME = os.getenv("EOD_SUMMARY_TIME", "16:20").strip() or "16:20"

WATCH_FEATURE_ENABLED = _env_bool("WATCH_FEATURE_ENABLED", False)
WATCH_POLL_ENABLED = _env_bool("WATCH_POLL_ENABLED", False)
WATCH_POLL_INTERVAL_SECONDS = _env_int("WATCH_POLL_INTERVAL_SECONDS", 60)
WATCH_ALERT_THRESHOLD_PCT = _env_float("WATCH_ALERT_THRESHOLD_PCT", 3.0)
INSTRUMENT_REGISTRY_REFRESH_ENABLED = _env_bool("INSTRUMENT_REGISTRY_REFRESH_ENABLED", False)
INSTRUMENT_REGISTRY_REFRESH_TIME = os.getenv("INSTRUMENT_REGISTRY_REFRESH_TIME", "06:20").strip() or "06:20"

ADMIN_STATUS_CHANNEL_ID = _env_channel_id("ADMIN_STATUS_CHANNEL_ID")
NEWS_TARGET_FORUM_ID = _env_channel_id("NEWS_TARGET_FORUM_ID")
EOD_TARGET_FORUM_ID = _env_channel_id("EOD_TARGET_FORUM_ID")
SCHEDULE_ALERT_CHANNEL_ID = _env_channel_id("SCHEDULE_ALERT_CHANNEL_ID")
STOCK_DASHBOARD_ROLE_CHANNEL_ID = _env_channel_id("STOCK_DASHBOARD_ROLE_CHANNEL_ID")
STOCK_DASHBOARD_ROLE_SYNC_ENABLED = _env_bool("STOCK_DASHBOARD_ROLE_SYNC_ENABLED", True)
STOCK_DASHBOARD_ROLE_SYNC_INTERVAL_SECONDS = max(
    300,
    min(_env_int("STOCK_DASHBOARD_ROLE_SYNC_INTERVAL_SECONDS", 300), 3600),
)
STOCK_DASHBOARD_ROLE_PREFIX = os.getenv("STOCK_DASHBOARD_ROLE_PREFIX", "").strip()
