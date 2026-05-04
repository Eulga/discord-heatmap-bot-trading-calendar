# 1. Document scope
- What inputs were analyzed:
  - `README.md`, `.env.example`, `docker-compose.yml`, `requirements.txt`, `pytest.ini`
  - Core runtime code: `bot/main.py`, `bot/app/settings.py`, `bot/app/bot_client.py`, `bot/app/command_sync.py`
  - Feature code: `bot/features/runner.py`, `bot/features/auto_scheduler.py`, `bot/features/intel_scheduler.py`, `bot/features/admin/command.py`, `bot/features/watch/command.py`, `bot/features/watch/service.py`, `bot/features/status/command.py`, `bot/features/kheatmap/*`, `bot/features/usheatmap/*`, `bot/features/news/*`, `bot/features/eod/policy.py`
  - Persistence/posting code: `bot/forum/repository.py`, `bot/forum/service.py`, `bot/app/types.py`, `bot/common/fs.py`
  - Market/news/provider code: `bot/markets/capture_service.py`, `bot/markets/providers/korea.py`, `bot/markets/providers/us.py`, `bot/markets/trading_calendar.py`, `bot/intel/providers/news.py`, `bot/intel/providers/market.py`, `bot/intel/instrument_registry.py`
  - Integration tests used as corroborating evidence: `tests/integration/test_auto_scheduler_logic.py`, `tests/integration/test_forum_upsert_flow.py`, `tests/integration/test_intel_scheduler_logic.py`
- What level of confidence this document has:
  - High confidence for startup flow, slash-command registration, forum/state persistence, heatmap posting, and scheduler trigger conditions because these are directly visible in code.
  - Medium confidence for live provider behavior and theme-selection quality because code was inspected but not executed against live APIs in this analysis.
  - Low confidence for any intended operational policy not encoded in code, especially EOD operational intent, watch baseline lifecycle, and diagnostic-surface access policy.
- Any known limits of the analysis:
  - No live Discord/API execution was performed for this document.
  - Future-facing docs such as `docs/specs/external-intel-api-spec.md` were not treated as authoritative for current behavior unless matched by code.
  - Some large heuristic sections inside `bot/intel/providers/news.py` were sampled enough to confirm structure and output shape, but not every ranking constant was reverse-listed here.

# 2. System overview (As-Is)
- The current system is a Discord bot that can post daily Korea/US heatmap images into Discord forum threads and can also run scheduled news, trend, watch-alert, and registry-refresh jobs. This is confirmed by `bot/main.py`, `bot/app/bot_client.py`, `bot/features/runner.py`, `bot/features/auto_scheduler.py`, and `bot/features/intel_scheduler.py`.
- The main runtime model is event-driven plus background polling:
  - slash commands trigger manual heatmap posting, route setup, watchlist changes, and status reads
  - `auto_screenshot_scheduler()` runs every 30 seconds and can catch up once per day after the fixed KST schedule has passed
  - `intel_scheduler()` runs every 15 seconds and checks exact-minute news/EOD times plus elapsed watch interval and registry refresh state
  - This is confirmed by `bot/features/auto_scheduler.py` and `bot/features/intel_scheduler.py`.
- The main external dependencies currently wired into runtime are:
  - Discord API via `discord.py`
  - Playwright Chromium plus Hankyung/Finviz pages for heatmap capture
  - `exchange_calendars` for KRX/NYSE trading-day checks
  - Optional Naver Search API, Marketaux API, KIS Open API, Massive API for live intel features
  - Optional OpenDART, SEC, and KRX data endpoints for instrument registry rebuilds
  - This is confirmed by `requirements.txt`, `bot/markets/providers/*.py`, `bot/markets/trading_calendar.py`, `bot/intel/providers/*.py`, and `bot/intel/instrument_registry.py`.
- The main persisted state/config mechanisms are:
  - `.env` loaded at import time by `bot/app/settings.py`
  - selectable app-state backend through `STATE_BACKEND`
  - `data/state/state.json` as the default mutable app state when `STATE_BACKEND=file`
  - PostgreSQL table `bot_app_state` as the optional mutable app state when `STATE_BACKEND=postgres` or `postgresql`
  - `data/state/instrument_registry.json` as an optional runtime registry override
  - `bot/intel/data/instrument_registry.json` and seed JSON as bundled registry artifacts
  - `data/heatmaps/...` as local image cache
  - `data/logs/bot.log` as rotating runtime log output
  - This is confirmed by `bot/app/settings.py`, `bot/forum/repository.py`, `bot/intel/instrument_registry.py`, `bot/markets/capture_service.py`, and `bot/common/logging.py`.

# 3. Implemented feature inventory

| Feature ID | Feature name | Status | Trigger | Output | Confidence |
| --- | --- | --- | --- | --- | --- |
| F-01 | Bot startup, command sync, and bootstrap routing | Implemented | process start and Discord `on_ready` | command sync, state bootstrap, background scheduler start, logs | Confirmed |
| F-02 | Manual heatmap posting (`/kheatmap`, `/usheatmap`) | Implemented | slash command | daily forum thread create/update with captured images | Confirmed |
| F-03 | Daily forum upsert and content-message sync | Implemented | called by heatmap/news/eod flows | thread reuse or creation, starter message edit, optional follow-up content sync | Confirmed |
| F-04 | Auto screenshot scheduler | Implemented | background scheduler | scheduled Korea/US heatmap execution, skip metadata, logs | Confirmed |
| F-05 | Admin route configuration and autoscreenshot toggle commands | Implemented | slash command | per-guild route state updates and auto-scheduler enable flag | Confirmed |
| F-06 | Watchlist management (`/watch add`, `/watch start`, `/watch stop`, `/watch delete`, `/watch list`) | Implemented | slash command | per-guild watchlist state update/read plus watch status/thread lifecycle control | Confirmed |
| F-07 | Status and diagnostic commands (`/health`, `/last-run`, `/source-status`) | Implemented | slash command | ephemeral text status summaries | Confirmed |
| F-08 | Scheduled news briefing posting | Implemented | intel scheduler exact-minute check | domestic/global daily forum threads and job/provider status updates | Confirmed |
| F-09 | Scheduled trend briefing posting | Implemented | nested inside news scheduler | trend summary thread with starter + region content messages | Confirmed |
| F-10 | Scheduled EOD summary posting | Partially implemented | intel scheduler exact-minute check | daily EOD forum thread using mock summary provider | Confirmed |
| F-11 | Watch poll and per-symbol forum-thread alerting | Implemented | intel scheduler interval check | watch forum thread updates/comments and watch/provider/job status updates | Confirmed |
| F-12 | Instrument registry load/search/runtime refresh | Implemented | startup lookup, watch commands, scheduler when enabled | local search, status rows, runtime registry rebuild file | Confirmed |
| F-13 | Legacy message ping handler (`!ping`) | Implemented | plain text message event | `pong` reply | Confirmed |

# 4. Detailed As-Is functional specification

## Feature: Bot startup, command sync, and bootstrap routing

### 4.1 Purpose
- Initialize the Discord client, register slash commands, sync commands, bootstrap env-provided route IDs into guild state, and start background schedulers.

### 4.2 Trigger
- Process start through `python -m bot.main`
- Discord `on_ready` event

### 4.3 Inputs
- Config inputs:
  - `DISCORD_BOT_TOKEN`
  - `DEFAULT_FORUM_CHANNEL_ID`
  - `NEWS_TARGET_FORUM_ID`
  - `EOD_TARGET_FORUM_ID`
  - logging env vars
- Runtime inputs:
  - current `data/state/state.json`
  - Discord app command sync result
- Discord resource inputs:
  - channels referenced by bootstrap env IDs

### 4.4 Processing flow
1. `bot/main.py` creates the bot app and calls `client.run(TOKEN)`.
2. `create_bot_app()` configures logging, creates a `discord.Client`, builds a `CommandTree`, and registers admin, status, watch, Korea heatmap, and US heatmap commands.
3. On the first `on_ready`, the bot attempts `tree.sync()` for global commands.
4. Command-sync success or failure is recorded into state via `record_command_sync()`.
5. `_bootstrap_guild_channel_routes_from_env()` loads current state and tries to resolve each optional bootstrap channel ID.
6. For each bootstrap channel:
   - inaccessible channels are ignored
   - wrong channel type is ignored
   - channels without guild context are ignored
   - if the target guild already has that route in state, bootstrap does nothing
   - otherwise the route is written into the matching guild entry in state
7. If any bootstrap route changed state, `save_state()` is called once.
8. `auto_screenshot_scheduler()` and `intel_scheduler()` are started if not already running.

### 4.5 Outputs
- Global slash commands available in Discord
- `system.job_last_runs.command-sync` state entry
- possible bootstrap route writes into `guilds.{guild_id}.*_channel_id`
- scheduler tasks started
- runtime logs

### 4.6 Persistence / state interaction
- Reads and writes `data/state/state.json`
- Writes runtime logs to `data/logs/bot.log`
- Reads env vars at module import time through `bot/app/settings.py`

### 4.7 Error / edge handling (As-Is)
- Command sync failures are caught, formatted into a Korean hint message, logged, and written to state; the bot does not stop in that path.
- Bootstrap channel fetches return `None` on any exception in `_fetch_channel()`.
- Bootstrap save errors are not explicitly caught inside `_bootstrap_guild_channel_routes_from_env()`.
- Schedulers are started after bootstrap; if bootstrap raises during save, that path is not explicitly isolated in this module.

