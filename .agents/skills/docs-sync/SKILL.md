---
name: docs-sync
description: Update the minimum necessary canonical docs after a code-confirmed behavior or ops change, following this repo's document boundaries.
---

# Docs Sync

Use this skill after implementation or review-confirmed behavior changes.

## Read First
1. `AGENTS.md`
2. `docs/context/operating-rules.md`
3. `docs/context/CURRENT_STATE.md`
4. Relevant current-truth doc such as `docs/specs/as-is-functional-spec.md` or `docs/operations/*`

## Rules
- Update only the minimum necessary docs
- Do not promote unverified assumptions into canonical docs
- Record implementation in `docs/context/development-log.md`
- Record review findings in `docs/context/review-log.md`
- Update `docs/context/session-handoff.md` only when the next session needs carry-forward context

## Common Targets
- `README.md` for onboarding or standard commands
- `docs/operations/config-reference.md` for env/default/provider wiring
- `docs/operations/runtime-runbook.md` for operator-facing behavior
- `docs/specs/as-is-functional-spec.md` for material deep behavior changes

## Done When
- Canonical docs match the code-confirmed change
- Log documents record what changed and how it was verified
