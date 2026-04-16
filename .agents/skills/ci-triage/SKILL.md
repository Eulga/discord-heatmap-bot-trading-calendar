---
name: ci-triage
description: Triage failing local or GitHub checks using the repo's standardized validation command and return the smallest safe fix scope.
---

# CI Triage

Use this skill when tests, collection, or CI jobs are failing.

## Standard Command
- Default verification entrypoint is `python scripts/run_repo_checks.py`
- Common suites:
  - `collect`
  - `unit`
  - `integration`
  - `full`

## Workflow
1. Reproduce with the narrowest failing suite first.
2. Identify root cause before proposing edits.
3. Prefer the smallest change that restores the failing path.
4. Re-run the affected suite after the fix.
5. Note any broader suite still left unverified.

## Review Focus
- Environment mismatch between local and CI
- Missing docs when run commands changed
- Tests that hide scheduler/state regressions behind mocks

## Done When
- Root cause is stated
- Exact suite run is recorded
- Remaining verification gaps are explicit