### 4.8 Operational constraints
- `DISCORD_BOT_TOKEN` is required at import time; missing token raises `RuntimeError`.
- In `_bootstrap_guild_channel_routes_from_env()`, forum bootstrap values are ignored unless the fetched channel is a `discord.ForumChannel`, and watch bootstrap values are ignored unless the fetched channel is a `discord.TextChannel`.
- Runtime routing reads state, not env, after bootstrap.

### 4.9 Confidence
- Confirmed

### 4.10 Evidence notes
- `bot/main.py`
- `bot/app/settings.py`
- `bot/app/bot_client.py`
- `bot/app/command_sync.py`
- `bot/common/logging.py`

## Feature: Manual heatmap posting (`/kheatmap`, `/usheatmap`)

### 4.1 Purpose
- Current code attempts to create or update a same-date forum post for Korea or US heatmap images in the current guild.

### 4.2 Trigger
- Slash command `/kheatmap`
- Slash command `/usheatmap`

### 4.3 Inputs
- Config inputs:
  - `KOREA_MARKET_URLS`, `US_MARKET_URLS`
  - capture selectors and user agent from settings/provider modules
- Runtime inputs:
  - guild ID from the interaction
  - per-guild `forum_channel_id` from state
  - cached image metadata in `commands.{command}.last_images`
- Provider inputs:
  - Playwright capture of target URLs
- Discord resource inputs:
  - target forum channel
  - existing same-day thread if present

### 4.4 Processing flow
1. The command defers the interaction with `thinking=True`.
2. If `interaction.guild_id` is missing, it returns a failure message.
3. `execute_heatmap_for_guild()` loads state and reads the guild’s `forum_channel_id`.
4. The code resolves the forum channel by cache or `fetch_channel()`. If the resolved object is missing, not a `ForumChannel`, or belongs to another guild, the command returns a failure message.
5. `get_or_capture_images()` checks the last image cache for each market target:
   - if a cached file path exists and cache TTL is still valid, the cached file is reused
   - otherwise the capture function is called and the new path/timestamp is stored
6. State is saved immediately after cache updates.
7. If all captures failed and no image path succeeded, the command returns a failure response and does not call forum upsert.
8. Otherwise a title and body are built from the policy modules and `upsert_daily_post()` is called with the images.
9. State is saved again after successful upsert.
10. The command sends a follow-up message containing the thread link and counts of successful and failed image items.

### 4.5 Outputs
- A created or updated forum thread for `kheatmap` or `usheatmap`
- Image attachments in the starter message
- Public follow-up command response with result text
- Logs for request and result

### 4.6 Persistence / state interaction
- Reads/writes `data/state/state.json`
- Writes image cache metadata under `commands.kheatmap.last_images` or `commands.usheatmap.last_images`
- Writes same-day daily post mapping via forum upsert
- Reads/writes local PNG files under `data/heatmaps/kheatmap/` or `data/heatmaps/usheatmap/`

### 4.7 Error / edge handling (As-Is)
- Missing guild returns a user-facing rejection.
- Missing or invalid guild forum route returns a user-facing failure.
- If at least one image path succeeded, the command still builds a body with a `Failed:` section and calls `upsert_daily_post()`.
- `discord.Forbidden`, `discord.HTTPException`, and generic exceptions from forum upsert are converted into user-facing failure messages.
- Forum resolution failure inside `_resolve_guild_forum_channel()` collapses to `None` on any exception.

### 4.8 Operational constraints
- The handler rejects invocations without `interaction.guild_id`.
- The handler returns a failure message unless `forum_channel_id` exists in state and resolves to a same-guild forum channel.
- Fresh capture attempts call Playwright and the target web pages. When fresh capture fails, posting can still continue only if another target succeeded or a recent cached file was reused.
- Cache reuse is TTL-based, not explicit content validation beyond file existence/age.

### 4.9 Confidence
- Confirmed

### 4.10 Evidence notes
- `bot/features/kheatmap/command.py`
- `bot/features/usheatmap/command.py`
- `bot/features/runner.py`
- `bot/markets/capture_service.py`
- `bot/features/kheatmap/policy.py`
- `bot/features/usheatmap/policy.py`

## Feature: Daily forum upsert and content-message sync

### 4.1 Purpose
- Current code attempts to reuse a same-date thread when a stored thread/message record can be fetched; otherwise it creates a new thread and updates state to point at the new resources.

### 4.2 Trigger
- Internal call from heatmap, news, trend, or EOD posting flows

### 4.3 Inputs
- Runtime inputs:
  - `state`
  - `guild_id`
  - `command_key`
  - `post_title`
  - `body_text`
  - `image_paths`
  - optional `content_texts`
- Discord resource inputs:
  - forum channel ID
  - existing thread/message IDs from state

### 4.4 Processing flow
1. Resolve the forum channel by `client.get_channel()` or `client.fetch_channel()`.
2. Reject non-forum channels by raising `ForumChannelTypeError`.
3. Look up today’s record in `commands.{command_key}.daily_posts_by_guild.{guild_id}.{date}`.
4. If `thread_id` and `starter_message_id` are present, try to load the thread and starter message.
5. If both are available:
   - rename the thread if the title changed
   - edit the starter message content and attachments
6. Otherwise create a new thread with the given title/body/files.
7. Persist the thread/starter IDs immediately into state.
8. If `content_texts` were supplied:
   - edit existing content messages by index when fetch succeeds
   - resend a content message when fetch fails for that index
   - append new content messages if there are more desired texts than stored IDs
   - persist content IDs after each successful content-message step
9. If there are more stored content IDs than desired texts:
   - try to delete the extra message
   - remove missing IDs from state when `discord.NotFound`
   - ignore `discord.Forbidden` and generic `discord.HTTPException` for delete cleanup
10. Return the resulting thread and `"created"` or `"updated"`.

### 4.5 Outputs
- Discord forum thread
- Updated starter message
- Optional follow-up content messages
- State record for same-day thread/message IDs

### 4.6 Persistence / state interaction
- Reads/writes `commands.{command_key}.daily_posts_by_guild`
- Uses `date_key()` without passing the scheduler’s `now`, so the record key is based on current runtime date at call time

### 4.7 Error / edge handling (As-Is)
- Existing thread fetch errors of type `NotFound`, `Forbidden`, and `HTTPException` all cause fallback to thread recreation path.
- Missing follow-up content IDs are cleaned from state.
- Some delete failures for extra content messages are ignored.
- Create/edit failures outside the local catch blocks bubble to the caller.

### 4.8 Operational constraints
- The function raises `ForumChannelTypeError` unless the resolved channel object is a `discord.ForumChannel`.
- Assumes the bot can edit thread names, edit starter messages, attach files, and send/delete follow-up messages.
- Same-date matching is state-record-based. No title search or Discord-side lookup by date/name is implemented in this function.

### 4.9 Confidence
- Confirmed

### 4.10 Evidence notes
- `bot/forum/service.py`
- `bot/forum/repository.py`
- `tests/integration/test_forum_upsert_flow.py`

## Feature: Auto screenshot scheduler

### 4.1 Purpose
- Current code attempts scheduled Korea/US heatmap posting for guilds whose `auto_screenshot_enabled` flag is true.

### 4.2 Trigger
- Background task `auto_screenshot_scheduler()` every 30 seconds

### 4.3 Inputs
- Config inputs:
  - fixed schedule in code: `15:35` KST for Korea, `06:05` KST for US
- Runtime inputs:
  - current KST time
  - guild auto-screenshot flags in state
  - last auto-attempt, last auto-run, and last auto-skip dates in state
- Provider inputs:
  - KRX/NYSE trading-day check helpers
  - heatmap capture through `execute_heatmap_for_guild()`

### 4.4 Processing flow
1. Every loop, `process_auto_screenshot_tick()` computes current date and eligible jobs whose fixed scheduled time has already passed in KST.
2. It loads state and enumerates guilds with `auto_screenshot_enabled == True`.
3. For each job and guild:
   - skip if today is already recorded in `last_auto_attempts.{command_key}`, `last_auto_runs.{command_key}`, or `last_auto_skips.{command_key}`
   - check trading day with the market-specific calendar helper using the scheduled KST timestamp for that job
   - on calendar failure, record one skip per date, record the day as an attempted auto run, and log a warning
   - on holiday, record one skip per date, record the day as an attempted auto run, and log info
4. When a trading day is confirmed, `execute_heatmap_for_guild()` is called.
5. On success, state is reloaded before saving `last_auto_runs` and `last_auto_attempts` to avoid clobbering runner changes.
6. If the refreshed state looks empty while previous guild state existed, the scheduler skips writing auto metadata and logs a warning.
7. On failure, state is reloaded before saving `last_auto_attempts`; the failure consumes that day’s scheduled auto attempt and no user-facing response exists.

### 4.5 Outputs
- Scheduled forum posts for heatmaps
 - `guilds.{guild_id}.last_auto_attempts`
- `guilds.{guild_id}.last_auto_runs`
- `guilds.{guild_id}.last_auto_skips`
- logs

### 4.6 Persistence / state interaction
- Reads/writes `data/state/state.json`
- Relies on `execute_heatmap_for_guild()` to persist image cache and daily post state

