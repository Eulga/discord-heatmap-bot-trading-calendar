import json
import socket
from urllib.error import HTTPError, URLError

import pytest

from bot.app import settings
from bot.features.local_model import client
from bot.features.local_model import command as local_command


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


@pytest.mark.asyncio
async def test_request_local_model_posts_openai_compatible_payload(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"choices": [{"message": {"content": "  안녕하세요.  "}}]})

    monkeypatch.setattr(client, "urlopen", fake_urlopen)

    text = await client.request_local_model(
        base_url="http://localhost:8081/v1/",
        model="gemma-e4b",
        prompt="테스트",
        timeout_seconds=12,
        max_tokens=123,
    )

    assert text == "안녕하세요."
    assert captured["url"] == "http://localhost:8081/v1/chat/completions"
    assert captured["timeout"] == 12
    assert captured["body"]["model"] == "gemma-e4b"
    assert captured["body"]["messages"][-1] == {"role": "user", "content": "테스트"}
    assert captured["body"]["max_tokens"] == 123
    assert captured["body"]["stream"] is False


@pytest.mark.asyncio
async def test_request_local_model_converts_timeout(monkeypatch):
    def fake_urlopen(_request, timeout=None):
        raise TimeoutError("slow")

    monkeypatch.setattr(client, "urlopen", fake_urlopen)

    with pytest.raises(client.LocalModelTimeoutError):
        await client.request_local_model(
            base_url="http://localhost:8081/v1",
            model="gemma-e4b",
            prompt="테스트",
            timeout_seconds=1,
            max_tokens=10,
        )


@pytest.mark.asyncio
async def test_request_local_model_converts_url_and_http_errors(monkeypatch):
    def fake_urlopen_url_error(_request, timeout=None):
        raise URLError(socket.timeout("slow"))

    monkeypatch.setattr(client, "urlopen", fake_urlopen_url_error)
    with pytest.raises(client.LocalModelTimeoutError):
        await client.request_local_model(
            base_url="http://localhost:8081/v1",
            model="gemma-e4b",
            prompt="테스트",
            timeout_seconds=1,
            max_tokens=10,
        )

    def fake_urlopen_http_error(request, timeout=None):
        raise HTTPError(request.full_url, 500, "server error", {}, None)

    monkeypatch.setattr(client, "urlopen", fake_urlopen_http_error)
    with pytest.raises(client.LocalModelApiError):
        await client.request_local_model(
            base_url="http://localhost:8081/v1",
            model="gemma-e4b",
            prompt="테스트",
            timeout_seconds=1,
            max_tokens=10,
        )


@pytest.mark.asyncio
async def test_request_local_model_rejects_invalid_response(monkeypatch):
    monkeypatch.setattr(client, "urlopen", lambda _request, timeout=None: FakeResponse({"choices": []}))

    with pytest.raises(client.LocalModelInvalidResponseError):
        await client.request_local_model(
            base_url="http://localhost:8081/v1",
            model="gemma-e4b",
            prompt="테스트",
            timeout_seconds=1,
            max_tokens=10,
        )


def test_format_model_response_truncates_to_discord_safe_limit():
    text = local_command._format_model_response("가" * 2000, 1800)

    assert len(text) <= 1800
    assert "일부를 생략" in text


def test_local_model_settings_integer_bounds(monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL_TIMEOUT_SECONDS", "999")
    monkeypatch.setenv("LOCAL_MODEL_MAX_RESPONSE_CHARS", "1")

    assert settings._env_bounded_int("LOCAL_MODEL_TIMEOUT_SECONDS", 45, 1, 120) == 120
    assert settings._env_bounded_int("LOCAL_MODEL_MAX_RESPONSE_CHARS", 1800, 200, 1900) == 200
