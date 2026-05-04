# Runtime Runbook

## Local Run
- Local bootstrap currently requires Python `3.10+`.
- On the current macOS host, `python3` is still `3.9.6`, so local bootstrap uses `/opt/homebrew/bin/python3.11`.
- Bootstrap the virtual environment:
  - Windows: `py -3 scripts/bootstrap_dev_env.py --with-playwright`
  - macOS/Linux: `python3.11 scripts/bootstrap_dev_env.py --with-playwright`
  - macOS/Linux alternate: any other `python3.10+` interpreter
- If `.venv` was created on another OS or is no longer runnable:
  - Windows: `py -3 scripts/bootstrap_dev_env.py --recreate --with-playwright`
  - macOS/Linux: `python3.11 scripts/bootstrap_dev_env.py --recreate --with-playwright`
  - macOS/Linux alternate: any other `python3.10+` interpreter
- Optional shell activation after bootstrap:
  - Windows: `.\.venv\Scripts\Activate.ps1`
  - macOS/Linux: `source .venv/bin/activate`
- Prepare configuration:
  - copy `.env.example` to `.env`
  - set the bot token and any feature-specific credentials you actually need
- Start the bot:
  - `python -m bot.main`

## Standard Validation
- Default local and CI validation entrypoint:
  - Windows: `py -3 scripts/run_repo_checks.py`
  - macOS/Linux: `python3 scripts/run_repo_checks.py`
- CI note:
  - `.github/workflows/pr-checks.yml` exports placeholder `DISCORD_BOT_TOKEN=ci-placeholder-token` because `bot.app.settings` requires a token at import time even for non-live test collection
  - local validation still needs `.env` or an explicit `DISCORD_BOT_TOKEN` when no local env file is present
- Narrower suites:
  - Windows: `py -3 scripts/run_repo_checks.py unit`
  - macOS/Linux: `python3 scripts/run_repo_checks.py unit`
  - Windows: `py -3 scripts/run_repo_checks.py integration`
  - macOS/Linux: `python3 scripts/run_repo_checks.py integration`
  - Windows: `py -3 scripts/run_repo_checks.py collect`
  - macOS/Linux: `python3 scripts/run_repo_checks.py collect`
- Live-only tests:
  - Windows: `py -3 scripts/run_repo_checks.py --include-live`
  - macOS/Linux: `python3 scripts/run_repo_checks.py --include-live`

## Docker Run
- Start:
  - `docker compose up -d --build`
- Start with PostgreSQL state backend:
  - set `STATE_BACKEND=postgres`
  - set `DATABASE_URL=postgresql://discord_heatmap:discord_heatmap@postgres:5432/discord_heatmap`
  - run `docker compose up -d --build`
- View logs:
  - `docker compose logs -f discord-bot`
- View PostgreSQL logs:
  - `docker compose logs -f postgres`
- Stop:
  - `docker compose down`
- Docker-specific note:
  - mounted `data/` directories are used so logs, state, and cached artifacts can survive container recreation
  - the local PostgreSQL service uses the named Docker volume `postgres-data`
  - if local Python is older than `3.10`, Docker is the supported fallback for validation commands such as `docker compose run --rm --build -v ${PWD}:/app discord-bot python scripts/run_repo_checks.py collect`

## State Backend
- Default state backend:
  - `STATE_BACKEND=file`
  - runtime state is `data/state/state.json`
- PostgreSQL state backend:
  - `STATE_BACKEND=postgres`
  - `DATABASE_URL` is required
  - `POSTGRES_STATE_KEY` defaults to `default`
  - the bot creates table `bot_app_state` on first use
  - the full app-state document is stored in `state JSONB`
  - when no database row exists, first load seeds from `data/state/state.json` if present
- PostgreSQL failures are fail-closed. If the backend is selected and the database is unavailable, the bot raises instead of silently replacing state with an empty document.

