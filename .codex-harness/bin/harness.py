#!/usr/bin/env python3
"""Small file-based state helper for the repo-local Codex harness."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HARNESS_DIR = ROOT / ".codex-harness"
STATE_PATH = HARNESS_DIR / "state.json"
STATE_TEMPLATE_PATH = HARNESS_DIR / "state.template.json"
REQUIREMENTS_PATH = HARNESS_DIR / "requirements.md"
REQUIREMENTS_TEMPLATE_PATH = HARNESS_DIR / "requirements.template.md"
PROMPTS_DIR = HARNESS_DIR / "prompts"

NEXT_BY_PHASE = {
    "intake": ("analysis", ".codex-harness/reports/01-analysis.md"),
    "analysis_ready": ("implementation", ".codex-harness/reports/02-implementation.md"),
    "implementation_ready": ("code-review", ".codex-harness/reports/03-code-review.md"),
    "review_ready": ("test", ".codex-harness/reports/04-test.md"),
    "test_ready": ("final-review", ".codex-harness/reports/05-final-review.md"),
    "done": (None, None),
}

COMPLETE_BY_ROLE = {
    "analysis": ("intake", "analysis_ready", ".codex-harness/reports/01-analysis.md"),
    "implementation": (
        "analysis_ready",
        "implementation_ready",
        ".codex-harness/reports/02-implementation.md",
    ),
    "code-review": (
        "implementation_ready",
        "review_ready",
        ".codex-harness/reports/03-code-review.md",
    ),
    "test": ("review_ready", "test_ready", ".codex-harness/reports/04-test.md"),
    "final-review": ("test_ready", "done", ".codex-harness/reports/05-final-review.md"),
}

PROMPT_BY_ROLE = {
    "orchestrator": "orchestrator.md",
    "analysis": "analysis.md",
    "implementation": "implementation.md",
    "code-review": "code-review.md",
    "test": "test.md",
    "final-review": "final-review.md",
}

REQUEST_PLACEHOLDER = "Paste the user's request here before starting the analysis session."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"state file not found: {STATE_PATH}. Run `.codex-harness/bin/harness.py init` first.")
    except json.JSONDecodeError as exc:
        die(f"state file is invalid JSON: {exc}")


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def expected_role(state: dict) -> str | None:
    role, _report = NEXT_BY_PHASE.get(state.get("phase"), (None, None))
    return role


def expected_report_for_phase(state: dict) -> str | None:
    _role, report = NEXT_BY_PHASE.get(state.get("phase"), (None, None))
    return report


def require_role_can_run(state: dict, role: str) -> None:
    if state.get("status") == "blocked":
        die(f"harness is blocked: {state.get('blocked_reason')}")
    if state.get("phase") == "done":
        die("harness is already done")
    expected = expected_role(state)
    if role != expected:
        die(f"role '{role}' cannot run during phase '{state.get('phase')}'; expected '{expected}'")


def normalize_report(report: str) -> str:
    raw_path = Path(report)
    candidate = raw_path if raw_path.is_absolute() else ROOT / raw_path
    try:
        relative = candidate.resolve().relative_to(ROOT.resolve())
    except ValueError:
        die("report path must be inside the project root")
    return relative.as_posix()


def require_report_exists(report: str) -> None:
    path = ROOT / report
    if not path.exists():
        die(f"report does not exist: {report}")
    if not path.is_file():
        die(f"report is not a file: {report}")


def render_requirements(request: str | None) -> str:
    try:
        text = REQUIREMENTS_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        die(f"requirements template not found: {REQUIREMENTS_TEMPLATE_PATH}")

    if request:
        text = text.replace(REQUEST_PLACEHOLDER, request.strip())
    return text if text.endswith("\n") else text + "\n"


def read_state_template() -> str:
    try:
        text = STATE_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        die(f"state template not found: {STATE_TEMPLATE_PATH}")

    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        die(f"state template is invalid JSON: {exc}")
    return text if text.endswith("\n") else text + "\n"


def command_init(args: argparse.Namespace) -> None:
    runtime_paths = [REQUIREMENTS_PATH, STATE_PATH]
    existing = [path.relative_to(ROOT).as_posix() for path in runtime_paths if path.exists()]
    if existing and not args.force:
        die("runtime harness file already exists: " + ", ".join(existing) + "; use --force to overwrite")

    HARNESS_DIR.mkdir(parents=True, exist_ok=True)
    (HARNESS_DIR / "reports").mkdir(parents=True, exist_ok=True)
    REQUIREMENTS_PATH.write_text(render_requirements(args.request), encoding="utf-8")
    STATE_PATH.write_text(read_state_template(), encoding="utf-8")
    print(f"initialized harness in {HARNESS_DIR.relative_to(ROOT).as_posix()}")


def command_status(_args: argparse.Namespace) -> None:
    print(json.dumps(load_state(), indent=2))


def command_next(_args: argparse.Namespace) -> None:
    state = load_state()
    if state.get("status") == "blocked":
        print(f"blocked: {state.get('blocked_reason')}")
        if state.get("last_report"):
            print(f"last report: {state['last_report']}")
        return
    role, report = NEXT_BY_PHASE.get(state.get("phase"), (None, None))
    if role is None:
        print("done")
        if state.get("last_report"):
            print(f"final report: {state['last_report']}")
        return
    print(f"next role: {role}")
    print(f"expected report: {report}")
    print(f"prompt: .codex-harness/prompts/{PROMPT_BY_ROLE[role]}")


def command_prompt(args: argparse.Namespace) -> None:
    prompt_name = PROMPT_BY_ROLE.get(args.role)
    if not prompt_name:
        die(f"unknown role: {args.role}")
    prompt_path = PROMPTS_DIR / prompt_name
    try:
        print(prompt_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"prompt not found: {prompt_path}")


def command_heartbeat(args: argparse.Namespace) -> None:
    state = load_state()
    require_role_can_run(state, args.role)
    state["status"] = "in_progress"
    state["active_role"] = args.role
    state["heartbeat_at"] = utc_now()
    state["blocked_reason"] = None
    save_state(state)
    print(f"heartbeat recorded for {args.role}")


def command_complete(args: argparse.Namespace) -> None:
    state = load_state()
    current_phase, next_phase, default_report = COMPLETE_BY_ROLE.get(args.role, (None, None, None))
    if current_phase is None:
        die(f"unknown role: {args.role}")
    if state.get("phase") != current_phase:
        die(f"role '{args.role}' cannot complete phase '{state.get('phase')}'; expected '{current_phase}'")
    report = normalize_report(args.report)
    if report != default_report:
        die(f"unexpected report path '{report}'; expected '{default_report}'")
    require_report_exists(report)

    state["phase"] = next_phase
    state["status"] = "complete" if next_phase == "done" else "ready"
    state["active_role"] = None
    state["heartbeat_at"] = utc_now()
    state["last_report"] = report
    state["next_report"] = expected_report_for_phase(state)
    state["blocked_reason"] = None
    save_state(state)
    print(f"{args.role} complete; phase is now {next_phase}")


def command_block(args: argparse.Namespace) -> None:
    state = load_state()
    if args.role not in COMPLETE_BY_ROLE:
        die(f"unknown role: {args.role}")
    report = normalize_report(args.report)
    require_report_exists(report)
    state["status"] = "blocked"
    state["active_role"] = args.role
    state["heartbeat_at"] = utc_now()
    state["last_report"] = report
    state["blocked_reason"] = args.reason
    save_state(state)
    print(f"{args.role} blocked: {args.reason}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the Codex harness state file.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create ignored runtime requirements and state files")
    init.add_argument("--request", help="original user request to insert into requirements.md")
    init.add_argument("--force", action="store_true", help="overwrite existing runtime files")
    init.set_defaults(func=command_init)

    subparsers.add_parser("status", help="print state.json").set_defaults(func=command_status)
    subparsers.add_parser("next", help="print next role and report").set_defaults(func=command_next)

    prompt = subparsers.add_parser("prompt", help="print a role prompt")
    prompt.add_argument("role", choices=sorted(PROMPT_BY_ROLE))
    prompt.set_defaults(func=command_prompt)

    heartbeat = subparsers.add_parser("heartbeat", help="mark a role as in progress")
    heartbeat.add_argument("role", choices=sorted(COMPLETE_BY_ROLE))
    heartbeat.set_defaults(func=command_heartbeat)

    complete = subparsers.add_parser("complete", help="complete the current role")
    complete.add_argument("role", choices=sorted(COMPLETE_BY_ROLE))
    complete.add_argument("report")
    complete.set_defaults(func=command_complete)

    block = subparsers.add_parser("block", help="mark the harness as blocked")
    block.add_argument("role", choices=sorted(COMPLETE_BY_ROLE))
    block.add_argument("report")
    block.add_argument("reason")
    block.set_defaults(func=command_block)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
