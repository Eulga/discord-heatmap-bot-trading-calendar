from __future__ import annotations

from datetime import timedelta

from bot.app.settings import WATCH_ALERT_COOLDOWN_MINUTES, WATCH_ALERT_THRESHOLD_PCT
from bot.common.clock import now_kst
from bot.forum.repository import get_watch_cooldown_hit, set_watch_cooldown_hit


def _signal_direction(change_pct: float) -> str | None:
    if change_pct >= WATCH_ALERT_THRESHOLD_PCT:
        return "up"
    if change_pct <= -WATCH_ALERT_THRESHOLD_PCT:
        return "down"
    return None


def evaluate_watch_signal(
    state,
    guild_id: int,
    symbol: str,
    base_price: float,
    current_price: float,
) -> tuple[bool, str, float]:
    change_pct = ((current_price - base_price) / base_price) * 100 if base_price > 0 else 0.0
    direction = _signal_direction(change_pct)
    if direction is None:
        return False, "", change_pct

    cooldown_key = f"{symbol.upper()}:{direction}"
    hit_at = get_watch_cooldown_hit(state, guild_id, cooldown_key)
    now = now_kst()
    if hit_at:
        from datetime import datetime

        try:
            last = datetime.fromisoformat(hit_at)
            if last.tzinfo is None:
                last = last.replace(tzinfo=now.tzinfo)
            if now - last <= timedelta(minutes=WATCH_ALERT_COOLDOWN_MINUTES):
                return False, direction, change_pct
        except ValueError:
            pass

    set_watch_cooldown_hit(state, guild_id, cooldown_key, now.isoformat())
    return True, direction, change_pct
