import json
import os

os.environ.setdefault("DISCORD_BOT_TOKEN", "test-token")

from bot.features.news import feedback


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return None


def test_build_news_feedback_view_uses_article_keys() -> None:
    view = feedback.build_news_feedback_view(
        [
            {"articleKey": "naver:1", "source": "Naver", "title": "삼성전자 공급계약"},
            {"id": "missing-key", "source": "Naver", "title": "articleKey 없는 뉴스"},
        ]
    )

    assert view is not None
    assert len(view.children) == 3
    for child in view.children:
        assert child.options[0].value == "naver:1"
        assert child.options[0].label.startswith("1. 삼성전자")
        assert child.placeholder in {"유용함", "불필요", "중복"}


def test_register_persistent_news_feedback_view_adds_restart_safe_selects() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.views = []

        def add_view(self, view) -> None:
            self.views.append(view)

    client = FakeClient()

    feedback.register_persistent_news_feedback_view(client)

    assert len(client.views) == 1
    view = client.views[0]
    assert view.timeout is None
    assert len(view.children) == 3
    assert {child.custom_id for child in view.children} == {
        "news-feedback:duplicate",
        "news-feedback:noise",
        "news-feedback:useful",
    }
    assert all(child.placeholder in {"유용함", "불필요", "중복"} for child in view.children)
    assert all(child.max_values == feedback.MAX_NEWS_FEEDBACK_OPTIONS for child in view.children)
    assert all(len(child.options) == feedback.MAX_NEWS_FEEDBACK_OPTIONS for child in view.children)


def test_record_news_feedback_sync_posts_collector_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(feedback, "STOCK_DATA_CONTROLLER_API_BASE_URL", "http://collector.local")
    monkeypatch.setattr(feedback, "STOCK_DATA_CONTROLLER_INTERNAL_TOKEN", "collector-token")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(feedback, "urlopen", fake_urlopen)

    feedback.record_news_feedback_sync(
        article_key="naver:1",
        discord_user_id="user-1",
        action="useful",
        guild_id="guild-1",
        channel_id="channel-1",
        thread_id="thread-1",
        message_id="message-1",
    )

    assert captured["url"] == "http://collector.local/news/feedback"
    assert captured["headers"]["X-internal-token"] == "collector-token"
    assert captured["body"] == {
        "action": "useful",
        "article_key": "naver:1",
        "channel_id": "channel-1",
        "discord_user_id": "user-1",
        "guild_id": "guild-1",
        "message_id": "message-1",
        "thread_id": "thread-1",
    }
