"""config/imaging.yaml: the segmentation prompt (D059).

The low-NDVI threshold is per crop, in config/crops/*.yaml (D077).
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.errors import ConfigError


@dataclass(frozen=True)
class ImagingConfig:
    segmentation_prompt: str


class _ImagingFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segmentation_prompt: str = Field(min_length=1)


def load_imaging_config(path: Path) -> ImagingConfig:
    try:
        raw = _ImagingFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    return ImagingConfig(raw.segmentation_prompt)
