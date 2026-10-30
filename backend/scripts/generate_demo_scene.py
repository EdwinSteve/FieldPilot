"""Generate the synthetic demo scene in data/satellite/ (D059). Deterministic.

Run from backend/: uv run python scripts/generate_demo_scene.py

Zone 1 (left half) is healthy maize. Zone 2 (right half) is stressed, with
three brown bare-soil patches, so its mean NDVI falls below the 0.4 demo
threshold. Bands are 64x32; the RGB image is 512x256 (8x8 pixels per band
pixel). Only the standard library is used: zlib and struct write the PNG.
"""

import json
import random
import struct
import sys
import zlib
from pathlib import Path

SCENE_DIR = Path(__file__).resolve().parents[2] / "data" / "satellite" / "neiva-2026-10-28"
BAND_W, BAND_H, SCALE = 64, 32, 8
RGB_W, RGB_H = BAND_W * SCALE, BAND_H * SCALE
# Bare-soil patches in RGB pixels: centre x, centre y, radius. All in zone 2.
PATCHES = ((330, 70, 38), (420, 170, 45), (300, 190, 30))
# Reflectances (red, nir) per surface: NDVI about 0.80, 0.45 and 0.09.
HEALTHY, STRESSED, SOIL = (0.05, 0.45), (0.12, 0.32), (0.25, 0.30)


def _surface(x: float, y: float) -> tuple[float, float]:
    if any((x - cx) ** 2 + (y - cy) ** 2 <= r * r for cx, cy, r in PATCHES):
        return SOIL
    return HEALTHY if x < RGB_W / 2 else STRESSED


def _bands(rng: random.Random) -> tuple[list[list[float]], list[list[float]]]:
    red, nir = [], []
    for by in range(BAND_H):
        red_row, nir_row = [], []
        for bx in range(BAND_W):
            r, n = _surface((bx + 0.5) * SCALE, (by + 0.5) * SCALE)
            red_row.append(round(r + rng.uniform(-0.01, 0.01), 3))
            nir_row.append(round(n + rng.uniform(-0.02, 0.02), 3))
        red.append(red_row)
        nir.append(nir_row)
    return red, nir


def _rgb(x: int, y: int, rng: random.Random) -> tuple[int, int, int]:
    noise = rng.randint(-12, 12)
    surface = _surface(x, y)
    if surface is SOIL:
        return (150 + noise, 110 + noise, 70 + noise)
    row_shade = 0 if (y // 8) % 2 else 25  # maize rows
    if surface is HEALTHY:
        return (40 + noise // 2, 110 + row_shade + noise, 30 + noise // 2)
    return (95 + noise // 2, 125 + row_shade + noise, 45 + noise // 2)  # paler, yellowish


def _png(rng: random.Random) -> bytes:
    rows = (b"\x00" + bytes(c for x in range(RGB_W) for c in _rgb(x, y, rng)) for y in range(RGB_H))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", RGB_W, RGB_H, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def write_scene(directory: Path) -> None:
    rng = random.Random(7)
    red, nir = _bands(rng)
    scene = {
        "acquired_on": "2026-10-28",
        "latitude": 2.95,
        "longitude": -75.3,
        "synthetic": True,
        "zones": {"Zona 1": [0.0, 0.0, 0.5, 1.0], "Zona 2": [0.5, 0.0, 1.0, 1.0]},
        "red": red,
        "nir": nir,
    }
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "scene.json").write_text(json.dumps(scene, separators=(",", ":")) + "\n")
    (directory / "rgb.png").write_bytes(_png(rng))


if __name__ == "__main__":
    sys.exit(write_scene(SCENE_DIR))
