import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import discord

from bot.app.settings import (
    INTEL_API_TIMEOUT_SECONDS,
    STOCK_DASHBOARD_API_BASE_URL,
    STOCK_DASHBOARD_INTERNAL_TOKEN,
    STOCK_DASHBOARD_LOGIN_CHANNEL_ID,
    STOCK_DASHBOARD_WEB_BASE_URL,
    TIMEZONE,
)

logger = logging.getLogger(__name__)

LOGIN_BUTTON_CUSTOM_ID = "stock_dashboard:login"
REGISTER_BUTTON_CUSTOM_ID = "stock_dashboard:register"
LOGIN_PANEL_TITLE = "Stock Board 로그인"
LOGIN_EMBED_COLOR = 0x14B8A6


class DashboardLoginError(RuntimeError):
    pass


def _dashboard_base_url() -> str:
    return (STOCK_DASHBOARD_WEB_BASE_URL or STOCK_DASHBOARD_API_BASE_URL).rstrip("/")


def _dashboard_public_base_url() -> str:
    base_url = STOCK_DASHBOARD_WEB_BASE_URL.rstrip("/")

    if not base_url:
        raise DashboardLoginError("대시보드 공개 주소가 설정되어 있지 않습니다.")

    if not base_url.startswith("https://"):
        raise DashboardLoginError("대시보드 공개 주소는 https 주소로 설정해야 합니다.")

    return base_url


def _format_expires_at(expires_at: int | float | None) -> str:
    if not expires_at:
        return "5분 후"

    try:
        timestamp = float(expires_at) / 1000
        return datetime.fromtimestamp(timestamp, TIMEZONE).strftime("%H:%M")
    except (OSError, OverflowError, ValueError):
        return "5분 후"


