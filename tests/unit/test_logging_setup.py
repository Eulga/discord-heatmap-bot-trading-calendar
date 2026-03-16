import logging

from bot.common.logging import _is_marked, setup_logging


def test_setup_logging_writes_runtime_log_file(tmp_path):
    log_path = tmp_path / "logs" / "bot.log"

    setup_logging(log_file_path=log_path, retention_days=3, console_enabled=False)

    logger = logging.getLogger("tests.logging")
    logger.info("file logging smoke test")

    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_path.exists()
    assert "file logging smoke test" in log_path.read_text(encoding="utf-8")


def test_setup_logging_does_not_duplicate_handlers(tmp_path):
    log_path = tmp_path / "logs" / "bot.log"

    setup_logging(log_file_path=log_path, retention_days=3, console_enabled=True)
    first_count = len(logging.getLogger().handlers)

    setup_logging(log_file_path=log_path, retention_days=3, console_enabled=True)
    second_count = len(logging.getLogger().handlers)

    assert second_count == first_count


def test_setup_logging_reconfigures_output_path(tmp_path):
    first_path = tmp_path / "logs-a" / "bot.log"
    second_path = tmp_path / "logs-b" / "bot.log"

    setup_logging(log_file_path=first_path, retention_days=1, console_enabled=False)
    setup_logging(log_file_path=second_path, retention_days=1, console_enabled=False)

    logger = logging.getLogger("tests.logging.reconfig")
    logger.info("reconfigured path")

    for handler in logging.getLogger().handlers:
        handler.flush()

    assert second_path.exists()
    assert "reconfigured path" in second_path.read_text(encoding="utf-8")


def test_setup_logging_closes_replaced_handlers(tmp_path):
    first_path = tmp_path / "logs-a" / "bot.log"
    second_path = tmp_path / "logs-b" / "bot.log"

    setup_logging(log_file_path=first_path, retention_days=1, console_enabled=False)
    old_handler = next(handler for handler in logging.getLogger().handlers if _is_marked(handler))

    setup_logging(log_file_path=second_path, retention_days=1, console_enabled=False)

    assert old_handler._closed is True
