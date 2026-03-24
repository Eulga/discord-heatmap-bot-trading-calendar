# Config Reference

## Scope
- This document summarizes the configuration boundary used by the current project structure.
- It is not a deep runtime spec and does not attempt to restate every provider query list or heuristic constant.
- For current implementation details, use `../specs/as-is-functional-spec.md`.

## Secret vs Non-Secret Boundary
- Secrets, tokens, and credentials belong in env.
- Mutable per-guild routing and other operational state belong in `data/state/state.json`.
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
  - `WATCH_ALERT_CHANNEL_ID`
- Startup copies these IDs into per-guild state only when the channel is accessible, the type matches, a guild context exists, and state does not already have that route.
- Runtime routing should be checked in `data/state/state.json` when validating actual behavior.

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
  - `WATCH_ALERT_COOLDOWN_MINUTES`
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

## Code-Confirmed Defaults
- Shared live-provider request behavior:
  - `INTEL_API_TIMEOUT_SECONDS = 5`
  - `INTEL_API_RETRY_COUNT = 1`
- Cache and auto screenshot:
  - `CACHE_TTL_SECONDS = 3600`
  - auto screenshot runs only on exact-minute checks hard-coded as `15:35` KST for Korea and `06:05` KST for US
- News:
  - `NEWS_BRIEFING_ENABLED = True`
  - `NEWS_BRIEFING_TIME = "07:30"`
  - `NEWS_BRIEFING_TRADING_DAYS_ONLY = False`
  - `NEWS_PROVIDER_KIND = "mock"`
- Watch:
  - `WATCH_POLL_ENABLED = True`
  - `WATCH_POLL_INTERVAL_SECONDS = 60`
  - `WATCH_ALERT_THRESHOLD_PCT = 3.0`
  - `WATCH_ALERT_COOLDOWN_MINUTES = 10`
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
- EOD wiring:
  - the scheduler currently uses `MockEodSummaryProvider()` unconditionally when EOD is enabled
- Status-only provider rows:
  - `twelvedata_reference` and `openfigi_mapping` are currently status rows, not active runtime providers in the inspected bot code

## Runtime State Paths
- Main mutable app state:
  - `data/state/state.json`
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
