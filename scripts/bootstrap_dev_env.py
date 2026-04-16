#!/usr/bin/env python3
"""Create or repair the local virtualenv for this repository."""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from scripts.dev_env_utils import (
        MIN_SUPPORTED_PYTHON,
        PROJECT_ROOT,
        VENV_DIR,
        format_python_version,
        format_script_invocation,
        inspect_venv,
    )
except ImportError:
    from dev_env_utils import (  # type: ignore[no-redef]
        MIN_SUPPORTED_PYTHON,
        PROJECT_ROOT,
        VENV_DIR,
        format_python_version,
        format_script_invocation,
        inspect_venv,
    )


def _run(command: list[str]) -> None:
    print(f"[bootstrap_dev_env] command={shlex.join(command)}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def _can_run_python(executable: Path) -> bool:
    try:
        completed = subprocess.run(
            [str(executable), "-c", "import sys"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0


def _recreate_message() -> str:
    return format_script_invocation("scripts/bootstrap_dev_env.py", "--recreate")


def _create_venv() -> None:
    _run([sys.executable, "-m", "venv", str(VENV_DIR)])


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or repair the local virtualenv.")
    parser.add_argument(
        "--with-playwright",
        action="store_true",
        help="install the Chromium browser used by Playwright live checks",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="delete and rebuild .venv when it belongs to another OS or interpreter",
    )
    args = parser.parse_args()

    if sys.version_info[:2] < MIN_SUPPORTED_PYTHON:
        minimum = format_python_version(MIN_SUPPORTED_PYTHON)
        current = format_python_version(sys.version_info[:3])
        print(
            "[bootstrap_dev_env] the current interpreter is too old for this repository.\n"
            f"Current: {current}\n"
            f"Required: Python {minimum}+\n"
            f"Install a newer local Python and rerun `{format_script_invocation('scripts/bootstrap_dev_env.py')}`.\n"
            "If you cannot install a newer local Python, use Docker as the validation fallback:\n"
            "docker compose run --rm --build -v ${PWD}:/app discord-bot python scripts/run_repo_checks.py collect",
            file=sys.stderr,
        )
        return 1

    inspection = inspect_venv()

    if args.recreate and VENV_DIR.exists():
        print(f"[bootstrap_dev_env] removing existing virtualenv at {VENV_DIR}")
        shutil.rmtree(VENV_DIR)
        inspection = inspect_venv()

    if inspection.status == "missing":
        _create_venv()
        inspection = inspect_venv()
    elif inspection.status == "cross_platform":
        print(
            "[bootstrap_dev_env] existing .venv appears to have been created on a different OS. "
            f"Re-run with `{_recreate_message()}`."
        )
        return 1
    elif inspection.status == "missing_python":
        print(
            "[bootstrap_dev_env] existing .venv is missing the current OS interpreter path. "
            f"Re-run with `{_recreate_message()}`."
        )
        return 1

    if not _can_run_python(inspection.expected_python):
        print(
            "[bootstrap_dev_env] existing .venv interpreter is not runnable from this machine. "
            f"Re-run with `{_recreate_message()}`."
        )
        return 1

    _run([str(inspection.expected_python), "-m", "pip", "install", "--upgrade", "pip"])
    _run([str(inspection.expected_python), "-m", "pip", "install", "-r", "requirements.txt"])

    if args.with_playwright:
        _run([str(inspection.expected_python), "-m", "playwright", "install", "chromium"])

    print(
        "[bootstrap_dev_env] ready. "
        f"Run `{format_script_invocation('scripts/run_repo_checks.py')}` for validation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
