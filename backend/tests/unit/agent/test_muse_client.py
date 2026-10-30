"""MuseClient against the real SDK, with HTTP answered in memory (no network)."""

import json
from collections.abc import Callable

import httpx2
import openai
import pytest

from app.agent.llm.muse import MuseClient
from app.agent.llm.ports import LLMUnavailableError
from app.agent.messages import (
    AssistantText,
    LLMResponse,
    Message,
    TokenUsage,
    ToolCall,
    ToolResult,
    ToolSpec,
    UserMessage,
)
from app.domain.models import JsonObject, JsonValue
from app.settings import Settings

KEY = "sk-test-not-a-real-key"
SPEC = ToolSpec("read_moisture", "Latest soil moisture.", {"type": "object", "properties": {}})


def _response(*output: JsonObject) -> JsonObject:
    return {
        "id": "resp-1",
        "object": "response",
        "created_at": 0,
        "model": "muse-spark-1.3",
        "status": "completed",
        "parallel_tool_calls": False,
        "tool_choice": "auto",
        "tools": [],
        "output": [dict(item) for item in output],
        "usage": {
            "input_tokens": 120,
            "output_tokens": 14,
            "total_tokens": 134,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }


FUNCTION_CALL: dict[str, JsonValue] = {
    "type": "function_call",
    "id": "fc-1",
    "call_id": "call-9",
    "name": "read_moisture",
    "arguments": '{"zone_id": 2}',
    "status": "completed",
}
TEXT: dict[str, JsonValue] = {
    "type": "message",
    "id": "msg-1",
    "role": "assistant",
    "status": "completed",
    "content": [{"type": "output_text", "text": "Zone 2 is dry.", "annotations": []}],
}


class Server:
    """Answers every request with `reply` and keeps the requests."""

    def __init__(self, reply: Callable[[httpx2.Request], httpx2.Response]) -> None:
        self.reply = reply
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.reply(request)

    def client(self) -> MuseClient:
        sdk = openai.OpenAI(
            api_key=KEY,
            base_url="https://muse.test/v1",
            max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(self)),
        )
        return MuseClient(sdk, "muse-spark-1.3")


def _json(body: object, status: int = 200) -> Callable[[httpx2.Request], httpx2.Response]:
    return lambda request: httpx2.Response(status, json=body)


def test_the_request_follows_the_workshop_contract() -> None:
    server = Server(_json(_response(FUNCTION_CALL)))
    transcript: list[Message] = [
        UserMessage("Assess zone 2."),
        AssistantText("Reading first."),
        ToolCall("call-1", "read_moisture", '{"zone_id": 2}'),
        ToolResult("call-1", '{"moisture_pct": 21.0}'),
    ]

    server.client().complete("You assess moisture.", transcript, [SPEC])

    [request] = server.requests
    body = json.loads(request.content)
    assert request.url.path == "/v1/responses"
    assert body["model"] == "muse-spark-1.3"
    assert body["instructions"] == "You assess moisture."
    assert body["store"] is False
    assert body["parallel_tool_calls"] is False
    assert body["input"] == [
        {"role": "user", "content": "Assess zone 2."},
        {"role": "assistant", "content": "Reading first."},
        {
            "type": "function_call",
            "call_id": "call-1",
            "name": "read_moisture",
            "arguments": '{"zone_id": 2}',
        },
        {"type": "function_call_output", "call_id": "call-1", "output": '{"moisture_pct": 21.0}'},
    ]
    assert body["tools"] == [
        {
            "type": "function",
            "name": "read_moisture",
            "description": "Latest soil moisture.",
            "parameters": {"type": "object", "properties": {}},
            "strict": False,
        }
    ]


def test_a_function_call_and_its_usage_are_parsed() -> None:
    server = Server(_json(_response(FUNCTION_CALL)))

    response = server.client().complete("sys", [UserMessage("Go.")], [SPEC])

    assert response == LLMResponse(
        None, ToolCall("call-9", "read_moisture", '{"zone_id": 2}'), TokenUsage(120, 14)
    )


def test_a_text_answer_is_parsed() -> None:
    server = Server(_json(_response(TEXT)))

    response = server.client().complete("sys", [UserMessage("Go.")], [])

    assert response.text == "Zone 2 is dry."
    assert response.tool_call is None


def test_a_server_error_becomes_llm_unavailable_without_details() -> None:
    server = Server(_json({"error": {"message": f"boom {KEY}"}}, status=500))

    with pytest.raises(LLMUnavailableError) as raised:
        server.client().complete("sys", [UserMessage("Go.")], [])

    assert str(raised.value) == "InternalServerError (HTTP 500)"
    assert KEY not in str(raised.value)
    assert raised.value.__cause__ is None


def test_an_auth_error_also_pauses_instead_of_crashing() -> None:
    server = Server(_json({"error": {"message": "bad key"}}, status=401))

    with pytest.raises(LLMUnavailableError, match=r"AuthenticationError \(HTTP 401\)"):
        server.client().complete("sys", [UserMessage("Go.")], [])


def test_a_connection_error_becomes_llm_unavailable() -> None:
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    with pytest.raises(LLMUnavailableError, match=r"^APIConnectionError$"):
        Server(refuse).client().complete("sys", [UserMessage("Go.")], [])


def test_available_models_lists_the_ids() -> None:
    body = {
        "object": "list",
        "data": [
            {"id": "muse-spark-1.3", "object": "model", "created": 0, "owned_by": "meta"},
            {"id": "sam-3.1", "object": "model", "created": 0, "owned_by": "meta"},
        ],
    }
    server = Server(_json(body))

    assert server.client().available_models() == frozenset({"muse-spark-1.3", "sam-3.1"})
    assert server.requests[0].url.path == "/v1/models"


def test_from_settings_needs_the_key_and_the_model() -> None:
    with pytest.raises(ValueError, match="MUSE_API_KEY and MUSE_AGENT_MODEL"):
        MuseClient.from_settings(Settings(_env_file=None, muse_api_key=None))
