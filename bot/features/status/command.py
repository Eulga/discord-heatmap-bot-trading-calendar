import discord
from discord import app_commands

from bot.forum.repository import get_job_last_runs, get_provider_statuses, load_state


def _fmt_dict_rows(value: dict[str, dict]) -> str:
    if not value:
        return "- (기록 없음)"
    rows = []
    for key, item in sorted(value.items()):
        status = item.get("status", item.get("ok", "-"))
        detail = item.get("detail", item.get("message", ""))
        ts = item.get("run_at", item.get("updated_at", ""))
        rows.append(f"- {key}: {status} | {detail} | {ts}")
    return "\n".join(rows)


def register(tree: app_commands.CommandTree, client) -> None:
    @tree.command(name="health", description="봇 상태 요약")
    async def health_command(interaction: discord.Interaction) -> None:
        state = load_state()
        runs = get_job_last_runs(state)
        providers = get_provider_statuses(state)
        text = "\n".join(["[Jobs]", _fmt_dict_rows(runs), "", "[Providers]", _fmt_dict_rows(providers)])
        await interaction.response.send_message(text, ephemeral=True)

    @tree.command(name="last-run", description="작업별 마지막 실행 결과")
    async def last_run_command(interaction: discord.Interaction) -> None:
        state = load_state()
        runs = get_job_last_runs(state)
        await interaction.response.send_message(_fmt_dict_rows(runs), ephemeral=True)

    @tree.command(name="source-status", description="데이터 소스 상태 조회")
    async def source_status_command(interaction: discord.Interaction) -> None:
        state = load_state()
        providers = get_provider_statuses(state)
        await interaction.response.send_message(_fmt_dict_rows(providers), ephemeral=True)
