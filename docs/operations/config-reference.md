# Config Reference

## Scope
- This document summarizes the configuration boundary used by the current project structure.
- It is not a deep runtime spec and does not attempt to restate every provider query list or heuristic constant.
- For current implementation details, use `../specs/as-is-functional-spec.md`.

## Secret vs Non-Secret Boundary
- Secrets, tokens, and credentials belong in env.
- Mutable per-guild routing and other operational state belong in PostgreSQL runtime state tables.
- The legacy JSON state document is now migration input/backup only; runtime route, scheduler, daily-post, status, and watch paths use split PostgreSQL rows.
- Bootstrap/default channel IDs may exist in env, but they are not the primary runtime source of truth in the inspected runtime paths.

## Required Secrets
- Always required:
  - `DISCORD_BOT_TOKEN`
- Conditionally required when the related live feature path is selected:
  - `NAVER_NEWS_CLIENT_ID`, `NAVER_NEWS_CLIENT_SECRET`
    - required when `NEWS_PROVIDER_KIND` is `naver` or `hybrid`
  - `MARKETAUX_API_TOKEN`
    - required when `NEWS_PROVIDER_KIND` is `marketaux` or `hybrid`
  - `KIS_APP_KEY`, `KIS_APP_SECRET`
    - required when `MARKET_DATA_PROVIDER_KIND` is `kis`
  - `DART_API_KEY`
    - required only when instrument registry refresh actually runs a live rebuild
  - `DATABASE_URL`
    - required for current bot startup because runtime state is PostgreSQL-backed
- Optional provider/status envs with narrower current roles:
  - `MASSIVE_API_KEY` or legacy `POLYGON_API_KEY`
    - optional US quote fallback only when `MARKET_DATA_PROVIDER_KIND` is `kis`
  - `TWELVEDATA_API_KEY`
    - currently only affects `/source-status` default rows
  - `OPENFIGI_API_KEY`
    - currently only affects `/source-status` default rows
  - `ADMIN_STATUS_CHANNEL_ID`
    - parsed from env but no direct runtime use was found in current bot code

## Bootstrap-only Env Vars
- The inspected runtime docs currently treat these as bootstrap/default route IDs rather than the primary runtime routing source:
  - `DEFAULT_FORUM_CHANNEL_ID`
  - `NEWS_TARGET_FORUM_ID`
  - `EOD_TARGET_FORUM_ID`
- Startup copies these IDs into per-guild state only when the channel is accessible, the type matches, a guild context exists, and state does not already have that route.
- Runtime routing should be checked in the configured app-state backend when validating actual behavior.
- Watch routing no longer has an env bootstrap/default channel; current code requires per-guild `watch_forum_channel_id` in state.

## Active Runtime Request Knobs
- Shared live-provider request behavior:
  - `INTEL_API_TIMEOUT_SECONDS`
  - `INTEL_API_RETRY_COUNT`
- These are active runtime envs used by current live provider construction for news and market-data paths.

## Feature Toggles
- News:
  - `NEWS_BRIEFING_ENABLED`
  - `NEWS_BRIEFING_TIME`
  - `NEWS_BRIEFING_TRADING_DAYS_ONLY`
  - `NEWS_PROVIDER_KIND`
- Watch:
  - `WATCH_POLL_ENABLED`
  - `WATCH_POLL_INTERVAL_SECONDS`
  - `WATCH_ALERT_THRESHOLD_PCT`
  - `MARKET_DATA_PROVIDER_KIND`
- EOD:
  - `EOD_SUMMARY_ENABLED`
  - `EOD_SUMMARY_TIME`
- Registry refresh:
  - `INSTRUMENT_REGISTRY_REFRESH_ENABLED`
  - `INSTRUMENT_REGISTRY_REFRESH_TIME`
- Logging:
  - `LOG_FILE_PATH`
  - `LOG_RETENTION_DAYS`
  - `LOG_CONSOLE_ENABLED`
- State persistence:
  - `STATE_BACKEND`
  - `DATABASE_URL`
  - `POSTGRES_STATE_KEY`

## Code-Confirmed Defaults
- Shared live-provider request behavior:
  - `INTEL_API_TIMEOUT_SECONDS = 5`
  - `INTEL_API_RETRY_COUNT = 1`
- Cache and auto screenshot:
  - `CACHE_TTL_SECONDS = 3600`
  - auto screenshot can run once per guild/job/date after the hard-coded `16:00` KST Korea schedule and `07:00` KST US schedule
