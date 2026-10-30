import pytest

from app.voice.speech import (
    MAX_BYTES,
    AudioInfo,
    MockSpeechToText,
    UnsupportedAudioError,
    check_wav,
)
from tests.unit.voice.wavs import claim_frames, make_wav


@pytest.mark.parametrize("rate", [16_000, 24_000])
def test_mono_16_bit_at_a_supported_rate_passes(rate: int) -> None:
    assert check_wav(make_wav(rate=rate, seconds=0.5)) == AudioInfo(rate, 500)


@pytest.mark.parametrize(
    ("audio", "message"),
    [
        (make_wav(channels=2), "2 channels, expected mono"),
        (make_wav(width=1), "8-bit samples, expected 16-bit"),
        (make_wav(rate=44_100), "44100 Hz, expected 16000 or 24000"),
    ],
)
def test_audio_the_service_would_refuse_is_refused_here(audio: bytes, message: str) -> None:
    with pytest.raises(UnsupportedAudioError, match=message):
        check_wav(audio)


def test_every_problem_is_named() -> None:
    with pytest.raises(UnsupportedAudioError, match=r"2 channels.*8-bit.*44100 Hz"):
        check_wav(make_wav(rate=44_100, channels=2, width=1))


def test_more_than_ten_minutes_is_refused() -> None:
    eleven_minutes = claim_frames(make_wav(rate=16_000), 16_000 * 60 * 11)

    with pytest.raises(UnsupportedAudioError, match="longer than 10 minutes"):
        check_wav(eleven_minutes)


def test_exactly_ten_minutes_passes() -> None:
    ten_minutes = claim_frames(make_wav(rate=16_000), 16_000 * 60 * 10)

    assert check_wav(ten_minutes).duration_ms == 600_000


def test_not_a_wav_is_refused() -> None:
    with pytest.raises(UnsupportedAudioError, match="not a PCM WAV file"):
        check_wav(b"ID3 an mp3, not a wav")


def test_more_than_32_mb_is_refused_before_parsing() -> None:
    with pytest.raises(UnsupportedAudioError, match="larger than 32 MB"):
        check_wav(b"\x00" * (MAX_BYTES + 1))


def test_the_mock_returns_its_transcript_and_records_calls() -> None:
    mock = MockSpeechToText("¿Riego hoy?")

    assert mock.transcribe(b"wav", "es") == "¿Riego hoy?"
    assert mock.calls == [(b"wav", "es")]
