---
name: external-intel-provider-rollout
description: Execute one external intelligence provider rollout at a time and keep provider wiring, scheduler behavior, tests, and current docs aligned.
---

# External Intel Provider Rollout

Use only after the provider scope and success criteria are agreed.

## Read First

1. `AGENTS.md`
2. `docs/IMPLEMENTATION.md`
3. `docs/operations/config-reference.md`
4. `docs/operations/runtime-runbook.md`

## Workflow

1. Lock the exact provider path before editing.
2. Keep vendor-specific fields out of scheduler and policy layers.
3. Change one provider path at a time.
4. Surface failures through provider/job status, not silent fallbacks.
5. Add or update targeted tests around normalization, failure handling, and status recording.
6. Update current docs only when behavior or operations changed.

## Done When

- Runtime behavior matches the current implementation map.
- Relevant tests or logical verification ran.
- Config and runbook docs match the changed provider behavior.
