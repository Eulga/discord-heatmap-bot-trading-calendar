---
name: external-intel-provider-rollout
description: Use this only after the rollout scope and success criteria are already agreed. Execute one external intel provider rollout at a time and keep scheduler, status, tests, and docs aligned for `news_briefing`, `trend_briefing`, `eod_summary`, and `watch_poll`.
---

# External Intel Provider Rollout

Use this skill after the user and Codex have already agreed the target path, success criteria, and rollout boundary. This is an execution checklist for a provider rollout, not a feature-design or brainstorming workflow.

If the task is still about choosing product direction, provider strategy, or broader architecture, stay in normal conversation first and only use this skill once the contract is locked.

Use this skill when the task touches any of these areas:

- `bot/intel/providers/news.py`
- `bot/intel/providers/market.py`
- `bot/features/intel_scheduler.py`
- `bot/app/settings.py`
- `docs/specs/external-intel-api-spec.md`
- `docs/operations/config-reference.md`
- `docs/operations/runtime-runbook.md`
- provider status, job status, env vars, or rollout docs

## Quick Start

1. Confirm the user and Codex already agreed the in-scope path, success criteria, and whether this is implementation, rollout validation, or docs-only alignment.
2. Read `docs/context/session-handoff.md`, `docs/context/goals.md`, `docs/specs/external-intel-api-spec.md`, and the current ops docs that govern provider wiring.
3. Inspect the current provider interface and the scheduler/status path that consumes it.
4. Identify which one of `news_briefing + trend_briefing`, `eod_summary`, or `watch_poll` is in scope.
5. Confirm the expected state updates, logs, tests, and docs before editing.

## Workflow

### 1. Lock the execution boundary before editing

- If the rollout scope or contract is still undecided, stop using this skill and clarify with the user first.
- Treat this skill as the implementation checklist that follows planning, not the planning step itself.

### 2. Fix the contract before the transport

- Normalize external data into the existing `NewsItem` / `NewsAnalysis`, `WatchSnapshot`, and `EodSummary` shapes used by the current runtime paths.
- Keep vendor-specific fields out of the scheduler and policy layers.
- Preserve the spec's timeout, retry, and rate-limit expectations unless the user asks to change them.

### 3. Change one provider path at a time

- Prefer a new adapter or a narrow replacement over a broad rewrite.
- Keep the current scheduler semantics intact while swapping the data source.
- For news rollout, treat `news_briefing` and `trend_briefing` as one provider surface and verify `trend_report`, trend posting, and status recording together.
- For watch rollout, verify `get_watch_snapshot(...)`, optional `warm_watch_snapshots(...)`, `session_date`, `session_close_price`, and freshness handling together.
- Do not couple news, EOD, and watch rollout work unless the task explicitly requires it.

### 4. Preserve operational truth

- Make sure provider failures surface through `set_provider_status(...)`.
- Make sure job outcomes still distinguish `ok`, `failed`, `skipped`, and `no-target` style paths when applicable.
- If provider keys, env semantics, or status rows change, keep `/source-status` and job/status output truthful.
- Treat stale or partial external data as an operational risk, not just a parsing problem.

### 5. Validate the risky edge

- Add or update targeted tests around the changed provider path.
- Prefer tests that cover normalization, scheduler failure handling, status recording, and the path-specific edge that changed.
- For news, include `trend_briefing` impact when the provider output or scoring/selection path changes.
- For watch, include snapshot freshness, session metadata, and warm-up behavior when provider wiring changes.
- If live verification is not possible, leave a short note about what remains unverified.

### 6. Update canonical docs and context

- Update `README.md` when env vars, run commands, or operating assumptions change.
- Update `docs/operations/config-reference.md` when provider wiring, env semantics, defaults, or bootstrap behavior change.
- Update `docs/operations/runtime-runbook.md` when operator-facing run, debug, routing, or permission behavior changes.
- Update the relevant `docs/context/*.md` files before finishing, following the repo's normal doc-boundary rules.
- Record remaining vendor, auth, quota, or data freshness risks explicitly.

## Repo-Specific Checks

### News briefing and trend briefing

- Keep dedup behavior tied to fetched items, not post-success assumptions.
- Verify regional split (`domestic`, `global`) still matches the post body contract.
- Verify `NewsAnalysis.trend_report` still supports current trend rendering and status behavior, not just the briefing body.

### EOD summary

- Keep the trading-day guard ahead of the external fetch when possible.
- Match `date_text`, index changes, and ranking rows to existing render expectations.
- The current runtime wiring still uses `MockEodSummaryProvider()`; do not write the checklist as if live EOD wiring is already complete.

### Watch poll

- Watch quote freshness, `session_date`, `session_close_price`, and cooldown behavior closely.
- The current runtime interface is `get_watch_snapshot(...)` with optional `warm_watch_snapshots(...)`; keep both aligned.
- Prefer batch-friendly adapter design even though the scheduler still consumes snapshots per symbol.

## Done When

- The changed provider path matches `docs/specs/external-intel-api-spec.md`.
- The changed runtime path still matches the current scheduler/provider interfaces it feeds.
- Relevant tests or logical verification were performed and recorded.
- Operational docs and `docs/context/*` were updated when behavior changed, including ops docs when provider wiring or operator behavior moved.
- Remaining rollout risk is written down instead of implied.
