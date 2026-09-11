"""OpenAI-compatible HTTP client for the local 9router gateway."""
from __future__ import annotations

import json
from urllib import request

from src.shared.config import Config


class LLMClient:
    def __init__(
        self,
        base_url: str = Config.LLM_BASE_URL,
        api_key: str = Config.LLM_API_KEY,
        model: str = Config.LLM_MODEL,
        timeout_seconds: int = 20,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> str:
        if not self._base_url or not self._model:
            raise RuntimeError("LLM_BASE_URL and LLM_MODEL must be configured")

        payload = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        http_request = request.Request(
            f"{self._base_url}/chat/completions",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
                content_type = response.headers.get("Content-Type", "unknown")
                try:
                    return _extract_reasoning(response_body, content_type)
                except (KeyError, TypeError, ValueError) as error:
                    raise RuntimeError(
                        "LLM gateway returned an unsupported response "
                        f"(status={response.status}, content_type={content_type}, "
                        f"body={response_body[:200]!r})"
                    ) from error
        except OSError as error:
            raise RuntimeError(f"Unable to reach LLM gateway: {error}") from error


def _extract_reasoning(response_body: str, content_type: str) -> str:
    normalized_body = response_body.strip()
    if "text/event-stream" in content_type:
        normalized_body = normalized_body.removesuffix("data: [DONE]").strip()

    try:
        data = json.loads(normalized_body)
        return _content_from_completion(data)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        if "text/event-stream" not in content_type:
            raise

    fragments: list[str] = []
    for line in normalized_body.splitlines():
        payload = line.removeprefix("data: ").strip()
        if not payload or payload == "[DONE]":
            continue
        fragments.append(_content_from_completion(json.loads(payload)))
    if not fragments:
        raise ValueError("LLM event stream did not contain content")
    return "".join(fragments)


def _content_from_completion(data: dict[str, object]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise KeyError("choices")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise TypeError("choice")
    message = choice.get("message")
    if isinstance(message, dict) and message.get("content") is not None:
        return str(message["content"])
    delta = choice.get("delta")
    if isinstance(delta, dict) and delta.get("content") is not None:
        return str(delta["content"])
    raise KeyError("message.content")