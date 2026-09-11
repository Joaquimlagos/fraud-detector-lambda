import json
from unittest.mock import patch

from src.analysis.llm_client import LLMClient


class FakeResponse:
    status = 200
    headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(
            {"choices": [{"message": {"content": "Generated explanation"}}]}
        ).encode("utf-8")


def test_llm_client_sends_openai_compatible_chat_request():
    client = LLMClient(
        base_url="http://localhost:9000/v1",
        api_key="test-key",
        model="test-model",
    )

    with patch("src.analysis.llm_client.request.urlopen", return_value=FakeResponse()) as urlopen:
        result = client.generate("Explain this transaction")

    request = urlopen.call_args.args[0]
    assert request.full_url == "http://localhost:9000/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer test-key"
    assert json.loads(request.data) == {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Explain this transaction"}],
    }
    assert result == "Generated explanation"


def test_llm_client_accepts_json_response_with_sse_done_marker():
    response_body = (
        '{"choices":[{"message":{"content":"Generated explanation"}}]}'
        "data: [DONE]"
    )

    with patch(
        "src.analysis.llm_client.request.urlopen",
        return_value=FakeResponseWithBody(response_body, "text/event-stream"),
    ):
        result = LLMClient(base_url="http://localhost:9000/v1", model="test").generate("prompt")

    assert result == "Generated explanation"


class FakeResponseWithBody(FakeResponse):
    def __init__(self, body, content_type):
        self._body = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body