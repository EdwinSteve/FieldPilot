"""A stand-in for the Meta Model API, for the end-to-end journey only.

It speaks the OpenAI Responses API that `MuseClient` and `Sam31Segmentation`
call (`POST /v1/responses`, `GET /v1/models`), so the backend runs exactly as
with the real model: same SDK, same HTTP, same checks. The agents are played
by `doubles.py`; SAM answers with the recorded segmentation of the demo
image. `GET /_e2e/log` lets the tests see every turn, and every refusal the
backend's checks returned to the model.

Never deployed: it lives under e2e/ and holds no key.
"""

import itertools
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request

from e2e.fake_muse.doubles import parse, step_for

SAM_RECORDINGS = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "sam"
MODELS = ("muse-spark-1.3", "sam-3.1", "muse-voice-transcribe-1.0")

app = FastAPI(title="Fake Muse (e2e)")
_ids = itertools.count(1)
_log: list[dict[str, Any]] = []


@app.get("/v1/models")
def models() -> dict[str, Any]:
    return {"object": "list", "data": [{"id": m, "object": "model", "owned_by": "e2e"}
                                       for m in MODELS]}  # fmt: skip


@app.post("/v1/responses")
async def responses(request: Request) -> dict[str, Any]:
    payload = await request.json()
    if _has_image(payload):
        return _response(payload, text=_recorded_sam(), call=None)
    conversation = parse(payload)
    step = step_for(conversation)
    call = step(conversation)
    _log.append({
        "agent": step.__name__,
        "question": conversation.question,
        "call": None if call is None else {"name": call.name, "arguments": call.arguments},
        "refusals": conversation.refusals(),
    })  # fmt: skip
    return _response(payload, text=None, call=call)


@app.get("/_e2e/log")
def log() -> list[dict[str, Any]]:
    return _log


def _has_image(payload: dict[str, Any]) -> bool:
    for item in payload.get("input", []):
        content = item.get("content")
        if isinstance(content, list) and any(part.get("type") == "input_image" for part in content):
            return True
    return False


def _recorded_sam() -> str:
    """The one recorded answer: three brown patches on the demo scene."""
    [recording] = sorted(SAM_RECORDINGS.glob("*.txt"))
    return recording.read_text(encoding="utf-8")


def _response(payload: dict[str, Any], text: str | None, call: Any) -> dict[str, Any]:
    n = next(_ids)
    output: list[dict[str, Any]] = []
    if text is not None:
        content = [{"type": "output_text", "text": text, "annotations": []}]
        output.append({"type": "message", "id": f"msg_{n}", "role": "assistant",
                       "status": "completed", "content": content})  # fmt: skip
    if call is not None:
        output.append({"type": "function_call", "id": f"fc_{n}", "call_id": f"call_{n}",
                       "name": call.name, "arguments": json.dumps(call.arguments),
                       "status": "completed"})  # fmt: skip
    return {
        "id": f"resp_{n}",
        "object": "response",
        "created_at": 0,
        "model": payload.get("model", ""),
        "status": "completed",
        "output": output,
        "parallel_tool_calls": False,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }
