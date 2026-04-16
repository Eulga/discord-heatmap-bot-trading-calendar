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
- View logs:
  - `docker compose logs -f discord-bot`
- Stop:
  - `docker compose down`
- Docker-specific note:
  - mounted `data/` directories are used so logs, state, and cached artifacts can survive container recreation
  - if local Python is older than `3.10`, Docker is the supported fallback for validation commands such as `docker compose run --rm --build -v ${PWD}:/app discord-bot python scripts/run_repo_checks.py collect`

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

## Logs and State Paths
- Main mutable state:
  - `data/state/state.json`
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
  - inspect `data/logs/bot.log` and `data/state/state.json`
- Watch thread behavior looks wrong:
  - verify `watch_forum_channel_id` exists in `data/state/state.json`
  - check `commands.watchpoll.symbol_threads_by_guild` and `system.watch_session_alerts`
  - confirm the bot can create forum threads and send/edit thread comments in the configured watch forum
- Render or capture problems:
  - retry after cached artifacts expire or are intentionally refreshed
  - verify Playwright/browser setup
- Unexpected scheduler behavior:
  - inspect latest run state via status commands or `data/state/state.json`
  - check whether multiple bot instances are running
  - use `../specs/as-is-functional-spec.md` as the current deep reference for exact scheduler semantics

## Shutdown / Cleanup
- Stop local or Docker bot processes before starting another instance with the same token.
- Check for duplicate local/background sessions when debugging repeated or unexpected behavior.
- Keep `data/state/`, `data/logs/`, and `data/heatmaps/` if you need continuity across restarts.