### 4.7 Error / edge handling (As-Is)
- Scheduler loop catches all exceptions, logs them, and sleeps 30 seconds before continuing.
- Skip reason is persisted once per day for holiday or calendar-check failure, and those outcomes also consume the day’s scheduled auto attempt.
- There is visible same-day catch-up logic after the fixed scheduled minute, but only one scheduled auto attempt is consumed per guild/job/date.

### 4.8 Operational constraints
- Exact-minute schedule only
- Depends on `exchange_calendars` data and the Discord/forum route already existing in state
- Uses the same forum upsert and capture constraints as manual heatmap posting

### 4.9 Confidence
- Confirmed

### 4.10 Evidence notes
- `bot/features/auto_scheduler.py`
- `bot/markets/trading_calendar.py`
- `tests/integration/test_auto_scheduler_logic.py`

## Feature: Admin route configuration and autoscreenshot toggle commands

### 4.1 Purpose
- Allow authorized users to configure per-guild posting routes and toggle auto screenshot mode.

### 4.2 Trigger
- Slash commands:
  - `/setforumchannel`
  - `/setnewsforum`
  - `/seteodforum`
  - `/setwatchforum`
  - `/autoscreenshot`

### 4.3 Inputs
- Config inputs:
  - `DISCORD_GLOBAL_ADMIN_USER_IDS`
- User inputs:
  - target forum/text channel
  - `on` or `off` choice for auto screenshot
- Runtime inputs:
  - guild context
  - member admin permission or owner status

### 4.4 Processing flow
1. Each command requires guild context.
2. `_is_authorized_admin()` allows the command when the user is:
   - the guild owner
   - a member with `administrator`
   - a user ID listed in `DISCORD_GLOBAL_ADMIN_USER_IDS`
3. Channel-setting commands also require the chosen channel to belong to the same guild.
4. The command loads state, writes the matching per-guild route field or `auto_screenshot_enabled`, saves state, logs success, and returns an ephemeral confirmation.

### 4.5 Outputs
- Updated guild routing fields or auto-screenshot flag in state
- Ephemeral success or rejection message
- Logs

### 4.6 Persistence / state interaction
- Writes `guilds.{guild_id}.forum_channel_id`
- Writes `guilds.{guild_id}.news_forum_channel_id`
- Writes `guilds.{guild_id}.eod_forum_channel_id`
- Writes `guilds.{guild_id}.watch_forum_channel_id`
- Writes `guilds.{guild_id}.auto_screenshot_enabled`

### 4.7 Error / edge handling (As-Is)
- No-guild use is rejected.
- Unauthorized use is rejected.
- Foreign-guild channel selection is rejected.
- There is no explicit precheck of the bot’s effective permissions on the selected channel in this module.

### 4.8 Operational constraints
- The slash option types enforce `ForumChannel` for forum routes.
- The actual posting capability is assumed, not prevalidated.

### 4.9 Confidence
- Confirmed

### 4.10 Evidence notes
- `bot/features/admin/command.py`
- `bot/forum/repository.py`

## Feature: Watchlist management (`/watch add`, `/watch start`, `/watch stop`, `/watch delete`, `/watch list`)

### 4.1 Purpose
- Maintain a per-guild shared watchlist of canonical market symbols backed by the local instrument registry.

### 4.2 Trigger
- Slash commands:
  - `/watch add`
  - `/watch start`
  - `/watch stop`
  - `/watch delete`
  - `/watch list`
- Slash-command autocomplete for add/start/stop/delete symbol inputs

### 4.3 Inputs
- User inputs:
  - raw symbol text, ticker, or instrument name
- Runtime inputs:
  - guild ID
  - current guild watchlist from state
- Provider inputs:
  - local registry search and canonical-symbol normalization

### 4.4 Processing flow
1. The command requires guild context.
2. `/watch add` resolves the symbol in this order:
   - exact canonical symbol
   - legacy domestic code or legacy US ticker normalization
   - local registry search
   - exact high-score search result
   - ambiguous search returns an error with candidate lines
3. `/watch start`, `/watch stop`, `/watch delete` resolve against the current guild watchlist, including canonical and legacy representations.
4. Successful `/watch add` requires `watch_forum_channel_id`, adds the symbol to the guild watchlist if it is not already present, saves immediately, and creates the persistent symbol thread with a blank starter for the newly added symbol.
5. Duplicate `/watch add` is a no-op; if the symbol is tracked but `inactive`, the command points the user to `/watch start` instead of reactivating inline.
6. `/watch start` only applies to inactive tracked symbols. It reuses or recreates the symbol thread with a blank starter, and same-session reactivation resets stored highest-band checkpoints so intraday alerts restart from a fresh active watch state.
7. `/watch stop` does not remove the symbol from the guild watchlist. Instead it clears watch cooldown, latch, baseline runtime state, and any stored current-price comment ID, records thread status as `inactive`, and attempts an update-only blank starter write when a tracked thread exists.
8. If no tracked symbol thread exists, or the stored thread/starter handle is stale, `/watch stop` does not create a new inactive thread. When a tracked thread/starter exists, stop state is committed only after the blank starter update succeeds; otherwise the command fails and keeps the symbol active.
9. `/watch delete` is admin-gated. It deletes the tracked Discord thread when possible, then removes the symbol from the watchlist, thread registry, reference snapshots, and session alerts.
10. Stored thread/starter recreation is only allowed for authoritative `discord.NotFound`; transient `discord.Forbidden` and generic `discord.HTTPException` bubble to the caller instead of creating a duplicate thread.
11. `/watch list` formats all tracked symbols using registry display names plus per-symbol watch status labels.
12. Autocomplete queries the local registry for add and the tracked guild watchlist for start/stop/delete, returning up to 25 choices.

### 4.5 Outputs
- Ephemeral confirmation or error message
- Updated `guilds.{guild_id}.watchlist`
- Updated `commands.watchpoll.symbol_threads_by_guild.{guild_id}.{symbol}` and blank starter message when add/start/stop/delete touches a tracked thread
- Updated `system.watch_reference_snapshots.{guild_id}.{symbol}` and `system.watch_session_alerts.{guild_id}.{symbol}` when delete clears tracked state
- Autocomplete choices for symbol search

### 4.6 Persistence / state interaction
- Reads/writes `guilds.{guild_id}.watchlist`
- Reads `guilds.{guild_id}.watch_forum_channel_id`
- Reads/writes `commands.watchpoll.symbol_threads_by_guild.{guild_id}.{symbol}`
- Reads/writes `guilds.{guild_id}.watch_alert_cooldowns`
- Reads/writes `guilds.{guild_id}.watch_alert_latches`
- Reads/writes `system.watch_baselines.{guild_id}`
- Reads/writes `system.watch_reference_snapshots.{guild_id}`
- Reads/writes `system.watch_session_alerts.{guild_id}`
- Reads the local instrument registry

### 4.7 Error / edge handling (As-Is)
- Empty input is rejected.
- Ambiguous symbol resolution returns candidate text rather than auto-selecting.
- `/watch add` is rejected when `watch_forum_channel_id` is missing.
- Duplicate add returns an ignored/already-registered message.
- `/watch start` on an already-active symbol and `/watch stop` on an already-inactive symbol return ignored messages.
- `/watch delete` rejects unauthorized users.
- Start/stop/delete on a missing symbol return an error message.
- This module does not perform an admin/owner permission check for add/start/stop/list, but `/watch delete` does enforce owner/admin/global-admin authorization.

### 4.8 Operational constraints
- The watchlist is stored per guild, not per user.
- Symbol resolution depends on the local registry snapshot.
- Response formatting is a single message; no length management is visible here.

### 4.9 Confidence
- Confirmed

### 4.10 Evidence notes
- `bot/features/watch/command.py`
- `bot/forum/repository.py`
- `bot/intel/instrument_registry.py`

## Feature: Status and diagnostic commands (`/health`, `/last-run`, `/source-status`)

### 4.1 Purpose
- Expose recent job status and provider status rows stored in local state, plus default rows derived from configuration.

### 4.2 Trigger
- Slash commands:
  - `/health`
  - `/last-run`
  - `/source-status`

### 4.3 Inputs
- Config inputs:
  - `EOD_SUMMARY_ENABLED`
  - `INSTRUMENT_REGISTRY_REFRESH_ENABLED`
  - `INSTRUMENT_REGISTRY_REFRESH_TIME`
  - `MARKET_DATA_PROVIDER_KIND`
  - provider credentials and tokens
  - `NEWS_PROVIDER_KIND`
- Runtime inputs:
  - `system.job_last_runs`
  - `system.provider_status`
  - `registry_status()`

### 4.4 Processing flow
1. The command loads state.
2. It merges stored status rows with built-in defaults:
   - default job rows include paused/scheduled placeholders for EOD and registry refresh
   - default provider rows include `instrument_registry`, `kis_quote`, `massive_reference`, `twelvedata_reference`, `openfigi_mapping`, plus news-provider rows depending on `NEWS_PROVIDER_KIND`
3. Legacy provider keys are remapped to newer names where needed.
4. The command formats rows as plain text lines of `key: status | detail | timestamp`.
5. The text is returned ephemerally.

### 4.5 Outputs
- Ephemeral plain-text status report
- Logs of command usage

### 4.6 Persistence / state interaction
- Reads `data/state/state.json`
- Reads live registry status from the current registry artifact
- Does not modify state

### 4.7 Error / edge handling (As-Is)
- No explicit authorization gate is visible in this module.
- No chunking or truncation logic is visible for long outputs.
- Missing rows are replaced by defaults rather than causing an error.

