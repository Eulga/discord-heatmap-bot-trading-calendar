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
    state = {"commands": {}, "guilds": {}}
    saved: dict[str, object] = {}

    monkeypatch.setattr(command_sync, "load_state", lambda: state)
    monkeypatch.setattr(command_sync, "save_state", lambda payload: saved.setdefault("state", payload))

    command_sync.record_command_sync("ok", "3 commands synced")

    job = saved["state"]["system"]["job_last_runs"]["command-sync"]
    assert job["status"] == "ok"
    assert job["detail"] == "3 commands synced"
    assert "run_at" in job


def test_record_command_sync_fails_open_when_state_write_breaks(monkeypatch, capsys):
    monkeypatch.setattr(command_sync, "load_state", lambda: {"commands": {}, "guilds": {}})

    def boom(_payload):
        raise OSError("disk full")

    monkeypatch.setattr(command_sync, "save_state", boom)

    command_sync.record_command_sync("failed", "sync failed")

    out = capsys.readouterr().out
    assert "상태 저장 실패" in out
    assert "disk full" in out
