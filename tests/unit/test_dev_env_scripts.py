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


def _patch_candidate_versions(
    monkeypatch,
    versions_by_executable: dict[Path, tuple[int, int, int]],
) -> None:
    monkeypatch.setattr(
        run_repo_checks,
        "_candidate_python_version",
        lambda executable: versions_by_executable.get(executable),
    )


def _imports_required_modules(executable: Path, module_name: str, expected_executable: Path) -> bool:
    return executable == expected_executable and module_name in set(run_repo_checks.REQUIRED_TEST_MODULES)


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
    inspection = _inspection(tmp_path, "missing")
    _patch_candidate_versions(monkeypatch, {current_python: (3, 11, 0)})

    monkeypatch.setattr(
        run_repo_checks,
        "_can_import_module",
        lambda executable, module_name: _imports_required_modules(executable, module_name, current_python),
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
    _patch_candidate_versions(
        monkeypatch,
        {
            current_python: (3, 11, 0),
            inspection.expected_python: (3, 11, 0),
        },
    )

    def fake_can_import_module(executable: Path, module_name: str) -> bool:
        return _imports_required_modules(executable, module_name, inspection.expected_python)

    monkeypatch.setattr(run_repo_checks, "_can_import_module", fake_can_import_module)

    resolved, failure = run_repo_checks.choose_pytest_interpreter(current_python=current_python, inspection=inspection)

    assert resolved == inspection.expected_python
    assert failure is None


def test_choose_pytest_interpreter_prefers_repo_venv_over_current_with_only_pytest(
    tmp_path,
    monkeypatch,
):
    current_python = tmp_path / "python3"
    current_python.write_text("", encoding="utf-8")
    inspection = _inspection(tmp_path, "ok")
    inspection.expected_python.parent.mkdir(parents=True)
    inspection.expected_python.write_text("", encoding="utf-8")
    _patch_candidate_versions(
        monkeypatch,
        {
            current_python: (3, 11, 0),
            inspection.expected_python: (3, 11, 0),
        },
    )

    def fake_can_import_module(executable: Path, module_name: str) -> bool:
        if executable == current_python:
            return module_name == "pytest"
        return _imports_required_modules(executable, module_name, inspection.expected_python)

    monkeypatch.setattr(run_repo_checks, "_can_import_module", fake_can_import_module)

    resolved, failure = run_repo_checks.choose_pytest_interpreter(current_python=current_python, inspection=inspection)

    assert resolved == inspection.expected_python
    assert failure is None


def test_choose_pytest_interpreter_rejects_old_current_python_even_when_pytest_is_present(
    tmp_path,
    monkeypatch,
):
    current_python = tmp_path / "python3"
    current_python.write_text("", encoding="utf-8")
    inspection = _inspection(tmp_path, "ok")
    inspection.expected_python.parent.mkdir(parents=True)
    inspection.expected_python.write_text("", encoding="utf-8")
    _patch_candidate_versions(
        monkeypatch,
        {
            current_python: (3, 9, 6),
            inspection.expected_python: (3, 11, 0),
        },
    )

    def fake_can_import_module(executable: Path, module_name: str) -> bool:
        return executable in {current_python, inspection.expected_python} and module_name in set(
            run_repo_checks.REQUIRED_TEST_MODULES
        )

    monkeypatch.setattr(run_repo_checks, "_can_import_module", fake_can_import_module)
    monkeypatch.setattr(run_repo_checks.sys, "version_info", (3, 9, 6))

    resolved, failure = run_repo_checks.choose_pytest_interpreter(current_python=current_python, inspection=inspection)

    assert resolved == inspection.expected_python
    assert failure is None


def test_choose_pytest_interpreter_rejects_old_repo_venv_even_when_pytest_is_present(
    tmp_path,
    monkeypatch,
):
    current_python = tmp_path / "python3"
    current_python.write_text("", encoding="utf-8")
    inspection = _inspection(tmp_path, "ok")
    inspection.expected_python.parent.mkdir(parents=True)
    inspection.expected_python.write_text("", encoding="utf-8")
    _patch_candidate_versions(
        monkeypatch,
        {
            current_python: (3, 9, 6),
            inspection.expected_python: (3, 9, 6),
        },
    )

    def fake_can_import_module(executable: Path, module_name: str) -> bool:
        return executable in {current_python, inspection.expected_python} and module_name in set(
            run_repo_checks.REQUIRED_TEST_MODULES
        )

    monkeypatch.setattr(run_repo_checks, "_can_import_module", fake_can_import_module)
    monkeypatch.setattr(run_repo_checks.sys, "version_info", (3, 9, 6))

    resolved, failure = run_repo_checks.choose_pytest_interpreter(current_python=current_python, inspection=inspection)

    assert resolved is None
    assert failure is not None
    assert "repo-local .venv uses Python 3.9.6" in failure
    assert "bootstrap_dev_env.py --recreate" in failure


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


def test_build_pytest_args_keeps_default_suite_without_explicit_target():
    args = run_repo_checks.build_pytest_args("integration", include_live=False, passthrough_args=["-k", "eod"])

    assert "tests/integration" in args


def test_build_pytest_args_omits_default_suite_when_explicit_target_is_passed():
    args = run_repo_checks.build_pytest_args(
        "integration",
        include_live=False,
        passthrough_args=["tests/integration/test_intel_scheduler_logic.py"],
    )

    assert "tests/integration" not in args
    assert args == ["-m", "pytest", "-q", "-m", "not live"]


def test_build_pytest_args_omits_default_suite_when_target_follows_separator():
    args = run_repo_checks.build_pytest_args(
        "unit",
        include_live=False,
        passthrough_args=["--", "tests/unit/test_dev_env_scripts.py"],
    )

    assert "tests/unit" not in args
    assert args == ["-m", "pytest", "-q", "-m", "not live"]


def test_build_pytest_args_keeps_default_suite_for_path_valued_option():
    args = run_repo_checks.build_pytest_args(
        "unit",
        include_live=False,
        passthrough_args=["--junitxml", "reports/unit.xml"],
    )

    assert "tests/unit" in args


def test_build_pytest_args_keeps_default_suite_for_ignored_test_path_option():
    args = run_repo_checks.build_pytest_args(
        "integration",
        include_live=False,
        passthrough_args=["--ignore", "tests/integration/test_intel_scheduler_logic.py"],
    )

    assert "tests/integration" in args


def test_build_pytest_args_keeps_default_suite_for_absolute_path_option_value():
    args = run_repo_checks.build_pytest_args(
        "integration",
        include_live=False,
        passthrough_args=["--rootdir", "/tmp"],
    )

    assert "tests/integration" in args


def test_build_pytest_args_still_detects_target_after_option_value():
    args = run_repo_checks.build_pytest_args(
        "unit",
        include_live=False,
        passthrough_args=["-k", "dev_env", "tests/unit/test_dev_env_scripts.py"],
    )

    assert "tests/unit" not in args
    assert args == ["-m", "pytest", "-q", "-m", "not live"]
