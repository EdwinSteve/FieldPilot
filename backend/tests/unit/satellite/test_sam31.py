"""Sam31Segmentation against the real SDK, with HTTP answered in memory (no network)."""

import base64
import json
from collections.abc import Callable

import httpx2
import openai
import pytest

from app.satellite.sam31 import Sam31Segmentation
from app.satellite.segmentation import Box, SegmentationUnavailableError
from app.settings import Settings

KEY = "sk-test-not-a-real-key"
PNG = b"\x89PNG fake"
TOKENS = "<0f>0<|box;x1=10;y1=20;x2=30;y2=40;w=100;h=50|><|mask;x=0;y=0;data=1,1,~|>"


def _response(text: str) -> dict[str, object]:
    return {
        "id": "resp-1",
        "object": "response",
        "created_at": 0,
        "model": "sam-3.1",
        "status": "completed",
        "parallel_tool_calls": False,
        "tool_choice": "auto",
        "tools": [],
        "output": [
            {
                "type": "message",
                "id": "m1",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
    }


def _client(
    reply: Callable[[httpx2.Request], httpx2.Response], seen: list[httpx2.Request]
) -> Sam31Segmentation:
    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return reply(request)

    sdk = openai.OpenAI(
        api_key=KEY,
        base_url="https://muse.test/v1",
        max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )
    return Sam31Segmentation(sdk, "sam-3.1")


def test_the_request_follows_the_workshop_contract() -> None:
    seen: list[httpx2.Request] = []
    client = _client(lambda r: httpx2.Response(200, json=_response(TOKENS)), seen)

    boxes = client.segment(PNG, "brown patch")

    assert boxes == (Box(10, 20, 30, 40, 100, 50),)
    body = json.loads(seen[0].content)
    assert body["model"] == "sam-3.1"
    assert body["store"] is False
    [message] = body["input"]
    assert message["role"] == "user"
    text, image = message["content"]
    assert text == {"type": "input_text", "text": "brown patch"}
    assert image["type"] == "input_image"
    assert image["image_url"] == "data:image/png;base64," + base64.b64encode(PNG).decode()


def test_an_empty_answer_is_no_boxes() -> None:
    client = _client(lambda r: httpx2.Response(200, json=_response("")), [])

    assert client.segment(PNG, "brown patch") == ()


def test_a_server_error_becomes_unavailable_without_details() -> None:
    def reply(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(503, json={"error": {"message": f"down {KEY}"}})

    with pytest.raises(SegmentationUnavailableError) as raised:
        _client(reply, []).segment(PNG, "brown patch")

    assert str(raised.value).endswith("(HTTP 503)")
    assert KEY not in str(raised.value)
    assert raised.value.__cause__ is None


def test_from_settings_needs_the_key_and_the_model() -> None:
    with pytest.raises(ValueError, match="MUSE_SEGMENTATION_MODEL"):
        Sam31Segmentation.from_settings(Settings(_env_file=None, muse_api_key=None))
