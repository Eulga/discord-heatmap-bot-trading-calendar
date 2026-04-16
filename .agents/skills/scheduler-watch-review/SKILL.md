---
name: scheduler-watch-review
description: Review scheduler, watch forum-thread, and job-status changes with special attention to state ordering, catch-up semantics, and thread lifecycle regressions.
---

# Scheduler And Watch Review

Use this skill when changes touch scheduler loops, watch polling, watch commands, or job/provider status surfaces.

## High-Risk Files
- `bot/features/intel_scheduler.py`
- `bot/features/auto_scheduler.py`
- `bot/features/watch/command.py`
- `bot/features/watch/service.py`
- `bot/forum/service.py`
- `bot/forum/repository.py`
- `bot/features/status/command.py`

## Must Check
- `ok` / `failed` / `skipped` / `no-target` semantics stay truthful
- Same-day catch-up and exact-minute logic stay explicit
- Watch stop/delete/start flows do not leave stale active state behind
- Thread update failures do not silently corrupt state
- Current-truth docs and regression tests move with the change

## Suggested Verification
- Windows: `py -3 scripts/run_repo_checks.py integration -- tests/integration/test_intel_scheduler_logic.py`
- macOS/Linux: `python3 scripts/run_repo_checks.py integration -- tests/integration/test_intel_scheduler_logic.py`
- Windows: `py -3 scripts/run_repo_checks.py integration -- tests/integration/test_watch_forum_flow.py`
- macOS/Linux: `python3 scripts/run_repo_checks.py integration -- tests/integration/test_watch_forum_flow.py`
- Windows: `py -3 scripts/run_repo_checks.py integration -- tests/integration/test_watch_poll_forum_scheduler.py`
- macOS/Linux: `python3 scripts/run_repo_checks.py integration -- tests/integration/test_watch_poll_forum_scheduler.py`

## Done When
- Scheduler truthfulness and watch lifecycle risks were explicitly reviewed
- Missing regression coverage is called out if it still exists
