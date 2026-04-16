from pathlib import Path

from scripts import dev_env_utils, run_repo_checks
from scripts.dev_env_utils import VenvInspection


def _inspection(tmp_path: Path, status: str) -> VenvInspection:
    venv_dir = tmp_path / ".venv"
    expected_python = venv_dir / "bin" / "python"
    alternate_python = venv_dir / "Scripts" / "python.exe"
    return VenvInspection(
        platform_key="posix",
        venv_dir=venv_dir,
        expected_python=expected_python,
        alternate_python=alternate_python,
        pyvenv_cfg=venv_dir / "pyvenv.cfg",
        cfg_values={},
        status=status,
    )


def test_inspect_venv_detects_cross_platform_layout(tmp_path):
    venv_dir = tmp_path / ".venv"
    scripts_dir = venv_dir / "Scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "python.exe").write_text("", encoding="utf-8")
    (venv_dir / "pyvenv.cfg").write_text("home = C:\\Python313\n", encoding="utf-8")

    inspection = dev_env_utils.inspect_venv(venv_dir, platform_key="posix")

    assert inspection.status == "cross_platform"
    assert inspection.expected_python == venv_dir / "bin" / "python"


def test_inspect_venv_detects_missing_current_os_python_path(tmp_path):
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")

    inspection = dev_env_utils.inspect_venv(venv_dir, platform_key="posix")

    assert inspection.status == "missing_python"


def test_choose_pytest_interpreter_prefers_current_python(tmp_path, monkeypatch):
    current_python = tmp_path / "python3"
    current_python.write_text("", encoding="utf-8")
    inspection = _inspection(tmp_path, "ok")
    inspection.expected_python.parent.mkdir(parents=True)
    inspection.expected_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        run_repo_checks,
        "_can_import_module",
        lambda executable, module_name: executable == current_python and module_name == "pytest",
    )

    resolved, failure = run_repo_checks.choose_pytest_interpreter(current_python=current_python, inspection=inspection)

    assert resolved == current_python
    assert failure is None


def test_choose_pytest_interpreter_falls_back_to_repo_venv(tmp_path, monkeypatch):
    current_python = tmp_path / "python3"
    current_python.write_text("", encoding="utf-8")
    inspection = _inspection(tmp_path, "ok")
    inspection.expected_python.parent.mkdir(parents=True)
    inspection.expected_python.write_text("", encoding="utf-8")

    def fake_can_import_module(executable: Path, module_name: str) -> bool:
        return executable == inspection.expected_python and module_name == "pytest"

    monkeypatch.setattr(run_repo_checks, "_can_import_module", fake_can_import_module)

    resolved, failure = run_repo_checks.choose_pytest_interpreter(current_python=current_python, inspection=inspection)

    assert resolved == inspection.expected_python
    assert failure is None


def test_choose_pytest_interpreter_reports_recreate_for_cross_platform_venv(tmp_path, monkeypatch):
    current_python = tmp_path / "python3"
    current_python.write_text("", encoding="utf-8")
    inspection = _inspection(tmp_path, "cross_platform")

    monkeypatch.setattr(run_repo_checks, "_can_import_module", lambda *_args, **_kwargs: False)

    resolved, failure = run_repo_checks.choose_pytest_interpreter(current_python=current_python, inspection=inspection)

    assert resolved is None
    assert failure is not None
    assert "bootstrap_dev_env.py --recreate" in failure


def test_choose_pytest_interpreter_mentions_python_version_when_current_python_is_too_old(
    tmp_path,
    monkeypatch,
):
    current_python = tmp_path / "python3"
    current_python.write_text("", encoding="utf-8")
    inspection = _inspection(tmp_path, "missing")

    monkeypatch.setattr(run_repo_checks, "_can_import_module", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(run_repo_checks.sys, "version_info", (3, 9, 6))

    resolved, failure = run_repo_checks.choose_pytest_interpreter(current_python=current_python, inspection=inspection)

    assert resolved is None
    assert failure is not None
    assert "Python 3.10+" in failure
    assert "docker compose run --rm --build -v ${PWD}:/app discord-bot" in failure
