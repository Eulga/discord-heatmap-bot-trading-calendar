# Current State

## Purpose
- This document is the short current-state summary for the next session or next agent.
- It is not the deep implementation spec, not a roadmap, and not a cumulative log.

## Canonical Docs
- Current implementation truth:
  - `../specs/as-is-functional-spec.md`
- Code-confirmed config/default and provider/env boundary:
  - `../operations/config-reference.md`
- Latest active handoff context:
  - `session-handoff.md`
- Current goals and work priorities:
  - `goals.md`
- Project operating/documentation rules:
  - `operating-rules.md`
- Long-term implementation and review history:
  - `development-log.md`
  - `review-log.md`
- Target/to-be contract for external intel rollout:
  - `../specs/external-intel-api-spec.md`
  - This is not the current runtime truth.

## Current System Snapshot
- The repository currently implements a Discord bot that can post Korea/US heatmaps and also contains scheduled news, trend, watch-poll, and instrument-registry-refresh flows.
- Per-guild mutable routing and runtime state now use the PostgreSQL split-state store at runtime.
  - `STATE_BACKEND=postgres` or `postgresql` and `DATABASE_URL` are required for bot startup.
  - `POSTGRES_STATE_KEY` namespaces all split rows.
  - The legacy `bot_app_state.state JSONB` row is preserved as a migration/rollback backup, not sync-written by runtime paths.
  - `data/state/state.json` is a one-time import fallback only when no legacy PostgreSQL row exists during `split_state_v1` migration.
- `watch_poll` is now code-confirmed as a session-aware forum-thread flow:
  - route source of truth is `watch_forum_channel_id`
  - `/setwatchforum` configures the route
  - `/watch add` only adds a new tracked symbol and creates its persistent thread
  - `/watch start` resumes a stopped symbol, `/watch stop` keeps the symbol but halts real-time polling, and `/watch delete` fully removes the symbol and thread
  - regular session polls keep the starter blank and update a bottom-positioned current-price comment for active symbols only
  - close finalization is now KST exact-minute gated: KRX symbols only attempt `마감가 알림` at 16:00 KST, and NAS/NYS/AMS symbols only attempt it at 07:00 KST; missed due minutes leave close finalization pending until the next due minute without blocking later regular-session current-price/band updates, but pending close targets are dropped from retry state once a later snapshot is no longer the immediately adjacent trading session
  - watch close prices are accumulated in PostgreSQL per `POSTGRES_STATE_KEY + symbol + session_date`; DB history is saved as soon as a close price is resolved, while Discord close comments remain governed by the due-minute finalization path
  - after the due minute has passed, active symbols can perform best-effort close-price DB catch-up until the next regular session, without creating Discord close comments
  - startup now warns when a guild still has only legacy `watch_alert_channel_id`, because hard cut mode requires an explicit `/setwatchforum` migration
- Code-confirmed command boundary:
  - forum/config/autoscreenshot commands are gated by guild owner, guild administrator, or a user ID listed in `DISCORD_GLOBAL_ADMIN_USER_IDS`
  - manual heatmap commands plus `/watch add`, `/watch start`, `/watch stop`, `/watch list` require guild context but are not admin-gated
  - `/watch delete` is gated by guild owner, guild administrator, or `DISCORD_GLOBAL_ADMIN_USER_IDS`
  - `/local ask` is gated by guild owner, guild administrator, or `DISCORD_GLOBAL_ADMIN_USER_IDS`
  - status commands do not currently apply a visible authorization gate
- Local model slash command:
  - `/local ask` is disabled by default through `LOCAL_MODEL_ENABLED=false`
  - when enabled, it calls an already-running OpenAI-compatible local model endpoint at `LOCAL_MODEL_BASE_URL`
  - Docker development defaults target Mac host `llama-server` at `http://host.docker.internal:8081/v1`
  - local model server lifecycle is external to bot/server restart workflows
  - the bot does not start/supervise the model server and does not grant shell/file/DB tools to the model
- The deep current behavior, visible ambiguities, and observed implementation gaps are documented in `../specs/as-is-functional-spec.md`.
- Current QA prioritization is documented separately in `../reports/qa-issue-review-2026-03-24.md`; treat that file as a review artifact, not as a runtime spec.

