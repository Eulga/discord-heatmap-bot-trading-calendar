#!/usr/bin/env python3
"""Cross-platform pytest entrypoint for local and CI validation."""

from __future__ import annotations

import argparse
import importlib.util
import shlex
import subprocess
import sys
from pathlib import Path

try:
    from scripts.dev_env_utils import (
        MIN_SUPPORTED_PYTHON,
        PROJECT_ROOT,
        VenvInspection,
        format_python_version,
        format_script_invocation,
        inspect_venv,
    )
except ImportError:
    from dev_env_utils import (  # type: ignore[no-redef]
        MIN_SUPPORTED_PYTHON,
        PROJECT_ROOT,
        VenvInspection,
        format_python_version,
        format_script_invocation,
        inspect_venv,
    )


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return str(left) == str(right)


def _can_import_module(executable: Path, module_name: str) -> bool:
    if _same_path(executable, Path(sys.executable)):
        return importlib.util.find_spec(module_name) is not None

    try:
        completed = subprocess.run(
            [str(executable), "-c", f"import {module_name}"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0


def _bootstrap_hint(*extra_args: str) -> str:
    return format_script_invocation("scripts/bootstrap_dev_env.py", *extra_args)


def _docker_hint(suite: str = "collect") -> str:
    return f"docker compose run --rm --build -v ${{PWD}}:/app discord-bot python scripts/run_repo_checks.py {suite}"


def _current_python_too_old() -> bool:
    return sys.version_info[:2] < MIN_SUPPORTED_PYTHON


def _resolution_failure(inspection: VenvInspection) -> str:
    minimum = format_python_version(MIN_SUPPORTED_PYTHON)
    current = format_python_version(sys.version_info[:3])

    if _current_python_too_old():
        return (
            "[run_repo_checks] no usable pytest interpreter found.\n"
            f"Current interpreter is Python {current}, but local bootstrap needs Python {minimum}+.\n"
            f"Install a newer local Python and rerun `{_bootstrap_hint()}`.\n"
            f"As a fallback, run checks in Docker, for example `{_docker_hint()}`."
        )

    if inspection.status == "cross_platform":
        return (
            "[run_repo_checks] no usable pytest interpreter found.\n"
            "The repo-local .venv appears to belong to a different OS.\n"
            f"Rebuild it with `{_bootstrap_hint('--recreate')}`."
        )

    if inspection.status == "missing":
        return (
            "[run_repo_checks] no usable pytest interpreter found.\n"
            f"Create the repo-local virtualenv with `{_bootstrap_hint()}`."
        )

    if inspection.status == "missing_python":
        return (
            "[run_repo_checks] no usable pytest interpreter found.\n"
            "The repo-local .venv is missing the interpreter path for this OS.\n"
            f"Rebuild it with `{_bootstrap_hint('--recreate')}`."
        )

    return (
        "[run_repo_checks] no usable pytest interpreter found.\n"
        f"Install test dependencies with `{_bootstrap_hint()}`."
    )


def choose_pytest_interpreter(
    current_python: Path | None = None,
    inspection: VenvInspection | None = None,
) -> tuple[Path | None, str | None]:
    resolved_current_python = current_python or Path(sys.executable)
    resolved_inspection = inspection or inspect_venv()

    if not _current_python_too_old() and _can_import_module(resolved_current_python, "pytest"):
        return resolved_current_python, None

    if (
        resolved_inspection.status == "ok"
        and not _same_path(resolved_current_python, resolved_inspection.expected_python)
        and _can_import_module(resolved_inspection.expected_python, "pytest")
    ):
        return resolved_inspection.expected_python, None

    return None, _resolution_failure(resolved_inspection)


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

    python_executable, failure = choose_pytest_interpreter()
    if python_executable is None:
        print(failure, file=sys.stderr)
        return 1

    pytest_args = [str(python_executable), *build_pytest_args(args.suite, args.include_live)]
    pytest_args.extend(unknown)

    print(f"[run_repo_checks] cwd={PROJECT_ROOT}")
    print(f"[run_repo_checks] command={shlex.join(pytest_args)}")
    completed = subprocess.run(pytest_args, cwd=PROJECT_ROOT)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