def _parse_dashboard_error(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:
        return f"대시보드 API 오류가 발생했습니다. ({exc.code})"

    message = payload.get("error") if isinstance(payload, dict) else None
    return str(message or f"대시보드 API 오류가 발생했습니다. ({exc.code})")


def _request_dashboard_auth_sync(path: str, discord_user_id: int, display_name: str, username: str) -> dict[str, Any]:
    if not STOCK_DASHBOARD_API_BASE_URL or not STOCK_DASHBOARD_INTERNAL_TOKEN:
        raise DashboardLoginError("대시보드 내부 API 설정이 없습니다.")

    if not _dashboard_base_url():
        raise DashboardLoginError("대시보드 웹 주소가 설정되어 있지 않습니다.")

    request = Request(
        f"{STOCK_DASHBOARD_API_BASE_URL.rstrip('/')}{path}",
        data=json.dumps(
            {
                "discordDisplayName": display_name,
                "discordUserId": str(discord_user_id),
                "discordUsername": username,
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "discord-heatmap-bot/1.0",
            "x-internal-token": STOCK_DASHBOARD_INTERNAL_TOKEN,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=INTEL_API_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise DashboardLoginError(_parse_dashboard_error(exc)) from exc
    except URLError as exc:
        raise DashboardLoginError("대시보드 API에 연결할 수 없습니다.") from exc

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise DashboardLoginError("대시보드 응답이 올바르지 않습니다.")

    return data


def _register_dashboard_user_sync(discord_user_id: int, display_name: str, username: str) -> dict[str, Any]:
    return _request_dashboard_auth_sync("/api/internal/auth/discord-register", discord_user_id, display_name, username)


def _issue_login_token_sync(discord_user_id: int, display_name: str, username: str) -> dict[str, Any]:
    data = _request_dashboard_auth_sync("/api/internal/auth/login-token", discord_user_id, display_name, username)
    if not data.get("token"):
        raise DashboardLoginError("대시보드 로그인 응답이 올바르지 않습니다.")

    return data


def _build_login_url(token: str) -> str:
    return f"{_dashboard_public_base_url()}/login/claim?token={quote(token)}"


class LoginLinkView(discord.ui.View):
    def __init__(self, url: str) -> None:
        super().__init__(timeout=300)
        self.add_item(discord.ui.Button(label="대시보드 열기", style=discord.ButtonStyle.link, url=url))


class DashboardLoginView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="계정 등록", style=discord.ButtonStyle.secondary, custom_id=REGISTER_BUTTON_CUSTOM_ID)
    async def register_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            payload = await asyncio.to_thread(
                _register_dashboard_user_sync,
                interaction.user.id,
                interaction.user.display_name,
                interaction.user.name,
            )
        except DashboardLoginError as exc:
            logger.warning(
                "[dashboard-login] registration failed user=%s reason=%s",
                getattr(interaction.user, "id", None),
                exc,
            )
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        except Exception:
            logger.exception("[dashboard-login] unexpected registration failure user=%s", interaction.user.id)
            await interaction.followup.send("계정을 등록하지 못했습니다. 잠시 후 다시 시도해 주세요.", ephemeral=True)
            return

        user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
        name = str(user.get("name") or interaction.user.display_name)
        already_registered = bool(payload.get("alreadyRegistered"))
        message = (
            f"{name}님은 이미 등록되어 있습니다. 이제 로그인 버튼을 눌러 주세요."
            if already_registered
            else f"{name}님 계정을 등록했습니다. 이제 로그인 버튼을 눌러 주세요."
        )
        await interaction.followup.send(message, ephemeral=True)

    @discord.ui.button(label="로그인", style=discord.ButtonStyle.primary, custom_id=LOGIN_BUTTON_CUSTOM_ID)
    async def login_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            payload = await asyncio.to_thread(
                _issue_login_token_sync,
                interaction.user.id,
                interaction.user.display_name,
                interaction.user.name,
            )
        except DashboardLoginError as exc:
            logger.warning(
                "[dashboard-login] token issue failed user=%s reason=%s",
                getattr(interaction.user, "id", None),
                exc,
            )
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        except Exception:
            logger.exception("[dashboard-login] unexpected token issue failure user=%s", interaction.user.id)
            await interaction.followup.send("로그인 링크를 발급하지 못했습니다. 잠시 후 다시 시도해 주세요.", ephemeral=True)
            return

        token = str(payload.get("token") or "")
        expires_at = payload.get("expiresAt")
        try:
            login_url = _build_login_url(token)
        except DashboardLoginError as exc:
            logger.warning(
                "[dashboard-login] public login url invalid user=%s reason=%s",
                getattr(interaction.user, "id", None),
                exc,
            )
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
        name = str(user.get("name") or interaction.user.display_name)
        expires_text = _format_expires_at(expires_at if isinstance(expires_at, (int, float)) else None)

        embed = discord.Embed(
            title=f"{name}님 입장 링크",
            description=f"아래 버튼을 눌러 대시보드에 로그인하세요.\n만료 시각: {expires_text}",
            color=LOGIN_EMBED_COLOR,
        )
        embed.set_footer(text="이 링크는 1회만 사용할 수 있습니다.")

        try:
            await interaction.followup.send(embed=embed, view=LoginLinkView(login_url), ephemeral=True)
        except discord.HTTPException:
            logger.exception("[dashboard-login] login link button response failed user=%s", interaction.user.id)
            await interaction.followup.send(f"로그인 링크를 버튼으로 표시하지 못했습니다.\n{login_url}", ephemeral=True)


def _login_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title=LOGIN_PANEL_TITLE,
        description="처음이면 계정 등록을 먼저 누르고, 이후 로그인 버튼으로 5분짜리 입장 링크를 발급받습니다.",
        color=LOGIN_EMBED_COLOR,
    )
    embed.set_footer(text="이미 등록된 사용자는 다시 등록되지 않습니다.")
    return embed


async def _find_existing_panel(channel: discord.abc.Messageable, bot_user_id: int) -> discord.Message | None:
    history = getattr(channel, "history", None)
    if history is None:
        return None

    async for message in history(limit=50):
        if message.author.id != bot_user_id:
            continue
        if any(embed.title == LOGIN_PANEL_TITLE for embed in message.embeds):
            return message
    return None


async def ensure_dashboard_login_panel(client: discord.Client) -> None:
    if STOCK_DASHBOARD_LOGIN_CHANNEL_ID is None:
        return

    channel = client.get_channel(STOCK_DASHBOARD_LOGIN_CHANNEL_ID)
    if channel is None:
        try:
            channel = await client.fetch_channel(STOCK_DASHBOARD_LOGIN_CHANNEL_ID)
        except Exception:
            logger.exception("[dashboard-login] login channel fetch failed channel=%s", STOCK_DASHBOARD_LOGIN_CHANNEL_ID)
            return

    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        logger.warning("[dashboard-login] login channel is not a text channel channel=%s", STOCK_DASHBOARD_LOGIN_CHANNEL_ID)
        return

    bot_user_id = getattr(client.user, "id", None)
    if not isinstance(bot_user_id, int):
        return

    embed = _login_panel_embed()
    view = DashboardLoginView()
    existing = await _find_existing_panel(channel, bot_user_id)

    if existing is not None:
        await existing.edit(embed=embed, view=view)
        logger.info("[dashboard-login] login panel refreshed channel=%s message=%s", channel.id, existing.id)
        return

    message = await channel.send(embed=embed, view=view)
    logger.info("[dashboard-login] login panel created channel=%s message=%s", channel.id, message.id)


def register(client: discord.Client) -> None:
    client.add_view(DashboardLoginView())
