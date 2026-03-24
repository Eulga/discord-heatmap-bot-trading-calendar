# Discord Heatmap Bot

Python Discord bot for posting Korea/US heatmaps and running related scheduled market/news automation.

## Setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
Copy-Item .env.example .env
```

Set the bot token in `.env` before running.

## Run

Local:

```powershell
python -m bot.main
```

Docker:

```powershell
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

## Tests

Default:

```powershell
pytest
```

Live-only:

```powershell
pytest -m live
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
