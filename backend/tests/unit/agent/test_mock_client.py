import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agent.llm.mock import MockLLMClient
from app.agent.llm.ports import FixtureExhaustedError, LLMUnavailableError
from app.agent.messages import LLMResponse, TokenUsage, ToolCall, UserMessage


def _write(tmp_path: Path, fixture: object) -> Path:
    path = tmp_path / "run.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    return path


def test_replays_a_fixture_in_order(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        {
            "responses": [
                {
                    "tool_call": {"name": "read_moisture", "arguments": {"zone_id": 2}},
                    "usage": {"input_tokens": 120, "output_tokens": 14},
                },
                {"text": "Done."},
            ]
        },
    )
    llm = MockLLMClient.from_fixture(path)

    first = llm.complete("sys", [UserMessage("Assess.")], [])
    second = llm.complete("sys", [UserMessage("Assess.")], [])

    assert first == LLMResponse(
        None, ToolCall("call-1", "read_moisture", '{"zone_id": 2}'), TokenUsage(120, 14)
    )
    assert second == LLMResponse("Done.", None)
    assert [r.messages for r in llm.requests] == [(UserMessage("Assess."),)] * 2


def test_a_call_past_the_end_raises_fixture_exhausted() -> None:
    llm = MockLLMClient([LLMResponse("Only one.", None)])
    llm.complete("sys", [], [])

    with pytest.raises(
        FixtureExhaustedError, match="call 2 asked for a response; the fixture has 1"
    ):
        llm.complete("sys", [], [])


def test_fixture_exhausted_is_not_an_outage() -> None:
    assert not issubclass(FixtureExhaustedError, LLMUnavailableError)
    assert not issubclass(LLMUnavailableError, FixtureExhaustedError)


def test_a_fixture_with_unknown_fields_is_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, {"responses": [{"txt": "typo"}]})

    with pytest.raises(ValidationError):
        MockLLMClient.from_fixture(path)
