import json
from pathlib import Path

from app.agent.llm.mock import MockLLMClient
from app.agent.llm.recording import RecordingLLMClient
from app.agent.messages import LLMResponse, TokenUsage, ToolCall, UserMessage

RESPONSES = [
    LLMResponse(None, ToolCall("call-1", "read_zone", '{"zone_id": 2}'), TokenUsage(120, 14)),
    LLMResponse(None, ToolCall("call-2", "read_zone", "{zone"), TokenUsage(90, 9)),
    LLMResponse("Listo.", None, TokenUsage(50, 3)),
]


def test_a_recording_replays_to_the_same_responses(tmp_path: Path) -> None:
    path = tmp_path / "llm" / "run.json"
    recorder = RecordingLLMClient(MockLLMClient(RESPONSES), path)

    for _ in RESPONSES:
        recorder.complete("sys", [UserMessage("Go.")], [])

    replay = MockLLMClient.from_fixture(path)
    assert [replay.complete("s", [], []) for _ in RESPONSES] == RESPONSES


def test_the_file_is_complete_after_every_response(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    recorder = RecordingLLMClient(MockLLMClient(RESPONSES), path)

    recorder.complete("sys", [], [])

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "responses": [
            {
                "text": None,
                "usage": {"input_tokens": 120, "output_tokens": 14},
                "tool_call": {"name": "read_zone", "arguments": {"zone_id": 2}},
            }
        ]
    }


def test_invalid_arguments_are_kept_as_raw_text(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    recorder = RecordingLLMClient(MockLLMClient(RESPONSES), path)
    recorder.complete("sys", [], [])
    recorder.complete("sys", [], [])

    second = json.loads(path.read_text(encoding="utf-8"))["responses"][1]

    assert second["tool_call"] == {"name": "read_zone", "arguments_json": "{zone"}


def test_only_responses_are_written(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    RecordingLLMClient(MockLLMClient(RESPONSES), path).complete(
        "secret instructions", [UserMessage("task")], []
    )

    text = path.read_text(encoding="utf-8")
    assert "secret instructions" not in text and "task" not in text
