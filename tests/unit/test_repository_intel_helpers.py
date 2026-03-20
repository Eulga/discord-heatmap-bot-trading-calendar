from bot.forum import repository


def test_watch_baseline_roundtrip():
    state = {"commands": {}, "guilds": {}}
    assert repository.get_watch_baseline(state, 1, "005930") is None
    repository.set_watch_baseline(state, 1, "005930", 70000.0, "2026-02-13T09:00:00+09:00")
    assert repository.get_watch_baseline(state, 1, "005930") == 70000.0


def test_news_dedup_cleanup_keeps_recent():
    state = {"commands": {}, "guilds": {}}
    for i in range(1, 11):
        date = f"2026-02-{i:02d}"
        repository.mark_news_dedup_seen(state, f"key-{i}", date)

    repository.cleanup_news_dedup(state, keep_recent_days=3)
    dedup = repository.get_system_state(state)["news_dedup"]
    assert sorted(dedup.keys()) == ["2026-02-08", "2026-02-09", "2026-02-10"]