## Discord Setup
- Confirm the bot is present in the target server and application commands are visible.
- Configure per-guild routes through the slash commands intended for forum routing.
- When features beyond the base heatmap flow are enabled, configure their specific target channels/forums as needed.
- The bot must be able to use application commands and post/send in the configured Discord resources.
- Code-confirmed command boundary:
  - `/setforumchannel`, `/setnewsforum`, `/seteodforum`, `/setwatchforum`, `/autoscreenshot` require guild owner, guild administrator, or a user ID listed in `DISCORD_GLOBAL_ADMIN_USER_IDS`
  - `/kheatmap`, `/usheatmap`, and `/watch *` require guild context but are not admin-gated
  - `/health`, `/last-run`, and `/source-status` do not currently apply a visible authorization gate in code
- Watch-specific operator note:
  - configure `/setwatchforum` before using `/watch add`
  - watch notifications now come from per-symbol forum-thread comments, so users need to follow the relevant thread if they want Discord notifications
  - `마감가 알림` is created only on KST due-minute poll ticks: `KRX:*` at 16:00 KST and `NAS:*`/`NYS:*`/`AMS:*` at 07:00 KST
  - if the runtime misses the due minute, close finalization is left pending until the next due minute; later regular-session current-price and band updates still continue
  - if a preserved pending close target has aged past the immediately adjacent trading session, the bot drops that pending retry state instead of retrying forever with an unresolvable snapshot

## Logs and State Paths
- Main mutable state, file backend:
  - `data/state/state.json`
- Main mutable state, PostgreSQL backend:
  - `bot_app_state.state` JSONB row identified by `POSTGRES_STATE_KEY`
- Optional runtime registry override:
  - `data/state/instrument_registry.json`
- Runtime logs:
  - `data/logs/bot.log`
- Cached heatmap artifacts:
  - `data/heatmaps/kheatmap/`
  - `data/heatmaps/usheatmap/`
- Deep state/config behavior reference:
  - `../specs/as-is-functional-spec.md`

## Basic Operator Checks
- After startup, confirm the bot connected and command sync completed in logs or status surfaces.
- Confirm the expected slash commands are visible in Discord.
- Set the required forum routes for the guild before expecting posts or alerts.
- Use the status commands to inspect recent job/provider state when debugging.
- If scheduler behavior looks wrong, also check for duplicate running bot processes and stale local/container state.
- For change validation before shipping, prefer `scripts/run_repo_checks.py` through the active interpreter over ad hoc `pytest` commands so local and CI behavior stay aligned.

## Troubleshooting
- Commands not visible:
  - check bot presence in the guild
  - check application-command permissions
  - allow for global command propagation delay
- Forum posting or watch-thread delivery fails:
  - verify the relevant guild route is configured
  - verify the bot can post/send in the target resource
  - inspect `data/logs/bot.log` and the configured app-state backend
- Watch thread behavior looks wrong:
  - verify `watch_forum_channel_id` exists in the configured app-state backend
  - check `commands.watchpoll.symbol_threads_by_guild` and `system.watch_session_alerts`
  - confirm the bot can create forum threads and send/edit thread comments in the configured watch forum
- Render or capture problems:
  - retry after cached artifacts expire or are intentionally refreshed
  - verify Playwright/browser setup
- Unexpected scheduler behavior:
  - inspect latest run state via status commands or `data/state/state.json`
  - when using PostgreSQL, inspect `bot_app_state` for the selected `POSTGRES_STATE_KEY`
  - check whether multiple bot instances are running
  - use `../specs/as-is-functional-spec.md` as the current deep reference for exact scheduler semantics

## Shutdown / Cleanup
- Stop local or Docker bot processes before starting another instance with the same token.
- Check for duplicate local/background sessions when debugging repeated or unexpected behavior.
- Keep `data/state/`, `data/logs/`, and `data/heatmaps/` if you need file-backend continuity across restarts.
- Keep the `postgres-data` Docker volume if you need PostgreSQL-backend continuity across container recreation.
