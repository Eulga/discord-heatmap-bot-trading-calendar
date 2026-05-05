---
name: check-pr-review
description: Check the current project's GitHub PR review state, address review findings, and finish clean PRs. Use when the user asks to confirm whether the current PR review is clean, inspect unresolved review threads, fix remaining findings, push the branch, request a fresh Codex review, or merge and delete a clean PR branch.
---

# Check PR Review

Use this skill to inspect the current branch's GitHub PR review state and finish actionable review follow-up. A PR is clean only when the current PR head has completed the Codex review loop. If the PR is clean, merge it and delete the remote and local feature branches. If the PR is not clean, inspect the findings, implement the smallest safe fix, verify, commit, push, and request a fresh Codex review.

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
   - If GitHub exposes a current-head clean Codex result only as a top-level comment, treat it as a completed clean review when:
     - a top-level `@codex review` request is visible after the current `headRefOid` was pushed
     - a later `chatgpt-codex-connector` top-level comment says it did not find major issues
     - no unresolved, non-outdated actionable thread remains
3. Classify review results.
   - Clean:
     - no unresolved, non-outdated actionable review thread remains
     - all required checks are successful
     - the latest completed automated Codex review reviewed the current PR head commit, or a current-head top-level Codex clean response is visible as described above
   - Not clean: at least one unresolved, non-outdated actionable thread remains, or the latest automated review reports findings.
   - Pending:
     - the latest review request has no completed response yet
     - or all actionable threads are resolved/outdated, but neither the latest completed Codex review nor a top-level Codex clean response covers the current PR head
   - If the PR head is newer than the latest completed Codex review:
     - check whether a top-level `@codex review` comment was already posted after the latest completed Codex review
     - if not, comment `@codex review`
     - report `Pending`, not `Clean`
     - do not make code changes
4. If clean, report:
   - First verify merge safety:
     - local worktree is clean
     - current local branch matches the PR `headRefName`
     - local `HEAD` matches `headRefOid`
     - PR state is open, mergeable, and not in a conflict/dirty merge state
     - all required checks are successful
   - If any merge-safety condition fails, report `Clean - blocked` with the exact blocker and do not merge.
   - If merge-safe, merge the PR with `gh pr merge <number> --squash --delete-branch --match-head-commit <headRefOid>` so a last-second unreviewed push cannot be merged.
   - If `gh pr merge` fails, stop immediately, report `Clean - blocked`, and do not delete the local branch.
   - After successful merge, clean up the local branch:
     - remember the feature branch and base branch from the PR
     - `git fetch origin <base>`
     - `git checkout <base>`
     - `git pull --ff-only origin <base>`
     - check whether the old local feature branch still exists with `git branch --list <feature-branch>`
     - if it exists, delete it with `git branch -D <feature-branch>`
     - if it is already gone, report local cleanup as `already-gone` rather than failing
   - Report PR URL, current PR head commit, latest reviewed commit or clean Codex response, check summary, merge method, remote branch deletion, local branch cleanup result, and current branch after cleanup.
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

- Lead with one status line: `Clean - merged`, `Clean - blocked`, `Not clean - fixed`, `Not clean - blocked`, or `Pending`.
- For non-clean reviews, list the actionable findings first, then summarize the implemented fix.
- For `Clean - merged`, summarize merge and branch cleanup first, then include the review/check evidence.
- For `Clean - blocked`, state that the review was clean but merge/branch cleanup was not performed, and list the exact blocker.
- For `Pending` caused by a stale completed review, explicitly report the current PR head commit, latest reviewed commit, check status, and whether a fresh `@codex review` was requested or already pending.
- Separate facts from inferences when GitHub data is partial.
- Do not resolve review threads.
- GitHub writes this skill may perform by default:
  - `@codex review` comment after pushing review-fix commits
  - one `@codex review` comment when the current PR head is newer than the latest completed Codex review and no newer request is visible
  - squash merge a clean PR and request remote branch deletion with `gh pr merge --squash --delete-branch --match-head-commit <headRefOid>`

## Done When

- The current branch PR was identified or the blocker was explained.
- Thread-aware review state was checked when possible.
- The response clearly says whether the PR was merged, is pending, was fixed, or is blocked.
- `Clean - merged` is reported only after the current PR head has a completed Codex review loop and green required checks.
- If clean, the PR was squash-merged, the remote PR branch deletion was requested, the local feature branch was deleted after switching to the base branch, or the merge/cleanup blocker was explained.
- If not clean, actionable findings were reviewed, fixed, verified, committed, pushed, and a fresh Codex review was requested.
