---
name: pr-review
description: Review a local diff or GitHub PR. Prioritize correctness, regressions, operational risk, docs drift, and missing tests.
---

# PR Review

## Read First

1. `AGENTS.md`
2. `docs/IMPLEMENTATION.md`
3. Relevant operations docs when runtime behavior changes

## Focus

- Bugs, regressions, missing tests, and operational risk
- Discord permission and routing mistakes
- Scheduler/job status truthfulness
- Docs drift against current behavior

## Output Shape

- Findings first, highest severity first
- Include file/path, risk, and why it matters
- If no findings are present, state that and mention residual verification gaps
