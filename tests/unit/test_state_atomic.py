from bot.forum import repository


def test_state_atomic_roundtrip(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(repository, "STATE_FILE", state_path)

    data = {"commands": {"kheatmap": {"daily_posts_by_guild": {}, "last_images": {}}}, "guilds": {}}
    repository.save_state(data)

    loaded = repository.load_state()
    assert "commands" in loaded
    assert "kheatmap" in loaded["commands"]
    assert "guilds" in loaded


def test_state_recover_on_invalid_json(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    state_path.write_text("{invalid", encoding="utf-8")
    monkeypatch.setattr(repository, "STATE_FILE", state_path)

    loaded = repository.load_state()
    assert loaded == {"commands": {}, "guilds": {}}
