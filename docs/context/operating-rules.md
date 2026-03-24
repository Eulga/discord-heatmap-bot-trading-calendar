# Operating Rules

## Scope
- This document holds project-level operating and documentation rules.
- It is not a runtime behavior spec and not a session log.

## Canonical Document Boundary
- `README.md`:
  - onboarding only
- `AGENTS.md`:
  - agent instructions and document read order only
- `CURRENT_STATE.md`:
  - short current-state summary
- `../specs/as-is-functional-spec.md`:
  - deep current implementation reference
- `../specs/external-intel-api-spec.md`:
  - target/to-be contract, not current runtime truth
- `session-handoff.md`:
  - latest active handoff only
- `session-history.md`:
  - older handoff archive
- `development-log.md`, `review-log.md`:
  - long-term logs, not current truth
- `../reports/*`:
  - dated reports, not canonical runtime truth

## Secrets vs State
- Secrets, tokens, and credentials belong in env or an equivalent secret store.
- Mutable per-guild routing and other non-secret operational state belong in `data/state/state.json`.
- Env channel/forum IDs are treated as bootstrap/default values, not as the primary runtime source of truth in the inspected paths.
- If an exception is needed, document the reason first in `design-decisions.md` and the current active context docs.

## Context Update Rules
- After meaningful work, update only the minimum necessary documents.
- Use `CURRENT_STATE.md` only when current runtime behavior or current code-confirmed concerns changed.
- Use `../operations/config-reference.md` when code-confirmed defaults, env semantics, bootstrap behavior, or provider wiring changed.
- Use `../operations/runtime-runbook.md` when operator-facing run, debug, routing, or permission behavior changed.
- Use `../specs/as-is-functional-spec.md` only when deep current implementation behavior changed materially.
- Record implemented work and verification in `development-log.md`.
- Record design changes, policy changes, or documented exceptions in `design-decisions.md`.
- Record review findings and risks in `review-log.md`.
- Update `session-handoff.md` only for latest carry-forward context needed by the next session.
- Move older handoff entries to `session-history.md` when the active handoff grows beyond the intended latest-active scope.
- Do not treat `../specs/qa-test-backlog.md`, `../reports/*`, `../specs/external-intel-api-spec.md`, or long-term logs as canonical current truth.
- Do not promote unverified assumptions into canonical documents.
- Prefer minimal targeted updates over broad documentation rewrites.

## Branch / Release Rules
- The currently documented branch rule is to open `develop -> master` release PRs directly rather than creating a separate release branch by default.
- Avoid flows where a change lands only on `master` and not on `develop` without an explicit documented exception.
- If the branch/release policy changes, record the reason in `design-decisions.md` and update the active context docs.

## Review Rules Pointer
- Repeated review gates live in `review-rules.md`.
- Review history and concrete findings live in `review-log.md`.
- The latest consolidated QA assessment currently lives in `../reports/qa-issue-review-2026-03-24.md`; treat it as a report artifact rather than a behavior spec.
