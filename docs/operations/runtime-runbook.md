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
  - set `STATE_BACKEND=postgres` or `postgresql`
  - set `DATABASE_URL` to a PostgreSQL database reachable from the process
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
  - dev PostgreSQL is configured for `Asia/Seoul`; verify with `docker compose exec -T postgres psql -U discord_heatmap -d discord_heatmap -c "SHOW timezone"`
  - run `docker compose up -d --build`
- Infra/checks-only startup without live Discord connection:
  - `docker compose up -d postgres`
  - `docker compose exec postgres pg_isready -U discord_heatmap -d discord_heatmap`
  - `docker compose run --rm -v "$PWD:/app" discord-bot python -c "from bot.forum.state_store import ensure_schema_and_migrate; ensure_schema_and_migrate(); print('state_migration_ok')"`
- View logs:
  - `docker compose logs -f discord-bot`
- View PostgreSQL logs:
  - `docker compose logs -f postgres`
- View PostgreSQL with GUI:
  - `docker compose up -d adminer`
  - open `http://127.0.0.1:8080`
  - use system `PostgreSQL`, server `postgres`, username/password/database from `docker-compose.yml`
- Inspect accumulated watch close prices:
  - in Adminer, open table `bot_watch_close_prices`
  - SQL example: `SELECT symbol, session_date, close_price, provider FROM bot_watch_close_prices ORDER BY session_date DESC, symbol LIMIT 20`
- Optional local model command:
  - `/local ask` expects an already-running external OpenAI-compatible local model endpoint
  - bot restart workflows and server restart skills do not start, stop, adopt, or health-check the model server
  - if an operator manually uses the repository helper scripts outside bot restart:
    - `scripts/start_local_model_server.sh`
    - `scripts/stop_local_model_server.sh`
  - those helper scripts use PID/log files:
    - `data/logs/local-model-server.pid`
    - `data/logs/local-model-server.log`
  - the helper uses port `8081` because Adminer uses `8080`
  - verify from the Docker bot container:
    - `docker compose exec -T discord-bot python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:8081/v1/models', timeout=10).read().decode('utf-8')[:500])"`
  - Docker `.env` should use `LOCAL_MODEL_BASE_URL=http://host.docker.internal:8081/v1`
- Stop:
  - `docker compose down`
- Docker-specific note:
  - mounted `data/` directories are used so logs, state, and cached artifacts can survive container recreation
  - the local PostgreSQL service uses the named Docker volume `postgres-data`
  - if local Python is older than `3.10`, Docker is the supported fallback for validation commands such as `docker compose run --rm --build -v ${PWD}:/app discord-bot python scripts/run_repo_checks.py collect`

## State Backend
- Current runtime state backend:
  - `STATE_BACKEND=postgres` or `postgresql`
  - `DATABASE_URL` is required
  - `POSTGRES_STATE_KEY` defaults to `default` and namespaces split rows
- Development PostgreSQL timezone is `Asia/Seoul`.
- Startup creates/migrates PostgreSQL tables before the Discord client is created.
- Runtime reads/writes split domain tables for guild routes, scheduler markers, daily posts, image cache, watch state, job/provider status, and news dedup.
- Legacy backup/import behavior:
  - `bot_app_state.state` keeps the old full JSONB document for rollback/audit.
  - if that row is absent, `data/state/state.json` can be imported once during `split_state_v1`.
  - runtime does not sync split rows back into `bot_app_state`.
- PostgreSQL failures are fail-closed. If the database is unavailable, the bot raises instead of silently replacing state with an empty document.

## Discord Setup
- Confirm the bot is present in the target server and application commands are visible.
- Configure per-guild routes through the slash commands intended for forum routing.
- When features beyond the base heatmap flow are enabled, configure their specific target channels/forums as needed.
- The bot must be able to use application commands and post/send in the configured Discord resources.
- Code-confirmed command boundary:
  - `/setforumchannel`, `/setnewsforum`, `/seteodforum`, `/setwatchforum`, `/autoscreenshot` require guild owner, guild administrator, or a user ID listed in `DISCORD_GLOBAL_ADMIN_USER_IDS`
  - `/kheatmap`, `/usheatmap`, and `/watch *` require guild context but are not admin-gated
  - `/local ask` requires guild owner, guild administrator, or a user ID listed in `DISCORD_GLOBAL_ADMIN_USER_IDS`
  - `/health`, `/last-run`, and `/source-status` do not currently apply a visible authorization gate in code
- Local model note:
  - `/local ask` only sends text to an already-running OpenAI-compatible local model HTTP server
  - the bot does not grant model-side shell, file, database, or tool access
  - default responses are ephemeral; public responses require `LOCAL_MODEL_PUBLIC_RESPONSES=true` and the command's `public` option
  - local model server lifecycle is managed outside bot/server restart workflows
- Watch-specific operator note:
  - configure `/setwatchforum` before using `/watch add`
  - watch notifications now come from per-symbol forum-thread comments, so users need to follow the relevant thread if they want Discord notifications
  - `마감가 알림` is created by separate watch-close jobs, not by the regular watch poll: `watch_close_krx` handles `KRX:*` from 16:00:00 through 16:29:59 KST, and `watch_close_us` handles `NAS:*`/`NYS:*`/`AMS:*` from 07:00:00 through 07:29:59 KST
  - if the runtime starts or is delayed shortly after the due minute, the 30-minute grace window can still finalize the close; outside that window, long-outage Discord close-comment backfill is not attempted
  - close prices are still accumulated in `bot_watch_close_prices` once a provider snapshot exposes `session_close_price`; after the due minute, DB catch-up can save a missing close price without creating a Discord close comment
  - if a preserved pending close target has aged past the immediately adjacent trading session, the bot drops that pending retry state instead of retrying forever with an unresolvable snapshot

## Logs and State Paths
- Main mutable state, PostgreSQL backend:
  - split `bot_*` domain tables identified by `POSTGRES_STATE_KEY`
  - `bot_app_state.state` is legacy backup/import source only
- Optional runtime registry override:
  - `data/state/instrument_registry.json`
- Runtime logs:
  - `data/logs/bot.log`
  - `data/logs/local-model-server.log`
  - `data/logs/local-model-server.pid`
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
  - check `bot_watch_symbols` and `bot_watch_session_alerts`
  - check `bot_watch_close_prices` and `bot_watch_close_price_attempts` when DB close-price accumulation looks incomplete
  - confirm the bot can create forum threads and send/edit thread comments in the configured watch forum
- Render or capture problems:
  - retry after cached artifacts expire or are intentionally refreshed
  - verify Playwright/browser setup
- Unexpected scheduler behavior:
  - inspect latest run state via status commands or `bot_job_status`
  - inspect per-guild scheduler markers in `bot_guild_job_markers`
  - check whether multiple bot instances are running
  - use `../specs/as-is-functional-spec.md` as the current deep reference for exact scheduler semantics

## Shutdown / Cleanup
- Stop local or Docker bot processes before starting another instance with the same token.
- Check for duplicate local/background sessions when debugging repeated or unexpected behavior.
- Keep `data/state/`, `data/logs/`, and `data/heatmaps/` if you need file-backend continuity across restarts.
- Keep the `postgres-data` Docker volume if you need PostgreSQL-backend continuity across container recreation.
