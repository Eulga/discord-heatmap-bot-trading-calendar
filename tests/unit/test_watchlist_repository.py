from bot.forum import repository


def test_watchlist_add_remove_list():
    state = {"commands": {}, "guilds": {}}

    assert repository.add_watch_symbol(state, 1, "005930") is True
    assert repository.add_watch_symbol(state, 1, "005930") is False
    assert repository.list_watch_symbols(state, 1) == ["005930"]

    assert repository.remove_watch_symbol(state, 1, "005930") is True
    assert repository.remove_watch_symbol(state, 1, "005930") is False
    assert repository.list_watch_symbols(state, 1) == []
