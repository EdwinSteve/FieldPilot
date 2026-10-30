"""Muse Voice Transcribe through Meta's file endpoint, POST /v1/asr/transcribe (D061).

Not the OpenAI-style /v1/audio/transcriptions, which Meta does not serve.
The request is multipart: a JSON `request` part and the WAV as `audio`.
Standard library only; the HTTP transport is injected so tests never reach
the network. Errors carry the class and HTTP status only, never the body or
the key.
"""

import json
import urllib.error
import urllib.request
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus
from typing import Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from app.settings import Settings
from app.voice.speech import SpeechUnavailableError, check_wav

# Language hints the service understands, by the codes the app uses.
LANGUAGES = {"es": "Spanish", "en": "English"}


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes


class HttpPost(Protocol):
    def __call__(
        self, url: str, headers: dict[str, str], body: bytes, timeout: float
    ) -> HttpResponse: ...


def urllib_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResponse:
    """The production transport. An HTTP error is a response; a network failure raises."""
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return HttpResponse(response.status, response.read())
    except urllib.error.HTTPError as error:
        return HttpResponse(error.code, b"")
    except (urllib.error.URLError, TimeoutError) as error:
        raise SpeechUnavailableError(type(error).__name__) from None


class _Transcription(BaseModel):
    model_config = ConfigDict(extra="ignore")

    transcript: str


class MuseVoiceTranscribe:
    """Implements `SpeechToText` (§4.9)."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        keywords: Sequence[str] = (),
        post: HttpPost = urllib_post,
    ) -> None:
        self._api_key = api_key
        self._url = base_url.rstrip("/") + "/asr/transcribe"
        self._model = model
        self._timeout = timeout_seconds
        self._keywords = tuple(keywords)
        self._post = post

    @classmethod
    def from_settings(
        cls, settings: Settings, keywords: Sequence[str] = ()
    ) -> "MuseVoiceTranscribe":
        if (
            settings.muse_api_key is None
            or not settings.muse_api_base_url
            or not settings.muse_transcribe_model
        ):
            raise ValueError(
                "MuseVoiceTranscribe needs MUSE_API_KEY, MUSE_API_BASE_URL and "
                "MUSE_TRANSCRIBE_MODEL"
            )
        return cls(
            settings.muse_api_key.get_secret_value(),
            settings.muse_api_base_url,
            settings.muse_transcribe_model,
            settings.muse_timeout_seconds,
            keywords,
        )

    def transcribe(self, audio: bytes, language: str) -> str:
        check_wav(audio)
        if language not in LANGUAGES:
            raise ValueError(f"unsupported language {language!r}; known: {sorted(LANGUAGES)}")
        boundary = uuid.uuid4().hex
        response = self._post(
            self._url,
            {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
            multipart_body(boundary, self._request(language), audio),
            self._timeout,
        )
        if response.status != HTTPStatus.OK:
            raise SpeechUnavailableError(f"HTTP {response.status}")
        try:
            return _Transcription.model_validate_json(response.body).transcript.strip()
        except ValidationError:
            raise SpeechUnavailableError("unexpected response shape") from None

    def _request(self, language: str) -> dict[str, object]:
        request: dict[str, object] = {
            "model": self._model,
            "audioEncoding": "WAV",
            "mode": "PUSH_TO_TALK",
            "languageBias": [LANGUAGES[language]],
        }
        if self._keywords:
            request["keywords"] = list(self._keywords)
        return request


def multipart_body(boundary: str, request: dict[str, object], audio: bytes) -> bytes:
    """The two parts the endpoint expects: `request` (JSON) and `audio` (WAV)."""
    head = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="request"\r\n'
        "Content-Type: application/json\r\n\r\n"
        f"{json.dumps(request, ensure_ascii=False)}\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="audio"; filename="audio.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n"
    )
    return head.encode("utf-8") + audio + f"\r\n--{boundary}--\r\n".encode("ascii")
