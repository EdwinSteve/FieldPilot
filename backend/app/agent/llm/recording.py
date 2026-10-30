"""Records a live run as a fixture `MockLLMClient` can replay (step 11 records the demo).

The file is rewritten after every response, so a run cut short still leaves
a usable fixture. Only model responses are written: never the key, the
request or any environment value.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from app.agent.llm.ports import LLMClient
from app.agent.messages import LLMResponse, Message, ToolSpec
from app.domain.models import JsonValue


class RecordingLLMClient:
    def __init__(self, inner: LLMClient, path: Path) -> None:
        self._inner = inner
        self._path = path
        self._responses: list[JsonValue] = []

    def complete(
        self, instructions: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> LLMResponse:
        response = self._inner.complete(instructions, messages, tools)
        self._responses.append(to_fixture(response))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"responses": self._responses}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return response


def to_fixture(response: LLMResponse) -> dict[str, JsonValue]:
    entry: dict[str, JsonValue] = {
        "text": response.text,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
    call = response.tool_call
    if call is not None:
        try:
            parsed = json.loads(call.arguments_json)
        except json.JSONDecodeError:
            parsed = None
        arguments: dict[str, JsonValue] = (
            {"arguments": parsed}
            if isinstance(parsed, dict)
            else {"arguments_json": call.arguments_json}
        )
        entry["tool_call"] = {"name": call.name, **arguments}
    return entry
