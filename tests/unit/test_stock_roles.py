from bot.features.stock_roles.service import (
    StockRoleTarget,
    _stock_role_targets_from_state,
    _subscription_option_label,
    chunk_stock_role_targets,
    stock_role_key,
    stock_role_mentions_for_items,
    stock_role_mentions_for_text,
    stock_role_name,
    stale_stock_role_targets,
    unused_stock_role_name,
)
from bot.forum.repository import get_guild_stock_role_ids, set_guild_stock_role_id


def test_stock_role_key_uses_market_prefix():
    assert stock_role_key("005930", "국장") == "KRX:005930"
    assert stock_role_key("aapl", "미장") == "US:AAPL"


def test_chunk_stock_role_targets_splits_discord_select_limit():
    targets = [
        StockRoleTarget(key=f"KRX:{index}", symbol=str(index), name=f"종목{index}", market="국장", category="반도체")
        for index in range(30)
    ]

    chunks = chunk_stock_role_targets(targets)

    assert [len(chunk) for chunk in chunks] == [25, 5]


def test_stock_role_mentions_match_symbol_and_name():
    state = {
        "guilds": {
            "1": {
                "stock_role_targets": {
                    "KRX:080220": {
                        "role_id": 10,
                        "symbol": "080220",
                        "name": "제주반도체",
                        "market": "국장",
                        "category": "반도체",
                    },
                    "US:AAPL": {
                        "role_id": 20,
                        "symbol": "AAPL",
                        "name": "Apple",
                        "market": "미장",
                        "category": "빅테크",
                    },
                }
            }
        }
    }

    assert stock_role_mentions_for_text(state, 1, "제주반도체 전일 대비 +5.4%") == "<@&10>"
    assert stock_role_mentions_for_text(state, 1, "AAPL beats estimates") == "<@&20>"


def test_stock_role_mentions_for_items_combines_news_text():
    state = {
        "guilds": {
            "1": {
                "stock_role_targets": {
                    "KRX:000660": {
                        "role_id": 30,
                        "symbol": "000660",
                        "name": "SK하이닉스",
                        "market": "국장",
                        "category": "AI·반도체",
                    }
                }
            }
        }
    }

    mentions = stock_role_mentions_for_items(
        state,
        1,
        [{"title": "HBM 공급 계약 확대", "summary": "SK하이닉스 수혜 기대"}],
    )

    assert mentions == "<@&30>"


def test_stock_role_name_keeps_symbol_for_disambiguation():
    target = StockRoleTarget(key="KRX:080220", symbol="080220", name="제주반도체", market="국장", category="반도체")

    role_name = stock_role_name(target)
    assert "제주반도체" in role_name
    assert "080220" in role_name


def test_set_guild_stock_role_id_persists_into_state():
    state = {"commands": {}, "guilds": {"1": {}}}

    set_guild_stock_role_id(state, 1, "KRX:080220", 123)

    assert state["guilds"]["1"]["stock_role_ids"] == {"KRX:080220": 123}
    assert get_guild_stock_role_ids(state, 1) == {"KRX:080220": 123}


def test_unused_stock_role_name_is_idempotent():
    assert unused_stock_role_name("종목 제주반도체 080220") == "미사용 종목 제주반도체 080220"
    assert unused_stock_role_name("미사용 종목 제주반도체 080220") == "미사용 종목 제주반도체 080220"


def test_stale_stock_role_targets_excludes_active_keys():
    previous_targets = {
        "KRX:080220": {"name": "제주반도체", "role_id": 10},
        "US:AAPL": {"name": "Apple", "role_id": 20},
    }
    role_ids = {"KRX:080220": 10, "US:AAPL": 20, "KRX:000660": 30}

    stale_targets = stale_stock_role_targets(previous_targets, role_ids, {"US:AAPL"})

    assert stale_targets == {
        "KRX:000660": {"role_id": 30},
        "KRX:080220": {"name": "제주반도체", "role_id": 10},
    }


def test_subscription_option_label_marks_current_subscription():
    target = StockRoleTarget(key="KRX:080220", symbol="080220", name="제주반도체", market="국장", category="반도체")

    assert _subscription_option_label(target, True).startswith("✅ ")
    assert _subscription_option_label(target, False).startswith("▫ ")


def test_stock_role_targets_from_state_restores_active_targets():
    state = {
        "guilds": {
            "1": {
                "stock_role_targets": {
                    "KRX:080220": {
                        "category": "반도체",
                        "market": "국장",
                        "name": "제주반도체",
                        "role_id": 123,
                        "symbol": "080220",
                    }
                }
            }
        }
    }

    targets = _stock_role_targets_from_state(state, 1)

    assert targets == [
        StockRoleTarget(
            key="KRX:080220",
            symbol="080220",
            name="제주반도체",
            market="국장",
            category="반도체",
            role_id=123,
        )
    ]
