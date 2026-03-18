---
name: ship-develop
description: "Ship the current branch into `develop` with the full GitHub flow: verify repo state, run the right tests, commit if needed, push, create or reuse a PR, merge when safe, and clean up the branch. Use when the user asks to merge the current branch into `develop`, create a PR, merge it, and delete the branch automatically."
---

# Ship Develop

Use this skill to finish the branch shipping workflow end to end instead of stopping at local edits.

For this repository, do not assume the GitHub default branch is `develop`. Verify the target base branch first. At the time this skill was created, the repo default branch is `master`, while `develop` exists as a working integration branch.

## Quick Start

1. Check `git status --short --branch` and confirm what branch you are on.
2. Run tests or validation proportional to the change.
3. If the tree is dirty, create the commit before shipping.
4. Run `scripts/ship_develop.py --base develop --wait-seconds 600`.
5. If the script reports a blocked or pending state, explain the reason instead of forcing a merge.

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
  - check and review status inspection
  - merge when safe
  - checkout `develop` and delete the local branch after a successful merge
- Preferred command:

```powershell
.\.venv\Scripts\python .agents/skills/ship-develop/scripts/ship_develop.py --base develop --wait-seconds 600
```

### 4. Interpret outcomes conservatively

- If checks fail, stop and summarize the failure.
- If the PR has `CHANGES_REQUESTED` or merge conflicts, stop and report exactly that.
- If checks are still pending and the wait budget expires, return the PR URL and current state instead of guessing.
- If merge succeeds, report the PR URL, merge method, and local branch cleanup result.

## Script Flags

- `--base develop`: target branch
- `--merge-method squash|merge|rebase`: default is `squash`
- `--create-only`: stop after PR creation or lookup
- `--wait-seconds N`: poll checks for up to `N` seconds before deciding
- `--interval-seconds N`: polling interval, default `20`
- `--keep-remote-branch`: do not request remote branch deletion during merge
- `--keep-local-branch`: do not switch to base and delete the local branch after merge
- `--dry-run`: print the plan without changing GitHub or Git state
- `--allow-dirty`: only for dry-run or unusual debugging; do not use for normal shipping

## Repo-Specific Notes

- `gh` may not be on `PATH` in this environment. The script already falls back to `C:\Program Files\GitHub CLI\gh.exe`.
- This repo currently has `allow_auto_merge=false`, so the normal path is direct merge after checks are green or absent.
- This repo currently has `delete_branch_on_merge=false`, so local cleanup is handled by the script after a successful merge.

## Done When

- The branch is pushed.
- A PR to `develop` exists or was reused.
- The merge either completed safely or stopped with a concrete reason.
- If merge completed, the workspace is on `develop` and the local feature branch is removed unless the user asked to keep it.
