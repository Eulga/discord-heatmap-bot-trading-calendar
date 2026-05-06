import logging

import discord
from discord import app_commands

from bot.app.settings import (
    EOD_SUMMARY_ENABLED,
    INSTRUMENT_REGISTRY_REFRESH_ENABLED,
    INSTRUMENT_REGISTRY_REFRESH_TIME,
    KIS_APP_KEY,
    KIS_APP_SECRET,
    MASSIVE_API_KEY,
    MARKETAUX_API_TOKEN,
    MARKET_DATA_PROVIDER_KIND,
    NEWS_COLLECTION_CLOSE_ENABLED,
    NEWS_COLLECTION_CLOSE_TIME,
    NEWS_COLLECTION_ENABLED,
    NEWS_COLLECTION_TIME,
    NEWS_DYNAMIC_RANKING_ENABLED,
    NEWS_PROVIDER_KIND,
    NAVER_NEWS_CLIENT_ID,
    NAVER_NEWS_CLIENT_SECRET,
    OPENFIGI_API_KEY,
    TWELVEDATA_API_KEY,
)
from bot.forum.state_store import get_job_last_runs, get_provider_statuses
from bot.intel.instrument_registry import registry_status

_LEGACY_PROVIDER_KEYS = {
    "market_data_provider": "kis_quote",
    "polygon_reference": "massive_reference",
}

logger = logging.getLogger(__name__)


def _interaction_user_id(interaction: discord.Interaction) -> int | None:
    return getattr(getattr(interaction, "user", None), "id", None)


def _provider_row(status: str, message: str, updated_at: str = "") -> dict[str, str]:
    return {"status": status, "message": message, "updated_at": updated_at}


def _fmt_status(value) -> str:
    if isinstance(value, bool):
        return "ok" if value else "failed"
    return str(value or "-")


def _fmt_dict_rows(value: dict[str, dict]) -> str:
    if not value:
        return "- (기록 없음)"
    rows = []
    for key, item in sorted(value.items()):
        status = _fmt_status(item.get("status", item.get("ok", "-")))
        detail = item.get("detail", item.get("message", ""))
        ts = item.get("run_at", item.get("updated_at", ""))
        rows.append(f"- {key}: {status} | {detail} | {ts}")
    return "\n".join(rows)


def _default_job_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    rows["news_collection"] = {
        "status": "scheduled" if NEWS_COLLECTION_ENABLED else "paused",
        "detail": f"daily-collection {NEWS_COLLECTION_TIME} KST" if NEWS_COLLECTION_ENABLED else "news-collection-disabled",
        "run_at": "",
    }
    rows["news_collection_close"] = {
        "status": "scheduled" if NEWS_COLLECTION_ENABLED and NEWS_COLLECTION_CLOSE_ENABLED else "paused",
        "detail": (
            f"daily-close-collection {NEWS_COLLECTION_CLOSE_TIME} KST"
            if NEWS_COLLECTION_ENABLED and NEWS_COLLECTION_CLOSE_ENABLED
            else "news-close-collection-disabled"
        ),
        "run_at": "",
    }
    if not EOD_SUMMARY_ENABLED:
        rows["eod_summary"] = {"status": "paused", "detail": "eod-summary-paused", "run_at": ""}
    rows["instrument_registry_refresh"] = {
        "status": "scheduled" if INSTRUMENT_REGISTRY_REFRESH_ENABLED else "paused",
        "detail": (
            f"daily-refresh {INSTRUMENT_REGISTRY_REFRESH_TIME} KST"
            if INSTRUMENT_REGISTRY_REFRESH_ENABLED
            else "instrument-registry-refresh-disabled"
        ),
        "run_at": "",
    }
    return rows


