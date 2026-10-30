"""Small WAV files built in memory for the voice tests."""

import io
import struct
import wave


def make_wav(rate: int = 24_000, channels: int = 1, width: int = 2, seconds: float = 0.5) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(b"\x00" * int(rate * seconds) * channels * width)
    return buffer.getvalue()


def claim_frames(audio: bytes, frames: int) -> bytes:
    """Rewrite the data chunk size, so the header claims `frames` 16-bit mono frames."""
    data_size_offset = audio.index(b"data") + 4
    return audio[:data_size_offset] + struct.pack("<I", frames * 2) + audio[data_size_offset + 4 :]
