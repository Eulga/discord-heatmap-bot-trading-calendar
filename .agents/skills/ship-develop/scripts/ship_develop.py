from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


def _find_gh() -> str:
    candidates = [
        os.getenv("GH_PATH"),
        shutil.which("gh"),
        r"C:\Program Files\GitHub CLI\gh.exe",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        if Path(candidate).exists():
            return str(Path(candidate))
    raise SystemExit("Could not find gh CLI. Set GH_PATH or install GitHub CLI.")


GIT = shutil.which("git") or "git"
GH = _find_gh()


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def run(cmd: list[str], *, check: bool = True) -> CommandResult:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    result = CommandResult(proc.returncode, proc.stdout.strip(), proc.stderr.strip())
    if check and proc.returncode != 0:
        detail = result.stderr or result.stdout or f"exit={proc.returncode}"
        raise RuntimeError(f"명령 실패: {' '.join(cmd)}\n{detail}")
    return result


def git(*args: str, check: bool = True) -> CommandResult:
    return run([GIT, *args], check=check)


def gh(*args: str, check: bool = True) -> CommandResult:
    return run([GH, *args], check=check)


def get_current_branch() -> str:
    return git("branch", "--show-current").stdout


def get_worktree_dirty() -> bool:
    return bool(git("status", "--porcelain").stdout)


def ensure_prerequisites(base: str, allow_dirty: bool) -> str:
    branch = get_current_branch()
    if not branch:
        raise SystemExit("Could not determine the current branch.")
    if branch == base:
        raise SystemExit(f"Current branch is already {base}. Run this from a feature branch.")
    if get_worktree_dirty() and not allow_dirty:
        raise SystemExit("Worktree is dirty. Commit first, or use --allow-dirty only for dry runs.")
    return branch


def get_repo_name() -> str:
    return json.loads(gh("repo", "view", "--json", "nameWithOwner").stdout)["nameWithOwner"]


def get_repo_settings(repo: str) -> dict[str, object]:
    return json.loads(
        gh(
            "api",
            f"repos/{repo}",
            "--jq",
            "{allow_auto_merge,delete_branch_on_merge,default_branch:.default_branch}",
        ).stdout
    )


def ensure_base_exists(base: str, repo: str) -> None:
    gh("api", f"repos/{repo}/branches/{base}")


def push_branch(branch: str) -> None:
    git("push", "-u", "origin", branch)


def get_existing_pr(branch: str, base: str) -> dict[str, object] | None:
    items = json.loads(
        gh(
            "pr",
            "list",
            "--state",
            "open",
            "--head",
            branch,
            "--base",
            base,
            "--json",
            "number,title,url",
        ).stdout
    )
    return items[0] if items else None


def create_pr(branch: str, base: str, title: str | None, body: str | None, draft: bool) -> dict[str, object]:
    cmd = ["pr", "create", "--head", branch, "--base", base]
    if draft:
        cmd.append("--draft")
    if title:
        cmd.extend(["--title", title])
    if body:
        cmd.extend(["--body", body])
    if not title and not body:
        cmd.append("--fill")
    gh(*cmd)
    pr = get_existing_pr(branch, base)
    if pr is None:
        raise RuntimeError("Failed to find the PR after creation.")
    return pr


def get_pr_details(pr_number: int) -> dict[str, object]:
    return json.loads(
        gh(
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,url,title,reviewDecision,mergeStateStatus,isDraft,state,baseRefName,headRefName",
        ).stdout
    )


def get_checks(pr_number: int, required: bool) -> tuple[list[dict[str, object]], int]:
    cmd = ["pr", "checks", str(pr_number), "--json", "bucket,name,state,workflow"]
    if required:
        cmd.append("--required")
    result = gh(*cmd, check=False)
    data = json.loads(result.stdout) if result.stdout else []
    return data, result.returncode


def summarize_checks(pr_number: int) -> dict[str, object]:
    checks, code = get_checks(pr_number, required=True)
    used_required = True
    if not checks:
        checks, code = get_checks(pr_number, required=False)
        used_required = False

    buckets = {"pass": 0, "fail": 0, "pending": 0, "skipping": 0, "cancel": 0}
    for item in checks:
        bucket = str(item.get("bucket", ""))
        if bucket in buckets:
            buckets[bucket] += 1

    return {
        "checks": checks,
        "exit_code": code,
        "used_required": used_required,
        "has_fail": buckets["fail"] > 0,
        "has_pending": buckets["pending"] > 0,
        "buckets": buckets,
    }


def wait_for_checks(pr_number: int, wait_seconds: int, interval_seconds: int) -> dict[str, object]:
    deadline = time.time() + wait_seconds
    while True:
        summary = summarize_checks(pr_number)
        if summary["has_fail"] or not summary["has_pending"]:
            return summary
        if time.time() >= deadline:
            return summary
        time.sleep(interval_seconds)


def merge_pr(pr_number: int, method: str, delete_remote_branch: bool) -> None:
    cmd = ["pr", "merge", str(pr_number)]
    if method == "squash":
        cmd.append("--squash")
    elif method == "merge":
        cmd.append("--merge")
    else:
        cmd.append("--rebase")
    if delete_remote_branch:
        cmd.append("--delete-branch")
    gh(*cmd)


def cleanup_local_branch(base: str, branch: str) -> None:
    git("fetch", "origin", base)
    git("checkout", base)
    git("pull", "--ff-only", "origin", base)
    git("branch", "-D", branch)


def print_plan(branch: str, base: str, args: argparse.Namespace) -> None:
    print("[dry-run] ship-develop plan")
    print(f"branch={branch}")
    print(f"base={base}")
    print(f"dirty={get_worktree_dirty()}")
    print(f"create_only={args.create_only}")
    print(f"merge_method={args.merge_method}")
    print(f"keep_remote_branch={args.keep_remote_branch}")
    print(f"keep_local_branch={args.keep_local_branch}")
    print(f"wait_seconds={args.wait_seconds}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Push the current branch, create/reuse a PR into a base branch, and merge when safe.")
    parser.add_argument("--base", default="develop")
    parser.add_argument("--title")
    parser.add_argument("--body")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--merge-method", choices=["squash", "merge", "rebase"], default="squash")
    parser.add_argument("--create-only", action="store_true")
    parser.add_argument("--wait-seconds", type=int, default=0)
    parser.add_argument("--interval-seconds", type=int, default=20)
    parser.add_argument("--keep-remote-branch", action="store_true")
    parser.add_argument("--keep-local-branch", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    branch = ensure_prerequisites(args.base, args.allow_dirty)
    repo = get_repo_name()
    ensure_base_exists(args.base, repo)

    if args.dry_run:
        print_plan(branch, args.base, args)
        return 0

    settings = get_repo_settings(repo)
    print(f"repo={repo} default_branch={settings.get('default_branch')} allow_auto_merge={settings.get('allow_auto_merge')}")

    push_branch(branch)
    pr = get_existing_pr(branch, args.base)
    if pr is None:
        pr = create_pr(branch, args.base, args.title, args.body, args.draft)
        print(f"pr_created={pr['url']}")
    else:
        print(f"pr_reused={pr['url']}")

    pr_number = int(pr["number"])
    details = get_pr_details(pr_number)
    print(
        "pr_status="
        f"state={details.get('state')} "
        f"review={details.get('reviewDecision')} "
        f"merge_state={details.get('mergeStateStatus')} "
        f"is_draft={details.get('isDraft')}"
    )

    if args.create_only:
        print(f"done=create-only url={details['url']}")
        return 0

    if details.get("isDraft") is True:
        print(f"done=blocked reason=draft url={details['url']}")
        return 2
    if details.get("reviewDecision") == "CHANGES_REQUESTED":
        print(f"done=blocked reason=changes-requested url={details['url']}")
        return 2
    if details.get("mergeStateStatus") == "DIRTY":
        print(f"done=blocked reason=merge-conflict url={details['url']}")
        return 2

    summary = summarize_checks(pr_number)
    if summary["has_pending"] and args.wait_seconds > 0:
        summary = wait_for_checks(pr_number, args.wait_seconds, args.interval_seconds)

    buckets = summary["buckets"]
    print(
        "checks="
        f"pass={buckets['pass']} fail={buckets['fail']} pending={buckets['pending']} "
        f"skipping={buckets['skipping']} cancel={buckets['cancel']}"
    )

    if summary["has_fail"]:
        print(f"done=blocked reason=checks-failed url={details['url']}")
        return 2
    if summary["has_pending"]:
        print(f"done=pending reason=checks-pending url={details['url']}")
        return 8

    merge_pr(pr_number, args.merge_method, delete_remote_branch=not args.keep_remote_branch)
    print(f"merged={details['url']} method={args.merge_method}")

    if not args.keep_local_branch:
        cleanup_local_branch(args.base, branch)
        print(f"local_cleanup=deleted branch={branch} current_branch={args.base}")
    else:
        print(f"local_cleanup=kept branch={branch}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