## Active Workstreams
- External intel provider rollout for news/watch/EOD paths.
- Operational stabilization around startup, scheduler reliability, and state safety.
- Heatmap posting flow verification in real Discord usage.
- Operator visibility through `/health`, `/last-run`, and `/source-status`.
- Agent-operating baseline uplift:
  - standardized local bootstrap via `scripts/bootstrap_dev_env.py`
  - standardized repo validation via `scripts/run_repo_checks.py` through the active interpreter for the current OS
  - repo-local Codex skills for staged harness operation, PR review, CI triage, docs sync, scheduler/watch review, safe dev server restart, and safe prod server restart
  - repo-local staged workflow templates and state helper under `.codex-harness/`, with run-specific state and reports ignored by git
  - GitHub PR template plus CI workflow under `.github/`
  - GitHub PR checks now inject placeholder `DISCORD_BOT_TOKEN` so import-time settings validation does not break non-live collect/unit/integration jobs
  - local bootstrap currently requires Python `3.10+`; Docker remains the fallback when only older system Python is available
  - current macOS host now has Homebrew `python3.11`, and `.venv` has been rebuilt successfully against `3.11.15`
- PostgreSQL split-state persistence is now the runtime backend for Discord route/thread/message IDs and scheduler/watch checkpoints.

## Code-Confirmed Current Behavior Concerns
- PostgreSQL backend failures are intended to fail closed at startup and repository access time.
- Runtime paths now write domain rows instead of rewriting one full `AppState` JSON document, reducing state lost-update risk for independent route, daily-post, scheduler/status, and watch updates.
- Watch close-price history is accumulated in dedicated PostgreSQL rows and is not included in legacy `AppState` snapshots.
- Same-row watch alert updates use row-level/compound repository operations where current behavior needs merge-like semantics.
- The implementation still does not include distributed scheduler leases or a Discord side-effect outbox, so duplicate bot instances can still duplicate external side effects.
- Heatmap auto screenshot uses same-day catch-up after its fixed KST schedule: `kheatmap` after 16:00 and `usheatmap` after 07:00, once per guild/job/date.
- News and EOD daily schedulers now use same-day catch-up after their configured time; they no longer depend on an exact-minute tick to run once per day.
- Forum upsert can recreate same-day content on transient Discord fetch failures.
- Watch close-finalization correctness still depends on Discord write success order plus provider delivery of `previous_close/session_close_price/session_date`.
- The checked-in local state still contains guilds with legacy `watch_alert_channel_id` but no `watch_forum_channel_id`, so watch forum migration is still an active rollout concern.
- Stopped watch symbols stay in the shared guild watchlist by design, so operator interpretation should use symbol status rather than raw watchlist membership alone.
- Severity and implementation priority for these concerns are tracked separately in `../reports/qa-issue-review-2026-03-24.md`.

## Do Not Assume
- Do not treat `../specs/external-intel-api-spec.md` as the current implementation truth.
- Do not treat `../specs/qa-test-backlog.md` as current test coverage; it is a backlog-style planning document.
- Do not treat `../reports/qa-issue-review-2026-03-24.md` as a runtime spec; it is a QA assessment/report.
- Do not assume live EOD behavior, robust daily catch-up beyond the current heatmap auto scheduler, operator-only watch/status access, or session-aware watch polling unless the current code or `../specs/as-is-functional-spec.md` confirms it.
- Key defaults and core provider/env wiring are now summarized in `../operations/config-reference.md`; do not assume more than that file or the code currently confirms.
- The presence of `.github/workflows/pr-checks.yml` does not prove secrets-backed Codex/GitHub automation beyond test collection and pytest execution.
- The placeholder `DISCORD_BOT_TOKEN` used by PR checks is only for import-time testability; it does not prove Discord connectivity or secret-backed CI validation.
- Do not assume `python` exists as a shell command on macOS/Linux; current docs now treat `scripts/bootstrap_dev_env.py` and `scripts/run_repo_checks.py` as interpreter-driven entrypoints.
- Do not assume the host system Python is new enough for local bootstrap; the current dependency set requires Python `3.10+`.
- Do not assume `python3` itself is the upgraded interpreter on macOS; on the current host it is still `3.9.6`, while `.venv` runs on Homebrew `python3.11`.

## Last Verified
- This summary was last updated on 2026-05-05 from:
  - `session-handoff.md`
  - `goals.md`
  - `../specs/as-is-functional-spec.md`
  - `../specs/watch-poll-functional-spec.md`
  - `../operations/config-reference.md`
  - `../reports/qa-issue-review-2026-03-24.md`
  - `../README.md`
  - `../../scripts/bootstrap_dev_env.py`
  - `../../.github/workflows/pr-checks.yml`
  - `../../.codex-harness/README.md`
  - `../../bot/forum/repository.py`
  - `../../bot/forum/state_store.py`
  - `../../tests/unit/test_state_atomic.py`
- Exact query-list defaults, ranking heuristics, and any future provider/runtime expansions still require direct code verification before being promoted into summary-level docs.
