---
name: server-restart-prod
description: Restart the production Discord heatmap bot safely from the production repository path, with stricter checks for dirty worktrees, Docker Compose/PostgreSQL health, schema smoke, Asia/Seoul timezone verification, logs, and rollback/stop guidance.
---

# Server Restart Prod

Use this skill when the user asks to start, restart, relaunch, redeploy, stop, or inspect the **production/운영** bot/runtime.

## Defaults

- Production repository path: `/Users/jaeik/Documents/discord-heatmap-bot-trading-calendar`.
- Production bot container name is expected to be `discord-heatmap-bot`.
- Do not run production commands from the development repo path.
- Keep `.env` secret. Do not print `.env`, tokens, container env vars, or `docker compose config` output. Use `docker compose config --quiet`.
- Do not inspect development project tokens or sibling container env vars.
- Do not use `docker compose down -v` or delete DB volumes unless the user explicitly asks for data deletion.
- Prefer the smallest restart that reflects the requested change:
  - process-only bounce for no env/code change
  - force recreate for `.env` reload
  - build for code/image changes

## Preflight

1. Move to the production repo and confirm location:

```bash
cd /Users/jaeik/Documents/discord-heatmap-bot-trading-calendar
pwd
git status --short --branch
docker compose config --quiet
docker compose ps
```

2. If the production worktree is dirty, pause before build/recreate unless the user explicitly asked to run the dirty code. A process-only restart may still be acceptable when no file changes need to take effect.

3. Confirm database health:

```bash
docker compose up -d postgres
docker compose exec postgres pg_isready -U discord_heatmap -d discord_heatmap
docker compose exec -T postgres psql -U discord_heatmap -d discord_heatmap -c "SHOW timezone"
```

4. Run schema smoke before live startup when the image/code might have changed:

```bash
docker compose run --rm -v "$PWD:/app" discord-bot python -c "from bot.forum.state_store import ensure_schema_and_migrate; ensure_schema_and_migrate(); print('schema_ok')"
```

## Restart Commands

Choose exactly one:

```bash
# Code/build changes:
docker compose up -d --build discord-bot

# .env changed and image rebuild is not required:
docker compose up -d --force-recreate discord-bot

# Process-only bounce:
docker compose restart discord-bot
```

## Verification

```bash
docker compose ps
docker compose logs --tail=160 discord-bot
```

Look for Gateway connection, command sync count, scheduler start, recent `watch_poll` or scheduler status, and absence of tracebacks.

Useful DB checks:

```bash
docker compose exec -T postgres psql -U discord_heatmap -d discord_heatmap -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'bot_%' ORDER BY table_name"
docker compose exec -T postgres psql -U discord_heatmap -d discord_heatmap -c "SELECT symbol, session_date, close_price, provider FROM bot_watch_close_prices ORDER BY session_date DESC, symbol LIMIT 20"
docker compose exec -T postgres psql -U discord_heatmap -d discord_heatmap -c "SHOW timezone"
```

## Failure Handling

- If startup fails, inspect logs first:

```bash
docker compose logs --tail=240 discord-bot
```

- Stop production bot only when it is crash-looping, repeatedly failing startup, or the user asked to stop it:

```bash
docker compose stop discord-bot
```

- If PostgreSQL is unhealthy, inspect `postgres` logs and do not touch volumes:

```bash
docker compose logs --tail=160 postgres
```

## Done When

- Production repo path was used.
- `docker compose config --quiet` passed.
- `postgres` is healthy.
- `SHOW timezone` was checked.
- Schema smoke ran when code/image changed.
- Production `discord-bot` is running or a concrete failure is reported.
- Final response includes commands run, service state, and any unresolved operational risk.