- News:
  - `NEWS_BRIEFING_ENABLED = True`
  - `NEWS_BRIEFING_TIME = "07:30"`
  - `NEWS_BRIEFING_TRADING_DAYS_ONLY = False`
  - `NEWS_PROVIDER_KIND = "mock"`
- Watch:
  - `WATCH_POLL_ENABLED = True`
  - `WATCH_POLL_INTERVAL_SECONDS = 60`
  - `WATCH_ALERT_THRESHOLD_PCT = 3.0`
  - `MARKET_DATA_PROVIDER_KIND = "mock"`
- EOD:
  - `EOD_SUMMARY_ENABLED = False`
  - `EOD_SUMMARY_TIME = "16:20"`
- Registry refresh:
  - `INSTRUMENT_REGISTRY_REFRESH_ENABLED = False`
  - `INSTRUMENT_REGISTRY_REFRESH_TIME = "06:20"`
- Logging:
  - `LOG_RETENTION_DAYS = 7`
  - `LOG_CONSOLE_ENABLED = True`
- State persistence:
  - `STATE_BACKEND = "postgres"`
  - `POSTGRES_STATE_KEY = "default"`
  - `DATABASE_URL` has no default and is required for the current runtime state backend

## Code-Confirmed Provider Wiring
- News provider selection:
  - `NEWS_PROVIDER_KIND = "mock"` -> `MockNewsProvider`
  - `NEWS_PROVIDER_KIND = "naver"` -> `NaverNewsProvider` or `ErrorNewsProvider` when credentials are missing
  - `NEWS_PROVIDER_KIND = "marketaux"` -> `MarketauxNewsProvider` or `ErrorNewsProvider` when the token is missing
  - `NEWS_PROVIDER_KIND = "hybrid"` -> `HybridNewsProvider` combining Naver for domestic and Marketaux for global, or `ErrorNewsProvider` when either credential set is missing
- Market data provider selection:
  - `MARKET_DATA_PROVIDER_KIND = "mock"` -> `MockMarketDataProvider`
  - `MARKET_DATA_PROVIDER_KIND = "kis"` -> `KisMarketDataProvider` or `ErrorMarketDataProvider` when KIS credentials are missing
  - when `MARKET_DATA_PROVIDER_KIND = "kis"` and `MASSIVE_API_KEY` or `POLYGON_API_KEY` is present, a `MassiveSnapshotMarketDataProvider` is attached as a US-only fallback through `RoutedMarketDataProvider`
  - the current watch path consumes normalized `WatchSnapshot` data via `get_watch_snapshot(...)`, not text-channel quote alerts
- EOD wiring:
  - the scheduler currently uses `MockEodSummaryProvider()` unconditionally when EOD is enabled
- Status-only provider rows:
  - `twelvedata_reference` and `openfigi_mapping` are currently status rows, not active runtime providers in the inspected bot code

## Runtime State Paths
- Current mutable runtime state when `STATE_BACKEND=postgres` or `postgresql`:
  - `bot_guild_config`
  - `bot_guild_job_markers`
  - `bot_daily_posts`
  - `bot_command_image_cache`
  - `bot_watch_symbols`
  - `bot_watch_reference_snapshots`
  - `bot_watch_session_alerts`
  - `bot_watch_alert_cooldowns`
  - `bot_watch_alert_latches`
  - `bot_watch_baselines`
  - `bot_job_status`
  - `bot_provider_status`
  - `bot_news_dedup`
  - all keyed by `POSTGRES_STATE_KEY`
- Accumulated watch close-price history:
  - `bot_watch_close_prices`
  - `bot_watch_close_price_attempts`
  - keyed by `POSTGRES_STATE_KEY`; these rows are historical/analytics data and are not exported into legacy `AppState` snapshots
- Migration/rollback state:
  - PostgreSQL table `bot_app_state` keeps the legacy full `AppState` JSONB row.
  - `data/state/state.json` is a one-time import fallback only when no legacy PostgreSQL row exists.
  - `bot_state_migrations` records `split_state_v1` idempotency.
- Optional runtime registry artifact:
  - `data/state/instrument_registry.json`
- Logs:
  - `data/logs/bot.log`
- Cached heatmap data:
  - `data/heatmaps/kheatmap/`
  - `data/heatmaps/usheatmap/`

## Known Ambiguities
- A provider env var appearing in settings or status output still does not prove that the related job is enabled or actively running.
- This document confirms core defaults and current provider wiring, but not every future/planned provider slot described in historical reports or target-contract docs.
