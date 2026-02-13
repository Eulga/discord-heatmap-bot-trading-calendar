from pathlib import Path

from bot.common.errors import CaptureValidationError


def ensure_capture_file(path: Path, min_size_bytes: int) -> None:
    if not path.exists():
        raise CaptureValidationError("screenshot file was not created")
    size = path.stat().st_size
    if size < min_size_bytes:
        raise CaptureValidationError(f"screenshot looks incomplete (too small: {size} bytes)")
