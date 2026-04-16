# Discord Heatmap Bot

Python Discord bot for posting Korea/US heatmaps and running related scheduled market/news automation.

## Setup

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

Set the bot token in `.env` before running.

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
python scripts/run_repo_checks.py
```

Unit only:

```bash
python scripts/run_repo_checks.py unit
```

Integration only:

```bash
python scripts/run_repo_checks.py integration
```

Collection / CI parity:

```bash
python scripts/run_repo_checks.py collect
```

Live-only:

```bash
python scripts/run_repo_checks.py --include-live
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
- Standardized validation entrypoint is `python scripts/run_repo_checks.py`
- Repo-local Codex skills now include:
  - `pr-review`
  - `ci-triage`
  - `docs-sync`
  - `scheduler-watch-review`
- GitHub PRs now have a default template and CI workflow under `.github/`
