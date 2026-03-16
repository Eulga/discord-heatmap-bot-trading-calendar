import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from bot.app.settings import LOG_CONSOLE_ENABLED, LOG_FILE_PATH, LOG_RETENTION_DAYS, TIMEZONE

_HANDLER_MARKER = "_discord_heatmap_log_handler"
_CONFIG_ATTR = "_discord_heatmap_logging_config"


class ZonedFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.fromtimestamp(record.created, TIMEZONE)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(timespec="seconds")


def _build_formatter() -> logging.Formatter:
    return ZonedFormatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _mark_handler(handler: logging.Handler) -> logging.Handler:
    setattr(handler, _HANDLER_MARKER, True)
    return handler


def _is_marked(handler: logging.Handler) -> bool:
    return bool(getattr(handler, _HANDLER_MARKER, False))


def setup_logging(
    log_file_path: Path = LOG_FILE_PATH,
    retention_days: int = LOG_RETENTION_DAYS,
    console_enabled: bool = LOG_CONSOLE_ENABLED,
) -> logging.Logger:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    desired_config = (str(log_file_path), retention_days, console_enabled)
    current_config = getattr(root_logger, _CONFIG_ATTR, None)
    if current_config == desired_config and any(_is_marked(handler) for handler in root_logger.handlers):
        return root_logger

    root_logger.handlers = [handler for handler in root_logger.handlers if not _is_marked(handler)]

    formatter = _build_formatter()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = _mark_handler(
        TimedRotatingFileHandler(
            filename=log_file_path,
            when="midnight",
            interval=1,
            backupCount=max(retention_days, 1),
            encoding="utf-8",
        )
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    if console_enabled:
        console_handler = _mark_handler(logging.StreamHandler())
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    setattr(root_logger, _CONFIG_ATTR, desired_config)
    return root_logger
