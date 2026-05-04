---
name: check-pr-review
description: Check the current project's GitHub PR review state and address review findings when it is not clean. Use when the user asks to confirm whether the current PR review is clean, inspect unresolved review threads, fix remaining findings, push the branch, and request a fresh Codex review.
---

# Check PR Review

Use this skill to inspect the current branch's GitHub PR review state and finish actionable review follow-up. A PR is clean only when the current PR head has completed the Codex review loop. If the PR is not clean, inspect the findings, implement the smallest safe fix, verify, commit, push, and request a fresh Codex review. Do not merge.

## Read First

1. `AGENTS.md`
2. `docs/context/CURRENT_STATE.md`
3. `docs/context/review-rules.md`

## Workflow

1. Resolve the PR for the current branch.
   - Run `git status --short --branch` to confirm branch and local dirtiness.
   - Use `gh pr view --json number,url,state,reviewDecision,mergeStateStatus,mergeable,headRefOid,statusCheckRollup,latestReviews,comments` when available.
2. Fetch thread-aware review state.
   - Prefer the GitHub plugin's `gh-address-comments` workflow when available.
   - Use its `scripts/fetch_comments.py` helper for `reviewThreads`, `isResolved`, `isOutdated`, file paths, and line anchors.
   - Treat flat PR comments as incomplete when deciding whether the review is clean.
   - Parse the latest completed Codex review body for `Reviewed commit:` and compare it to the current `headRefOid`. Prefix matches are acceptable when GitHub displays abbreviated commits.
3. Classify review results.
   - Clean:
     - no unresolved, non-outdated actionable review thread remains
     - all required checks are successful
     - the latest completed automated Codex review reviewed the current PR head commit
   - Not clean: at least one unresolved, non-outdated actionable thread remains, or the latest automated review reports findings.
   - Pending:
     - the latest review request has no completed response yet
     - or all actionable threads are resolved/outdated, but the latest completed Codex review reviewed an older commit than the current PR head
   - If the PR head is newer than the latest completed Codex review:
     - check whether a top-level `@codex review` comment was already posted after the latest completed Codex review
     - if not, comment `@codex review`
     - report `Pending`, not `Clean`
     - do not make code changes
4. If clean, report:
   - PR URL
   - current PR head commit and latest reviewed commit
   - check summary if available
   - any residual risk or local dirty files
5. If not clean, inspect and fix:
   - Group findings by file and behavior area.
   - For each finding, identify the risk, target file/line, code or doc change, and expected regression test.
   - Implement all unresolved actionable findings unless a finding is ambiguous or conflicts with repo behavior; ask only when the ambiguity is risky.
   - Keep changes scoped to the review findings and required docs/tests.
   - Do not include unrelated local changes in the review-fix commit.
6. Verify after edits:
   - Use the smallest relevant `scripts/run_repo_checks.py` command first.
   - Run broader `unit`, `integration`, or `collect` checks when shared behavior, docs inventory, or scheduler state changed.
   - If verification cannot run, stop before committing unless the user explicitly accepts the risk.
7. Commit and push:
   - Stage only the review-fix files.
   - Commit with a concise message that describes the review fix.
   - Push the current branch to its upstream.
8. Request fresh Codex review:
   - After a successful push, comment `@codex review` on the PR.
   - Also request a fresh review when the current PR head is newer than the latest completed Codex review and no newer `@codex review` request is already visible.
   - Do not wait for the new review unless the user explicitly asks to wait.
   - Report the PR URL, pushed commit, verification, and that Codex review was requested.
9. If pending, report the PR URL and pending review state without waiting unless the user explicitly asks to wait.

## Output Shape

- Lead with one status line: `Clean`, `Not clean - fixed`, `Not clean - blocked`, or `Pending`.
- For non-clean reviews, list the actionable findings first, then summarize the implemented fix.
- For `Pending` caused by a stale completed review, explicitly report the current PR head commit, latest reviewed commit, check status, and whether a fresh `@codex review` was requested or already pending.
- Separate facts from inferences when GitHub data is partial.
- Do not resolve review threads or merge.
- The only GitHub write this skill performs by default is the final `@codex review` comment after pushing review-fix commits.
  - Exception: a stale completed Codex review for the current PR head may also trigger a single `@codex review` request as described above.

## Done When

- The current branch PR was identified or the blocker was explained.
- Thread-aware review state was checked when possible.
- The response clearly says whether the PR is clean, pending, fixed, or blocked.
- `Clean` is reported only after the current PR head has a completed Codex review and green required checks.
- If not clean, actionable findings were reviewed, fixed, verified, committed, pushed, and a fresh Codex review was requested.
