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
