---
name: server-restart-dev
description: Restart this repository's development Discord heatmap bot safely, including Docker Compose/PostgreSQL/Adminer setup, dev container naming, .env reload behavior, schema smoke checks, Asia/Seoul PostgreSQL timezone verification, logs, and rollback/stop guidance.
---

# Server Restart Dev

Use this skill when the user asks to start, restart, relaunch, redeploy, stop, or inspect the **development** bot/runtime for this repository.

## Defaults

- This repository path is the development bot runtime.
- Preferred dev runtime is Docker Compose with PostgreSQL.
- The live dev bot container name is `discord-heatmap-bot-dev`.
- PostgreSQL runs with `timezone=Asia/Seoul`; verify with `SHOW timezone`.
- Keep `.env` secret. Do not print `.env`, tokens, or `docker compose config` output. Use `docker compose config --quiet`.
- Keep `postgres` and `adminer` running unless the user asks for a full stop.
- Do not use `docker compose down -v` unless the user explicitly asks to delete DB data.
- Do not inspect sibling project tokens or running container env vars. Do not block this dev bot startup because a sibling project container exists.
- Only check this Compose project/service state before starting `discord-bot`.
- Treat local LLM/model server availability as an external service concern. Do not start, stop, adopt, or health-check `llama-server` as part of this dev bot restart skill.

## Mode Selection

- **Infra/checks only**: Start/verify `postgres` and `adminer`, run schema smoke, do not start `discord-bot`.
- **Live dev restart**: Ensure PostgreSQL is healthy, recreate/start `discord-bot`, then verify logs.
- **Env reload**: If `.env` changed, use `docker compose up -d --force-recreate discord-bot`.
- **Code or Dockerfile changed**: Use `docker compose up -d --build discord-bot`.
- **Process-only bounce**: Use `docker compose restart discord-bot` only when env/code did not change.

## Workflow

1. Inspect state without exposing secrets:

```bash
git status --short --branch
docker compose config --quiet
docker compose ps
```

2. Start or confirm database services:

```bash
docker compose up -d postgres adminer
docker compose exec postgres pg_isready -U discord_heatmap -d discord_heatmap
docker compose exec -T postgres psql -U discord_heatmap -d discord_heatmap -c "SHOW timezone"
```

3. Run schema smoke before live startup:

```bash
docker compose run --rm -v "$PWD:/app" discord-bot python -c "from bot.forum.state_store import ensure_schema_and_migrate; ensure_schema_and_migrate(); print('schema_ok')"
```

4. If the user asked for live dev restart, choose the right command:

```bash
# Code/build changes:
docker compose up -d --build discord-bot

# .env changed and image rebuild is not required:
docker compose up -d --force-recreate discord-bot

# Process-only bounce:
docker compose restart discord-bot
```

5. Verify startup:

```bash
docker compose ps
docker compose logs --tail=120 discord-bot
```

Look for Gateway connection, command sync count, scheduler start, and absence of tracebacks.

## DB Checks

```bash
docker compose exec -T postgres psql -U discord_heatmap -d discord_heatmap -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'bot_%' ORDER BY table_name"
docker compose exec -T postgres psql -U discord_heatmap -d discord_heatmap -c "SELECT symbol, session_date, close_price, provider FROM bot_watch_close_prices ORDER BY session_date DESC, symbol LIMIT 20"
docker compose exec -T postgres psql -U discord_heatmap -d discord_heatmap -c "SHOW timezone"
```

## Failure Handling

- If startup fails, inspect logs and stop `discord-bot` if it is crash-looping:

```bash
docker compose logs --tail=200 discord-bot
docker compose stop discord-bot
```

- If PostgreSQL is unhealthy, inspect `postgres` logs before touching data:

```bash
docker compose logs --tail=120 postgres
```

## Done When

- The chosen dev mode is stated.
- `docker compose config --quiet` passed.
- `postgres` is healthy.
- PostgreSQL reports `Asia/Seoul` for `SHOW timezone`.
- Schema smoke passed.
- For live dev restart, `discord-bot` is running as `discord-heatmap-bot-dev` and logs show startup success or a concrete failure.
- Final response includes commands run, service state, and unresolved risk.