### 4.8 Operational constraints
- Output format is message-text based, not embeds.
- Effective content length is constrained by Discord’s message size, but this module does not appear to enforce a limit.
- Some provider rows are status placeholders only; not every configured row implies active runtime use.

### 4.9 Confidence
- Confirmed

### 4.10 Evidence notes
- `bot/features/status/command.py`
- `bot/forum/repository.py`
- `bot/intel/instrument_registry.py`

## Feature: Scheduled news briefing posting

### 4.1 Purpose
- Current code attempts to fetch news from the configured provider, build region-specific briefing text, and post separate domestic/global threads per guild at the scheduled minute.

### 4.2 Trigger
- `intel_scheduler()` exact-minute check when `NEWS_BRIEFING_ENABLED` is true and current time matches `NEWS_BRIEFING_TIME`

### 4.3 Inputs
- Config inputs:
  - `NEWS_BRIEFING_ENABLED`
  - `NEWS_BRIEFING_TIME`
  - `NEWS_BRIEFING_TRADING_DAYS_ONLY`
  - `NEWS_PROVIDER_KIND`
  - Naver/Marketaux query, limit, age, timeout, and retry env vars
- Runtime inputs:
  - current KST datetime
  - per-guild `news_forum_channel_id` from state, including values explicitly configured by command or initialized into state by startup `NEWS_TARGET_FORUM_ID` bootstrap
  - previous job status and per-guild last auto-run dates
- Provider inputs:
  - `news_provider` singleton built at module import time
  - `NewsAnalysis` containing `briefing_items`
- Discord resource inputs:
  - forum channel for each guild

### 4.4 Processing flow
1. `_run_news_job()` loads state and enumerates guild IDs.
2. For each guild:
   - it migrates legacy `newsbriefing` post state into `newsbriefing-domestic` if needed
   - it treats the guild as already complete only when:
     - `guilds.{guild_id}.last_auto_runs.newsbriefing` equals today
     - both domestic and global daily threads exist for today
     - trend briefing is complete or was explicitly skipped for today
   - otherwise it requires `news_forum_channel_id`; `forum_channel_id` alone does not make the guild eligible for news/trend posting
3. If `NEWS_BRIEFING_TRADING_DAYS_ONLY` is true, the job checks KRX trading day before forum resolution/posting.
4. For pending guilds, the forum channel is resolved through `_resolve_guild_forum_channel_id()`.
5. The job calls the provider analysis path:
   - `news_provider.analyze(now)` when available
   - otherwise `provider.fetch(now)` plus empty trend report wrapper
6. On provider success, job/provider status rows are updated.
7. Briefing items are deduplicated by `story_key()`, then split by `region`.
8. Domestic and global bodies are rendered separately with `build_news_region_body()`.
9. For each pending guild, two separate `upsert_daily_post()` calls are made:
   - `newsbriefing-domestic`
   - `newsbriefing-global`
10. If both region upserts succeed for that guild, the guild’s `last_auto_runs.newsbriefing` is set to today.
11. At the end, job status for `news_briefing` is computed from counts of `posted`, posting failures, forum resolution failures, and missing forums.

### 4.5 Outputs
- Two daily forum threads per guild when posting succeeds:
  - domestic news thread
  - global news thread
- `system.job_last_runs.news_briefing`
- provider status rows such as `naver_news` or `marketaux_news`
- logs

### 4.6 Persistence / state interaction
- Reads/writes `data/state/state.json`
- Writes daily post records under `newsbriefing-domestic` and `newsbriefing-global`
- Writes per-guild `last_auto_runs.newsbriefing`
- Writes provider/job status in `system`

### 4.7 Error / edge handling (As-Is)
- Provider failure marks `news_briefing` and `trend_briefing` as failed and returns immediately.
- If no unresolved target forums exist:
  - forum-resolution failure can mark failed
  - only-missing-forum with no completed guilds can mark skipped
- Per-guild posting failure increments `failed` and continues with later guilds.
- Job status is `ok` only when at least one guild posted and total failures are zero; otherwise it is `failed`.
- No visible same-day catch-up exists if the process starts after the scheduled minute.

### 4.8 Operational constraints
- Provider objects are built once at import time in `bot/features/intel_scheduler.py`.
- Routing depends on per-guild forum state.
- Domestic/global posts are separate threads, not sections of one thread.
- Trading-day gating, when enabled, is based on KRX only.

### 4.9 Confidence
- Confirmed

### 4.10 Evidence notes
- `bot/features/intel_scheduler.py`
- `bot/features/news/policy.py`
- `bot/intel/providers/news.py`
- `tests/integration/test_intel_scheduler_logic.py`

## Feature: Scheduled trend briefing posting

### 4.1 Purpose
- Current code attempts to generate a separate trend-theme thread from the news analysis and stores region details in follow-up content messages when the trend posting path runs.

### 4.2 Trigger
- Nested inside `_run_news_job()` after briefing analysis

### 4.3 Inputs
- Runtime inputs:
  - `analysis.trend_report`
  - same pending guild list computed for the news job
- Provider inputs:
  - trend themes produced by the configured news provider analysis
- Discord resource inputs:
  - same forum channel used for news briefing

### 4.4 Processing flow
1. The news analysis provides `trend_report` for `domestic` and `global`.
2. The scheduler only displays a region’s themes when that region has at least 3 themes.
3. If both regions are below 3 themes, the trend job is not posted:
   - `guilds.{guild_id}.last_auto_skips.trendbriefing` is set with `insufficient-themes ...`
   - final `trend_briefing` job status becomes `skipped`
4. If at least one region qualifies:
   - a starter body is rendered summarizing counts and selected theme names
   - region content messages are rendered with `build_trend_region_messages()`
   - regions with no displayed themes produce a placeholder content message
5. `upsert_daily_post()` is called with:
   - command key `trendbriefing`
   - starter body
   - zero image paths
   - `content_texts` containing the region detail blocks
6. Successful posting sets `guilds.{guild_id}.last_auto_runs.trendbriefing` for today.
7. Final job status is computed separately from the news briefing status.

### 4.5 Outputs
- A same-day trend thread per guild when at least one region qualifies
- Starter message plus follow-up content messages
- `system.job_last_runs.trend_briefing`
- `guilds.{guild_id}.last_auto_runs.trendbriefing` or `last_auto_skips.trendbriefing`

### 4.6 Persistence / state interaction
- Writes `trendbriefing` daily post record with `content_message_ids`
- Writes per-guild last-run or last-skip metadata

### 4.7 Error / edge handling (As-Is)
- Trend posting failure is counted separately from news posting failure and logged.
- If one region has fewer than 3 themes but the other qualifies, the non-qualifying region is rendered as placeholder content rather than suppressing the whole trend thread.
- There is no separate scheduler trigger or retry path for trend outside the news job.

### 4.8 Operational constraints
- Depends entirely on the current news analysis result.
- Message splitting/truncation is handled inside `trend_policy.py` with a 2000-character limit.
- Theme quality depends on provider heuristics and taxonomy scoring, which are implementation-specific.

### 4.9 Confidence
- Confirmed

### 4.10 Evidence notes
- `bot/features/intel_scheduler.py`
- `bot/features/news/trend_policy.py`
- `bot/intel/providers/news.py`
- `tests/integration/test_intel_scheduler_logic.py`

## Feature: Scheduled EOD summary posting

### 4.1 Purpose
- Post an end-of-day summary thread for eligible guilds when the EOD job is enabled.

### 4.2 Trigger
- `intel_scheduler()` exact-minute check when `EOD_SUMMARY_ENABLED` is true and current time matches `EOD_SUMMARY_TIME`

### 4.3 Inputs
- Config inputs:
  - `EOD_SUMMARY_ENABLED`
  - `EOD_SUMMARY_TIME`
- Runtime inputs:
  - current KST datetime
  - per-guild `eod_forum_channel_id` or fallback `forum_channel_id`
  - per-guild `last_auto_runs.eodsummary`
- Provider inputs:
  - module-level `eod_provider`, currently set to `MockEodSummaryProvider()`

### 4.4 Processing flow
1. `_run_eod_job()` loads state and finds guilds not already marked complete for today.
2. The target forum is `eod_forum_channel_id` or fallback `forum_channel_id`.
3. The job checks KRX trading day before attempting forum resolution or posting.
4. Forum channels are resolved with the same helper used by the news job.
5. `eod_provider.get_summary(now)` is called.
6. The body is rendered by `build_eod_body()`.
7. Each pending guild receives an `upsert_daily_post()` call with command key `eodsummary`.
8. Successful guilds receive `last_auto_runs.eodsummary = today`.
9. Final job status is computed from posted count, failures, and forum-resolution failures.

### 4.5 Outputs
- A daily EOD forum thread per guild when the feature is enabled and posting succeeds
- `system.job_last_runs.eod_summary`
- `system.provider_status.eod_provider`

### 4.6 Persistence / state interaction
- Reads/writes `data/state/state.json`
- Writes daily post records under `commands.eodsummary`
- Writes per-guild `last_auto_runs.eodsummary`

### 4.7 Error / edge handling (As-Is)
- Provider failure sets `eod_provider` false and marks `eod_summary` failed.
- Holiday or calendar-check failure marks `eod_summary` skipped.
- Per-guild posting failure increments `failed` and continues.
- No manual command path for EOD posting is visible in the inspected code.

