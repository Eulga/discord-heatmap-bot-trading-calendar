from bot.features.quote import command as quote_command


def test_build_quote_embed_groups_theme_quotes_in_one_card():
    embed = quote_command._build_quote_embed(
        {
            "theme": "반도체",
            "items": [
                {
                    "change": "5.26",
                    "market": "국장",
                    "name": "기가비스",
                    "quoteAvailable": True,
                    "symbol": "420770",
                },
                {
                    "change": "-5.10",
                    "market": "국장",
                    "name": "엘에스일렉트릭",
                    "quoteAvailable": True,
                    "symbol": "010120",
                },
            ],
        }
    )

    assert embed.title == "반도체 시세"
    assert "(420770) 기가비스" in embed.description
    assert "🔴" in embed.description
    assert "+5.26%" in embed.description
    assert "(010120) 엘에스일렉트릭" in embed.description
    assert "🔵" in embed.description
    assert "-5.10%" in embed.description
    assert "급등" not in embed.description
    assert "급락" not in embed.description
    assert embed.color.value == quote_command.QUOTE_EMBED_COLOR


def test_build_quote_embed_handles_empty_theme():
    embed = quote_command._build_quote_embed({"theme": "반도체", "items": []})

    assert embed.title == "반도체 시세"
    assert embed.description == "해당 테마에 등록된 관심종목이 없습니다."


def test_build_stock_embed_shows_single_stock_summary():
    embed = quote_command._build_stock_embed(
        {
            "item": {
                "category": "반도체",
                "change": "5.26",
                "market": "국장",
                "name": "기가비스",
                "news": "반도체 검사장비 수요 확대",
                "price": "42,000",
                "symbol": "420770",
            },
            "query": "기가비스",
        }
    )

    assert embed.title == "(420770) 기가비스"
    assert "반도체 · 국장" in embed.description
    assert "현재가 42,000" in embed.description
    assert "🔴" in embed.description
    assert "+5.26%" in embed.description
    assert embed.footer.text is not None


def test_build_news_embed_lists_theme_news():
    embed = quote_command._build_news_embed(
        {
            "theme": "반도체",
            "items": [
                {
                    "source": "Naver",
                    "symbol": "005930",
                    "time": "오전 9:10",
                    "title": "HBM 수요 기대 지속",
                }
            ],
        }
    )

    assert embed.title == "반도체 뉴스"
    assert "• HBM 수요 기대 지속" in embed.description
    assert "005930 · Naver · 오전 9:10" in embed.description


def test_build_schedule_embed_lists_events():
    embed = quote_command._build_schedule_embed(
        {
            "range": "today",
            "items": [
                {
                    "date": "2026-06-18",
                    "eventType": "economic",
                    "market": "미장",
                    "time": "03:00",
                    "title": "미국 기준금리 발표",
                }
            ],
        }
    )

    assert embed.title == "오늘 일정"
    assert "🌐 매크로 경제" in embed.description
    assert "2026-06-18 03:00 · 미국 기준금리 발표" in embed.description
    assert "미국 기준금리 발표" in embed.description
    assert embed.footer.text == "KST 기준"


def test_build_help_embed_lists_supported_commands():
    embed = quote_command._build_help_embed()

    assert "/시세" in embed.description
    assert "/종목" in embed.description
    assert "/뉴스" in embed.description
    assert "/일정" in embed.description
    assert "일부만 입력" in embed.description
    assert "자동완성" in embed.description


def test_theme_normalizer_ignores_punctuation_and_case():
    assert quote_command._normalize_theme_key("AI·반도체") == quote_command._normalize_theme_key("ai 반도체")
    assert quote_command._normalize_theme_key("AI/반도체") == quote_command._normalize_theme_key("ai반도체")


def test_resolve_theme_input_accepts_similar_theme_name():
    payload = {"themes": [{"count": 2, "name": "AI·반도체"}, {"count": 1, "name": "빅테크"}]}

    resolved, suggestions = quote_command._resolve_theme_input("ai 반도체", payload)

    assert resolved == "AI·반도체"
    assert suggestions == []


def test_resolve_theme_input_returns_suggestions_for_weak_match():
    payload = {"themes": [{"count": 2, "name": "AI·반도체"}, {"count": 1, "name": "빅테크"}]}

    resolved, suggestions = quote_command._resolve_theme_input("에이아이반도체", payload)

    assert resolved is None
    assert suggestions == ["AI·반도체"]


def test_resolve_theme_input_treats_all_as_empty_theme():
    payload = {"themes": [{"count": 2, "name": "AI·반도체"}]}

    resolved, suggestions = quote_command._resolve_theme_input("전체", payload)

    assert resolved == ""
    assert suggestions == []


def test_theme_choices_include_counts_for_autocomplete():
    payload = {"themes": [{"count": 2, "name": "AI·반도체"}, {"count": 1, "name": "빅테크"}]}

    choices = quote_command._theme_choices(payload, "ai")

    assert choices[0] == ("AI·반도체", "AI·반도체", 2)
