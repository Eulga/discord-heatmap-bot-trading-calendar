from datetime import datetime
from zoneinfo import ZoneInfo

from bot.features.news import trend_policy
from bot.intel.providers.news import NewsItem, ThemeBrief, TrendThemeReport

KST = ZoneInfo("Asia/Seoul")


def _make_item(title: str, source: str, minute: int) -> NewsItem:
    return NewsItem(
        title=title,
        link=f"https://example.com/{title}",
        source=source,
        published_at=datetime(2026, 3, 19, 7, minute, tzinfo=KST),
        region="domestic",
    )


def test_build_trend_region_messages_splits_by_theme_block():
    themes = tuple(
        ThemeBrief(
            theme_name=f"테마 {index}",
            region="domestic",
            score=40 - index,
            reason_tags=("기사 4건", "3개 소스"),
            representative_items=(
                _make_item(f"대표 기사 {index}-1", f"source-{index}-1", 10 + index),
                _make_item(f"대표 기사 {index}-2", f"source-{index}-2", 20 + index),
            ),
            article_count=4,
            source_count=3,
        )
        for index in range(1, 4)
    )

    messages = trend_policy.build_trend_region_messages("domestic", themes, max_chars=220)

    assert len(messages) >= 2
    assert all(message.startswith("[국내 트렌드 테마]") for message in messages)
    assert all(len(message) <= 220 for message in messages)


def test_build_trend_region_messages_use_plain_theme_title_and_article_prefix():
    theme = ThemeBrief(
        theme_name="반도체",
        region="domestic",
        score=52,
        reason_tags=("기사 4건", "3개 소스"),
        representative_items=(
            _make_item("삼성전자 HBM 수주 확대", "source-1", 10),
            _make_item("SK하이닉스 공급 계약", "source-2", 20),
        ),
        article_count=4,
        source_count=3,
    )

    message = trend_policy.build_trend_region_messages("domestic", (theme,))[0]

    assert "[국내 트렌드 테마]" in message
    assert "\n반도체\n" in message
    assert "\n1. 반도체\n" not in message
    assert "근거: 기사 4건 | 3개 소스" in message
    assert "기사: 삼성전자 HBM 수주 확대" in message


def test_build_trend_starter_body_summarizes_regions():
    report = TrendThemeReport(
        generated_at=datetime(2026, 3, 19, 7, 30, tzinfo=KST),
        themes_by_region={
            "domestic": (
                ThemeBrief(
                    theme_name="반도체",
                    region="domestic",
                    score=52,
                    reason_tags=("기사 4건", "3개 소스"),
                    representative_items=(),
                    article_count=4,
                    source_count=3,
                ),
            ),
            "global": (),
        },
    )

    body = trend_policy.build_trend_starter_body("2026-03-19 07:30:00", report)

    assert "국내 테마 1개 | 해외 테마 0개" in body
    assert "반도체" in body
    assert "(유의미한 테마 부족)" in body


def test_build_trend_region_messages_caps_oversized_single_theme_block():
    long_title = "매우 긴 헤드라인 " * 30
    long_link = "https://example.com/" + ("segment-" * 40)
    theme = ThemeBrief(
        theme_name="반도체",
        region="domestic",
        score=88,
        reason_tags=("기사 9건", "6개 소스", "대표 종목 다수", "추가 근거 " * 20),
        representative_items=(
            NewsItem(
                title=long_title,
                link=long_link,
                source="source-1",
                published_at=datetime(2026, 3, 19, 7, 10, tzinfo=KST),
                region="domestic",
            ),
            NewsItem(
                title=long_title,
                link=long_link,
                source="source-2",
                published_at=datetime(2026, 3, 19, 7, 20, tzinfo=KST),
                region="domestic",
            ),
        ),
        article_count=9,
        source_count=6,
    )

    messages = trend_policy.build_trend_region_messages("domestic", (theme,), max_chars=180)

    assert messages
    assert all(len(message) <= 180 for message in messages)