### 4.8 Operational constraints
- The feature is disabled by default in settings.
- The current provider is a mock provider wired directly in `bot/features/intel_scheduler.py`.
- Posting still depends on forum routing in state.

### 4.9 Confidence
- Confirmed

### 4.10 Evidence notes
- `bot/features/intel_scheduler.py`
- `bot/features/eod/policy.py`
- `bot/intel/providers/market.py`

## Feature: Watch poll and per-symbol forum-thread alerting

### 4.1 Purpose
- Current code polls watched symbols on an interval, keeps each per-symbol forum thread starter blank, updates a current-price comment during regular session hours, emits band-crossing comments, and finalizes the session with a close comment only at market-specific KST due minutes.

### 4.2 Trigger
- `intel_scheduler()` interval check when `WATCH_POLL_ENABLED` is true

### 4.3 Inputs
- Config inputs:
  - `WATCH_POLL_ENABLED`
  - `WATCH_POLL_INTERVAL_SECONDS`
  - `WATCH_ALERT_THRESHOLD_PCT`
  - `MARKET_DATA_PROVIDER_KIND`
  - KIS and Massive credentials
- Runtime inputs:
  - guild watchlists
  - guild `watch_forum_channel_id`
  - `commands.watchpoll.symbol_threads_by_guild`
  - `system.watch_reference_snapshots`
  - `system.watch_session_alerts`
  - current datetime
- Provider inputs:
  - `quote_provider` module-level singleton
  - `get_watch_snapshot()` and optional `warm_watch_snapshots()` on the provider
- Discord resource inputs:
  - per-symbol forum threads, blank starters, and comments in the configured watch forum

### 4.4 Processing flow
1. `_run_watch_poll()` loads state and scans all guilds.
2. Target symbols are the union of active watchlist entries and inactive symbols that still have an unfinalized session in `system.watch_session_alerts`.
3. Guilds with watch symbols but no configured watch forum are counted as `missing_forum_guilds`.
4. If the provider exposes `warm_watch_snapshots()`, it is called once with the unique symbol set that is eligible for regular-session updates or KST-due close finalization across pending guilds.
5. Malformed or unsupported persisted symbols are treated as per-symbol watch snapshot failures and do not abort processing for other guilds or symbols.
6. For each guild and symbol, `_run_watch_poll()` calls `quote_provider.get_watch_snapshot()` only when the symbol is eligible for a regular-session active update or a close-finalization due minute.
7. During market regular-session hours:
   - the current-price comment is updated from the latest snapshot
   - when a band comment is created, the current-price comment is recreated after it so the latest watch state remains at the bottom of the thread
   - if deleting the old current-price comment during that recreate step fails with `Forbidden` or `HTTPException`, the bot logs the cleanup failure, clears the stale ID, and still attempts to send a replacement current-price comment
   - `previous_close` becomes the reference basis for percent-change rendering
   - same-session reactivation after `/watch add` resets stored highest-band checkpoints before fresh band detection resumes
   - the session state resets when `session_date` changes
   - at most one highest newly crossed `3%` band comment is created per poll
   - band comment send failures do not block current-price comment updates, and failed band checkpoints are not advanced
   - the rendered band label uses the effective threshold `max(0.1, WATCH_ALERT_THRESHOLD_PCT) * band` with trailing-zero trimming, while the trailing signed percent still uses the exact `change_pct`
8. Outside regular-session hours:
   - current-price and intraday updates are skipped
   - close finalization is attempted only when the poll tick is in the configured KST due minute
   - `KRX:*` close finalization is due only at KST `16:00`, while `NAS:*`, `NYS:*`, and `AMS:*` close finalization is due only at KST `07:00`
   - due-minute matching uses the KST hour and minute; if the scheduler misses that minute, close finalization remains pending until the next due minute
   - when a later regular session starts before a missed close is finalized, the old close target is preserved under `pending_close_sessions` and regular-session current-price/band processing continues against the new session
   - if a later due-minute snapshot can close both a pending old session and the current active session, pending close comments are created first and the current session close comment is created after them
   - if a pending old close target is no longer the immediately adjacent previous trading session for the due-minute snapshot, the pending retry entry is dropped without creating a close comment
   - the latest unfinalized session is finalized by deleting the tracked current-price comment plus tracked intraday comments, then reusing or creating a same-session close comment
   - `snapshot.previous_close` is only used as a close-price fallback when the snapshot belongs to the immediately adjacent next trading session
   - post-close snapshots are allowed to reuse last-trade `asof` timestamps without failing stale-quote validation when `session_close_price` exists for the current off-hours session
   - band-label `%` text follows the same effective-threshold rule even when the configured threshold is fractional or below `1.0`; the trailing signed percent remains the exact `change_pct`
9. Final job status is derived from counts of `active_symbols`, `updated_threads`, `updated_current_comments`, `finalized_sessions`, `dropped_pending_close_sessions`, `missing_forum_guilds`, `thread_failures`, `snapshot_failures`, and `comment_failures`.

### 4.5 Outputs
- Blank starter updates and thread comments in per-symbol watch forum threads
- `system.job_last_runs.watch_poll`
- provider status updates keyed per snapshot fetch
- watch reference/session state updates

### 4.6 Persistence / state interaction
- Reads/writes `guilds.{guild_id}.watch_forum_channel_id`
- Reads/writes `commands.watchpoll.symbol_threads_by_guild.{guild_id}.{symbol}`
- Reads/writes `system.watch_reference_snapshots.{guild_id}.{symbol}`
- Reads/writes `system.watch_session_alerts.{guild_id}.{symbol}`
- Legacy cooldown/latch and `system.watch_baselines` are kept only for compatibility or cleanup, not as active alert inputs
- Reads/writes provider/job status in `system`

### 4.7 Error / edge handling (As-Is)
- Snapshot failures increment counters and skip current-price/comment updates for that symbol.
- Missing or invalid watch forum/thread failures increment counters and skip that symbol.
- Band comment failures increment counters but do not block current-price comment updates for that symbol.
- Current-price comment failures increment counters but the job continues for other symbols.
- Current-price comment recreate cleanup failures are best-effort and do not block replacement current-price comment sends.
- `/watch stop` current-price comment cleanup is best-effort and does not block inactive status persistence.
- Close-finalization current-price comment cleanup is best-effort and does not block close comment creation or `last_finalized_session_date` persistence.
- Close finalization remains pending when `session_close_price` is unavailable and is retried on a later KST due-minute poll.
- If a prior session is still unfinalized at the next regular-session open and the current tick is not the market-specific KST due minute, the bot queues the old close target under `pending_close_sessions`, rotates current reference/session state, and keeps regular-session monitoring active.
- Pending close targets that have aged beyond the adjacent-session `previous_close` fallback window are removed from retry state on a later KST due-minute poll.
- Final job status becomes `failed` if any thread/snapshot/comment failures occurred.

### 4.8 Operational constraints
- The watchlist is stored under each guild’s state entry rather than under a user-scoped key.
- Watch thread reuse is keyed by `(guild_id, canonical_symbol)` and does not rotate daily.
- Session semantics are market-calendar aware for KRX and US regular sessions.
- Quote freshness and symbol coverage still depend on the selected provider path and its internal checks.
- The detailed current watch behavior is documented in `docs/specs/watch-poll-functional-spec.md`.

### 4.9 Confidence
- Confirmed for scheduler, thread, snapshot, and state-write paths in local code and tests; live Discord/KIS smoke remains unverified in this session.

### 4.10 Evidence notes
- `bot/features/intel_scheduler.py`
- `bot/features/watch/service.py`
- `bot/forum/repository.py`
- `bot/intel/providers/market.py`
- `tests/integration/test_intel_scheduler_logic.py`

## Feature: Instrument registry load/search/runtime refresh

### 4.1 Purpose
- Provide local instrument lookup for watch commands and quote resolution, with an optional runtime refresh job that rebuilds the registry from external sources.

### 4.2 Trigger
- Registry load on demand when watch commands or quote providers call `load_registry()`
- Scheduler-driven refresh when `INSTRUMENT_REGISTRY_REFRESH_ENABLED` is true

### 4.3 Inputs
- Config inputs:
  - `INSTRUMENT_REGISTRY_REFRESH_ENABLED`
  - `INSTRUMENT_REGISTRY_REFRESH_TIME`
  - `DART_API_KEY`
- Runtime inputs:
  - runtime registry file
  - bundled registry file
  - seed file
  - current datetime and previous refresh status
- Provider inputs:
  - OpenDART corp code file
  - SEC company ticker JSON
  - KRX structured product finder endpoints

### 4.4 Processing flow
1. `load_registry()` checks files in this order:
   - `data/state/instrument_registry.json`
   - `bot/intel/data/instrument_registry.json`
   - `bot/intel/data/instrument_registry_seed.json`
   - otherwise an empty registry object
2. `registry.search()` performs canonical-symbol handling and ranked text search over loaded records.
3. Watch commands and quote providers use the registry for canonical-symbol resolution and display formatting.
4. When refresh is enabled, `intel_scheduler()` checks `_should_start_instrument_registry_refresh()`:
   - only after the scheduled time
   - not again after same-day success
   - retry allowed after same-day failure except same-minute repeats and `dart-api-key-missing`
