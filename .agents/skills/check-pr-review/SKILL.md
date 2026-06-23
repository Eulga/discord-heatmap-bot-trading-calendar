---
name: check-pr-review
description: Inspect the current PR review state, address actionable findings, verify, and finish the PR when clean.
---

# Check PR Review

## Read First

1. `AGENTS.md`
2. `docs/IMPLEMENTATION.md`

## Workflow

1. Confirm branch and worktree state with `git status --short --branch`.
2. Inspect PR state and review comments.
3. Fix only unresolved actionable findings.
4. Run the narrowest relevant verification, usually `python scripts/run_repo_checks.py`.
5. Commit and push only the review-fix files when asked or when the workflow requires it.

## Output Shape

- Lead with `Clean`, `Not clean`, `Pending`, or `Blocked`.
- Findings first when review issues remain.
- Report verification and any skipped checks.
