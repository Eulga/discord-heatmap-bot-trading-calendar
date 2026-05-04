import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _copy_harness(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    shutil.copytree(
        REPO_ROOT / ".codex-harness",
        project / ".codex-harness",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "requirements.md", "state.json"),
    )
    return project


def _run(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(project / ".codex-harness" / "bin" / "harness.py"), *args],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )


def _state(project: Path) -> dict:
    return json.loads((project / ".codex-harness" / "state.json").read_text(encoding="utf-8"))


def _write_report(project: Path, report: str) -> None:
    path = project / report
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Role Report\n\n## Status\n\ncomplete\n",
        encoding="utf-8",
    )


def test_init_creates_runtime_files_from_templates(tmp_path):
    project = _copy_harness(tmp_path)

    completed = _run(project, "init", "--request", "Add staged workflow")

    assert completed.returncode == 0, completed.stderr
    assert _state(project)["phase"] == "intake"
    requirements = (project / ".codex-harness" / "requirements.md").read_text(encoding="utf-8")
    assert "Add staged workflow" in requirements
    assert "Paste the user's request here" not in requirements


def test_init_does_not_overwrite_existing_runtime_files_without_force(tmp_path):
    project = _copy_harness(tmp_path)

    first = _run(project, "init", "--request", "First request")
    second = _run(project, "init", "--request", "Second request")

    assert first.returncode == 0, first.stderr
    assert second.returncode != 0
    requirements = (project / ".codex-harness" / "requirements.md").read_text(encoding="utf-8")
    assert "First request" in requirements
    assert "Second request" not in requirements
    assert "use --force to overwrite" in second.stderr


def test_full_happy_path_transitions_to_done(tmp_path):
    project = _copy_harness(tmp_path)
    assert _run(project, "init").returncode == 0

    roles = [
        ("analysis", ".codex-harness/reports/01-analysis.md", "analysis_ready"),
        ("implementation", ".codex-harness/reports/02-implementation.md", "implementation_ready"),
        ("code-review", ".codex-harness/reports/03-code-review.md", "review_ready"),
        ("test", ".codex-harness/reports/04-test.md", "test_ready"),
        ("final-review", ".codex-harness/reports/05-final-review.md", "done"),
    ]

    for role, report, expected_phase in roles:
        next_result = _run(project, "next")
        assert next_result.returncode == 0, next_result.stderr
        assert f"next role: {role}" in next_result.stdout

        prompt_result = _run(project, "prompt", role)
        assert prompt_result.returncode == 0, prompt_result.stderr
        assert "Session Prompt" in prompt_result.stdout

        heartbeat = _run(project, "heartbeat", role)
        assert heartbeat.returncode == 0, heartbeat.stderr
        assert _state(project)["status"] == "in_progress"
        assert _state(project)["active_role"] == role

        _write_report(project, report)
        complete = _run(project, "complete", role, report)
        assert complete.returncode == 0, complete.stderr
        assert _state(project)["phase"] == expected_phase

    final_state = _state(project)
    assert final_state["status"] == "complete"
    assert final_state["active_role"] is None
    assert final_state["next_report"] is None


def test_block_records_report_and_reason(tmp_path):
    project = _copy_harness(tmp_path)
    assert _run(project, "init").returncode == 0
    assert _run(project, "heartbeat", "analysis").returncode == 0
    _write_report(project, ".codex-harness/reports/01-analysis.md")

    blocked = _run(
        project,
        "block",
        "analysis",
        ".codex-harness/reports/01-analysis.md",
        "missing acceptance criteria",
    )

    assert blocked.returncode == 0, blocked.stderr
    state = _state(project)
    assert state["status"] == "blocked"
    assert state["active_role"] == "analysis"
    assert state["blocked_reason"] == "missing acceptance criteria"
    next_result = _run(project, "next")
    assert "blocked: missing acceptance criteria" in next_result.stdout


def test_report_path_outside_project_is_rejected(tmp_path):
    project = _copy_harness(tmp_path)
    outside_report = tmp_path / "outside.md"
    outside_report.write_text("# Outside\n", encoding="utf-8")
    assert _run(project, "init").returncode == 0
    assert _run(project, "heartbeat", "analysis").returncode == 0

    completed = _run(project, "complete", "analysis", str(outside_report))

    assert completed.returncode != 0
    assert "inside the project root" in completed.stderr
