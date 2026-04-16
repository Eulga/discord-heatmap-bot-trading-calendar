#!/usr/bin/env python3
"""Cross-platform pytest entrypoint for local and CI validation."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_pytest_args(suite: str, include_live: bool) -> list[str]:
    args: list[str] = ["-m", "pytest"]

    if suite == "collect":
        args.extend(["--collect-only", "-q"])
    elif suite == "unit":
        args.extend(["tests/unit", "-q"])
    elif suite == "integration":
        args.extend(["tests/integration", "-q"])
    elif suite == "full":
        args.extend(["tests/unit", "tests/integration", "-q"])
    else:
        raise ValueError(f"unsupported suite: {suite}")

    if include_live:
        args.extend(["-m", "live"])
    elif suite != "collect":
        args.extend(["-m", "not live"])

    return args


def main() -> int:
    parser = argparse.ArgumentParser(description="Run standardized repository checks.")
    parser.add_argument(
        "suite",
        choices=("collect", "unit", "integration", "full"),
        nargs="?",
        default="full",
        help="check suite to run",
    )
    parser.add_argument(
        "--include-live",
        action="store_true",
        help="run live-marked tests instead of the default non-live selection",
    )
    args, unknown = parser.parse_known_args()

    pytest_args = [sys.executable, *build_pytest_args(args.suite, args.include_live)]
    pytest_args.extend(unknown)

    print(f"[run_repo_checks] cwd={PROJECT_ROOT}")
    print(f"[run_repo_checks] command={shlex.join(pytest_args)}")
    completed = subprocess.run(pytest_args, cwd=PROJECT_ROOT)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
