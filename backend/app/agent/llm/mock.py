"""Replays recorded model responses in order. Never reaches the network."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, JsonValue

from app.agent.llm.ports import FixtureExhaustedError
from app.agent.messages import LLMResponse, Message, TokenUsage, ToolCall, ToolSpec


@dataclass(frozen=True)
class LLMRequest:
    """What the loop sent on one call, kept so tests can inspect it."""

    instructions: str
    messages: tuple[Message, ...]
    tools: tuple[ToolSpec, ...]


class MockLLMClient:
    """Answers call n with response n; a call past the end raises (D049)."""

    def __init__(self, responses: Sequence[LLMResponse]) -> None:
        self._responses = tuple(responses)
        self.requests: list[LLMRequest] = []

    @classmethod
    def from_fixture(cls, path: Path) -> "MockLLMClient":
        """Load a JSON fixture: `{"responses": [{"text", "tool_call", "usage"}, ...]}`."""
        fixture = _Fixture.model_validate_json(path.read_text(encoding="utf-8"))
        return cls([entry.to_response(f"call-{n}") for n, entry in enumerate(fixture.responses, 1)])

    def complete(
        self, instructions: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> LLMResponse:
        self.requests.append(LLMRequest(instructions, tuple(messages), tuple(tools)))
        call = len(self.requests)
        if call > len(self._responses):
            raise FixtureExhaustedError(
                f"call {call} asked for a response; the fixture has {len(self._responses)}"
            )
        return self._responses[call - 1]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _FixtureToolCall(_StrictModel):
    name: str
    arguments: dict[str, JsonValue]


class _FixtureUsage(_StrictModel):
    input_tokens: int = 0
    output_tokens: int = 0


class _FixtureResponse(_StrictModel):
    text: str | None = None
    tool_call: _FixtureToolCall | None = None
    usage: _FixtureUsage = _FixtureUsage()

    def to_response(self, call_id: str) -> LLMResponse:
        call = (
            ToolCall(call_id, self.tool_call.name, json.dumps(self.tool_call.arguments))
            if self.tool_call
            else None
        )
        return LLMResponse(
            self.text, call, TokenUsage(self.usage.input_tokens, self.usage.output_tokens)
        )


class _Fixture(_StrictModel):
    responses: list[_FixtureResponse]
