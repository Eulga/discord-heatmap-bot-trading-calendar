# Runtime Runbook

## Local Run
- Create and activate a virtual environment:
  - `py -3 -m venv .venv`
  - `.\.venv\Scripts\Activate.ps1`
- Install dependencies:
  - `python -m pip install --upgrade pip`
  - `pip install -r requirements.txt`
  - `python -m playwright install chromium`
- Prepare configuration:
  - copy `.env.example` to `.env`
  - set the bot token and any feature-specific credentials you actually need
- Start the bot:
  - `python -m bot.main`

## Docker Run
- Start:
  - `docker compose up -d --build`
- View logs:
  - `docker compose logs -f discord-bot`
- Stop:
  - `docker compose down`
- Docker-specific note:
  - mounted `data/` directories are used so logs, state, and cached artifacts can survive container recreation

## Discord Setup
- Confirm the bot is present in the target server and application commands are visible.
- Configure per-guild routes through the slash commands intended for forum/text routing.
- When features beyond the base heatmap flow are enabled, configure their specific target channels/forums as needed.
- The bot must be able to use application commands and post/send in the configured Discord resources.
- Code-confirmed command boundary:
  - `/setforumchannel`, `/setnewsforum`, `/seteodforum`, `/setwatchchannel`, `/autoscreenshot` require guild owner, guild administrator, or a user ID listed in `DISCORD_GLOBAL_ADMIN_USER_IDS`
  - `/kheatmap`, `/usheatmap`, and `/watch *` require guild context but are not admin-gated
  - `/health`, `/last-run`, and `/source-status` do not currently apply a visible authorization gate in code

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
- Set the required forum/text routes for the guild before expecting posts or alerts.
- Use the status commands to inspect recent job/provider state when debugging.
- If scheduler behavior looks wrong, also check for duplicate running bot processes and stale local/container state.

## Troubleshooting
- Commands not visible:
  - check bot presence in the guild
  - check application-command permissions
  - allow for global command propagation delay
- Forum or alert posting fails:
  - verify the relevant guild route is configured
  - verify the bot can post/send in the target resource
  - inspect `data/logs/bot.log` and `data/state/state.json`
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