5. Refresh runs in a background task and does not block watch polling.
6. In the refresh path, `build_live_registry()` is called with `DART_API_KEY`. If the key is blank, the function raises `dart-api-key-missing`. On successful execution, the code fetches OpenDART, SEC, and KRX source data and then calls `save_registry()`.
7. Completion or failure updates `system.job_last_runs.instrument_registry_refresh` and `system.provider_status.instrument_registry`.

### 4.5 Outputs
- Searchable in-memory/local registry
- Optional runtime registry file replacement
- status rows describing active source and counts

### 4.6 Persistence / state interaction
- Reads bundled and runtime registry JSON files
- Writes `data/state/instrument_registry.json` on successful refresh
- Writes registry refresh job/provider status to `data/state/state.json`

### 4.7 Error / edge handling (As-Is)
- Missing or invalid runtime registry payload can raise when directly loaded.
- `registry_status()` converts registry load failure into a failed status row instead of throwing.
- On refresh failure, the inspected code records failure detail and does not call `save_registry()` in that run.
- Refresh and heatmap auto scheduling are the inspected scheduler paths with explicit same-day catch-up logic after scheduled time.

### 4.8 Operational constraints
- Registry refresh depends on external network access and `DART_API_KEY`.
- Search behavior is local-data driven, not live lookup driven.
- The active registry source is whichever file is found first in the load order.

### 4.9 Confidence
- Confirmed for load order, local search usage, and scheduler wiring; ambiguous for operational completeness of externally rebuilt symbol coverage.

### 4.10 Evidence notes
- `bot/intel/instrument_registry.py`
- `bot/features/intel_scheduler.py`
- `bot/features/watch/command.py`
- `bot/intel/providers/market.py`

## Feature: Legacy message ping handler (`!ping`)

### 4.1 Purpose
- A legacy message-event handler replies `pong` to a literal text command.

### 4.2 Trigger
- Message event where `message.content == "!ping"`

### 4.3 Inputs
- Runtime inputs:
  - Discord message content
  - current client user identity

### 4.4 Processing flow
1. `on_message` ignores messages from the bot itself.
2. If the content exactly matches `!ping`, the bot sends `pong` to the same channel.

### 4.5 Outputs
- Plain text message `pong`

### 4.6 Persistence / state interaction
- None visible

### 4.7 Error / edge handling (As-Is)
- No explicit error handling is visible in this event handler.
- `message_content` intent is set to `False` in `BotApp.__init__()`, so whether this path receives content in production depends on Discord runtime behavior outside this file.

### 4.8 Operational constraints
- This handler is only reachable if Discord delivers message content to `on_message` under the current runtime configuration.
- This path is separate from slash commands.

### 4.9 Confidence
- Confirmed for handler presence; ambiguous for practical reachability under the current `message_content` configuration.

### 4.10 Evidence notes
- `bot/app/bot_client.py`

# 5. Runtime behavior summary

## 5.1 Startup behavior
- `.env` is loaded at import time in `bot/app/settings.py`.
- Missing `DISCORD_BOT_TOKEN` stops startup with `RuntimeError`.
- Logging is configured before the bot client is created.
- On the first `on_ready`, the bot tries to sync global slash commands, records `command-sync` status in state, bootstraps optional env channel IDs into guild state, and starts background schedulers.
- The bot also retains a legacy `on_message` handler for `!ping`.

## 5.2 Scheduled execution behavior
- `auto_screenshot_scheduler()` wakes every 30 seconds and can run heatmap jobs any time after the fixed `15:35` / `06:05` KST schedule has passed, but only once per guild/job/date.
- `intel_scheduler()` wakes every 15 seconds.
- News and EOD jobs are exact-minute checks against configured `HH:MM` values.
- Watch polling is elapsed-interval based using `last_watch_run`.
- Instrument registry refresh is interval-loop driven but has explicit same-day-after-scheduled-time catch-up logic.

## 5.3 Manual/admin command behavior
- Heatmap commands defer the interaction and send a follow-up message without `ephemeral=True`, so the code path appears to produce a normal follow-up message.
- Admin route/toggle commands send ephemeral confirmations or rejections.
- Watch and status commands send ephemeral responses.
- Only admin route/toggle commands visibly enforce owner/admin/global-admin authorization.

## 5.4 Posting/update/upsert behavior
- Same-date thread lookup uses a state record under `commands.{command_key}.daily_posts_by_guild.{guild_id}.{date}`.
- If a stored thread/starter pair can be reloaded, the bot edits the existing thread.
- If that pair cannot be reloaded, the bot creates a new thread.
- Trend posting optionally uses follow-up content messages and persists them incrementally.
- News posting uses two separate threads for domestic/global plus an optional separate trend thread.

## 5.5 State persistence behavior
- The configured app-state backend is the main mutable store for guild routing, image cache metadata, daily post mappings, auto-run metadata, watch runtime state, and job/provider status.
- Default `STATE_BACKEND=file` reads/writes `data/state/state.json`.
- File backend `load_state()` returns an empty state on missing file, invalid JSON, non-dict payload, `JSONDecodeError`, or `OSError`.
- File backend `save_state()` uses atomic temp-file replacement.
- `STATE_BACKEND=postgres` or `postgresql` reads/writes PostgreSQL table `bot_app_state`, keyed by `POSTGRES_STATE_KEY`, with the full app-state document stored in `state JSONB`.
- PostgreSQL backend creates the table on first use and seeds the row from the current file state if no row exists.
- PostgreSQL backend failures raise runtime errors instead of returning empty state.
- Runtime registry is a separate JSON file under `data/state/instrument_registry.json`.

## 5.6 Failure behavior
- Heatmap command failures return user-facing text messages.
- Scheduler loops catch broad exceptions and continue after logging.
- News/EOD/watch jobs write `system.job_last_runs` with `ok`, `failed`, or `skipped` outcomes.
- Provider failures usually update `system.provider_status` as well.
- Some Discord fetch/edit/delete failures are swallowed locally and converted into fallback or partial-cleanup behavior.
- There is no visible global coordination for multi-process safety or job leasing.

# 6. Configuration and dependency map

## Environment variables
- Name: `DISCORD_BOT_TOKEN`
  - Purpose: bot login token
  - Required vs optional: required
  - Observed usage: imported in `bot/app/settings.py`, used by `bot/main.py`
  - Risk if missing: process fails at startup
- Name: `DISCORD_GLOBAL_ADMIN_USER_IDS`
  - Purpose: allowlisted cross-guild admin IDs
  - Required vs optional: optional
  - Observed usage: admin route/toggle command authorization
  - Risk if missing: only guild-owner/admin authorization remains
- Name: `DEFAULT_FORUM_CHANNEL_ID`, `NEWS_TARGET_FORUM_ID`, `EOD_TARGET_FORUM_ID`
  - Purpose: bootstrap/default route IDs
  - Required vs optional: optional
  - Observed usage: startup bootstrap into per-guild state, not direct runtime routing in the inspected paths
  - Risk if missing: startup bootstrap seeding does not occur; in the inspected code, per-guild route writes otherwise come from slash-command handlers
- Name: `LOG_FILE_PATH`, `LOG_RETENTION_DAYS`, `LOG_CONSOLE_ENABLED`
  - Purpose: runtime log configuration
  - Required vs optional: optional with defaults
  - Observed usage: `bot/common/logging.py`
  - Risk if missing: defaults used
- Name: `NEWS_BRIEFING_ENABLED`, `NEWS_BRIEFING_TIME`, `NEWS_BRIEFING_TRADING_DAYS_ONLY`
  - Purpose: enable and schedule the news job
  - Required vs optional: optional with defaults
  - Observed usage: `bot/features/intel_scheduler.py`
  - Risk if missing: defaults apply; if disabled the job does not run
- Name: `NEWS_PROVIDER_KIND`
  - Purpose: choose `mock`, `naver`, `marketaux`, or `hybrid`
  - Required vs optional: optional with default `mock`
  - Observed usage: provider singleton construction in `bot/features/intel_scheduler.py`
  - Risk if missing: mock provider is used
- Name: `NAVER_NEWS_*`, `MARKETAUX_*`, `INTEL_API_TIMEOUT_SECONDS`, `INTEL_API_RETRY_COUNT`
  - Purpose: configure news provider credentials, queries, limits, and request behavior
  - Required vs optional: optional, but credentials are required for live provider modes
  - Observed usage: `bot/features/intel_scheduler.py` and `bot/intel/providers/news.py`
  - Risk if missing: when a live provider mode is selected without matching credentials, the builder returns `ErrorNewsProvider`; otherwise query defaults are used
- Name: `MARKET_DATA_PROVIDER_KIND`, `KIS_APP_KEY`, `KIS_APP_SECRET`, `MASSIVE_API_KEY`
  - Purpose: configure watch quote provider and optional US fallback
  - Required vs optional: optional; if `MARKET_DATA_PROVIDER_KIND=kis` and KIS credentials are missing, the builder returns `ErrorMarketDataProvider`
  - Observed usage: `bot/features/intel_scheduler.py` and `bot/intel/providers/market.py`
  - Risk if missing: mock market data or error provider may be used; Massive fallback absent without key
- Name: `EOD_SUMMARY_ENABLED`, `EOD_SUMMARY_TIME`
  - Purpose: enable and schedule EOD posting
  - Required vs optional: optional with defaults
  - Observed usage: `bot/features/intel_scheduler.py`
  - Risk if missing: EOD remains disabled by default
