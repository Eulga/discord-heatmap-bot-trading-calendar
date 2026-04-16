# AGENTS.md

## 1) Purpose
- This file is for agent instructions and document pointers for this repository.
- It is not the project wiki, not the runtime runbook, and not the current implementation spec.

## 2) Canonical Read Order
1. `docs/context/CURRENT_STATE.md`
2. `docs/context/session-handoff.md`
3. `docs/context/goals.md`
4. Review work only: `docs/context/review-rules.md`
5. Current implementation detail when needed: `docs/specs/as-is-functional-spec.md`
6. Runtime operations when needed: `docs/operations/runtime-runbook.md`
7. Config/env boundary when needed: `docs/operations/config-reference.md`
8. Project operating/documentation rules: `docs/context/operating-rules.md`
9. Historical context only when needed:
   - `docs/context/design-decisions.md`
   - `docs/context/development-log.md`
   - `docs/context/review-log.md`
   - `docs/context/session-history.md`
10. Target/to-be contract only when the task is about rollout or planned behavior:
   - `docs/specs/external-intel-api-spec.md`

## 3) Working Rules
- Start by reading the current context and the directly relevant code or documents.
- Keep changes small and deliberate. Prefer the smallest effective change over broad rewrites.
- Respect the existing code style, structure, naming, and file layout unless there is a strong reason not to.
- Ask only when a risky misunderstanding is likely; otherwise make a reasonable assumption and state it.
- Use `python scripts/run_repo_checks.py` as the default verification entrypoint for local and CI validation unless the task requires a narrower command.
- If a required tool or dependency is missing, ask for approval before installing it and before switching to a workaround path.
- When working from an explicit plan or in Plan mode, if the work produced file changes, update any required docs before handoff and always create a commit before handoff.
- If `docs/context/session-handoff.md` needs carry-forward updates, include those handoff changes in the same commit rather than leaving them uncommitted.
- Verify work proportionally. If you cannot run validation, say so explicitly.
- Distinguish facts from inferences in both analysis and close-out.
- For review tasks, prioritize defects, regressions, missing tests, and operational risk over praise.
- Do not expose secrets, tokens, credentials, or personal data in output or docs.
- Do not perform destructive or hard-to-reverse actions without explicit user approval.
- Treat the following as the default definition of done unless the task clearly narrows scope:
  - code or docs changed only as much as needed
  - relevant verification ran through `scripts/run_repo_checks.py` or an explicitly narrower command
  - canonical docs/logs are updated when current behavior or operator truth changed

## 4) Documentation Update Rules
- After implemented work or code-verified behavior changes, update only the minimum necessary docs.
- Update `docs/context/CURRENT_STATE.md` only when current runtime behavior or current code-confirmed concerns changed.
- Update `docs/operations/config-reference.md` when defaults, env semantics, bootstrap behavior, or provider wiring changed.
- Update `docs/operations/runtime-runbook.md` when operator-facing run, debug, routing, or permission behavior changed.
- Update `docs/specs/as-is-functional-spec.md` only for material deep-implementation changes.
- Record implemented work and verification in `docs/context/development-log.md`.
- Record design-level decisions or policy exceptions in `docs/context/design-decisions.md`.
- Record review findings and risk notes in `docs/context/review-log.md`.
- Update `docs/context/session-handoff.md` only when the next session needs carry-forward context.
- Move older handoff history to `docs/context/session-history.md` when `session-handoff.md` grows beyond the latest-active scope.
- Do not treat logs, backlog docs, review reports, or target-contract docs as current truth.
- Do not promote unverified assumptions into canonical docs.
- Prefer minimal targeted updates over broad documentation rewrites.
- For detailed document boundaries, follow `docs/context/operating-rules.md`.

## 5) Repo-Specific Boundaries
- `README.md`:
  - onboarding only
- `docs/context/CURRENT_STATE.md`:
  - short current-state summary
- `docs/specs/as-is-functional-spec.md`:
  - deep current implementation truth
- `docs/specs/external-intel-api-spec.md`:
  - target/to-be contract, not current runtime truth
- `docs/context/development-log.md` and `docs/context/review-log.md`:
  - long-term logs, not current truth
- `docs/reports/*`:
  - dated reports, not canonical runtime truth

## 6) Subagent Rules
- In a new thread, use subagents only when the user explicitly indicates delegation/subagent use.
- Default interpretation for `기본 3-agent 패턴`:
  - `repo_explorer + reviewer + docs_researcher`
- Skip `docs_researcher` when no external or documentation check is needed.
- Keep blocking implementation work in the main session; use sidecar agents for exploration, review, or docs checks.
- When `integration_tester` is used for this repo, its default test target is:
  - `.\.venv\Scripts\python.exe -m pytest tests/integration`

## 7) Pointers To Deeper Docs
- Onboarding:
  - `README.md`
- Standardized validation:
  - `scripts/run_repo_checks.py`
- Runtime operations:
  - `docs/operations/runtime-runbook.md`
- Config/env/state boundary:
  - `docs/operations/config-reference.md`
- Operating/documentation rules:
  - `docs/context/operating-rules.md`
- Current implementation reference:
  - `docs/specs/as-is-functional-spec.md`
- Historical reports:
  - `docs/reports/*`
