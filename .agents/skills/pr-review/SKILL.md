---
name: pr-review
description: Review a local diff or GitHub PR with this repo's review rules. Prioritize correctness, regressions, state safety, scheduler truthfulness, docs drift, and missing tests.
---

# PR Review

Use this skill when the task is to review code changes rather than implement them.

## Read First
1. `AGENTS.md`
2. `docs/context/CURRENT_STATE.md`
3. `docs/context/review-rules.md`
4. `docs/context/session-handoff.md`
5. `docs/specs/as-is-functional-spec.md` when behavior-level truth matters

## Focus
- Bugs, regressions, missing tests, and operational risk
- State safety and state/save ordering
- Scheduler/job status truthfulness
- Docs drift against current behavior
- Permission and routing mistakes

## Output Shape
- Findings first, highest severity first
- Each finding should include file/path, risk, and why it matters
- If no findings are present, say so explicitly and note any residual verification gaps

## Done When
- The diff was checked against `review-rules.md`
- Any docs or test gaps are called out explicitly
- Facts and inferences are separated