- Name: `WATCH_POLL_ENABLED`, `WATCH_POLL_INTERVAL_SECONDS`, `WATCH_ALERT_THRESHOLD_PCT`
  - Purpose: enable watch polling and band-comment thresholds
  - Required vs optional: optional with defaults
  - Observed usage: `bot/features/intel_scheduler.py`, `bot/features/watch/service.py`
  - Risk if missing: defaults apply
- Name: `INSTRUMENT_REGISTRY_REFRESH_ENABLED`, `INSTRUMENT_REGISTRY_REFRESH_TIME`, `DART_API_KEY`
  - Purpose: optional daily registry rebuild
  - Required vs optional: refresh schedule optional, `DART_API_KEY` required only for live rebuild
  - Observed usage: `bot/features/intel_scheduler.py`, `bot/intel/instrument_registry.py`
  - Risk if missing: refresh disabled or fails with `dart-api-key-missing`
- Name: `TWELVEDATA_API_KEY`, `OPENFIGI_API_KEY`
  - Purpose: configured-status placeholders for reference/mapping providers
  - Required vs optional: optional
  - Observed usage: default provider rows in `bot/features/status/command.py`
  - Risk if missing: status rows show `disabled`; no active runtime use was confirmed in inspected paths
- Name: `ADMIN_STATUS_CHANNEL_ID`
  - Purpose: documented as manual/admin status channel
  - Required vs optional: optional
  - Observed usage: read in settings only; no direct runtime use was confirmed in inspected code
  - Risk if missing: no confirmed runtime effect

## Config files
- Name: `.env`
  - Purpose: secret and bootstrap/default runtime configuration
  - Required vs optional: required in practice because `DISCORD_BOT_TOKEN` must come from somewhere
  - Observed usage: loaded by `dotenv.load_dotenv()`
  - Risk if missing: startup failure if required vars are not otherwise set in environment
- Name: `.env.example`
  - Purpose: sample configuration and commentary
  - Required vs optional: optional
  - Observed usage: documentation/reference only
  - Risk if missing: lower operator discoverability, no direct runtime failure
- Name: `docker-compose.yml`
  - Purpose: containerized background run with mounted data directories
  - Required vs optional: optional
  - Observed usage: defines env file and mounts for `data/heatmaps`, `data/state`, `data/logs`
  - Risk if missing: no direct effect on local Python run; Docker path unavailable
- Name: `pytest.ini`
  - Purpose: test execution defaults
  - Required vs optional: optional for runtime, relevant for project test behavior
  - Observed usage: excludes `live` tests by default
  - Risk if missing: test selection behavior changes, not runtime behavior

## Provider interfaces
- Name: `NewsProvider`
  - Purpose: fetch and/or analyze news into `NewsAnalysis`
  - Required vs optional: required for news job execution
  - Observed usage: implemented by `MockNewsProvider`, `NaverNewsProvider`, `MarketauxNewsProvider`, `HybridNewsProvider`, `ErrorNewsProvider`
  - Risk if missing: news job fails or uses mock/error behavior
- Name: `MarketDataProvider`
  - Purpose: return `WatchSnapshot` for watch polling
  - Required vs optional: required for watch polling
  - Observed usage: implemented by `MockMarketDataProvider`, `KisMarketDataProvider`, `MassiveSnapshotMarketDataProvider`, `RoutedMarketDataProvider`, `ErrorMarketDataProvider`
  - Risk if missing: watch job fails or uses mock/error behavior
- Name: `EodSummaryProvider`
  - Purpose: return `EodSummary` for EOD posting
  - Required vs optional: required if EOD job is enabled
  - Observed usage: protocol exists; current runtime wiring uses `MockEodSummaryProvider`
  - Risk if missing: EOD job fails

## Discord resources
- Name: per-guild forum channels
  - Purpose: target for heatmap, news, trend, and EOD threads
  - Required vs optional: required per feature/guild
  - Observed usage: stored in state and resolved before posting
  - Risk if missing: feature is skipped or command fails for that guild
- Name: per-guild watch forums with persistent symbol threads
  - Purpose: target for blank watch starters plus current-price, band, and close comments
  - Required vs optional: required for watch delivery
  - Observed usage: resolved at watch-poll time and `/watch add`
  - Risk if missing: watch job counts missing-forum guilds and `/watch add` is rejected
- Name: forum threads and starter/content messages
  - Purpose: concrete posted artifacts for same-day upsert
  - Required vs optional: created as needed
  - Observed usage: tracked by thread/message IDs in state
  - Risk if missing: new thread creation path is used or posting fails
- Name: slash commands
  - Purpose: user/admin interaction surface
  - Required vs optional: central to manual use
  - Observed usage: global app commands synced at startup
  - Risk if missing: bot still runs but manual interaction surface is degraded

## Local state files
- Name: `data/state/state.json`
  - Purpose: default mutable application state and PostgreSQL seed source
  - Required vs optional: optional at first run, central after initialization when `STATE_BACKEND=file`
  - Observed usage: nearly all feature modules through `load_state()` / `save_state()` in file backend
  - Risk if missing: file backend starts with empty state; PostgreSQL backend seeds an empty row if no database row exists
- Name: PostgreSQL `bot_app_state`
  - Purpose: optional mutable application state backend
  - Required vs optional: required only when `STATE_BACKEND=postgres` or `postgresql`
  - Observed usage: `bot/forum/repository.py` stores the full `AppState` document in `state JSONB`
  - Risk if missing: table is created on first use; if the database is unreachable, selected PostgreSQL backend fails closed
- Name: `data/state/instrument_registry.json`
  - Purpose: runtime registry override artifact
  - Required vs optional: optional
  - Observed usage: first-choice registry source if present
  - Risk if missing: bundled registry is used instead
- Name: `bot/intel/data/instrument_registry.json`
  - Purpose: bundled registry snapshot
  - Required vs optional: optional fallback, but effectively important for watch lookup
  - Observed usage: second-choice registry source
  - Risk if missing: seed or empty registry fallback
- Name: `bot/intel/data/instrument_registry_seed.json`
  - Purpose: seed fallback registry payload
  - Required vs optional: fallback only
  - Observed usage: last local registry source before empty registry
  - Risk if missing: registry can become empty if no bundled/runtime artifact exists
- Name: `data/heatmaps/kheatmap/*`, `data/heatmaps/usheatmap/*`
  - Purpose: cached PNG captures
  - Required vs optional: created on demand
  - Observed usage: capture cache reuse in heatmap commands
  - Risk if missing: recapture required
- Name: `data/logs/bot.log`
  - Purpose: persisted runtime log
  - Required vs optional: created on demand
  - Observed usage: logging subsystem
  - Risk if missing: recreated; historical logs absent

## External services/APIs
- Name: Discord API
  - Purpose: command sync, channel/thread/message operations, alert delivery
  - Required vs optional: required
  - Observed usage: all command/posting paths
  - Risk if missing: bot cannot operate
- Name: Hankyung market map pages
  - Purpose: Korea heatmap capture source
  - Required vs optional: required for fresh Korea capture
  - Observed usage: `bot/markets/providers/korea.py`
  - Risk if missing: fresh Korea capture fails; a recent cached image may still be used if matching state and file conditions are satisfied
- Name: Finviz map pages
  - Purpose: US heatmap capture source
  - Required vs optional: required for fresh US capture
  - Observed usage: `bot/markets/providers/us.py`
  - Risk if missing: fresh US capture fails; a recent cached image may still be used if matching state and file conditions are satisfied
- Name: `exchange_calendars`
  - Purpose: KRX/NYSE session-day checks
  - Required vs optional: required for trading-day gating
  - Observed usage: auto scheduler and optional news/EOD gating
  - Risk if missing: calendar helpers fail and jobs may skip
- Name: Naver Search API
  - Purpose: domestic/global news provider in `naver` or `hybrid` mode
  - Required vs optional: optional unless selected
  - Observed usage: `NaverNewsProvider`
  - Risk if missing: live news provider builder returns error provider
- Name: Marketaux API
  - Purpose: global news provider in `marketaux` or `hybrid` mode
  - Required vs optional: optional unless selected
  - Observed usage: `MarketauxNewsProvider`
  - Risk if missing: live news provider builder returns error provider
- Name: KIS Open API
  - Purpose: live quote provider for watch polling
  - Required vs optional: optional unless `MARKET_DATA_PROVIDER_KIND=kis`
  - Observed usage: `KisMarketDataProvider`
  - Risk if missing: error provider in KIS mode or mock mode when not selected
- Name: Massive API
  - Purpose: optional US fallback quote source
  - Required vs optional: optional
  - Observed usage: `MassiveSnapshotMarketDataProvider`
  - Risk if missing: no US fallback; KIS-only behavior remains
- Name: OpenDART, SEC, KRX data endpoints
  - Purpose: live registry rebuild inputs
  - Required vs optional: optional unless registry refresh or manual rebuild is used
  - Observed usage: `build_live_registry()`
  - Risk if missing: registry refresh fails or cannot enrich beyond bundled data

# 7. Ambiguities and unverifiable areas
- Area: Intended operational role of `ADMIN_STATUS_CHANNEL_ID`
  - Why ambiguous: the variable exists in settings and docs but no direct runtime use was confirmed in the inspected code.
  - What seems likely: it was intended for future/manual operator notifications.
  - What cannot be confirmed: whether any command or scheduler is supposed to post there in the current release.
  - Why this ambiguity matters: operators may expect alerts/status pushes that do not actually occur.
