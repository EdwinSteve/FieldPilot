"""config/imaging.yaml: the low-NDVI threshold and the segmentation prompt (D059)."""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.errors import ConfigError


@dataclass(frozen=True)
class ImagingConfig:
    low_ndvi_threshold: float
    segmentation_prompt: str


class _ImagingFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    low_ndvi_threshold: float = Field(gt=-1, lt=1)
    segmentation_prompt: str = Field(min_length=1)


def load_imaging_config(path: Path) -> ImagingConfig:
    try:
        raw = _ImagingFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    return ImagingConfig(raw.low_ndvi_threshold, raw.segmentation_prompt)
