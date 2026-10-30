"""MuseVoiceTranscribe with the HTTP transport replaced: the request it builds, the
answers it accepts, and the errors it reports. No network."""

import json
import re
import urllib.error
from pathlib import Path

import pytest

from app.settings import Settings
from app.voice import muse
from app.voice.muse import HttpResponse, MuseVoiceTranscribe, urllib_post
from app.voice.speech import SpeechUnavailableError, UnsupportedAudioError
from tests.unit.voice.wavs import make_wav

KEY = "sk-test-not-a-real-key"
RECORDED = Path(__file__).resolve().parents[2] / "fixtures" / "voice" / "transcribe_response.json"
AUDIO = make_wav()


class FakePost:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str], bytes, float]] = []

    def __call__(
        self, url: str, headers: dict[str, str], body: bytes, timeout: float
    ) -> HttpResponse:
        self.calls.append((url, headers, body, timeout))
        return self.response


def _client(post: FakePost, keywords: tuple[str, ...] = ()) -> MuseVoiceTranscribe:
    return MuseVoiceTranscribe(
        KEY, "https://api.meta.ai/v1/", "muse-voice-transcribe-1.0", 30.0, keywords, post
    )


def _ok(body: bytes | None = None) -> FakePost:
    return FakePost(HttpResponse(200, body if body is not None else RECORDED.read_bytes()))


def _parts(headers: dict[str, str], body: bytes) -> dict[str, bytes]:
    boundary = re.search(r"boundary=(\w+)", headers["Content-Type"])
    assert boundary is not None
    parts = {}
    for chunk in body.split(b"--" + boundary.group(1).encode())[1:-1]:
        head, _, content = chunk.strip(b"\r\n").partition(b"\r\n\r\n")
        name = re.search(rb'name="(\w+)"', head)
        assert name is not None
        parts[name.group(1).decode()] = content
    return parts


def test_the_request_follows_the_documented_file_endpoint() -> None:
    post = _ok()

    _client(post, keywords=("maíz", "riego")).transcribe(AUDIO, "es")

    [(url, headers, body, timeout)] = post.calls
    assert url == "https://api.meta.ai/v1/asr/transcribe"
    assert headers["Authorization"] == f"Bearer {KEY}"
    assert headers["Accept"] == "application/json"
    assert timeout == 30.0
    parts = _parts(headers, body)
    assert json.loads(parts["request"]) == {
        "model": "muse-voice-transcribe-1.0",
        "audioEncoding": "WAV",
        "mode": "PUSH_TO_TALK",
        "languageBias": ["Spanish"],
        "keywords": ["maíz", "riego"],
    }
    assert parts["audio"] == AUDIO


def test_no_keywords_means_no_keywords_field() -> None:
    post = _ok()

    _client(post).transcribe(AUDIO, "es")

    request = json.loads(_parts(post.calls[0][1], post.calls[0][2])["request"])
    assert "keywords" not in request


def test_the_recorded_answer_gives_its_transcript() -> None:
    transcript = _client(_ok()).transcribe(AUDIO, "es")

    assert transcript == "¿Necesita agua el maíz de la zona dos? De casualidad?."


def test_surrounding_whitespace_is_dropped() -> None:
    post = _ok(b'{"transcript": "  hola  ", "turns": []}')

    assert _client(post).transcribe(AUDIO, "es") == "hola"


@pytest.mark.parametrize("status", [400, 401, 413, 429, 500, 503])
def test_an_http_error_is_unavailable_with_the_status_only(status: int) -> None:
    post = FakePost(HttpResponse(status, json.dumps({"message": KEY}).encode()))

    with pytest.raises(SpeechUnavailableError) as raised:
        _client(post).transcribe(AUDIO, "es")

    assert str(raised.value) == f"HTTP {status}"
    assert raised.value.__cause__ is None


def test_an_unexpected_body_is_unavailable() -> None:
    with pytest.raises(SpeechUnavailableError, match="unexpected response shape"):
        _client(_ok(b"<html>gateway</html>")).transcribe(AUDIO, "es")


def test_bad_audio_never_reaches_the_service() -> None:
    post = _ok()

    with pytest.raises(UnsupportedAudioError):
        _client(post).transcribe(make_wav(rate=44_100), "es")
    assert post.calls == []


def test_an_unknown_language_is_refused_before_sending() -> None:
    post = _ok()

    with pytest.raises(ValueError, match="unsupported language 'qu'"):
        _client(post).transcribe(AUDIO, "qu")
    assert post.calls == []


def test_from_settings_needs_key_url_and_model() -> None:
    with pytest.raises(ValueError, match="MUSE_TRANSCRIBE_MODEL"):
        MuseVoiceTranscribe.from_settings(Settings(_env_file=None, muse_api_key=None))


def test_urllib_post_turns_a_network_failure_into_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*args: object, **kwargs: object) -> object:
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(muse.urllib.request, "urlopen", refuse)

    with pytest.raises(SpeechUnavailableError, match=r"^URLError$"):
        urllib_post("https://api.meta.ai/v1/asr/transcribe", {}, b"", 1.0)


def test_urllib_post_returns_an_http_error_as_a_status(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        raise urllib.error.HTTPError("https://x", 403, "Forbidden", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(muse.urllib.request, "urlopen", forbidden)

    assert urllib_post("https://x", {}, b"", 1.0) == HttpResponse(403, b"")
