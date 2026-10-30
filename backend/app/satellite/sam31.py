"""SAM 3.1 through the official OpenAI SDK, as in the Meta workshop (D043, D058, D059).

One of the Muse adapters allowed to import `openai`. Every SDK error becomes
SegmentationUnavailableError, carrying the error class and status only.
"""

import base64

import openai
from openai.types.responses import (
    EasyInputMessageParam,
    ResponseInputImageParam,
    ResponseInputTextParam,
)

from app.agent.llm.muse import describe_error
from app.satellite.segmentation import Box, SegmentationUnavailableError, parse_boxes
from app.settings import Settings


class Sam31Segmentation:
    def __init__(self, client: openai.OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> "Sam31Segmentation":
        if settings.muse_api_key is None or not settings.muse_segmentation_model:
            raise ValueError("Sam31Segmentation needs MUSE_API_KEY and MUSE_SEGMENTATION_MODEL")
        client = openai.OpenAI(
            api_key=settings.muse_api_key.get_secret_value(),
            base_url=settings.muse_api_base_url,
            timeout=settings.muse_timeout_seconds,
        )
        return cls(client, settings.muse_segmentation_model)

    def segment(self, image_png: bytes, prompt: str) -> tuple[Box, ...]:
        image_url = "data:image/png;base64," + base64.b64encode(image_png).decode("ascii")
        try:
            response = self._client.responses.create(
                model=self._model,
                input=[
                    EasyInputMessageParam(
                        role="user",
                        content=[
                            ResponseInputTextParam(type="input_text", text=prompt),
                            ResponseInputImageParam(
                                type="input_image", image_url=image_url, detail="auto"
                            ),
                        ],
                    )
                ],
                store=False,
            )
        except openai.APIError as exc:
            raise SegmentationUnavailableError(describe_error(exc)) from None
        return parse_boxes(response.output_text or "")
