from datetime import datetime
from zoneinfo import ZoneInfo

from bot.features.news import policy
from bot.intel.providers.news import NewsItem

KST = ZoneInfo("Asia/Seoul")


def _make_item(region: str, index: int) -> NewsItem:
    return NewsItem(
        title=f"{region} 시장 핵심 뉴스 headline {index} with extra context for trimming checks",
        link=f"https://example.com/{region}/article/{index}/with/a/very/long/path/for/discord/body/limit",
        source=f"{region}-source-{index}.example.com",
        published_at=datetime(2026, 3, 19, 7, 30, tzinfo=KST),
        region=region,
    )


def test_build_news_body_stays_within_discord_limit():
    domestic = [_make_item("domestic", index) for index in range(20)]
    global_items = [_make_item("global", index) for index in range(20)]

    body = policy.build_body("2026-03-19 07:30:00", domestic, global_items)

    assert len(body) <= policy.DISCORD_MESSAGE_LIMIT
    assert "[국내]" in body
    assert "[해외]" in body
    assert body.count("\n- ") + body.startswith("- ") < 40


def test_build_news_body_keeps_placeholders_when_empty():
    body = policy.build_body("2026-03-19 07:30:00", [], [])

    assert "- (데이터 없음)" in body
    assert len(body) <= policy.DISCORD_MESSAGE_LIMIT


def test_build_region_body_stays_within_discord_limit():
    domestic = [_make_item("domestic", index) for index in range(20)]

    body = policy.build_region_body("2026-03-19 07:30:00", "domestic", domestic)

    assert len(body) <= policy.DISCORD_MESSAGE_LIMIT
    assert "[국내]" in body
    assert "[해외]" not in body


def test_build_region_title_uses_region_label(monkeypatch):
    monkeypatch.setattr(policy, "date_key", lambda dt=None: "2026-02-13")

    assert policy.build_post_title("domestic") == "[2026-02-13 국내 경제 뉴스 브리핑]"
    assert policy.build_post_title("global") == "[2026-02-13 해외 경제 뉴스 브리핑]"