def _default_provider_rows() -> dict[str, dict[str, str]]:
    kis_status = "configured" if MARKET_DATA_PROVIDER_KIND == "kis" and KIS_APP_KEY and KIS_APP_SECRET else "disabled"
    kis_message = "selected=kis" if MARKET_DATA_PROVIDER_KIND == "kis" else f"selected={MARKET_DATA_PROVIDER_KIND}"
    if MARKET_DATA_PROVIDER_KIND == "kis" and not (KIS_APP_KEY and KIS_APP_SECRET):
        kis_message = "selected=kis credentials-missing"
    rows = {
        "instrument_registry": registry_status(),
        "kis_quote": _provider_row(
            kis_status,
            kis_message,
        ),
        "massive_reference": _provider_row(
            "configured" if MASSIVE_API_KEY else "disabled",
            "us reference + fallback quote",
        ),
        "twelvedata_reference": _provider_row(
            "configured" if TWELVEDATA_API_KEY else "disabled",
            "global reference + future fx/eod slot",
        ),
        "openfigi_mapping": _provider_row(
            "configured" if OPENFIGI_API_KEY else "disabled",
            "offline reconciliation only",
        ),
    }
    if NEWS_PROVIDER_KIND in {"naver", "hybrid"}:
        rows["naver_news"] = _provider_row(
            "configured" if NAVER_NEWS_CLIENT_ID and NAVER_NEWS_CLIENT_SECRET else "disabled",
            "domestic news provider",
        )
    if NEWS_PROVIDER_KIND in {"marketaux", "hybrid"}:
        rows["marketaux_news"] = _provider_row(
            "configured" if MARKETAUX_API_TOKEN else "disabled",
            "global finance news provider",
        )
    if NEWS_DYNAMIC_RANKING_ENABLED:
        rows["kis_news_ranking"] = _provider_row(
            "configured" if KIS_APP_KEY and KIS_APP_SECRET else "disabled",
            "dynamic news query universe" if KIS_APP_KEY and KIS_APP_SECRET else "dynamic-ranking-credentials-missing",
        )
    else:
        rows["kis_news_ranking"] = _provider_row("paused", "dynamic-ranking-disabled")
    if not EOD_SUMMARY_ENABLED:
        rows["eod_provider"] = _provider_row("paused", "eod-summary-paused")
    return rows


def _merge_defaults(actual: dict[str, dict], defaults: dict[str, dict]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for key, value in actual.items():
        normalized_key = _LEGACY_PROVIDER_KEYS.get(key, key)
        if normalized_key not in merged or normalized_key == key:
            merged[normalized_key] = value
    for key, value in defaults.items():
        merged.setdefault(key, value)
    return merged


def register(tree: app_commands.CommandTree, client) -> None:
    @tree.command(name="health", description="봇 상태 요약")
    async def health_command(interaction: discord.Interaction) -> None:
        runs = _merge_defaults(get_job_last_runs(), _default_job_rows())
        providers = _merge_defaults(get_provider_statuses(), _default_provider_rows())
        text = "\n".join(["[Jobs]", _fmt_dict_rows(runs), "", "[Providers]", _fmt_dict_rows(providers)])
        logger.info("[command] health requested guild=%s user=%s", interaction.guild_id, _interaction_user_id(interaction))
        await interaction.response.send_message(text, ephemeral=True)

    @tree.command(name="last-run", description="작업별 마지막 실행 결과")
    async def last_run_command(interaction: discord.Interaction) -> None:
        runs = _merge_defaults(get_job_last_runs(), _default_job_rows())
        logger.info("[command] last-run requested guild=%s user=%s", interaction.guild_id, _interaction_user_id(interaction))
        await interaction.response.send_message(_fmt_dict_rows(runs), ephemeral=True)

    @tree.command(name="source-status", description="데이터 소스 상태 조회")
    async def source_status_command(interaction: discord.Interaction) -> None:
        providers = _merge_defaults(get_provider_statuses(), _default_provider_rows())
        logger.info("[command] source-status requested guild=%s user=%s", interaction.guild_id, _interaction_user_id(interaction))
        await interaction.response.send_message(_fmt_dict_rows(providers), ephemeral=True)
