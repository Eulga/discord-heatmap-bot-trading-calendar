from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = PROJECT_ROOT / ".venv"
MIN_SUPPORTED_PYTHON = (3, 10)
_WINDOWS_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:\\")


@dataclass(frozen=True)
class VenvInspection:
    platform_key: str
    venv_dir: Path
    expected_python: Path
    alternate_python: Path
    pyvenv_cfg: Path
    cfg_values: dict[str, str]
    status: str


def current_platform_key() -> str:
    return "windows" if os.name == "nt" else "posix"


def default_python_command(platform_key: str | None = None) -> str:
    return "py -3" if (platform_key or current_platform_key()) == "windows" else "python3"


def format_python_version(version_info: tuple[int, int, int] | tuple[int, int]) -> str:
    return ".".join(str(part) for part in version_info)


def format_script_invocation(script_path: str, *args: str, platform_key: str | None = None) -> str:
    parts = [default_python_command(platform_key), script_path, *args]
    return " ".join(part for part in parts if part)


def venv_python_path(venv_dir: Path = VENV_DIR, platform_key: str | None = None) -> Path:
    resolved_platform = platform_key or current_platform_key()
    if resolved_platform == "windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def alternate_venv_python_path(venv_dir: Path = VENV_DIR, platform_key: str | None = None) -> Path:
    resolved_platform = platform_key or current_platform_key()
    if resolved_platform == "windows":
        return venv_dir / "bin" / "python"
    return venv_dir / "Scripts" / "python.exe"


def read_pyvenv_cfg(pyvenv_cfg: Path) -> dict[str, str]:
    if not pyvenv_cfg.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in pyvenv_cfg.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        values[key.strip().lower()] = value.strip()
    return values


def infer_platform_from_cfg(cfg_values: dict[str, str]) -> str | None:
    raw = " ".join(cfg_values.values())
    if not raw:
        return None
    if "\\" in raw or _WINDOWS_DRIVE_PREFIX.search(raw):
        return "windows"
    if "/" in raw:
        return "posix"
    return None


def inspect_venv(venv_dir: Path = VENV_DIR, platform_key: str | None = None) -> VenvInspection:
    resolved_platform = platform_key or current_platform_key()
    expected_python = venv_python_path(venv_dir, resolved_platform)
    alternate_python = alternate_venv_python_path(venv_dir, resolved_platform)
    pyvenv_cfg = venv_dir / "pyvenv.cfg"
    cfg_values = read_pyvenv_cfg(pyvenv_cfg)
    inferred_cfg_platform = infer_platform_from_cfg(cfg_values)

    if not venv_dir.exists():
        status = "missing"
    elif expected_python.exists():
        status = "ok"
    elif alternate_python.exists() or (
        inferred_cfg_platform is not None and inferred_cfg_platform != resolved_platform
    ):
        status = "cross_platform"
    else:
        status = "missing_python"

    return VenvInspection(
        platform_key=resolved_platform,
        venv_dir=venv_dir,
        expected_python=expected_python,
        alternate_python=alternate_python,
        pyvenv_cfg=pyvenv_cfg,
        cfg_values=cfg_values,
        status=status,
    )
