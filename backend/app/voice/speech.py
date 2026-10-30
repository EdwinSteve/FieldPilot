"""The speech-to-text port, its errors and local WAV checks (§4.9, D061).

The audio is checked before it leaves the machine, so a file the service
would refuse is refused here with a clear reason.
"""

import io
import wave
from dataclasses import dataclass
from typing import Protocol

SAMPLE_RATES_HZ = frozenset({16_000, 24_000})
MAX_DURATION_MS = 10 * 60 * 1000  # the service refuses longer audio
MAX_BYTES = 32 * 1024 * 1024  # the service refuses larger requests


class SpeechUnavailableError(Exception):
    """The transcription service could not answer. Carries class and status only."""


class UnsupportedAudioError(ValueError):
    """Audio the service would refuse: not mono 16-bit PCM WAV at 16 or 24 kHz, or too long."""


class NothingHeardError(Exception):
    """The transcript is empty: there is no question to answer."""


@dataclass(frozen=True)
class AudioInfo:
    sample_rate_hz: int
    duration_ms: int


class SpeechToText(Protocol):
    def transcribe(self, audio: bytes, language: str) -> str: ...


def check_wav(audio: bytes) -> AudioInfo:
    """Mono, 16-bit PCM, 16 or 24 kHz, at most 10 minutes and 32 MB."""
    if len(audio) > MAX_BYTES:
        raise UnsupportedAudioError("audio is larger than 32 MB")
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            channels, width, rate = wav.getnchannels(), wav.getsampwidth(), wav.getframerate()
            frames = wav.getnframes()
    except (wave.Error, EOFError) as error:
        raise UnsupportedAudioError(f"not a PCM WAV file ({error})") from None
    problems = []
    if channels != 1:
        problems.append(f"{channels} channels, expected mono")
    if width != 2:
        problems.append(f"{8 * width}-bit samples, expected 16-bit")
    if rate not in SAMPLE_RATES_HZ:
        problems.append(f"{rate} Hz, expected 16000 or 24000")
    duration_ms = 1000 * frames // rate if rate else 0
    if duration_ms > MAX_DURATION_MS:
        problems.append("longer than 10 minutes")
    if problems:
        raise UnsupportedAudioError("unsupported WAV: " + "; ".join(problems))
    return AudioInfo(rate, duration_ms)


class MockSpeechToText:
    """Returns a fixed transcript; records each call."""

    def __init__(self, transcript: str) -> None:
        self._transcript = transcript
        self.calls: list[tuple[bytes, str]] = []

    def transcribe(self, audio: bytes, language: str) -> str:
        self.calls.append((audio, language))
        return self._transcript
