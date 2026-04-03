---
name: ship-develop
description: "Ship the current branch into a target base branch with the full GitHub flow. Default base is `develop`, but a trailing skill argument like `$ship-develop master` means `--base master`. Verify repo state, run the right tests, commit if needed, push, create or reuse a PR, request Codex review, address findings until clean, and merge when safe."
---

# Ship Develop

Use this skill to finish the branch shipping workflow end to end instead of stopping at local edits.

## Invocation Argument

- Default target base branch is `develop`.
- If the skill invocation includes one trailing bare branch name, interpret it as the target base branch.
- Example: `[$ship-develop](/Users/jaeik/Documents/discord-heatmap-bot-trading-calendar/.agents/skills/ship-develop/SKILL.md) master` means "ship the current branch into `master`", so use `--base master`.
- If no trailing branch name is provided, keep using `--base develop`.

For this repository, do not assume the GitHub default branch is `develop`. Verify the target base branch first. At the time this skill was created, the repo default branch is `master`, while `develop` exists as a working integration branch.

## Quick Start

1. Check `git status --short --branch` and confirm what branch you are on.
2. Run tests or validation proportional to the change.
3. If the tree is dirty, create the commit before shipping.
4. Resolve the target base branch from the invocation. Default to `develop`, but if the user invoked `$ship-develop master`, use `master`.
5. For the default first pass, run `scripts/ship_develop.py --base <resolved-base> --codex-review`.
6. If the script reports `codex-review-requested`, return the PR URL and stop. After Codex review is expected to be ready, rerun with `--wait-codex-seconds 300 --wait-seconds 600` so the script can observe the result before merge and then watch checks.
7. If the script reports `codex-review-findings`, read the PR review comments, fix them, rerun validation, and run the same command again.
8. Use `--require-review` only when the user explicitly wants human approval before merge.

## Workflow

### 1. Verify the branch is really ready

- Read the current diff and make sure there are no unresolved conflicts or unrelated edits.
- Use the existing project rules in `AGENTS.md` before shipping.
- If the branch contains only doc or config changes, use lighter verification and say so explicitly.

### 2. Commit before you ship

- If `git status --porcelain` is non-empty, review the files, stage intentionally, and create a commit.
- Do not run the shipping script against a dirty tree unless you are only doing a dry run.
- Use a concise commit message that reflects the branch delta.

### 3. Use the shipping script

- The script handles:
  - branch and worktree checks
  - push with upstream setup
  - PR create or reuse
  - Codex review request and optional polling
  - human review gate inspection when requested
  - check status inspection
  - merge when safe after Codex is clean
  - checkout the chosen base branch and delete the local branch after a successful merge
- Preferred command:

```powershell
.\.venv\Scripts\python .agents/skills/ship-develop/scripts/ship_develop.py --base <resolved-base> --codex-review
```

### 4. Interpret outcomes conservatively

- If the script reports `codex-review-requested`, the review request was posted and the skill intentionally stopped without polling. Return the PR URL and let Codex review complete asynchronously.
- If the script reports `codex-review-findings`, inspect the PR review comments from `chatgpt-codex-connector[bot]`, fix them locally, rerun tests, push, and rerun the same command.
- If the script reports `codex-review-pending`, wait and rerun instead of merging blind.
- If checks fail, stop and summarize the failure.
- If human review is required and the PR is not approved yet, stop after PR creation or reuse and report the PR URL.
- If the PR has `CHANGES_REQUESTED` or merge conflicts, stop and report exactly that.
- If checks are still pending and the wait budget expires, return the PR URL and current state instead of guessing.
- If merge succeeds, report the PR URL, merge method, and local branch cleanup result.

## Script Flags

- `--base <branch>`: target branch. Default to `develop` when the skill invocation does not provide a trailing base branch argument.
- `--merge-method squash|merge|rebase`: default is `squash`
- `--create-only`: stop after PR creation or lookup
- `--codex-review`: comment `@codex review` on the PR; if `--wait-codex-seconds` is omitted or `0`, request the review and stop immediately
- `--wait-codex-seconds N`: when `N > 0`, poll Codex review status for up to `N` seconds after posting the review request
- `--require-review`: require `APPROVED` before merge
- `--wait-review-seconds N`: optionally poll for review state before giving up
- `--wait-seconds N`: poll checks for up to `N` seconds before deciding
- `--interval-seconds N`: polling interval, default `20`
- `--keep-remote-branch`: do not request remote branch deletion during merge
- `--keep-local-branch`: do not switch to base and delete the local branch after merge
- `--dry-run`: print the plan without changing GitHub or Git state
- `--allow-dirty`: only for dry-run or unusual debugging; do not use for normal shipping

## Repo-Specific Notes

- `gh` may not be on `PATH` in this environment. The script already falls back to `C:\Program Files\GitHub CLI\gh.exe`.
- This repo currently has no branch protection on `develop`, so the review gate lives in this script rather than GitHub policy.
- Release shipping to `master` should be invoked as `$ship-develop master`, which maps to `--base master`.
- The default practical workflow is iterative:
  - pass 1: create or update the PR, request Codex review, and stop immediately with the PR URL
  - middle passes: after review lands, rerun with `--wait-codex-seconds` to inspect findings, then fix findings and rerun again as needed
  - final pass: Codex returns clean, checks are green, and the script merges
- Human approval remains an optional second gate when the user explicitly asks for it.
- This repo currently has `delete_branch_on_merge=false`, so local cleanup is handled by the script after a successful merge.

## Done When

- The branch is pushed.
- A PR to the chosen base branch exists or was reused.
- The merge either completed safely or stopped with a concrete reason.
- If merge completed, the workspace is on the chosen base branch and the local feature branch is removed unless the user asked to keep it.
