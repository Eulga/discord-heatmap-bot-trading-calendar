# Discord Heatmap Bot

Python Discord bot for posting Korea/US heatmaps and running related scheduled market/news automation.

## Setup

Local bootstrap currently requires Python `3.10+`. On this macOS host, `python3` is still `3.9.6`, so the working local interpreter is `python3.11`. If the machine only has an older Python, use Docker for validation instead of `.venv`.

```bash
# Windows: py -3 scripts/bootstrap_dev_env.py --with-playwright
# macOS/Linux: python3.11 scripts/bootstrap_dev_env.py --with-playwright
# macOS/Linux alternate: any other python3.10+ interpreter
cp .env.example .env
```

If `.venv` was created on another OS or no longer matches the current interpreter, rebuild it with:

```bash
# Windows: py -3 scripts/bootstrap_dev_env.py --recreate --with-playwright
# macOS/Linux: python3.11 scripts/bootstrap_dev_env.py --recreate --with-playwright
# macOS/Linux alternate: any other python3.10+ interpreter
```

Optional shell activation after bootstrap:

```bash
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
```

Set the bot token in `.env` before running.

Docker fallback for validation when a suitable local Python is unavailable:

```bash
docker compose run --rm --build -v ${PWD}:/app discord-bot python scripts/run_repo_checks.py collect
```

## Run

Local:

```bash
python -m bot.main
```

Docker:

```bash
docker compose up -d --build
docker compose logs -f discord-bot
docker compose down
```

Optional local model server for `/local ask`:

```bash
scripts/start_local_model_server.sh
scripts/stop_local_model_server.sh
```

The helper scripts keep PID/log files under `data/logs/` and use port `8081` for the Mac host `llama-server`. They are manual helpers only; bot/server restart skills do not manage the local model server lifecycle.

## State Persistence

Default runtime state uses `data/state/state.json`.

PostgreSQL can be enabled by setting:

```bash
STATE_BACKEND=postgres
DATABASE_URL=postgresql://discord_heatmap:discord_heatmap@postgres:5432/discord_heatmap
POSTGRES_STATE_KEY=default
```

The PostgreSQL backend stores the existing app-state document in the
`bot_app_state` JSONB table. On first load it seeds from `data/state/state.json`
when no database row exists.

The compose file includes a local `postgres` service for `STATE_BACKEND=postgres`
development, but the bot still uses file state unless `.env` selects the
PostgreSQL backend.

## Minimal Architecture

- `bot/app`: bootstrap, settings, command sync
- `bot/forum`: state repository and forum upsert
- `bot/markets`: capture/cache and market helpers
- `bot/intel`: provider and registry logic
- `bot/features`: slash commands and schedulers
- Watch polling uses `/setwatchforum` plus persistent per-symbol forum threads instead of a shared text alert channel.

## Tests

Default:

```bash
# Windows: py -3 scripts/run_repo_checks.py
# macOS/Linux: python3 scripts/run_repo_checks.py
# current macOS host also works with: python3.11 scripts/run_repo_checks.py
```

Unit only:

```bash
# Windows: py -3 scripts/run_repo_checks.py unit
# macOS/Linux: python3 scripts/run_repo_checks.py unit
# current macOS host also works with: python3.11 scripts/run_repo_checks.py unit
```

Integration only:

```bash
# Windows: py -3 scripts/run_repo_checks.py integration
# macOS/Linux: python3 scripts/run_repo_checks.py integration
# current macOS host also works with: python3.11 scripts/run_repo_checks.py integration
```

Collection / CI parity:

```bash
# Windows: py -3 scripts/run_repo_checks.py collect
# macOS/Linux: python3 scripts/run_repo_checks.py collect
# current macOS host also works with: python3.11 scripts/run_repo_checks.py collect
```

Live-only:

```bash
# Windows: py -3 scripts/run_repo_checks.py --include-live
# macOS/Linux: python3 scripts/run_repo_checks.py --include-live
# current macOS host also works with: python3.11 scripts/run_repo_checks.py --include-live
```

## Deeper Docs

- Current state summary:
  - `docs/context/CURRENT_STATE.md`
- Latest active handoff:
  - `docs/context/session-handoff.md`
- Project operating rules:
  - `docs/context/operating-rules.md`
- Runtime runbook:
  - `docs/operations/runtime-runbook.md`
- Config boundary and env/state reference:
  - `docs/operations/config-reference.md`
- Deep current implementation reference:
  - `docs/specs/as-is-functional-spec.md`
- Target/to-be external intel contract:
  - `docs/specs/external-intel-api-spec.md`
- Existing integration test references:
  - `docs/specs/integration-test-cases.md`
  - `docs/specs/integration-live-test-cases.md`

## Agent Workflow

- Default agent read order starts at `AGENTS.md`
- Bootstrap helper is `scripts/bootstrap_dev_env.py`
- Standardized validation entrypoint is `scripts/run_repo_checks.py`, invoked with the active interpreter for the current OS
- Repo-local Codex skills now include:
  - `codex-harness`
  - `pr-review`
  - `ci-triage`
  - `docs-sync`
  - `scheduler-watch-review`
  - `server-restart-dev`
  - `server-restart-prod`
- Staged Codex workflow templates and state helper live in `.codex-harness/`;
  run-specific `requirements.md`, `state.json`, and role reports are ignored
  runtime files created from tracked templates.
- GitHub PRs now have a default template and CI workflow under `.github/`
