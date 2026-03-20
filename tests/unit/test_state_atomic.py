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


def test_state_migrates_legacy_state_file(tmp_path, monkeypatch):
    state_path = tmp_path / "state" / "state.json"
    legacy_path = tmp_path / "heatmaps" / "state.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text('{"commands": {}, "guilds": {"1": {"forum_channel_id": 123}}}', encoding="utf-8")
    monkeypatch.setattr(repository, "STATE_FILE", state_path)
    monkeypatch.setattr(repository, "LEGACY_STATE_FILE", legacy_path)

    loaded = repository.load_state()

    assert loaded["guilds"]["1"]["forum_channel_id"] == 123
    assert state_path.exists()
    assert not legacy_path.exists()
