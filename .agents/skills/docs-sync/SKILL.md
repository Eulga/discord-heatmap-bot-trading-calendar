---
name: docs-sync
description: Update the minimum necessary current docs after a code-confirmed behavior or ops change.
---

# Docs Sync

## Read First

1. `AGENTS.md`
2. `docs/IMPLEMENTATION.md`
3. `docs/operations/config-reference.md`
4. `docs/operations/runtime-runbook.md`

## Rules

- Update only current docs.
- Do not recreate old context logs, reports, or to-be spec documents.
- Update `docs/IMPLEMENTATION.md` when feature ownership or data flow changes.
- Update `docs/operations/config-reference.md` when env vars, defaults, or wiring changes.
- Update `docs/operations/runtime-runbook.md` when operator steps, deployment, permissions, or debugging changes.
