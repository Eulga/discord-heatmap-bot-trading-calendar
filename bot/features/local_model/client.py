from __future__ import annotations

import asyncio
import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_SYSTEM_PROMPT = (
    "한국어로 명확하고 간결하게 답변하세요. "
    "Discord 메시지로 전달 가능한 일반 텍스트만 출력하세요. "
    "파일, 쉘, 데이터베이스, 외부 서비스를 직접 조작한다고 말하지 마세요."
)


class LocalModelError(RuntimeError):
    """Base error for local model calls."""


class LocalModelConfigurationError(LocalModelError):
    """Raised when the local model endpoint config is invalid."""


class LocalModelTimeoutError(LocalModelError):
    """Raised when the local model server does not respond in time."""


class LocalModelApiError(LocalModelError):
    """Raised when the local model server returns an HTTP or connection error."""


class LocalModelInvalidResponseError(LocalModelError):
    """Raised when the local model server returns an unexpected response shape."""


def _chat_completions_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise LocalModelConfigurationError("LOCAL_MODEL_BASE_URL is empty.")
    return f"{normalized}/chat/completions"


def _extract_message_content(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise LocalModelInvalidResponseError("Local model response was not a JSON object.")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LocalModelInvalidResponseError("Local model response did not include choices.")
    first = choices[0]
    if not isinstance(first, dict):
        raise LocalModelInvalidResponseError("Local model choice was not an object.")
    message = first.get("message")
    if not isinstance(message, dict):
        raise LocalModelInvalidResponseError("Local model choice did not include a message.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LocalModelInvalidResponseError("Local model message content was empty.")
    return content.strip()


def _post_chat_completion(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: int,
    max_tokens: int,
) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": False,
    }
    request = Request(
        _chat_completions_url(base_url),
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except HTTPError as exc:
        raise LocalModelApiError(f"Local model server returned HTTP {exc.code}.") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise LocalModelTimeoutError("Local model request timed out.") from exc
    except URLError as exc:
        if isinstance(getattr(exc, "reason", None), socket.timeout):
            raise LocalModelTimeoutError("Local model request timed out.") from exc
        raise LocalModelApiError("Local model server was unreachable.") from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalModelInvalidResponseError("Local model response was not valid JSON.") from exc
    return _extract_message_content(payload)


async def request_local_model(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: int,
    max_tokens: int,
) -> str:
    return await asyncio.to_thread(
        _post_chat_completion,
        base_url=base_url,
        model=model,
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
    )
