"""Satellite scenes from data/satellite/<scene>/scene.json and rgb.png (§4.9, D059).

A scene carries the red and near-infrared bands, an RGB image for
segmentation, and each zone's area as a normalized box keyed by zone name.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.errors import ConfigError
from app.satellite.ndvi import NormalizedBox, Raster

# Like the forecast fixtures: a plot this close uses the scene.
MAX_COORDINATE_DELTA_DEG = 0.1


@dataclass(frozen=True)
class Scene:
    scene_id: str  # the directory name
    acquired_on: date
    latitude: float
    longitude: float
    synthetic: bool
    zones: Mapping[str, NormalizedBox]
    red: Raster
    nir: Raster
    rgb_path: Path

    def rgb_png(self) -> bytes:
        return self.rgb_path.read_bytes()


class _SceneFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acquired_on: date
    latitude: float
    longitude: float
    synthetic: bool
    zones: dict[str, tuple[float, float, float, float]] = Field(min_length=1)
    red: list[list[float]] = Field(min_length=1)
    nir: list[list[float]] = Field(min_length=1)


class ImageryLoader:
    def __init__(self, scenes: Sequence[Scene]) -> None:
        self._scenes = tuple(scenes)

    @classmethod
    def from_directory(cls, directory: Path) -> "ImageryLoader":
        """Every `*/scene.json` under `directory`. A missing directory means no scenes."""
        files = sorted(directory.glob("*/scene.json")) if directory.is_dir() else []
        return cls([load_scene(path) for path in files])

    def latest(self, lat: float, lon: float, on_or_before: date) -> Scene | None:
        """The newest scene near the plot, taken on or before the day; None if there is none."""
        candidates = [
            scene
            for scene in self._scenes
            if scene.acquired_on <= on_or_before
            and abs(scene.latitude - lat) <= MAX_COORDINATE_DELTA_DEG
            and abs(scene.longitude - lon) <= MAX_COORDINATE_DELTA_DEG
        ]
        return max(candidates, key=lambda scene: scene.acquired_on, default=None)


def load_scene(path: Path) -> Scene:
    try:
        raw = _SceneFile.model_validate_json(path.read_text(encoding="utf-8"))
        zones = {name: NormalizedBox(*box) for name, box in raw.zones.items()}
    except (ValidationError, ValueError) as error:
        raise ConfigError(f"{path}: {error}") from error
    red, nir = _raster(raw.red), _raster(raw.nir)
    problems = _band_problems(red, nir)
    rgb = path.parent / "rgb.png"
    if not rgb.is_file():
        problems.append("rgb.png is missing")
    if problems:
        raise ConfigError(f"{path}: " + "; ".join(problems))
    return Scene(
        path.parent.name,
        raw.acquired_on,
        raw.latitude,
        raw.longitude,
        raw.synthetic,
        zones,
        red,
        nir,
        rgb,
    )


def _raster(rows: list[list[float]]) -> Raster:
    return tuple(tuple(row) for row in rows)


def _band_problems(red: Raster, nir: Raster) -> list[str]:
    problems = []
    widths = {len(row) for row in (*red, *nir)}
    if len(widths) != 1 or len(red) != len(nir):
        problems.append("red and nir must be rectangular and of the same shape")
    if any(not 0 <= value <= 1 for row in (*red, *nir) for value in row):
        problems.append("reflectance values must be within [0, 1]")
    return problems
