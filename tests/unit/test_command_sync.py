from bot.app import command_sync
from bot.app.command_sync import format_command_sync_error


def test_format_command_sync_error_mentions_installation_page_for_generic_errors():
    text = format_command_sync_error(RuntimeError("Command sync failed unexpectedly"))

    assert "설치 (Installation)" in text
    assert "Guild Install(서버 설치)" in text


def test_format_command_sync_error_mentions_scope_for_forbidden_like_errors():
    text = format_command_sync_error(RuntimeError("403 Forbidden (error code: 50001): Missing Access"))

    assert "applications.commands" in text
    assert "다시 초대" in text


def test_format_command_sync_error_mentions_token_for_auth_errors():
    text = format_command_sync_error(RuntimeError("401 Unauthorized"))

    assert "DISCORD_BOT_TOKEN" in text


def test_record_command_sync_persists_job_result(monkeypatch):
    saved: dict[str, str] = {}

    def set_job_last_run(job_key: str, status: str, detail: str) -> None:
        saved["job_key"] = job_key
        saved["status"] = status
        saved["detail"] = detail

    monkeypatch.setattr(command_sync, "set_job_last_run", set_job_last_run)

    command_sync.record_command_sync("ok", "3 commands synced")

    assert saved == {"job_key": "command-sync", "status": "ok", "detail": "3 commands synced"}


def test_record_command_sync_fails_open_when_state_write_breaks(monkeypatch, caplog):
    def boom(_job_key: str, _status: str, _detail: str) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(command_sync, "set_job_last_run", boom)

    with caplog.at_level("WARNING"):
        command_sync.record_command_sync("failed", "sync failed")

    assert "상태 저장 실패" in caplog.text
    assert "disk full" in caplog.text
