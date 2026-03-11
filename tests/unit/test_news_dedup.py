from bot.forum import repository


def test_news_dedup_state():
    state = {"commands": {}, "guilds": {}}
    key = "abc"
    date_text = "2026-02-13"
    assert repository.is_news_dedup_seen(state, key, date_text) is False
    repository.mark_news_dedup_seen(state, key, date_text)
    assert repository.is_news_dedup_seen(state, key, date_text) is True
