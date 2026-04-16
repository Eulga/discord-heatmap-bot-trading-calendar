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
- Per-guild mutable routing and runtime state are stored in `data/state/state.json`.
- `watch_poll` is now code-confirmed as a session-aware forum-thread flow:
  - route source of truth is `watch_forum_channel_id`
  - `/setwatchforum` configures the route
  - `/watch add` only adds a new tracked symbol and creates its persistent thread
  - `/watch start` resumes a stopped symbol, `/watch stop` keeps the symbol but halts real-time polling, and `/watch delete` fully removes the symbol and thread
  - regular session polls update starter/comment state for active symbols only
  - off-hours polls only attempt close finalization, including stopped symbols that still have an unfinalized session
  - startup now warns when a guild still has only legacy `watch_alert_channel_id`, because hard cut mode requires an explicit `/setwatchforum` migration
- Code-confirmed command boundary:
  - forum/config/autoscreenshot commands are gated by guild owner, guild administrator, or a user ID listed in `DISCORD_GLOBAL_ADMIN_USER_IDS`
  - manual heatmap commands plus `/watch add`, `/watch start`, `/watch stop`, `/watch list` require guild context but are not admin-gated
  - `/watch delete` is gated by guild owner, guild administrator, or `DISCORD_GLOBAL_ADMIN_USER_IDS`
  - status commands do not currently apply a visible authorization gate
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
  - repo-local Codex skills for PR review, CI triage, docs sync, and scheduler/watch review
  - GitHub PR template plus CI workflow under `.github/`
  - local bootstrap currently requires Python `3.10+`; Docker remains the fallback when only older system Python is available

## Code-Confirmed Current Behavior Concerns
- State reads can fail open and later be saved back as authoritative empty state.
- State writes are not visibly serialized across commands, schedulers, and startup paths.
- Heatmap, news, and EOD daily schedulers now use same-day catch-up after their configured time; they no longer depend on an exact-minute tick to run once per day.
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
- Do not assume `python` exists as a shell command on macOS/Linux; current docs now treat `scripts/bootstrap_dev_env.py` and `scripts/run_repo_checks.py` as interpreter-driven entrypoints.
- Do not assume the host system Python is new enough for local bootstrap; the current dependency set requires Python `3.10+`.

## Last Verified
- This summary was last updated on 2026-04-16 from:
  - `session-handoff.md`
  - `goals.md`
  - `../specs/as-is-functional-spec.md`
  - `../specs/watch-poll-functional-spec.md`
  - `../operations/config-reference.md`
  - `../reports/qa-issue-review-2026-03-24.md`
  - `../README.md`
  - `../../scripts/bootstrap_dev_env.py`
  - `../../.github/workflows/pr-checks.yml`
- Exact query-list defaults, ranking heuristics, and any future provider/runtime expansions still require direct code verification before being promoted into summary-level docs.
