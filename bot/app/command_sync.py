import logging

import discord
from discord import app_commands

from bot.forum.repository import load_state, save_state, set_job_last_run


logger = logging.getLogger(__name__)


def _compact_exception_text(exc: Exception) -> str:
    return " ".join(str(exc).split()) or exc.__class__.__name__


def record_command_sync(status: str, detail: str) -> None:
    try:
        state = load_state()
        set_job_last_run(state, "command-sync", status, detail)
        save_state(state)
    except Exception as exc:
        logger.warning("[command-sync] 상태 저장 실패: %s", _compact_exception_text(exc))


def format_command_sync_error(exc: Exception) -> str:
    detail = _compact_exception_text(exc)
    detail_lower = detail.lower()
    hints: list[str] = []

    if isinstance(exc, app_commands.MissingApplicationID):
        hints.append(
            "봇 토큰이 잘못되었거나 현재 토큰이 애플리케이션과 연결되지 않았습니다. "
            "`DISCORD_BOT_TOKEN`이 개발자 포털의 같은 앱 > `Bot(봇)` 페이지에서 발급한 토큰인지 확인하세요."
        )

    if isinstance(exc, discord.Forbidden) or "missing access" in detail_lower or "missing permissions" in detail_lower:
        hints.append(
            "봇이 서버에 다시 설치되어야 할 수 있습니다. "
            "개발자 포털 `설치 (Installation)`에서 `Guild Install(서버 설치)`가 켜져 있는지 확인하고 다시 초대해 보세요."
        )

    if any(
        token in detail_lower
        for token in (
            "integration_types",
            "installation context",
            "install context",
            "guild install",
            "user install",
            "applications.commands",
            "application command",
        )
    ):
        hints.append(
            "최근 개발자 포털 한글화로 메뉴명이 달라졌습니다. "
            "`설치 (Installation)`에서 필요한 설치 컨텍스트와 `설치 링크 (Install Link)` 설정을 다시 확인하세요."
        )

    if "401" in detail_lower or "unauthorized" in detail_lower:
        hints.append("인증 실패입니다. `.env`의 `DISCORD_BOT_TOKEN` 값과 실제 실행 중인 앱이 일치하는지 확인하세요.")

    if "403" in detail_lower or "forbidden" in detail_lower:
        hints.append(
            "권한 또는 설치 설정 문제일 수 있습니다. "
            "서버에 초대할 때 `bot`과 `applications.commands` 스코프가 포함된 링크를 사용했는지 확인하세요."
        )

    if "50035" in detail_lower or "invalid form body" in detail_lower:
        hints.append("Discord가 명령 스키마를 거부했습니다. 최근 커맨드 이름/설명 길이 또는 옵션 구성을 바꿨다면 함께 점검하세요.")

    if not hints:
        hints.append(
            "개발자 포털 `설치 (Installation)`과 서버 초대 링크를 다시 확인하세요. "
            "한글 UI에서는 `Guild Install(서버 설치)`와 `설치 링크 (Install Link)`가 핵심 확인 지점입니다."
        )

    joined_hints = "\n".join(f"- {hint}" for hint in hints)
    return f"슬래시 커맨드 동기화 실패: {detail}\n{joined_hints}"
