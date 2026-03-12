# Sunday Kheatmap Investigation

Date: 2026-03-12
Workspace: `C:\Users\kin50\Documents\New project\discord-heatmap-bot-trading-calendar`

## Summary

- The user reported that `kheatmap` appeared to run on Sunday, 2026-03-08.
- The command input channel did not show a `/kheatmap` invocation on that date.
- Screenshot evidence showed a forum post titled `[2026-03-08 한국장 히트맵]` with body text:
  - `2026-03-08 15:35:57 KST 업데이트`
  - `kospi: captured`
  - `kosdaq: captured`
- This timestamp aligns almost exactly with the auto scheduler's `15:35 KST` trigger window.

## What We Verified In Code

- Built-in `kheatmap` execution paths in the repository are effectively:
  - Slash command path: `bot/features/kheatmap/command.py` -> `bot/features/runner.py`
  - Auto scheduler path: `bot/features/auto_scheduler.py`
- The auto scheduler only queues `kheatmap` when `now.hour == 15 and now.minute == 35`.
- The auto scheduler then calls `safe_check_krx_trading_day(now)` and should skip with `reason=holiday` on non-trading days.
- KRX trading-day checks are implemented through `exchange_calendars` with calendar `XKRX`.
- KST is forced in code via `ZoneInfo("Asia/Seoul")`, with a UTC+9 fallback if zone loading fails.
- The body text format seen in the screenshot matches the normal `kheatmap` body builder and runner flow.

## Branch And Reproduction Notes

- `master` and `release/v1` both point to commit `3c763b0`.
- `develop` points to commit `bdb2cdf`.
- Reproducing Sunday `2026-03-08 15:35 KST` on `master` and `release/v1` resulted in:
  - `safe_check_krx_trading_day(...) == (False, None)`
  - Auto scheduler skip with `reason=holiday`
  - `execute_heatmap_for_guild()` not called
- Targeted tests passed in local `.venv`:
  - `tests/unit/test_trading_calendar.py`
  - `tests/integration/test_auto_scheduler_logic.py`

## Interpretation Of The Screenshot Evidence

- The screenshot strongly suggests the Sunday post came from the auto scheduler path rather than a slash command typed in the observed command channel.
- The auto scheduler posts directly to the forum and does not create a visible `/kheatmap` invocation message in the command input channel.
- The precise `15:35:57 KST` timestamp is highly consistent with the scheduler loop waking inside the `15:35` minute.

## Most Likely Root-Cause Candidates

1. The live process was not actually running the same code currently checked locally.
   - Most likely sub-case: an older image or different deployment artifact was still running.

2. Another host or container was running with the same bot token.
   - This explains why the observed forum activity may not match what was expected from the local workspace.

3. The running image was stale.
   - `docker compose` may have been started without rebuilding or recreating the container.

4. The live environment had a different or broken `exchange_calendars` installation.
   - Low probability, but still plausible if the library or its dependencies differed from local reproduction.

5. The bot process restarted around the trigger time.
   - This does not explain Sunday execution by itself, but it does explain the exact `15:35:57` timing if the scheduler started inside that minute.

6. Persisted runtime state kept auto mode enabled.
   - The mounted `data/heatmaps` directory can preserve scheduler state between restarts.

## Things That Became Less Likely

- A plain Docker OS timezone mismatch by itself.
  - The code uses KST explicitly for scheduling and formatting.

- A normal calendar-check failure.
  - The code skips on calendar errors; it does not run.

- A reconnect-only duplicate scheduler inside a single process.
  - The bot guards against re-creating the scheduler task unless the old task is done.

## State File Indicators To Check Later

Inspect `data/heatmaps/state.json` and look at:

- `guilds.<guild_id>.auto_screenshot_enabled`
- `guilds.<guild_id>.last_auto_runs.kheatmap`
- `guilds.<guild_id>.last_auto_skips.kheatmap`
- `commands.kheatmap.last_run_at`
- `commands.kheatmap.last_images.kospi.captured_at`
- `commands.kheatmap.last_images.kosdaq.captured_at`

Interpretation hints:

- If `last_auto_runs.kheatmap == "2026-03-08"`, auto execution is confirmed.
- If `last_auto_skips.kheatmap.date == "2026-03-08"` and `reason == "holiday"`, the scheduler woke up and skipped correctly, so another process/path posted.
- If `commands.kheatmap.last_run_at` is on 2026-03-08 but `last_auto_runs.kheatmap` is not, then execution likely came from a non-auto path or another runtime.

## Log Strings To Search

Look for these in container or process logs:

- `[auto-screenshot] success guild=... command=kheatmap`
- `[auto-screenshot] skipped guild=... command=kheatmap`
- `Auto screenshot scheduler started.`
- `Logged in as`
- `Synced`

Helpful surrounding clues:

- Any restart or login event near `2026-03-08 15:35 KST`
- Any image rebuild or deployment event before the post
- Any evidence of multiple bot processes

## Constraints During This Investigation

- Docker CLI was not available in the current shell, so the live container itself could not be inspected from this environment.
- No production `data/heatmaps/state.json` was present in the local workspace at investigation time.

## Current Best Judgment

Given the screenshot and the local reproduction results, the strongest working theory is:

- The Sunday post was produced by an auto-scheduler-capable runtime that was not identical to the code/environment verified locally.

The top concrete suspects are:

- stale deployment image
- another running instance with the same token
- live dependency mismatch around `exchange_calendars`