- Area: EOD feature maturity vs operational intent
  - Why ambiguous: the scheduler path is implemented, but the runtime provider is hardcoded to `MockEodSummaryProvider` and README calls the feature paused.
  - What seems likely: the code path exists for a paused or development-stage feature.
  - What cannot be confirmed: whether production use with live data was ever intended in the current branch.
  - Why this ambiguity matters: documentation could overstate EOD readiness.
- Area: Watch baseline lifecycle
  - Why ambiguous: baseline is stored and reused, but no separate reset policy or rollover rule is documented in code.
  - What seems likely: baseline stays fixed until first set or symbol removal.
  - What cannot be confirmed: whether baseline is supposed to reset daily, after alerts, or by admin action.
  - Why this ambiguity matters: alert semantics depend on baseline lifecycle.
- Area: Exact starter-thread reuse safety on transient Discord errors
  - Why ambiguous: `upsert_daily_post()` treats `NotFound`, `Forbidden`, and generic `HTTPException` the same when fetching existing thread/starter.
  - What seems likely: the code prefers recreation when it cannot fetch the existing thread.
  - What cannot be confirmed: whether duplicate-avoidance under transient Discord failures is considered acceptable in current operations.
  - Why this ambiguity matters: same-day post reuse may be less reliable than the happy-path design suggests.
- Area: Intended authorization scope for watch and status commands
  - Why ambiguous: admin commands have explicit auth, watch/status commands do not, and no higher-level policy doc in code enforces a common rule.
  - What seems likely: watch/status were implemented as guild-available commands.
  - What cannot be confirmed: whether this openness is deliberate product behavior or an unfinished policy.
  - Why this ambiguity matters: reverse docs should not assume stronger access control than the code provides.
- Area: Cross-guild isolation under multiple running bot instances
  - Why ambiguous: state is a shared local JSON file with no visible inter-process locking.
  - What seems likely: single-process operation is assumed.
  - What cannot be confirmed: whether multi-instance deployment is supported or intentionally unsupported.
  - Why this ambiguity matters: operational guidance and failure analysis differ sharply between single-writer and multi-writer assumptions.
- Area: Watch polling market-hours semantics
  - Why ambiguous: detailed operator intent for thread-follow expectations and future notification-volume tuning still lives outside this document.
  - What seems likely: current implementation intentionally uses market-session-aware current-price comment behavior with off-hours close finalization only.
  - What cannot be confirmed: whether future rollout will add further forum-notification controls.
  - Why this ambiguity matters: operator expectations for Discord notification volume depend on these choices.
- Area: Heatmap command response visibility
  - Why ambiguous: `run_heatmap_command()` uses `interaction.response.defer(thinking=True)` and `followup.send(message)` without `ephemeral=True`.
  - What seems likely: the result message is a normal visible follow-up.
  - What cannot be confirmed: exact UI behavior across Discord clients without live execution in this analysis.
  - Why this ambiguity matters: operator expectations differ between public and ephemeral responses.

# 8. Observed gaps in current implementation
- Gap ID: G-01
  - Gap: `load_state()` fails open to an empty state on JSON decode or file I/O errors.
  - Observed evidence: `bot/forum/repository.py::load_state`
  - Current operational risk: a bad read can make the application behave as if all routes/watchlists/status history were absent.
  - Confidence: Confirmed
- Gap ID: G-02
  - Gap: state writes are plain load-modify-save operations with no visible inter-process or cross-task locking at repository level.
  - Observed evidence: `bot/forum/repository.py`, multiple direct `load_state()`/`save_state()` call sites across schedulers and commands
  - Current operational risk: concurrent writers can overwrite unrelated changes.
  - Confidence: Confirmed
- Gap ID: G-03
  - Gap: news and EOD schedulers are exact-minute only and do not show same-day catch-up logic after a late start.
  - Observed evidence: `bot/features/intel_scheduler.py`
  - Current operational risk: startup or reconnect after the scheduled minute can skip a day’s news/EOD run.
  - Confidence: Confirmed
- Gap ID: G-04
  - Gap: route setup commands do not visibly validate the bot’s effective permissions on the chosen channel.
  - Observed evidence: `bot/features/admin/command.py`
  - Current operational risk: configuration can succeed even if later posting will fail.
  - Confidence: Confirmed
- Gap ID: G-05
- Gap: watch add/start/stop/list commands do not visibly enforce owner/admin/global-admin authorization.
- Observed evidence: `bot/features/watch/command.py`
  - Current operational risk: any guild member with command access can add, start, stop, or inspect the shared guild watchlist; only destructive delete is currently restricted.
  - Confidence: Confirmed
- Gap ID: G-06
  - Gap: status commands do not visibly enforce operator-only access.
  - Observed evidence: `bot/features/status/command.py`
  - Current operational risk: provider and job diagnostics are available to any user who can invoke the commands.
  - Confidence: Confirmed
- Gap ID: G-07
  - Gap: status and watch list responses do not show explicit message-length management.
  - Observed evidence: `bot/features/status/command.py`, `bot/features/watch/command.py`
  - Current operational risk: long outputs may exceed Discord message limits.
  - Confidence: Confirmed
- Gap ID: G-08
  - Gap: existing thread/starter fetch failures of several types all fall back to recreation logic.
  - Observed evidence: `bot/forum/service.py`
  - Current operational risk: transient Discord API issues may lead to duplicate same-day forum content.
  - Confidence: Confirmed
- Gap ID: G-09
  - Gap: live Discord/KIS smoke for the new watch forum-thread flow is still unverified in the inspected session.
  - Observed evidence: implementation and automated tests were updated locally, but no live forum permission or vendor credential check was executed here.
  - Current operational risk: runtime permission issues or provider payload mismatches may still appear only in production-like conditions.
  - Confidence: Confirmed
- Gap ID: G-10
  - Gap: EOD summary runtime provider is mock-only in the inspected code.
  - Observed evidence: `bot/features/intel_scheduler.py` sets `eod_provider = MockEodSummaryProvider()`
  - Current operational risk: enabling EOD will post mock content unless code changes elsewhere alter this wiring.
  - Confidence: Confirmed
- Gap ID: G-11
  - Gap: startup bootstrap save is not visibly isolated from the rest of `on_ready`.
  - Observed evidence: `bot/app/bot_client.py::_bootstrap_guild_channel_routes_from_env`
  - Current operational risk: bootstrap save failure can interfere with scheduler start sequence.
  - Confidence: Confirmed

# 9. Separation of As-Is vs To-Be

| Item | As-Is current behavior | Unknown / ambiguous | Should NOT be assumed from current code |
| --- | --- | --- | --- |
| Heatmap routing | Runtime heatmap posting reads per-guild forum route from `data/state/state.json` | Whether env bootstrap is always intended to remain supported | Do not assume env IDs are runtime fallback routing |
| Same-day post reuse | Reuse depends on stored thread/message IDs and successful fetch/edit of existing resources | Reliability under transient Discord fetch failures | Do not assume idempotent upsert under all API failure modes |
| Auto screenshot schedule | Checks every 30s and can run once per guild/job/date any time after fixed `15:35`/`06:05` KST schedule has passed | Whether same-day late execution is operationally acceptable for all guilds | Do not assume an exact-minute-only trigger |
| News posting | Posts separate domestic/global daily threads and an optional trend thread | Whether partial-region success should count as healthy | Do not assume robust regional failure isolation |
| Trend posting | In current code, the trend thread is skipped unless at least one region has 3+ themes; empty displayed regions are rendered as placeholder content messages | Intended theme-quality guarantee | Do not assume business-quality trend accuracy from current heuristics |
| EOD summary | Scheduler path exists but provider is mock and feature default is off | Whether live EOD was meant to be production-ready | Do not assume real market-close data |
| Watch polling | Polls stored watchlist on interval and updates per-symbol forum threads with session-aware band/close comments | Live Discord/forum permissions and vendor payload stability | Do not assume live smoke has already validated the rollout |
| Watch authorization | Guild-only check is present; explicit admin auth is not | Whether open watchlist mutation is intentional | Do not assume watchlist changes are admin-restricted |
| Status commands | Return state/default diagnostic rows ephemerally | Intended audience and any future operator-only policy | Do not assume diagnostics are access-controlled |
| Instrument registry refresh | Has explicit same-day catch-up and writes runtime override file on success | Extent of operational monitoring around refresh | Do not assume other schedulers share the same catch-up behavior |
| Provider rows in `/source-status` | Some rows are derived from config defaults, not live activity | Whether every shown provider is actively wired into runtime jobs | Do not assume “configured” means currently used in a job |
| State safety | JSON state is atomically written per save | Multi-process safety or transactional merge behavior | Do not assume strong concurrency safety |

# 10. Optional improvement notes
- The current code would benefit from a separate operator-facing document that explicitly states:
  - which commands are intentionally public vs admin-only
  - what follow/notification expectation operators should set for watch forum threads
  - whether EOD is development-only or supported when enabled
- The current code/docs would also benefit from a dedicated state-schema document for `data/state/state.json` and a scheduler contract document that distinguishes exact-minute jobs from the registry refresh catch-up path.
- The current code/docs would also benefit from a dedicated state-schema document for `data/state/state.json` and a scheduler contract document that clearly separates heatmap catch-up behavior from exact-minute news/EOD jobs and the registry refresh catch-up path.
